"""Integração de leitura do plano com histórico remoto."""

import unittest
from datetime import date, timedelta
from unittest.mock import patch
from pathlib import Path
import tempfile

from src.ui.screens.calendar import CalendarScreen
from src.ui.screens.calendar_detail import CalendarDetailScreen
from src.ui.training_review import week_summary
from src.intervals_adapter import _training_event
from textual.app import App
from textual.widgets import Label


class CalendarHistoryTest(unittest.TestCase):
    def test_leitura_preserva_arquivo_do_plano(self):
        class Provider:
            def events(self, **kwargs): return []
            def activities(self, **kwargs): return []
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            original = b'{"workouts": [{"day": "2026-11-02", "name": "Teste"}]}'
            path.write_bytes(original)
            with patch("src.ui.screens.calendar.PLAN", path), patch("src.ui.utils.get_app") as app:
                app.return_value.client.return_value = Provider()
                CalendarScreen()._load_workouts()
            self.assertEqual(path.read_bytes(), original)

    def test_leitura_de_historico_nao_grava_plano_nem_provider(self):
        from unittest.mock import Mock
        provider = Mock()
        provider.events.return_value = [_training_event({"id": 42,
            "external_id": "hermes-plan-2026-11-02", "start_date_local": "2026-11-02T07:30:00"})]
        provider.activities.return_value = []
        plan = [{"day": "2026-11-02", "name": "Local"}]
        import copy
        before = copy.deepcopy(plan)
        with patch("src.ui.screens.calendar.load_plan", return_value=plan), \
             patch("src.ui.utils.get_app") as app:
            app.return_value.client.return_value = provider
            CalendarScreen()._load_workouts()
        self.assertEqual(plan, before)
        provider.create_event.assert_not_called()
        provider.update_event.assert_not_called()
        provider.delete_event.assert_not_called()
        app.return_value.save_plan.assert_not_called()

    def test_detalhe_multiplos_planos_nao_diz_que_todos_foram_realizados(self):
        local_a = {"external_id": "a"}
        local_b = {"external_id": "b"}
        entry = {"planned": local_a, "local_plans": [local_a, local_b],
                 "done": {"id": "fit"}, "matching_required": True,
                 "matched_activity_id": "fit"}
        self.assertEqual(CalendarDetailScreen("2026-11-02", entry)._status_text(),
                         "MÚLTIPLOS TREINOS • CONSULTE DETALHES")

    def test_treino_hoje_nao_pareado_com_extra_permanece_pendente(self):
        today = date.today().isoformat()
        detail = CalendarDetailScreen(today, {"planned": {"name": "Treino"},
            "done": {"id": "extra"}, "matching_required": True})
        self.assertEqual(detail._status_text(), "PLANEJADO • PENDENTE • ATIVIDADE EXTRA")

    def test_prescricao_futura_sem_atividade_esta_pendente(self):
        future = (date.today() + timedelta(days=3)).isoformat()
        detail = CalendarDetailScreen(future, {"planned": {"name": "Treino"}})
        self.assertEqual(detail._status_text(), "PLANEJADO • PENDENTE")

    def test_evento_em_data_divergente_nao_gera_segunda_prescricao(self):
        class Provider:
            def events(self, **kwargs):
                return [_training_event({"id": 42, "external_id": "hermes-plan-x",
                    "start_date_local": "2026-11-03T07:30:00", "name": "Remoto"})]
            def activities(self, **kwargs):
                return []
        local = {"day": "2026-11-02", "external_id": "hermes-plan-x", "planned_duration": 3600}
        with patch("src.ui.screens.calendar.load_plan", return_value=[local]), \
             patch("src.ui.utils.get_app") as app:
            app.return_value.client.return_value = Provider()
            entries = CalendarScreen()._load_workouts()
        self.assertTrue(entries["2026-11-02"]["plan_divergence"])
        self.assertTrue(entries["2026-11-03"]["plan_divergence"])
        self.assertNotIn("planned", entries["2026-11-03"])
        summary = week_summary(entries, date(2026, 11, 2), date(2026, 11, 4))
        self.assertEqual(summary.planned_duration_seconds, 3600)
        self.assertEqual(summary.missed, 1)

    def test_atividade_nao_conclui_duas_prescricoes_com_mesmo_id_externo(self):
        local = {"external_id": "x", "planned_duration": 600}
        remote1 = {"external_id": "x", "event_id": "1", "planned_duration": 600}
        remote2 = {"external_id": "x", "event_id": "2", "planned_duration": 600}
        activity = {"id": "fit", "duration": 600}
        entries = {"2026-11-02": {"planned": local, "local_plans": [local],
            "remote_plans": [remote1, remote2], "activities": [activity],
            "matching_required": True, "matches_by_external": {"x": "fit"},
            "matches_by_event": {"2": "fit"}}}
        summary = week_summary(entries, date(2026, 11, 2), date(2026, 11, 4))
        self.assertEqual((summary.completed, summary.missed, summary.extra), (1, 1, 0))

    def test_mesmo_external_id_em_eventos_distintos_nao_duplica_pareamento(self):
        a = {"external_id": "x", "event_id": "1", "planned_duration": 1800}
        b = {"external_id": "x", "event_id": "2", "planned_duration": 1800}
        activity = {"id": "fit", "planned_event_id": "1", "duration": 1800}
        entries = {"2026-11-02": {"planned": a, "remote_plans": [a, b],
            "activities": [activity], "matching_required": True,
            "matches_by_external": {"x": "fit"}, "matches_by_event": {"1": "fit"}}}
        summary = week_summary(entries, date(2026, 11, 2), date(2026, 11, 4))
        self.assertEqual((summary.completed, summary.missed, summary.extra), (1, 1, 0))

    def test_resumo_soma_cada_prescricao_sem_duplicar_evento_remoto(self):
        local_a = {"external_id": "a", "planned_duration": 1800, "tss": 20}
        local_b = {"external_id": "b", "planned_duration": 2400, "tss": 30}
        remote_a = {"external_id": "a", "event_id": "1", "planned_duration": 1800, "tss": 20}
        remote_c = {"external_id": "c", "event_id": "3", "planned_duration": 1200, "tss": 10}
        entries = {"2026-11-02": {"planned": local_a, "local_plans": [local_a, local_b],
                                   "remote_plans": [remote_a, remote_c], "matching_required": True}}
        summary = week_summary(entries, date(2026, 11, 2), date(2026, 11, 4))
        self.assertEqual((summary.planned_duration_seconds, summary.planned_tss), (5400, 60))
        self.assertEqual(summary.missed, 3)

    def test_prioriza_atividade_pareada_mesmo_com_outra_mais_completa(self):
        class Provider:
            def events(self, **kwargs):
                return [_training_event({"id": 42, "external_id": "hermes-plan-2026-11-02",
                    "start_date_local": "2026-11-02T07:30:00", "paired_activity_id": "fit"})]
            def activities(self, **kwargs):
                return [{"id": "fit", "source": "UPLOAD", "start_date_local": "2026-11-02T08:00:00"},
                        {"id": "extra", "source": "UPLOAD", "start_date_local": "2026-11-02T12:00:00",
                         "moving_time": 1000, "icu_training_load": 20, "average_watts": 100}]
        with patch("src.ui.screens.calendar.load_plan", return_value=[]), \
             patch("src.ui.utils.get_app") as app:
            app.return_value.client.return_value = Provider()
            entry = CalendarScreen()._load_workouts()["2026-11-02"]
        self.assertEqual(entry["done"]["id"], "fit")
        self.assertEqual(len(entry["activities"]), 2)

    def test_atividade_no_mesmo_dia_sem_vinculo_nao_conclui_plano(self):
        entry = {"planned": {"name": "Intervalos"},
                 "done": {"id": "a", "duration": 600},
                 "activities": [{"id": "a", "duration": 600}],
                 "matching_required": True, "matched_activity_id": None}
        summary = week_summary({"2026-11-02": entry}, date(2026, 11, 2), date(2026, 11, 4))
        self.assertEqual((summary.completed, summary.missed, summary.extra), (0, 1, 1))
        detail = CalendarDetailScreen("2026-11-02", entry)
        self.assertEqual(detail._status_text(), "PLANEJADO • NÃO REALIZADO • ATIVIDADE EXTRA")

    def test_preserva_plano_local_e_sinaliza_divergencia_com_mesmo_evento(self):
        class Provider:
            def events(self, **kwargs):
                return [_training_event({"id": 42, "external_id": "hermes-plan-2026-11-02",
                    "start_date_local": "2026-11-02T07:30:00", "name": "Remoto",
                    "moving_time": 2400})]
            def activities(self, **kwargs):
                return []
        local = {"day": "2026-11-02", "name": "Local", "planned_duration": 3600,
                 "external_id": "hermes-plan-2026-11-02"}
        with patch("src.ui.screens.calendar.load_plan", return_value=[local]), \
             patch("src.ui.utils.get_app") as app:
            app.return_value.client.return_value = Provider()
            entry = CalendarScreen()._load_workouts()["2026-11-02"]
        self.assertEqual(entry["planned"], local)
        self.assertTrue(entry["plan_divergence"])
        self.assertEqual(entry["remote_plans"][0]["name"], "Remoto")

    def test_resumo_conta_execucao_tardia_e_outras_atividades_uma_vez(self):
        first = {"id": "fit", "duration": 3600, "tss": 34, "planned_day": "2026-11-02"}
        extra = {"id": "extra", "duration": 1200, "tss": 12}
        entries = {"2026-11-02": {"planned": {"planned_duration": 3600, "tss": 35}},
                   "2026-11-03": {"done": first, "activities": [first, extra]}}
        summary = week_summary(entries, date(2026, 11, 2), date(2026, 11, 4))
        self.assertEqual((summary.completed, summary.missed, summary.extra), (0, 1, 2))
        self.assertEqual((summary.actual_duration_seconds, summary.actual_tss), (4800, 46))

    def test_perfil_historico_e_datas_no_detalhe(self):
        planned = {"origin": "intervals", "historical_power_steps": (
            (600, 0.45, 0.75), (2400, 0.6, 0.6), (600, 0.7, 0.45))}
        screen = CalendarScreen()
        self.assertTrue(screen._profile_sparkline(planned))
        detail = CalendarDetailScreen("2026-11-02", {
            "planned": planned, "linked_activity_day": "2026-11-03"})
        self.assertEqual("PLANEJADO • NÃO REALIZADO", detail._status_text())
        self.assertTrue(detail._profile(planned))
        late = CalendarDetailScreen("2026-11-03", {
            "done": {"planned_day": "2026-11-02"}})
        self.assertEqual("REALIZADO FORA DO PLANO", late._status_text())

    def test_evento_historico_e_execucao_tardia(self):
        class Provider:
            def events(self, **kwargs):
                return [_training_event({"id": 42, "external_id": "hermes-plan-2026-11-02",
                         "category": "WORKOUT", "start_date_local": "2026-11-02T07:30:00",
                         "name": "Recuperação", "paired_activity_id": "fit",
                         "workout_doc": {"steps": [{"duration": 600, "power": {"units": "%ftp", "value": 60}}]}})]

            def activities(self, **kwargs):
                return [{"id": "manual", "source": "MANUAL", "paired_event_id": 42,
                         "start_date_local": "2026-11-02T07:30:00"},
                        {"id": "fit", "source": "UPLOAD", "paired_event_id": 42,
                         "start_date_local": "2026-11-03T20:31:00", "moving_time": 3600}]

        provider = Provider()
        with patch("src.ui.screens.calendar.load_plan", return_value=[]), \
             patch("src.ui.utils.get_app") as app:
            app.return_value.client.return_value = provider
            entries = CalendarScreen()._load_workouts()
        self.assertEqual(entries["2026-11-02"]["planned"]["origin"], "intervals")
        self.assertEqual(entries["2026-11-02"]["linked_activity_day"], "2026-11-03")
        self.assertNotIn("done", entries["2026-11-02"])
        self.assertEqual(entries["2026-11-03"]["done"]["id"], "fit")
        self.assertEqual(entries["2026-11-03"]["done"]["planned_day"], "2026-11-02")

    def test_falha_de_eventos_preserva_plano_local(self):
        class Provider:
            def events(self, **kwargs):
                raise OSError("indisponível")
            def activities(self, **kwargs):
                return []

        screen = CalendarScreen()
        with patch("src.ui.screens.calendar.load_plan", return_value=[{"day": "2026-11-02", "name": "Local"}]), \
             patch("src.ui.utils.get_app") as app:
            app.return_value.client.return_value = Provider()
            entries = screen._load_workouts()
        self.assertEqual(entries["2026-11-02"]["planned"]["name"], "Local")
        self.assertTrue(screen._history_unavailable)
        summary = week_summary(entries, date(2026, 11, 2), date(2026, 11, 4))
        self.assertEqual(summary.missed, 0)
        self.assertEqual(summary.unknown, 1)
        self.assertEqual(CalendarDetailScreen("2026-11-02", entries["2026-11-02"])._status_text(),
                         "STATUS INDISPONÍVEL")


class CalendarHistoryRenderTest(unittest.IsolatedAsyncioTestCase):
    async def test_evento_de_ontem_e_execucao_extra_em_dias_distintos(self):
        class Provider:
            def events(self, **kwargs):
                return [_training_event({"id": 42, "external_id": "hermes-plan-2026-11-02",
                    "start_date_local": "2026-11-02T07:30:00", "name": "Recuperação",
                    "paired_activity_id": "fit", "moving_time": 3600,
                    "workout_doc": {"steps": [{"duration": 600, "power": {"units": "%ftp", "value": 60}}]}})]
            def activities(self, **kwargs):
                return [{"id": "manual", "source": "MANUAL", "paired_event_id": 42,
                         "start_date_local": "2026-11-02T07:30:00"},
                        {"id": "fit", "source": "UPLOAD", "paired_event_id": 42,
                         "name": "Zwift", "start_date_local": "2026-11-03T20:31:00", "moving_time": 3600}]
        screen = CalendarScreen()
        screen.view_mode = "week"
        screen.current_date = screen.selected_date = date(2026, 11, 2)
        with patch("src.ui.screens.calendar.load_plan", return_value=[]), patch("src.ui.utils.get_app") as app:
            app.return_value.client.return_value = Provider()
            entries = screen._load_workouts()
        screen._load_workouts = lambda: entries
        screen._activity_profile_sparkline = lambda *args, **kwargs: ""
        class TestApp(App):
            def on_mount(self): self.push_screen(screen)
        async with TestApp().run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            cards = {}
            for card in screen.query(".day-card"):
                labels = [label.render().plain for label in card.query(Label)]
                if labels:
                    cards[labels[0]] = labels
            self.assertTrue(any("Não realizado" in text for text in cards["2/11"]))
            self.assertFalse(any("2026-11-03" in text for text in cards["2/11"]))
            self.assertTrue(any("Extra" in text for text in cards["3/11"]))
            summary = week_summary(entries, date(2026, 11, 2), date(2026, 11, 4))
            self.assertEqual((summary.missed, summary.extra), (1, 1))
            self.assertEqual(CalendarDetailScreen("2026-11-02", entries["2026-11-02"])._status_text(), "PLANEJADO • NÃO REALIZADO")
            self.assertEqual(CalendarDetailScreen("2026-11-03", entries["2026-11-03"])._status_text(), "REALIZADO FORA DO PLANO")


if __name__ == "__main__":
    unittest.main()
