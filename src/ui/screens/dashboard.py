# src/ui/screens/dashboard.py
"""Tela Dashboard - Visão geral (somente leitura)."""

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Label, Static

from ..utils import load_dashboard_data
from ..widgets.metric_card import MetricCard
from ..widgets.status_bar import StatusBar
from ..constants import MSG_NO_PLAN
from src.ui.screens.calendar import BLOCKS, ZONE_COLORS


class DashboardScreen(Screen):
    CSS = """
    DashboardScreen {
        background: $surface;
    }

    #dashboard-scroll {
        height: 1fr;
    }

    .title {
        text-style: bold;
        padding: 1 2;
    }

    .metrics {
        height: auto;
        padding: 0 2;
    }

    .info-card {
        border: round $panel;
        margin: 1 2;
        padding: 1 2;
        height: auto;
    }

    .plain-section {
        margin: 1 2;
        height: auto;
    }

    .card-title {
        text-style: bold;
        padding: 0 0 1 0;
    }

    .pmc {
        padding: 0 1;
    }

    .today-header {
        text-style: bold;
    }

    .today-meta {
        color: $text-muted;
    }

    .workout-profile {
        padding: 1 0 0 0;
    }

    .next-cards {
        layout: horizontal;
        height: auto;
    }

    .next-card {
        border: round $panel;
        margin: 0 1;
        padding: 1;
        width: 1fr;
        height: auto;
    }

    .next-card-title {
        text-style: bold;
    }

    .next-card-meta {
        color: $text-muted;
    }

    .next-card-profile {
        padding: 1 0 0 0;
    }

    .actions {
        layout: horizontal;
        height: auto;
    }

    .actionsbox {
        margin: 1 2 2 2;
        padding: 1 2;
        border: round $panel;
        height: auto;
    }
    """

    BINDINGS = [
        ("g", "generate", "Gerar Plano"),
        ("p", "publish", "Publicar"),
        ("r", "reconcile", "Reconciliar"),
        ("c", "calendar", "Calendário"),
        ("t", "readiness", "Prontidão"),
        ("s", "settings", "Preferências"),
        ("q", "quit", "Sair"),
    ]

    def compose(self) -> ComposeResult:
        data = load_dashboard_data()
        yield Container(
            Label("HERMES COACH - DASHBOARD", classes="title"),
            Horizontal(
                MetricCard("FTP", f"{data['ftp']}W"),
                MetricCard(f"VO₂ · {data['vo2_date'][8:10]}/{data['vo2_date'][5:7]}" if data.get("vo2_date") else "VO₂", str(data['vo2'])),
                MetricCard("CTL", str(data['ctl'])),
                MetricCard("ATL", str(data['atl'])),
                MetricCard("TSB", str(data['tsb'])),
                classes="metrics",
            ),
            VerticalScroll(
                Vertical(
                    Label("PMC - CTL / ATL / TSB", classes="card-title"),
                    Static("\n".join(data.get("pmc_chart", [])) or "Sem dados suficientes para gerar o gráfico PMC.", classes="pmc"),
                    classes="info-card",
                ),
                Vertical(
                    Label("TREINO DE HOJE", classes="card-title"),
                    Horizontal(self._today_card_content(data), classes="next-cards"),
                    classes="plain-section",
                ),
                Vertical(
                    Label("PRÓXIMOS TREINOS", classes="card-title"),
                    self._next_cards(data),
                    classes="info-card",
                ),
                Vertical(
                    Label("AÇÕES RÁPIDAS", classes="section"),
                    Horizontal(
                        Button("Gerar Plano (g)", id="btn_gen"),
                        Button("Prontidão (t)", id="btn_today"),
                        Button("Reconciliar (r)", id="btn_rec"),
                        Button("Publicar (p)", id="btn_pub"),
                        Button("Calendário (c)", id="btn_cal"),
                        Button("Preferências (s)", id="btn_settings"),
                        classes="actions",
                    ),
                    classes="actionsbox",
                ),
                id="dashboard-scroll",
            ),
            classes="main",
        )
        status = "Sem plano" if not data["has_plan"] else f"Planos: {len(data['plan'])} treinos"
        yield StatusBar(status)

    def _zone_color(self, intensity: float) -> str:
        if intensity < 0.56:
            return ZONE_COLORS[0]
        if intensity < 0.76:
            return ZONE_COLORS[1]
        if intensity < 0.84:
            return ZONE_COLORS[2]
        if intensity <= 0.97:
            return ZONE_COLORS[3]
        if intensity <= 1.05:
            return ZONE_COLORS[4]
        if intensity <= 1.20:
            return ZONE_COLORS[5]
        return ZONE_COLORS[6]

    def _profile_sparkline(self, w: dict, width: int = 24) -> str:
        try:
            params = w.get("params") or {}
            if not isinstance(params, dict):
                return ""
            warmup = int(params.get("warmup_sec") or 0)
            cooldown = int(params.get("cooldown_sec") or 0)
            repeats = int(params.get("repeats") or 1)
            on_sec = int(params.get("on_sec") or 0)
            off_sec = int(params.get("off_sec") or 0)
            on_p = float(params.get("on_power") or 0.6)
            off_p = float(params.get("off_power") or on_p)
            if on_sec <= 0 and warmup <= 0 and cooldown <= 0:
                return ""

            profile = []
            if warmup > 0:
                for i in range(min(max(1, warmup // 300), 4)):
                    profile.append(0.4 + 0.15 * i)
            for r in range(repeats):
                if on_sec > 0:
                    profile.append(min(1.1, on_p))
                if off_sec > 0 and r < repeats - 1:
                    profile.append(max(0.3, off_p))
            if cooldown > 0:
                for i in range(min(max(1, cooldown // 300), 4)):
                    profile.append(max(0.3, 0.6 - 0.1 * i))

            if not profile:
                return ""

            if len(profile) != width:
                step = (len(profile) - 1) / max(1, width - 1)
                profile = [profile[round(i * step)] for i in range(width)]

            lo, hi = min(profile), max(profile)
            span = hi - lo if hi > lo else 1.0
            output = []
            for p in profile:
                idx = max(0, min(len(BLOCKS) - 1, round((p - lo) / span * (len(BLOCKS) - 1))))
                output.append(f"[{self._zone_color(p)}]{BLOCKS[idx]}[/{self._zone_color(p)}]")
            return "".join(output)
        except Exception:
            return ""

    def _today_card_content(self, data):
        if not data["has_plan"]:
            return Static(MSG_NO_PLAN)
        w = data["today_workout"]
        if not w:
            return Static("Hoje não tem treino no plano.")
        container = Vertical(classes="next-card")
        name = w.get("name", "—")
        dur = w.get("planned_duration") or 0
        try:
            dur_m = int(int(dur) // 60)
        except Exception:
            dur_m = 0
        tss = w.get("tss")
        try:
            tss_s = f"{float(tss):.0f}"
        except Exception:
            tss_s = "—"
        focus = w.get("focus", "—")
        container.compose_add_child(Label(f"{w.get('day', 'HOJE')}", classes="next-card-title"))
        container.compose_add_child(Label(f"[{focus}] {name}", classes="next-card-meta"))
        container.compose_add_child(Label(f"{dur_m} min · TSS {tss_s}", classes="next-card-meta"))
        spark = self._profile_sparkline(w)
        if spark:
            container.compose_add_child(Static(spark, classes="next-card-profile"))
        return container

    def _today_card(self, data):
        return self._today_card_content(data)

    def _next_cards(self, data):
        if not data["has_plan"] or not data["next_days"]:
            return Static("Sem próximos treinos.")
        row = Horizontal(classes="next-cards")
        for w in data["next_days"]:
            card = Vertical(classes="next-card")
            d = w.get("day", "—")
            name = w.get("name", "—")
            focus = w.get("focus", "—")
            dur = w.get("planned_duration") or 0
            try:
                dur_m = int(int(dur) // 60)
            except Exception:
                dur_m = 0
            tss = w.get("tss")
            try:
                tss_s = f"{float(tss):.0f}"
            except Exception:
                tss_s = "—"
            card.compose_add_child(Label(f"{d}", classes="next-card-title"))
            card.compose_add_child(Label(f"[{focus}] {name}", classes="next-card-meta"))
            card.compose_add_child(Label(f"{dur_m} min · TSS {tss_s}", classes="next-card-meta"))
            spark = self._profile_sparkline(w)
            if spark:
                card.compose_add_child(Static(spark, classes="next-card-profile"))
            row.compose_add_child(card)
        return row

    def action_quit(self):
        self.app.exit()

    def action_calendar(self):
        from .calendar import CalendarScreen
        self.app.push_screen(CalendarScreen())

    def action_readiness(self):
        from .readiness import ReadinessScreen
        self.app.push_screen(ReadinessScreen())

    def action_settings(self):
        from .preferences import PreferencesScreen
        self.app.push_screen(PreferencesScreen())

    def action_generate(self):
        self._open_operation("build")

    def action_publish(self):
        self._open_operation("push")

    def action_reconcile(self):
        self._open_operation("reconcile")

    def _open_operation(self, name: str) -> None:
        from ..operations import OperationName
        from .operation import OperationModal
        self.app.push_screen(OperationModal(OperationName(name), self._reload))

    def _reload(self) -> None:
        self.refresh(recompose=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_cal":
            self.action_calendar()
        elif event.button.id == "btn_settings":
            self.action_settings()
        elif event.button.id == "btn_gen":
            self.action_generate()
        elif event.button.id == "btn_pub":
            self.action_publish()
        elif event.button.id == "btn_rec":
            self.action_reconcile()
        elif event.button.id == "btn_today":
            from .readiness import ReadinessScreen
            self.app.push_screen(ReadinessScreen())
