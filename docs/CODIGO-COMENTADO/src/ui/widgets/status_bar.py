# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║ ARQUIVO COMENTADO: src/ui/widgets/status_bar.py                              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
#
# DESCRIÇÃO: Cópia didática do código da TUI local-first.
#
# Gerado em: 2026-10-29 19:44:17
#
# ATENÇÃO: CÓPIA PARA ESTUDO APENAS
# - Arquivo original: src/ui/widgets/status_bar.py (NÃO MODIFICADO)
# - Esta cópia contém APENAS cabeçalho explicativo adicionado no topo
# - Todo o código abaixo é IDÊNTICO ao original
#
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

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
