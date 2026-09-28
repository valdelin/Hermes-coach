import math
import unittest
from datetime import date, timedelta

from src import recovery


def _ride(day, load, done=True, _id=None):
    e = {
        "id": _id or ("r" + day.isoformat()),
        "start_date_local": day.isoformat() + "T00:00:00",
        "icu_training_load": load,
        "name": f"treino {day}",
    }
    if done:
        e["paired_activity_id"] = "p" + day.isoformat()
    return e


class ActualDailyLoadTest(unittest.TestCase):
    def test_conta_apenas_treinos_feitos(self):
        d1 = date(2026, 9, 1)
        d2 = date(2026, 9, 2)
        events = [
            _ride(d1, 50, done=True),
            _ride(d1, 10, done=True),      # segundo treino no mesmo dia
            _ride(d2, 70, done=False),     # planejado nao-feito: fora
            {"id": "x", "start_date_local": d2.isoformat() + "T00:00:00",
             "tss": 30},                   # sem pareamento: fora
        ]
        daily = recovery.actual_daily_load(events)
        self.assertEqual(daily, {d1: 60.0})

    def test_ignora_carga_invalida(self):
        events = [
            {"id": "1", "start_date_local": "2026-09-01T00:00:00",
             "paired_activity_id": "p1", "icu_training_load": None},
            {"id": "2", "start_date_local": "2026-09-02T00:00:00",
             "paired_activity_id": "p2", "icu_training_load": -5},
            {"id": "3", "start_date_local": "2026-09-03T00:00:00",
             "paired_activity_id": "p3", "icu_training_load": "abc"},
        ]
        daily = recovery.actual_daily_load(events)
        self.assertEqual(daily, {})


class PmcSeriesTest(unittest.TestCase):

    def test_serie_vazia_para_sem_dados(self):
        self.assertEqual(recovery.pmc_series({}), [])

    def test_faz_serie_por_cada_dia_do_historico(self):
        d0 = date.today() - timedelta(days=30)
        daily = {d0: 50.0}
        rows = recovery.pmc_series(daily)
        self.assertEqual(len(rows), 31)
        self.assertEqual(rows[0][0], d0)
        self.assertEqual(rows[-1][0], date.today())

    def test_converge_para_carga_constante(self):
        # carga constante 30/dia -> CTL converge para ~30 (EWMA 42)
        today = date.today()
        d0 = today - timedelta(days=400)
        daily = {d0 + timedelta(days=i): 30.0 for i in range(401)}
        rows = recovery.pmc_series(daily)
        self.assertGreater(rows[-1][1], 29.5)
        self.assertLess(rows[-1][1], 30.5)

    def test_hiato_faz_ctl_decair(self):
        today = date.today()
        d0 = today - timedelta(days=200)
        daily = {d0 + timedelta(days=i): 30.0 for i in range(150)}
        rows = recovery.pmc_series(daily)
        after = rows[-1][1]
        # 50 dias de zero depois de 150 de carga: CTL bem abaixo do platô de 30
        self.assertLess(after, 20.0)
        self.assertGreater(after, 5.0)


class PmcSeriesAnchoredTest(unittest.TestCase):
    """A serie ancorada parte dos valores REAIS do Intervals (sem cold-start),
    decaindo EWMA com TSS 0 entre os dias de treino."""

    def test_vazio_sem_valores_reais(self):
        self.assertEqual(recovery.pmc_series_anchored({}, date(2026, 9, 1),
                                                      date(2026, 9, 30)), [])

    def test_parte_do_primeiro_valor_real_sem_zero(self):
        d0 = date(2026, 9, 10)
        rows = recovery.pmc_series_anchored({d0: (40.0, 20.0)},
                                            date(2026, 9, 1), d0)
        # comeca no dia do primeiro treino com o CTL/ATL reais (NAO em zero)
        self.assertEqual(rows[0][0], d0)
        self.assertEqual(rows[0][1], 40.0)
        self.assertEqual(rows[0][2], 20.0)

    def test_decai_no_zero_como_ewma_42_7(self):
        d0 = date(2026, 9, 10)
        rows = recovery.pmc_series_anchored({d0: (40.0, 20.0)},
                                            d0, date(2026, 9, 20))
        # 10 dias sem treino: CTL decai tau 42, ATL tau 7
        kc = 1 - math.exp(-1 / 42)
        ka = 1 - math.exp(-1 / 7)
        self.assertAlmostEqual(rows[-1][1], 40.0 * (1 - kc) ** 10, places=6)
        self.assertAlmostEqual(rows[-1][2], 20.0 * (1 - ka) ** 10, places=3)

    def test_dia_com_valor_real_ancora_direto(self):
        d0 = date(2026, 9, 1)
        d1 = date(2026, 9, 5)
        real = {d0: (40.0, 20.0), d1: (50.0, 60.0)}
        rows = recovery.pmc_series_anchored(real, d0, d1)
        # no dia do segundo treino, usa o CTL/ATL reais, sem decair
        self.assertEqual(rows[-1][1], 50.0)
        self.assertEqual(rows[-1][2], 60.0)
        # dias intermediarios decaem a partir do primeiro valor real
        kc = 1 - math.exp(-1 / 42)
        ka = 1 - math.exp(-1 / 7)
        self.assertAlmostEqual(rows[1][1], 40.0 * (1 - kc), places=6)
        self.assertAlmostEqual(rows[1][2], 20.0 * (1 - ka), places=6)
        self.assertAlmostEqual(rows[3][1], 40.0 * (1 - kc) ** 3, places=6)

    def test_janela_anterior_ao_primeiro_valor_nao_vira_zero(self):
        d0 = date(2026, 9, 10)
        rows = recovery.pmc_series_anchored({d0: (40.0, 20.0)},
                                            date(2026, 9, 1), d0)
        self.assertEqual(len(rows), 1)  # so o dia com valor real
        self.assertEqual(rows[0][1], 40.0)


class StateTest(unittest.TestCase):
    def test_resumo_do_pico_de_ctl(self):
        d0 = date(2026, 1, 1)
        rows = [(d0 + timedelta(days=i), i * 1.0, 5.0, i * 1.0 - 5.0)
                for i in range(60)]
        st = recovery.state(rows)
        self.assertEqual(st["peak_ctl"], 59.0)
        self.assertEqual(st["peak_ctl_day"], d0 + timedelta(days=59))
        self.assertEqual(st["current_ctl"], 59.0)
        # pico de TSB na extremidade (maior ctl - 5)
        self.assertEqual(st["peak_tsb"], 54.0)
        # melhor janela de 30 dias = ultimos 30 (media de 30..59 = 44.5)
        self.assertAlmostEqual(st["window_avg"], 44.5, places=3)

    def test_none_sem_dados(self):
        self.assertIsNone(recovery.state([]))


class EstimateReturnTest(unittest.TestCase):
    def test_ate_99_nao_antes_de_90(self):
        r = recovery.estimate_return(10, 15, 40, 80, ramp_pts=9)
        self.assertIsNotNone(r["weeks_90"])
        self.assertIsNotNone(r["weeks_99"])
        self.assertGreaterEqual(r["weeks_99"], r["weeks_90"])

    def test_rampa_maior_nunca_mais_lenta(self):
        a = recovery.estimate_return(10, 15, 40, 80, ramp_pts=6)
        b = recovery.estimate_return(10, 15, 40, 80, ramp_pts=12)
        self.assertLessEqual(b["weeks_99"], a["weeks_99"])

    def test_ja_na_meta_vira_zero(self):
        r = recovery.estimate_return(50, 50, 40, 300, ramp_pts=9)
        self.assertEqual(r["weeks_99"], 0)

    def test_horizonte_curto_nao_atinge(self):
        r = recovery.estimate_return(5, 30, 60, 50, ramp_pts=9,
                                     max_weeks=4)
        self.assertIsNone(r["weeks_90"])
        self.assertIsNone(r["weeks_99"])

    def test_teto_de_volume_igual_a_ctl_x_7(self):
        r = recovery.estimate_return(5, 5, 40, 50, ramp_pts=9)
        self.assertEqual(r["target_weekly"], 280)


class RampScheduleTest(unittest.TestCase):
    def test_primeira_semana_igual_ao_volume_atual(self):
        sched = recovery.ramp_schedule(target_ctl=50, weekly_now=80,
                                       ramp_pts=9, weeks=6)
        self.assertEqual(sched[0], 80.0)
        self.assertEqual(len(sched), 6)

    def test_deload_a_cada_4_semanas(self):
        sched = recovery.ramp_schedule(target_ctl=200, weekly_now=100,
                                       ramp_pts=10, weeks=8)
        # semanas 4 e 8 (deload) menores que a anterior nao-tambem-deload
        self.assertLess(sched[3], sched[2])
        self.assertLess(sched[7], sched[6])

    def test_nunca_ultrapassa_o_teto_do_ctl_alvo(self):
        target = 40.0
        sched = recovery.ramp_schedule(target_ctl=target, weekly_now=200,
                                       ramp_pts=50, weeks=12)
        self.assertLessEqual(max(sched), target * 7 + 0.1)


if __name__ == "__main__":
    unittest.main()