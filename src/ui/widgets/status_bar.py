# src/ui/widgets/status_bar.py
"""Rodapé com status do plano."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Label
from datetime import datetime


class StatusBar(Horizontal):
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: $boost;
    }
    StatusBar Label {
        padding: 0 2;
    }
    """

    def __init__(self, status: str = ""):
        super().__init__()
        self.status = status

    def compose(self) -> ComposeResult:
        yield Label(f"Hermes Coach | {self.status} | {datetime.now().strftime('%H:%M')}")
