"""Projeção de vínculos entre eventos e atividades do calendário."""

import unittest

from src.ui.history import link_activities, historical_power_steps


class ActivityLinksTest(unittest.TestCase):
    def test_execucao_tardia_e_manual_duplicado(self):
        events = [{"id": 42, "start_date_local": "2026-11-02T07:30:00",
                   "paired_activity_id": "fit"}]
        activities = [
            {"id": "manual", "source": "MANUAL", "paired_event_id": 42,
             "start_date_local": "2026-11-02T07:30:00"},
            {"id": "fit", "source": "UPLOAD", "paired_event_id": 42,
             "start_date_local": "2026-11-03T20:31:00"},
        ]
        result = link_activities(events, activities)
        self.assertEqual([a["id"] for a in result.activities], ["fit"])
        self.assertEqual(result.event_activity["42"], "fit")
        self.assertEqual(result.activity_event["fit"], "42")

    def test_manual_legitimo_e_mesmo_nome_sem_vinculo_sao_preservados(self):
        events = [{"id": 42, "name": "Treino", "paired_activity_id": "fit"}]
        activities = [
            {"id": "manual", "source": "MANUAL", "name": "Treino"},
            {"id": "fit", "source": "UPLOAD", "name": "Treino"},
            {"id": "outro", "source": "UPLOAD", "name": "Treino"},
        ]
        result = link_activities(events, activities)
        self.assertEqual([a["id"] for a in result.activities], ["manual", "fit", "outro"])
        self.assertNotIn("manual", result.activity_event)
        self.assertNotIn("outro", result.activity_event)

    def test_manual_nao_e_suprimido_se_fit_pareado_nao_estiver_disponivel(self):
        events = [{"id": 42, "paired_activity_id": "fit"}]
        activities = [{"id": "manual", "source": "MANUAL", "paired_event_id": 42}]
        result = link_activities(events, activities)
        self.assertEqual(result.activities, tuple(activities))
        self.assertEqual(result.event_activity, {})


class HistoricalPowerStepsTest(unittest.TestCase):
    def test_perfil_estruturado_preserva_rampas_e_bloco(self):
        event = {"workout_doc": {"steps": [
            {"duration": 600, "power": {"units": "%ftp", "start": 45, "end": 75}},
            {"duration": 2400, "power": {"units": "%ftp", "value": 60}},
            {"duration": 600, "power": {"units": "%ftp", "start": 70, "end": 45}},
        ]}}
        self.assertEqual(historical_power_steps(event), (
            (600, 0.45, 0.75), (2400, 0.6, 0.6), (600, 0.7, 0.45)))

    def test_sem_potencia_ou_formato_desconhecido_nao_inventa_perfil(self):
        for event in ({}, {"workout_doc": {"steps": [
                {"duration": 600, "power": {"units": "watts", "value": 120}}]}},
                {"workout_doc": {"steps": [{"duration": 600}]}}):
            with self.subTest(event=event):
                self.assertIsNone(historical_power_steps(event))


if __name__ == "__main__":
    unittest.main()
