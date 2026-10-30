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


if __name__ == "__main__":
    unittest.main()
