# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ ARQUIVO COMENTADO: src/ui/app.py                                             ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# DESCRIÇÃO: Cópia didática do código da TUI local-first.
#
# Gerado em: 2026-10-29 19:44:17
#
# ATENÇÃO: CÓPIA PARA ESTUDO APENAS
# - Arquivo original: src/ui/app.py (NÃO MODIFICADO)
# - Esta cópia contém APENAS cabeçalho explicativo adicionado no topo
# - Todo o código abaixo é IDÊNTICO ao original
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# src/ui/app.py
"""Aplicação TUI principal do Hermes Coach."""

from textual.app import App
from .screens.dashboard import DashboardScreen
from .screens.calendar import CalendarScreen
from .screens.readiness import ReadinessScreen


class HermesCoachApp(App):
    CSS = """
    Screen {
        background: $surface;
    }
    .title {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    .metrics {
        height: 7;
        padding: 0 1;
    }
    .section {
        text-style: bold;
        padding: 1 1 0 1;
    }
    .workout {
        padding: 0 2;
    }
    .next {
        padding: 0 2;
    }
    .actions {
        padding: 1 2;
    }
    .main {
        padding: 0 1;
    }
    """
    BINDINGS = [
        ("q", "quit", "Sair"),
        ("c", "calendar", "Calendário"),
        ("p", "readiness", "Prontidão"),
        ("r", "readiness", "Prontidão"),
    ]

    def on_mount(self):
        self.title = "Hermes Coach"
        self.push_screen(DashboardScreen())

    def action_calendar(self):
        self.push_screen(CalendarScreen())

    def action_readiness(self):
        self.push_screen(ReadinessScreen())


def run():
    app = HermesCoachApp()
    app.run()


if __name__ == "__main__":
    run()
