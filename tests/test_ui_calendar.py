"""Regressões visuais dos resumos de treino no calendário."""

import unittest
from datetime import date

from textual.app import App

from src.ui.screens.calendar import CalendarScreen


class CalendarTestApp(App):
    def __init__(self, screen: CalendarScreen) -> None:
        super().__init__()
        self._calendar_screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._calendar_screen)


class CalendarWorkoutSummaryTest(unittest.IsolatedAsyncioTestCase):
    async def test_perfis_da_terceira_semana_aparecem_no_render_mensal(self):
        screen = CalendarScreen()
        screen.current_date = screen.selected_date = date(2026, 11, 10)
        workout = {"name": "Treino", "params": {
            "warmup_sec": 600, "on_sec": 1800, "on_power": 0.9,
            "cooldown_sec": 600,
        }}
        screen._load_workouts = lambda: {
            f"2026-11-{day:02}": {"planned": workout} for day in (9, 11, 13)
        }
        async with CalendarTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            lines = ["".join(segment.text for segment in strip._segments)
                     for strip in screen._compositor.render_strips()]
            profiles = [line for line in lines if line.count("█") >= 3]
            self.assertTrue(profiles, "perfis dos três cards não foram renderizados")
            self.assertGreaterEqual(sum(c in "▁▂▃▄▅▆▇█" for c in profiles[0]), 36)

    async def test_card_planejado_reserva_linha_visivel_para_perfil_de_potencia(self):
        screen = CalendarScreen()
        screen.current_date = screen.selected_date = __import__("datetime").date(2026, 11, 2)
        screen._load_workouts = lambda: {
            "2026-11-02": {
                "planned": {
                    "name": "Sweet Spot",
                    "planned_duration": 3600,
                    "tss": 55,
                    "params": {
                        "warmup_sec": 600,
                        "repeats": 2,
                        "on_sec": 720,
                        "off_sec": 180,
                        "on_power": 0.90,
                        "off_power": 0.55,
                        "cooldown_sec": 600,
                    },
                },
            },
        }

        async with CalendarTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            profile = screen.query_one(".workout-profile")
            self.assertEqual(profile.region.height, 1)
            self.assertEqual(profile.styles.padding.top, 0)
            self.assertEqual(len(profile.render().plain), 12)
            self.assertIn("█", profile.render().plain)
            self.assertIn("Planejado · 60m · TSS55", [
                label.render().plain for label in screen.query(".workout-meta")
            ])

if __name__ == "__main__":
    unittest.main()
