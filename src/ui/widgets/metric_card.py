# src/ui/widgets/metric_card.py
"""Card simples para exibir métricas (FTP/CTL/ATL/TSB/VO₂)."""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Label


class MetricCard(Vertical):
    DEFAULT_CSS = """
    MetricCard {
        width: 1fr;
        height: 7;
        border: tall $accent;
        padding: 1 1;
    }
    MetricCard .metric-title {
        text-align: center;
        text-style: bold;
    }
    MetricCard .metric-value {
        text-align: center;
        text-style: bold;
        padding-top: 1;
    }
    """

    def __init__(self, title: str, value: str = "—", subtitle: str = ""):
        super().__init__()
        self._title = title
        self._value = "—" if value is None or str(value).strip() == "" else str(value)

    def compose(self) -> ComposeResult:
        yield Label(self._title, classes="metric-title")
        yield Label(self._value, classes="metric-value")
