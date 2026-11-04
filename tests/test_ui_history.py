"""Projeção de vínculos entre eventos e atividades do calendário."""

import unittest

from src.ui.history import link_activities, historical_power_steps, compare_power_structure


class ActivityLinksTest(unittest.TestCase):
    def test_mesmo_id_repetido_nao_duplica_atividade(self):
        activities = [{"id": "same", "duration": 3600}, {"id": "same", "duration": 3600}]
        result = link_activities([], activities)
        self.assertEqual([a["id"] for a in result.activities], ["same"])

    def test_manual_duplicado_quando_atividade_pareada_tambem_e_manual(self):
        events = [{"id": 42, "paired_activity_id": "principal"}]
        activities = [{"id": "copia", "source": "MANUAL", "paired_event_id": 42},
                      {"id": "principal", "source": "MANUAL", "paired_event_id": 42}]
        result = link_activities(events, activities)
        self.assertEqual([a["id"] for a in result.activities], ["principal"])

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
    def test_compara_estrutura_sem_estimar_campos_ausentes(self):
        local = {"params": {"warmup_sec": 600, "warmup_power_low": .45,
            "warmup_power_high": .75, "repeats": 1, "on_sec": 2400, "off_sec": 0,
            "on_power": .6, "cooldown_sec": 600, "cooldown_power_low": .7,
            "cooldown_power_high": .45}}
        remote = ((600, .45, .75), (2400, .6, .6), (600, .7, .45))
        self.assertIs(compare_power_structure(local, remote), True)
        self.assertIs(compare_power_structure(local, ((600, .45, .75), (2400, .7, .7), (600, .7, .45))), False)
        self.assertIsNone(compare_power_structure({"params": {}}, remote))
        self.assertIsNone(compare_power_structure(local, None))

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

    def test_potencia_conflitante_nao_gera_grafico(self):
        event = {"workout_doc": {"steps": [{"duration": 600,
            "power": {"units": "%ftp", "value": 60, "start": 45, "end": 75}}]}}
        self.assertIsNone(historical_power_steps(event))


if __name__ == "__main__":
    unittest.main()
