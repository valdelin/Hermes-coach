import unittest
from datetime import date

from src.coach import (build_workout, decide_focus, estimate_tss,
                       last_ftp_test, latest_metrics, suggest_ftp_test,
                       wellness_summary, format_wellness,
                       FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2,
                       FOCUS_ZONE2, Metrics)


class DecideFocusTest(unittest.TestCase):
    def test_limites_de_tsb(self):
        self.assertEqual(decide_focus(-20), FOCUS_ZONE2)
        self.assertEqual(decide_focus(-10), FOCUS_SWEETSPOT)
        self.assertEqual(decide_focus(0), FOCUS_THRESHOLD)
        self.assertEqual(decide_focus(7), FOCUS_VO2)

    def test_fronteiras(self):
        self.assertEqual(decide_focus(-15), FOCUS_SWEETSPOT)
        self.assertEqual(decide_focus(-5), FOCUS_THRESHOLD)
        self.assertEqual(decide_focus(5), FOCUS_VO2)


class LatestMetricsTest(unittest.TestCase):
    def test_pega_npc_mais_recente_por_data(self):
        events = [
            {"start_time_local": "2026-09-10", "summary": {"tsb": "-30", "ctl": "40", "atl": "70", "tss": "50"}},
            {"start_time_local": "2026-09-12", "tsb": "-8", "ctl": "55", "atl": "63", "tss": "60"},
            {"no-metrics": True},
        ]
        m = latest_metrics(events)
        self.assertIsInstance(m, Metrics)
        self.assertEqual(m.tsb, -8)
        self.assertEqual(m.tss, 60)

    def test_vazio(self):
        self.assertIsNone(latest_metrics([]))

    def test_tsb_calculado_de_icu_ctl_atl(self):
        events = [
            {"start_date_local": "2026-09-10T07:00:00",
             "icu_ctl": "18.65", "icu_atl": "23.15", "icu_training_load": "40"},
        ]
        m = latest_metrics(events)
        self.assertAlmostEqual(m.tsb, -4.5)
        self.assertEqual(m.tss, 40)


class TssTest(unittest.TestCase):
    def test_zona_2_estimado(self):
        p = build_workout(-20, 200)
        self.assertGreater(estimate_tss(p, 200), 0)


class FtpTestSuggestionTest(unittest.TestCase):
    def test_detecta_ramp_test_no_nome(self):
        events = [
            {"name": "Ramp Test", "start_date_local": "2026-07-01T07:00:00"},
            {"name": "2026-09-10 - Treino de Zona 2", "start_date_local": "2026-09-10T07:00:00"},
        ]
        self.assertEqual(last_ftp_test(events), "2026-07-01")

    def test_nenhum_teste_detectado(self):
        self.assertIsNone(last_ftp_test([]))
        self.assertIsNone(last_ftp_test([{"name": "Treino de Zona 2", "day": "2026-09-01"}]))

    def test_fora_da_janela_sugere_reteste(self):
        events = [{"name": "Ramp Test", "start_date_local": "2026-06-01T07:00:00"}]
        sug = suggest_ftp_test(events, 200, weeks=8, today=date(2026, 9, 1))
        self.assertTrue(sug.due)
        self.assertEqual(sug.days_since, 92)

    def test_dentro_da_janela_nao_sugere(self):
        events = [{"name": "Ramp Test", "start_date_local": "2026-08-01T07:00:00"}]
        sug = suggest_ftp_test(events, 200, weeks=8, today=date(2026, 9, 1))
        self.assertFalse(sug.due)
        self.assertEqual(sug.days_since, 31)

    def test_sem_teste_e_historico_curto_nao_sugere(self):
        events = [{"name": "Treino de Zona 2", "day": "2026-08-20"}]
        sug = suggest_ftp_test(events, 200, weeks=8, today=date(2026, 9, 1))
        self.assertFalse(sug.due)

    def test_sem_teste_e_historico_longo_sugere(self):
        events = [{"name": "Treino de Zona 2", "day": "2026-01-10"},
                  {"name": "Treino de Sweet Spot", "day": "2026-01-12"}]
        sug = suggest_ftp_test(events, 200, weeks=8, today=date(2026, 9, 1))
        self.assertTrue(sug.due)

    def test_janela_ftp_builder_seis_semanas(self):
        events = [{"name": "Ramp Test", "start_date_local": "2026-08-01T07:00:00"}]
        sug = suggest_ftp_test(events, 200, today=date(2026, 9, 1), goal="ftp-builder")
        self.assertFalse(sug.due)  # 31 dias < 42 (6 semanas)
        self.assertIn("janela de 6 semanas", sug.reason)
        # ao final do bloco (>= 6 semanas) sugere
        events = [{"name": "Ramp Test", "start_date_local": "2026-07-20T07:00:00"}]
        sug = suggest_ftp_test(events, 200, today=date(2026, 9, 1), goal="ftp-builder")
        self.assertTrue(sug.due)  # 43 dias >= 42
        self.assertIn("6 semanas", sug.reason)

    def test_janela_time_trial_quatro_semanas(self):
        events = [{"name": "Ramp Test", "start_date_local": "2026-08-10T07:00:00"}]
        sug = suggest_ftp_test(events, 200, today=date(2026, 9, 1), goal="time-trial")
        self.assertFalse(sug.due)  # 22 dias < 28 (4 semanas)
        self.assertIn("janela de 4 semanas", sug.reason)

    def test_janela_time_trial_quatro_semanas_due(self):
        events = [{"name": "Ramp Test", "start_date_local": "2026-08-01T07:00:00"}]
        sug = suggest_ftp_test(events, 200, today=date(2026, 9, 1), goal="time-trial")
        self.assertTrue(sug.due)  # 31 dias >= 28
        self.assertIn("4 semanas", sug.reason)

    def test_sem_goal_mantem_oito_semanas(self):
        events = [{"name": "Ramp Test", "start_date_local": "2026-07-10T07:00:00"}]
        sug = suggest_ftp_test(events, 200, today=date(2026, 9, 1))  # goal=None
        self.assertFalse(sug.due)  # 53 dias < 56 (8 semanas)
        self.assertIn("janela de 8 semanas", sug.reason)

    def test_sem_goal_mantem_oito_semanas_due(self):
        events = [{"name": "Ramp Test", "start_date_local": "2026-07-01T07:00:00"}]
        sug = suggest_ftp_test(events, 200, today=date(2026, 9, 1))  # goal=None
        self.assertTrue(sug.due)  # 62 dias >= 56
        self.assertIn("8 semanas", sug.reason)


class WellnessSummaryTest(unittest.TestCase):
    """Issue #4: expor RHR/sono/HRV do sync Garmin -> Intervals no info."""

    def _records(self):
        return [
            {"id": "2026-09-12", "restingHR": 50, "sleepSecs": 28740, "steps": 9060},
            {"id": "2026-09-13", "restingHR": 49, "sleepSecs": 30600, "steps": 4828},
            {"id": "2026-09-14", "restingHR": 51, "sleepSecs": 18360, "steps": 3483},
            {"id": "2026-09-15", "restingHR": 54, "sleepSecs": 20040, "steps": 4551},
            {"id": "2026-09-16", "restingHR": 54, "sleepSecs": 18180, "steps": 6790},
            {"id": "2026-09-17", "restingHR": 55, "sleepSecs": 27120, "steps": 1548},
        ]

    def test_valores_ultimo_e_media(self):
        s = wellness_summary(self._records(), days=7)
        self.assertIsNotNone(s)
        self.assertEqual(s["resting_hr_last"], 55.0)
        self.assertEqual(s["resting_hr_avg"], 52.166666666666664)
        self.assertEqual(s["sleep_hours_last"], 7.5)   # 27120s / 3600
        self.assertEqual(s["steps_last"], 1548.0)

    def test_hrv_ausente_fica_none(self):
        s = wellness_summary(self._records())
        self.assertIsNone(s["hrv_last"])
        self.assertIn("HRV sem dados (FR935)", format_wellness(s))

    def test_hrv_presente_quando_dado_existe(self):
        recs = self._records() + [{"id": "2026-09-18", "hrv": 62, "hrvSDNN": 45}]
        s = wellness_summary(recs)
        self.assertEqual(s["hrv_last"], 62.0)
        self.assertIn("HRV 62ms", format_wellness(s))

    def test_vazio_retorna_none(self):
        self.assertIsNone(wellness_summary([]))
        self.assertIsNone(wellness_summary([{"x": 1}]))
        self.assertEqual(format_wellness(None),
                         "sem dados (sync Garmin -> Intervals pendente)")

    def test_respeita_janela_de_dias(self):
        s = wellness_summary(self._records(), days=3)
        self.assertEqual(s["days"], 3)
        self.assertEqual(s["resting_hr_last"], 55.0)
        self.assertEqual(s["resting_hr_avg"], 54.333333333333336)  # 54,54,55


if __name__ == "__main__":
    unittest.main()