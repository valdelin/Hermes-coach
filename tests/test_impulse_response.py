import unittest
import math
from datetime import date, timedelta

from src.impulse_response import (ImpulseResponseEngine, daily_tss_series,
                                  daily_load_by_date, fill_daily_series,
                                  forecast_pmc)


class CalculateTssTest(unittest.TestCase):
    def test_exemplo_60min_95pct(self):
        # Exemplo do doc de arquitetura: 60 min a 95% do limiar (threshold=1.0)
        engine = ImpulseResponseEngine()
        self.assertAlmostEqual(engine.calculate_tss(3600, 0.95, 1.0), 90.25)

    def test_potencia_em_watts(self):
        engine = ImpulseResponseEngine()
        # 1h a 160W com FTP 182W -> IF = 160/182 = 0.8791
        # TSS = IF^2 * 1h * 100 = 77.29 (round de 77.2853)
        self.assertAlmostEqual(engine.calculate_tss(3600, 160, 182), 77.29, places=2)

    def test_exemplo_do_plano(self):
        # 20 min a 60% do FTP (recuperacao de ontem no plan.json)
        engine = ImpulseResponseEngine()
        self.assertAlmostEqual(engine.calculate_tss(1200, 0.6, 1.0), 12.0)

    def test_threshold_invalido(self):
        engine = ImpulseResponseEngine()
        self.assertEqual(engine.calculate_tss(3600, 200, 0), 0.0)
        self.assertEqual(engine.calculate_tss(3600, 200, -1), 0.0)

    def test_intensidade_zero(self):
        engine = ImpulseResponseEngine()
        self.assertEqual(engine.calculate_tss(3600, 0, 200), 0.0)


class ComputeMetricsTest(unittest.TestCase):
    def test_historico_vazio(self):
        m = ImpulseResponseEngine().compute_metrics([])
        self.assertEqual(m["ctl_fitness"], 0.0)
        self.assertEqual(m["atl_fatigue"], 0.0)
        self.assertEqual(m["tsb_form"], 0.0)

    def test_um_dia(self):
        engine = ImpulseResponseEngine()
        m = engine.compute_metrics([42])
        # ctl = 42*(1-exp(-1/42)) ~= 0.99; atl = 42*(1-exp(-1/7)) ~= 5.59
        self.assertAlmostEqual(m["ctl_fitness"], 1.0, places=1)
        self.assertAlmostEqual(m["atl_fatigue"], 5.6, places=1)
        self.assertAlmostEqual(m["tsb_form"], -4.6, places=1)

    def test_serie_constante_converge(self):
        engine = ImpulseResponseEngine()
        m = engine.compute_metrics([100] * 500)
        self.assertAlmostEqual(m["ctl_fitness"], 100.0, delta=0.5)
        self.assertAlmostEqual(m["atl_fatigue"], 100.0, delta=0.5)
        self.assertAlmostEqual(m["tsb_form"], 0.0, delta=1.0)

    def test_tsb_eh_ctl_menos_atl(self):
        # Exemplo do doc de arquitetura (14 dias)
        series = [45, 60, 0, 80, 50, 90, 0, 40, 70, 0, 85, 60, 100, 0]
        m = ImpulseResponseEngine().compute_metrics(series)
        self.assertAlmostEqual(m["tsb_form"], m["ctl_fitness"] - m["atl_fatigue"],
                               delta=0.2)
        # historico recente de treino -> ATL > CTL (TSB negativo)
        self.assertLess(m["tsb_form"], 0)

    def test_constantes_personalizadas(self):
        engine = ImpulseResponseEngine(ctl_time_constant=10, atl_time_constant=3)
        m = engine.compute_metrics([100] * 200)
        self.assertAlmostEqual(m["ctl_fitness"], 100.0, delta=0.5)
        self.assertAlmostEqual(m["atl_fatigue"], 100.0, delta=0.5)

    def test_valores_iniciais_projecao(self):
        # Partindo de um estado atual, aplicar carga futura atualiza o TSB
        engine = ImpulseResponseEngine()
        m = engine.compute_metrics([40, 40, 40], initial_ctl=17.4, initial_atl=16.5)
        self.assertGreater(m["ctl_fitness"], 17.4)
        self.assertGreater(m["atl_fatigue"], 16.5)
        self.assertNotAlmostEqual(m["tsb_form"], 17.4 - 16.5, places=1)


class DailyTssSeriesTest(unittest.TestCase):
    def test_agrega_por_dia_e_ordena(self):
        events = [
            {"start_date_local": "2026-09-01T07:00:00", "icu_training_load": "40"},
            {"start_date_local": "2026-09-01T18:00:00", "tss": "20"},
            {"start_date_local": "2026-09-03T07:00:00", "tss": "50"},
            {"start_date_local": "2026-09-02T07:00:00", "icu_training_load": "30"},
            {"no-load": True},
        ]
        series = daily_tss_series(events, window_days=60, today=date(2026, 9, 10))
        self.assertEqual(series, [60.0, 30.0, 50.0])

    def test_respeita_janela(self):
        events = [
            {"start_date_local": "2026-06-01T07:00:00", "tss": "99"},  # fora (30d)
            {"start_date_local": "2026-09-01T07:00:00", "tss": "50"},
            {"start_date_local": "2026-09-12T07:00:00", "tss": "70"},  # futuro/hoje+2
        ]
        series = daily_tss_series(events, window_days=30, today=date(2026, 9, 10))
        self.assertEqual(series, [50.0])

    def test_desconsidera_sem_carga(self):
        events = [
            {"start_date_local": "2026-09-01T07:00:00"},
            {"start_date_local": "2026-09-02T07:00:00", "icu_training_load": None},
            {"day": "2026-09-03", "tss": "0"},
        ]
        series = daily_tss_series(events, window_days=60, today=date(2026, 9, 10))
        self.assertEqual(series, [])


class DailyLoadByDateTest(unittest.TestCase):
    def test_mapa_por_data(self):
        events = [
            {"start_date_local": "2026-09-01T07:00:00", "icu_training_load": "40"},
            {"start_date_local": "2026-09-01T18:00:00", "tss": "20"},
            {"start_date_local": "2026-09-03T07:00:00", "tss": "50"},
            {"no-load": True},
        ]
        m = daily_load_by_date(events, window_days=60, today=date(2026, 9, 10))
        self.assertEqual(m[date(2026, 9, 1)], 60.0)
        self.assertEqual(m[date(2026, 9, 3)], 50.0)
        self.assertEqual(len(m), 2, "dias sem carga nao entram no mapa")

    def test_respeita_janela(self):
        events = [
            {"start_date_local": "2026-06-01T07:00:00", "tss": "99"},
            {"day": "2026-09-05", "tss": "30"},
        ]
        m = daily_load_by_date(events, window_days=30, today=date(2026, 9, 10))
        self.assertEqual(m, {date(2026, 9, 5): 30.0})


class FillDailySeriesTest(unittest.TestCase):
    def test_preenche_zeros_entre_dias_com_carga(self):
        by_day = {
            date(2026, 9, 1): 50.0,
            date(2026, 9, 3): 80.0,
        }
        series = fill_daily_series(by_day, date(2026, 9, 1), date(2026, 9, 4))
        self.assertEqual(series, [50.0, 0.0, 80.0, 0.0])

    def test_extremidades_inclusivas(self):
        by_day = {date(2026, 9, 2): 30.0}
        series = fill_daily_series(by_day, date(2026, 9, 2), date(2026, 9, 2))
        self.assertEqual(series, [30.0])

    def test_dia_unicamente_sem_carga(self):
        series = fill_daily_series({}, date(2026, 9, 5), date(2026, 9, 5))
        self.assertEqual(series, [0.0])

    def test_intervalo_invertido_vazio(self):
        series = fill_daily_series({}, date(2026, 9, 5), date(2026, 9, 1))
        self.assertEqual(series, [])


class ForecastPmcTest(unittest.TestCase):
    TODAY = date(2026, 9, 10)

    def _plan(self, pairs):
        return [{"day": day, "tss": tss} for day, tss in pairs]

    def test_serie_comeca_em_hoje_com_estado_inicial(self):
        plan = self._plan([("2026-09-11", 100), ("2026-09-12", 100)])
        fc = forecast_pmc([], plan, initial_ctl=50.0, initial_atl=40.0,
                          today=self.TODAY)
        self.assertEqual(fc["series"][0]["day"], "2026-09-10")
        self.assertEqual(fc["series"][0]["ctl"], 50.0)
        self.assertEqual(fc["series"][0]["atl"], 40.0)
        self.assertEqual(fc["series"][0]["tsb"], 10.0)
        self.assertEqual(fc["series"][-1]["day"], "2026-09-12")
        self.assertEqual(fc["end"]["tsb_form"], fc["series"][-1]["tsb"])

    def test_aplica_carga_esperada_no_primeiro_dia(self):
        plan = self._plan([("2026-09-11", 100)])
        fc = forecast_pmc([], plan, initial_ctl=0.0, initial_atl=0.0,
                          today=self.TODAY)
        row = fc["series"][1]
        self.assertEqual(row["day"], "2026-09-11")
        self.assertAlmostEqual(row["ctl"],
                               round(100 * (1 - math.exp(-1 / 42)), 1), places=1)
        self.assertAlmostEqual(row["atl"],
                               round(100 * (1 - math.exp(-1 / 7)), 1), places=1)

    def test_dia_de_descanso_decai_atl(self):
        plan = self._plan([("2026-09-11", 200), ("2026-09-12", 0),
                           ("2026-09-13", 200)])
        fc = forecast_pmc([], plan, initial_ctl=0.0, initial_atl=0.0,
                          today=self.TODAY)
        by_day = {r["day"]: r for r in fc["series"]}
        self.assertGreater(by_day["2026-09-12"]["atl"], 0.0)
        self.assertLess(by_day["2026-09-12"]["atl"],
                        by_day["2026-09-11"]["atl"],
                        "zero no dia -> ATL decai em vez de subir")

    def test_multiplos_treinos_no_mesmo_dia_somam(self):
        plan = [{"day": "2026-09-11", "tss": 100},
                {"day": "2026-09-11", "tss": 50}]
        fc = forecast_pmc([], plan, initial_ctl=0.0, initial_atl=0.0,
                          today=self.TODAY)
        row = fc["series"][1]
        self.assertAlmostEqual(row["atl"],
                               round(150 * (1 - math.exp(-1 / 7)), 1), places=1)

    def test_horizonte_limita_projecao(self):
        plan = self._plan([("2026-09-11", 100), ("2026-09-13", 100)])
        fc = forecast_pmc([], plan, initial_ctl=10.0, initial_atl=10.0,
                          today=self.TODAY, horizon=date(2026, 9, 12))
        self.assertEqual(fc["series"][-1]["day"], "2026-09-12")

    def test_plano_vazio_retorna_sem_serie(self):
        fc = forecast_pmc([], [], initial_ctl=10.0, initial_atl=10.0,
                          today=self.TODAY)
        self.assertEqual(fc["series"], [])
        self.assertIsNone(fc["end"])

    def test_sem_estado_inicial_usa_historico_real(self):
        events = [{"day": "2026-09-09", "tss": "100"}]
        plan = self._plan([("2026-09-11", 100)])
        fc = forecast_pmc(events, plan, today=self.TODAY)
        self.assertGreater(fc["series"][0]["ctl"], 0.0,
                           "historico real (mesmo 1 dia) alimenta o estado atual")
        self.assertEqual(fc["series"][-1]["day"], "2026-09-11")

    def test_alerta_tsb_baixo(self):
        plan = self._plan([("2026-09-11", 1000)])
        fc = forecast_pmc([], plan, initial_ctl=50.0, initial_atl=5.0,
                          today=self.TODAY)
        self.assertTrue(fc["alerts"], "carga enorme deve cruzar TSB <= -10")
        self.assertEqual(fc["alerts"][0]["day"], "2026-09-11")
        self.assertLessEqual(fc["alerts"][0]["tsb"], -10.0)

    def test_zona_risco_alto(self):
        """Friel: TSB < -30 classifica como high-risk e vira indicador #17."""
        plan = self._plan([("2026-09-11", 1000)])
        fc = forecast_pmc([], plan, initial_ctl=50.0, initial_atl=5.0,
                          today=self.TODAY)
        self.assertTrue(fc["high_risk"], "TSB < -30 deve aparecer em high_risk")
        self.assertEqual(fc["high_risk"][0]["day"], "2026-09-11")
        self.assertLess(fc["high_risk"][0]["tsb"], -30.0)
        self.assertEqual(fc["series"][1]["zone"], "high-risk")
        self.assertEqual([r["day"] for r in fc["transition"]],
                         ["2026-09-10"],
                         "estado inicial (TSB 45) cai em transition; cargas a frente nao")

    def test_zona_transicao(self):
        """Friel: TSB > +25 classifica como transition (descanso longo)."""
        plan = self._plan([("2026-09-11", 10), ("2026-09-12", 10)])
        fc = forecast_pmc([], plan, initial_ctl=60.0, initial_atl=10.0,
                          today=self.TODAY)
        self.assertTrue(fc["transition"], "TSB alto e estável deve ficar > +25")
        for r in fc["transition"]:
            self.assertGreater(r["tsb"], 25.0)
        self.assertTrue(all(row["zone"] == "transition"
                            for row in fc["series"]))
        self.assertEqual(fc["high_risk"], [])

    def test_zonas_intermediarias(self):
        """Bordas Friel: -30..-10 optimal, -10..+5 grey, +5..25 freshness."""
        plan = self._plan([("2026-09-11", 100)])
        fc = forecast_pmc([], plan, initial_ctl=30.0, initial_atl=20.0,
                          today=self.TODAY)
        today_row = fc["series"][0]
        self.assertEqual(today_row["tsb"], 10.0)
        self.assertEqual(today_row["zone"], "freshness",
                         "TSB 10 esta na zona de frescor (+5..+25)")
        self.assertEqual(fc["alerts"], [])
        self.assertEqual(fc["high_risk"], [])
        self.assertEqual(fc["transition"], [])

    def test_plano_vazio_zonas_vazias(self):
        fc = forecast_pmc([], [], initial_ctl=10.0, initial_atl=10.0,
                          today=self.TODAY)
        self.assertEqual(fc["high_risk"], [])
        self.assertEqual(fc["transition"], [])


if __name__ == "__main__":
    unittest.main()