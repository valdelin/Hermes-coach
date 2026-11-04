"""Integração headless do detalhe de treino no calendário."""

import unittest

from textual.app import App

from src.ui.screens.calendar_detail import CalendarDetailScreen


class CalendarDetailTestApp(App):
    def __init__(self, screen: CalendarDetailScreen) -> None:
        super().__init__()
        self._detail_screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._detail_screen)


def _screen_text(screen: CalendarDetailScreen) -> list[str]:
    return [widget.render().plain for widget in screen.query("Label, Static")]


class CalendarDetailTest(unittest.IsolatedAsyncioTestCase):
    async def test_perfil_historico_sem_estrutura_informa_indisponibilidade(self):
        screen = CalendarDetailScreen("2026-11-02", {"planned": {
            "name": "Histórico", "origin": "intervals", "historical_power_steps": None}})
        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            self.assertIn("Perfil planejado indisponível.", text)
            self.assertIn("Intervals.icu", text)

    async def test_atividade_sem_stream_nao_estima_zonas(self):
        screen = CalendarDetailScreen("2026-11-02", {"done": {"id": "a", "duration": 3600, "average_watts": 150}})
        screen._load_activity_streams = lambda activity: ([], None, {}, {})
        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            self.assertIn("Zonas de potência realizadas: indisponíveis", text)
            self.assertNotIn("POTÊNCIA", text)

    async def test_divergencia_remota_sem_plano_exibe_evento(self):
        remote = {"name": "Sessão remota", "day": "2026-11-03", "origin": "intervals",
                  "shadowed_by_local": True, "historical_power_steps": ((600, .45, .75),)}
        screen = CalendarDetailScreen("2026-11-03", {"plan_divergence": True, "remote_plans": [remote]})
        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            self.assertIn("Plano local difere do evento remoto.", text)
            self.assertIn("Evento remoto: Sessão remota · 2026-11-03", text)

    async def test_perfil_planejado_disponivel_nao_e_dito_indisponivel_sem_stream(self):
        planned = {"origin": "intervals", "historical_power_steps": ((600, .45, .75),)}
        screen = CalendarDetailScreen("2026-11-02", {"planned": planned, "done": {"id": "a"}})
        screen._load_activity_streams = lambda activity: ([], None, {}, {})
        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            self.assertIn("PERFIL PLANEJADO", text)
            self.assertIn("Perfil realizado indisponível.", text)
            self.assertNotIn("Perfil planejado indisponível.", text)

    async def test_exibe_metricas_e_perfil_de_atividade_adicional(self):
        first = {"id": "a", "name": "Primeira", "duration": 600}
        second = {"id": "b", "name": "Segunda", "duration": 1200, "tss": 22}
        screen = CalendarDetailScreen("2026-11-02", {"done": first, "activities": [first, second]})
        screen._load_activity_streams = lambda activity: ([], None, {}, {})
        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            for expected in ("ATIVIDADE: Segunda", "20 min", "22", "Perfil realizado indisponível."):
                self.assertIn(expected, text)

    async def test_detalhe_planejado_mostra_estrutura_sem_streams_reais(self):
        planned = {
            "name": "Sweet Spot", "focus": "sweetspot", "planned_duration": 3600,
            "tss": 55,
            "params": {"warmup_sec": 600, "repeats": 2, "on_sec": 720,
                       "off_sec": 180, "on_power": 0.90, "off_power": 0.55,
                       "cooldown_sec": 600},
        }
        screen = CalendarDetailScreen("2026-11-02", {"planned": planned})
        screen._load_activity_streams = lambda done: ([], None, {}, {})

        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            self.assertIn("TREINO PLANEJADO", text)
            self.assertIn("Foco", text)
            self.assertIn("sweetspot", text)
            self.assertIn("60 min", text)
            self.assertIn("55", text)
            self.assertIn("PERFIL DO TREINO", text)
            self.assertIn("ESTRUTURA", text)
            self.assertIn("Aquecimento", text)
            self.assertIn("Trabalho", text)
            self.assertIn("Recuperação", text)
            self.assertIn("Desaquecimento", text)

    async def test_detalhe_compara_planejado_e_realizado_lado_a_lado(self):
        planned = {"name": "Sweet Spot", "focus": "sweetspot", "planned_duration": 3600,
                   "tss": 55, "params": {"on_sec": 1800, "on_power": 0.90}}
        done = {"name": "Zwift", "duration": 3300, "tss": 48,
                "average_watts": 180, "normalized_power": 195}
        screen = CalendarDetailScreen("2026-11-02", {"planned": planned, "done": done})
        screen._load_activity_streams = lambda activity: ([], None, {}, {})

        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            for expected in ("COMPARAÇÃO FACTUAL", "PLANEJADO", "REALIZADO", "60 min", "55 min",
                             "55", "48", "Δ duração", "-5 min", "Δ TSS", "-7", "180 W", "195 W"):
                with self.subTest(expected=expected):
                    self.assertIn(expected, text)

    async def test_comparacao_mantem_ausencia_como_traco(self):
        screen = CalendarDetailScreen(
            "2026-11-02",
            {"planned": {"planned_duration": 3600, "tss": 55}, "done": {"duration": 3300}},
        )
        screen._load_activity_streams = lambda activity: ([], None, {}, {})

        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            self.assertIn("COMPARAÇÃO FACTUAL", text)
            self.assertGreaterEqual(text.count("—"), 3)

    async def test_detalhe_planejado_omite_campos_ausentes(self):
        screen = CalendarDetailScreen("2026-11-02", {"planned": {"name": "Teste"}})
        screen._load_activity_streams = lambda activity: ([], None, {}, {})

        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = _screen_text(screen)
            self.assertIn("TREINO PLANEJADO", text)
            self.assertIn("Teste", text)
            self.assertNotIn("Foco", text)
            self.assertNotIn("Duração", text)
            self.assertNotIn("TSS", text)

    async def test_perfil_planejado_usa_cores_por_zona(self):
        planned = {
            "focus": "sweetspot", "planned_duration": 3600, "tss": 55,
            "params": {"warmup_sec": 600, "repeats": 1, "on_sec": 1800, "on_power": 0.90, "cooldown_sec": 600},
        }
        screen = CalendarDetailScreen("2026-11-02", {"planned": planned})
        screen._load_activity_streams = lambda activity: ([], None, {}, {})

        async with CalendarDetailTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            profile_texts = [widget.render().markup for widget in screen.query("Static")]
            combined = " ".join(profile_texts)
            self.assertIn("[#", combined)
            self.assertIn("PERFIL DO TREINO", [w.render().plain for w in screen.query("Label")])


if __name__ == "__main__":
    unittest.main()
