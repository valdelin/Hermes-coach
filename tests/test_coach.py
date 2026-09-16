import unittest
from datetime import date

from src.coach import (build_workout, decide_focus, estimate_tss,
                       last_ftp_test, latest_metrics, suggest_ftp_test,
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


if __name__ == "__main__":
    unittest.main()