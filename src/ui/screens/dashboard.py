# src/ui/screens/dashboard.py
"""Tela Dashboard - Visão geral (somente leitura)."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from ..utils import load_dashboard_data
from ..widgets.metric_card import MetricCard
from ..widgets.status_bar import StatusBar
from ..constants import MSG_NO_PLAN


class DashboardScreen(Screen):
    BINDINGS = [
        ("g", "generate", "Gerar Plano"),
        ("p", "publish", "Publicar"),
        ("r", "reconcile", "Reconciliar"),
        ("c", "calendar", "Calendário"),
        ("t", "readiness", "Prontidão"),
        ("q", "quit", "Sair"),
    ]

    def compose(self) -> ComposeResult:
        data = load_dashboard_data()
        yield Container(
            Label("HERMES COACH - DASHBOARD", classes="title"),
            Horizontal(
                MetricCard("FTP", f"{data['ftp']}W"),
                MetricCard("VO₂", str(data['vo2'])),
                MetricCard("CTL", str(data['ctl'])),
                MetricCard("ATL", str(data['atl'])),
                MetricCard("TSB", str(data['tsb'])),
                classes="metrics",
            ),
            Vertical(
                Label("PMC - CTL / ATL / TSB", classes="section"),
                Static("\n".join(data.get("pmc_chart", [])) or "Sem dados suficientes para gerar o gráfico PMC.", classes="pmc"),
                classes="pmcbox",
            ),
            Vertical(
                Label("TREINO DE HOJE", classes="section"),
                Static(self._today_text(data), classes="workout"),
                classes="today",
            ),
            Vertical(
                Label("PRÓXIMOS DIAS", classes="section"),
                Static(self._next_text(data), classes="next"),
                classes="nextbox",
            ),
            Vertical(
                Label("AÇÕES RÁPIDAS", classes="section"),
                Horizontal(
                    Button("Gerar Plano (g)", id="btn_gen"),
                    Button("Prontidão (t)", id="btn_today"),
                    Button("Reconciliar (r)", id="btn_rec"),
                    Button("Publicar (p)", id="btn_pub"),
                    Button("Calendário (c)", id="btn_cal"),
                    classes="actions",
                ),
                classes="actionsbox",
            ),
            classes="main",
        )
        status = "Sem plano" if not data["has_plan"] else f"Planos: {len(data['plan'])} treinos"
        yield StatusBar(status)

    def _today_text(self, data):
        if not data["has_plan"]:
            return MSG_NO_PLAN
        w = data["today_workout"]
        if not w:
            return "Hoje não tem treino no plano."
        name = w.get("name", "—")
        dur = w.get("planned_duration", 0) // 60
        tss = w.get("tss", 0)
        focus = w.get("focus", "—")
        return f"[{focus}] {name} | {dur} min | TSS {tss:.0f}"

    def _next_text(self, data):
        if not data["has_plan"] or not data["next_days"]:
            return "Sem próximos treinos."
        lines = []
        for w in data["next_days"]:
            d = w.get("day", "—")
            name = w.get("name", "—")
            dur = w.get("planned_duration", 0) // 60
            tss = w.get("tss", 0)
            lines.append(f"{d} | {name} | {dur}m | TSS {tss:.0f}")
        return "\n".join(lines)

    def action_quit(self):
        self.app.exit()

    def action_calendar(self):
        from .calendar import CalendarScreen
        self.app.push_screen(CalendarScreen())

    def action_readiness(self):
        from .readiness import ReadinessScreen
        self.app.push_screen(ReadinessScreen())

    def action_generate(self):
        self.app.bell()
        self.notify("Use 'g' no terminal CLI ou rode: python scripts/hermes_agent.py build")

    def action_publish(self):
        self.app.bell()
        self.notify("Acesse Publicar (p): sempre com push --dry-run primeiro.")

    def action_reconcile(self):
        self.app.bell()
        self.notify("Rode: python scripts/hermes_agent.py reconcile")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cal":
            self.action_calendar()
        elif event.button.id == "btn_gen":
            self.action_generate()
        elif event.button.id == "btn_pub":
            self.action_publish()
        elif event.button.id == "btn_rec":
            self.action_reconcile()
        elif event.button.id == "btn_today":
            from .readiness import ReadinessScreen
            self.app.push_screen(ReadinessScreen())
