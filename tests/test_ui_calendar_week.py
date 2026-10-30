"""Integração headless do resumo semanal no calendário."""

import unittest
from datetime import date

from textual.app import App

from src.ui.screens.calendar import CalendarScreen


class CalendarWeekTestApp(App):
    def __init__(self, screen: CalendarScreen) -> None:
        super().__init__()
        self._calendar_screen = screen

    def on_mount(self) -> None:
        self.push_screen(self._calendar_screen)


class CalendarWeekSummaryTest(unittest.IsolatedAsyncioTestCase):
    async def test_semana_exibe_totais_status_e_zonas_planejadas(self):
        planned = {
            "focus": "sweetspot", "planned_duration": 3600, "tss": 55,
            "params": {"warmup_sec": 600, "repeats": 2, "on_sec": 720,
                       "off_sec": 180, "on_power": 0.90, "off_power": 0.55,
                       "cooldown_sec": 600},
        }
        screen = CalendarScreen()
        screen.view_mode = "week"
        screen.current_date = screen.selected_date = date(2026, 10, 26)
        screen._load_workouts = lambda: {
            "2026-10-26": {"planned": planned, "done": {"duration": 3300, "tss": 48}},
            "2026-10-27": {"planned": {"planned_duration": 1800, "tss": 20}},
            "2026-10-30": {"planned": {"planned_duration": 2400, "tss": 30}},
            "2026-10-29": {"done": {"duration": 1200, "tss": 15}},
        }

        async with CalendarWeekTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            text = [widget.render().plain for widget in screen.query("Label")]
            for expected in ("RESUMO SEMANAL", "Planejado: 130m · TSS105",
                             "Realizado: 75m · TSS63",
                             "1 realizado · 1 perdido · 1 pendente · 1 extra",
                             "Zonas planejadas:", "Zonas realizadas: indisponível"):
                with self.subTest(expected=expected):
                    self.assertIn(expected, text)

    async def test_navegar_semana_recalcula_resumo(self):
        screen = CalendarScreen()
        screen.view_mode = "week"
        screen.current_date = screen.selected_date = date(2026, 10, 26)
        screen._load_workouts = lambda: {
            "2026-10-26": {"planned": {"planned_duration": 1800, "tss": 20}},
            "2026-11-02": {"planned": {"planned_duration": 3600, "tss": 40}},
        }

        async with CalendarWeekTestApp(screen).run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            self.assertIn("Planejado: 30m · TSS20", [x.render().plain for x in screen.query("Label")])
            screen.action_next()
            await pilot.pause()
            self.assertIn("Planejado: 60m · TSS40", [x.render().plain for x in screen.query("Label")])


if __name__ == "__main__":
    unittest.main()
