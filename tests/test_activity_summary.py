import unittest
from datetime import date

from src import activity_summary as s


class _DoneClient:
    """2 treinos feitos + 1 planejado-nao-feito (fica fora)."""

    def events(self, **params):
        return [
            {"id": "ev1", "paired_activity_id": "i1",
             "start_date_local": "2026-09-22T19:00:00", "name": "Z1"},
            {"id": "ev2", "paired_activity_id": "i2",
             "start_date_local": "2026-09-23T15:37:38", "name": "Limiar"},
            {"id": "ev3", "start_date_local": "2026-09-24T07:30:00",
             "name": "nao feito"},
        ]

    def activity(self, aid):
        if aid == "i1":
            return {"name": "Zwift - Z1", "type": "VirtualRide",
                    "moving_time": 2400, "distance": 15000.0,
                    "total_elevation_gain": 50.0, "icu_training_load": 20,
                    "icu_average_watts": 90, "icu_weighted_avg_watts": 95,
                    "average_heartrate": 120}
        return {"name": "Zwift - Limiar", "type": "VirtualRide",
                "moving_time": 3225, "distance": 24732.67,
                "total_elevation_gain": 175.0, "icu_training_load": 58,
                "icu_average_watts": 133, "icu_weighted_avg_watts": 147,
                "average_heartrate": 153}


class PeriodRangeTest(unittest.TestCase):
    def test_dia_e_o_proprio_dia(self):
        self.assertEqual(s.period_range(date(2026, 9, 23), "day"),
                         (date(2026, 9, 23), date(2026, 9, 23)))

    def test_semana_sao_7_dias_terminando_no_ancla(self):
        self.assertEqual(s.period_range(date(2026, 9, 23), "week"),
                         (date(2026, 9, 17), date(2026, 9, 23)))

    def test_mes_sao_30_dias_terminando_no_ancla(self):
        self.assertEqual(s.period_range(date(2026, 9, 23), "month"),
                         (date(2026, 8, 25), date(2026, 9, 23)))

    def test_trimestre_sao_90_dias_terminando_no_ancla(self):
        self.assertEqual(s.period_range(date(2026, 9, 23), "quarter"),
                         (date(2026, 6, 26), date(2026, 9, 23)))

    def test_semestre_sao_180_dias_terminando_no_ancla(self):
        self.assertEqual(s.period_range(date(2026, 9, 23), "semester"),
                         (date(2026, 3, 28), date(2026, 9, 23)))

    def test_ano_sao_365_dias_terminando_no_ancla(self):
        self.assertEqual(s.period_range(date(2026, 9, 23), "year"),
                         (date(2025, 9, 24), date(2026, 9, 23)))

    def test_periodo_invalido_rejeitado(self):
        with self.assertRaises(ValueError):
            s.period_range(date(2026, 9, 23), "ano")


class ResolvePeriodTest(unittest.TestCase):
    ANCHOR = date(2026, 9, 23)

    def test_duracao_livre_de_dias(self):
        self.assertEqual(s.resolve_period(self.ANCHOR, "45d"),
                         (date(2026, 8, 10), self.ANCHOR))

    def test_duracao_livre_de_meses(self):
        self.assertEqual(s.resolve_period(self.ANCHOR, "6m"),
                         (date(2026, 3, 28), self.ANCHOR))

    def test_duracao_livre_de_anos(self):
        self.assertEqual(s.resolve_period(self.ANCHOR, "1y"),
                         (date(2025, 9, 24), self.ANCHOR))

    def test_nome_fixo_delega_ao_period_range(self):
        self.assertEqual(s.resolve_period(self.ANCHOR, "week"),
                         (date(2026, 9, 17), self.ANCHOR))

    def test_plan_usa_a_janela_dos_dias_do_plano(self):
        days = [date(2026, 9, 14), date(2026, 9, 16), date(2026, 9, 21)]
        self.assertEqual(s.resolve_period(self.ANCHOR, "plan", plan_days=days),
                         (date(2026, 9, 14), date(2026, 9, 21)))

    def test_plan_sem_dias_rejeitado(self):
        with self.assertRaises(ValueError):
            s.resolve_period(self.ANCHOR, "plan")

    def test_custom_usa_start_end(self):
        self.assertEqual(
            s.resolve_period(self.ANCHOR, "custom",
                             start="2026-06-01", end="2026-08-31"),
            (date(2026, 6, 1), date(2026, 8, 31)))

    def test_custom_sem_start_rejeitado(self):
        with self.assertRaises(ValueError):
            s.resolve_period(self.ANCHOR, "custom", end="2026-08-31")


class PeriodLabelTest(unittest.TestCase):
    def test_nome_fixo(self):
        self.assertEqual(s.period_label("semester"), "semestre")

    def test_duracao_singular(self):
        self.assertEqual(s.period_label("1y"), "1 ano")

    def test_duracao_plural(self):
        self.assertEqual(s.period_label("6m"), "6 meses")

    def test_desconhecido_retorna_o_proprio(self):
        self.assertEqual(s.period_label("xyz"), "xyz")


class DoneActivitiesTest(unittest.TestCase):
    def test_conta_apenas_treinos_feitos(self):
        rows = s.done_activities(_DoneClient(), date(2026, 9, 22),
                                 date(2026, 9, 24))
        self.assertEqual(len(rows), 2)
        self.assertEqual([r["name"] for r in rows],
                         ["Zwift - Z1", "Zwift - Limiar"])

    def test_carrega_agregados_por_linha(self):
        rows = s.done_activities(_DoneClient(), date(2026, 9, 22),
                                 date(2026, 9, 24))
        limiar = rows[1]
        self.assertEqual(limiar["day"], "2026-09-23")
        self.assertEqual(limiar["time_s"], 3225)
        self.assertAlmostEqual(limiar["distance_m"], 24732.67)
        self.assertEqual(limiar["load"], 58.0)
        self.assertEqual(limiar["avg_power"], 133)


class SummarizeTest(unittest.TestCase):
    def test_totais_e_medias_ponderadas_por_tempo(self):
        rows = s.done_activities(_DoneClient(), date(2026, 9, 22),
                                 date(2026, 9, 24))
        agg = s.summarize(rows)
        self.assertEqual(agg["sessions"], 2)
        self.assertEqual(agg["time_s"], 2400 + 3225)
        self.assertAlmostEqual(agg["load"], 78.0)
        self.assertAlmostEqual(agg["distance_m"], 39732.67)
        expected_power = (90 * 2400 + 133 * 3225) / (2400 + 3225)
        self.assertAlmostEqual(agg["avg_power"], expected_power)
        expected_hr = (120 * 2400 + 153 * 3225) / (2400 + 3225)
        self.assertAlmostEqual(agg["avg_hr"], expected_hr)

    def test_sem_treinos_nao_quebra(self):
        agg = s.summarize([])
        self.assertEqual(agg["sessions"], 0)
        self.assertEqual(agg["time_s"], 0)
        self.assertIsNone(agg.get("avg_power"))


class FmtTest(unittest.TestCase):
    def test_fmt_time(self):
        self.assertEqual(s.fmt_time(3600), "1h00")
        self.assertEqual(s.fmt_time(3225), "53m45")
        self.assertEqual(s.fmt_time(45), "45s")

    def test_fmt_dist(self):
        self.assertEqual(s.fmt_dist(24732.67), "24.7 km")
        self.assertEqual(s.fmt_dist(800), "800 m")


class WeightedAvgTest(unittest.TestCase):
    def test_ignora_linhas_sem_valor(self):
        rows = [
            {"time_s": 100, "avg_power": 100},
            {"time_s": 300, "avg_power": None},
        ]
        self.assertAlmostEqual(s._weighted_avg(rows, "avg_power"), 100.0)

    def test_none_sem_valores(self):
        self.assertIsNone(s._weighted_avg([{"time_s": 10, "x": None}], "x"))


if __name__ == "__main__":
    unittest.main()