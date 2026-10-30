# src/ui/screens/readiness.py
"""Tela de Prontidão (Readiness)"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Grid, Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

try:
    from src.readiness_assessment import (
        READINESS_AXIS_SPECS,
        ReadinessAssessment,
        ReadinessLevel,
    )
except Exception:
    try:
        from readiness_assessment import (
            READINESS_AXIS_SPECS,
            ReadinessAssessment,
            ReadinessLevel,
        )
    except Exception:
        READINESS_AXIS_SPECS = ()
        ReadinessAssessment = None
        ReadinessLevel = None


class ReadinessScreen(Screen):
    CSS = """
    ReadinessScreen {
        background: $surface;
    }

    #header {
        height: 3;
        layout: horizontal;
        align: center middle;
        padding: 0 2;
        background: $boost;
    }

    #title {
        width: 1fr;
        text-style: bold;
    }

    #date {
        width: auto;
        color: $text-muted;
    }

    #overview {
        height: 7;
        layout: horizontal;
        padding: 1 2;
    }

    .ov-card {
        width: 1fr;
        height: 5;
        border: round $panel;
        padding: 0 2;
        align: center middle;
    }

    .overview-good {
        border: round $success;
    }

    .overview-warning {
        border: round $warning;
    }

    .overview-bad {
        border: round $error;
    }

    .ov-label {
        color: $text-muted;
    }

    .ov-value {
        text-style: bold;
        text-align: center;
    }

    .section {
        text-style: bold;
        padding: 1 2 0 2;
    }

    #axes {
        layout: grid;
        grid-size: 2;
        grid-gutter: 1 1;
        padding: 0 2;
    }

    .axis-card {
        height: 5;
        border: round $panel;
        padding: 0 2;
        layout: vertical;
    }

    .axis-good {
        border: round $success;
    }

    .axis-warning {
        border: round $warning;
    }

    .axis-bad {
        border: round $error;
    }

    .axis-missing {
        border: round $panel;
        color: $text-muted;
    }

    .axis-header {
        layout: horizontal;
        height: 1;
    }

    .axis-name {
        width: 1fr;
    }

    .axis-score {
        width: auto;
        color: $text-muted;
    }

    .axis-bar {
        height: 1;
        padding-top: 1;
    }

    #reco {
        padding: 0 3;
    }

    .reco-item {
        color: $text;
    }

    #footnote {
        padding: 1 2 0 2;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Voltar"),
        Binding("h", "back", "Dashboard"),
        Binding("q", "quit", "Sair"),
        Binding("r", "refresh", "Atualizar"),
        Binding("a", "check", "Verificar prontidão"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="header"):
            yield Label("PRONTIDÃO DO DIA", id="title")
            yield Label(date.today().isoformat(), id="date")
        yield Horizontal(id="overview")
        yield Label("EIXOS", classes="section")
        yield Grid(id="axes")
        yield Label("RECOMENDAÇÕES", classes="section")
        yield Vertical(id="reco")
        yield Label("", id="footnote")
        yield Footer()

    def on_mount(self) -> None:
        self._load()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()

    def action_refresh(self) -> None:
        self._load()

    def action_check(self) -> None:
        from ..operations import OperationName
        from .operation import OperationModal
        self.app.push_screen(OperationModal(OperationName.CHECK, self._load))

    def _bar(self, val: float | None) -> str:
        if val is None:
            return "[#777777]sem dados[/#777777]"
        v = max(0.0, min(1.0, float(val)))
        color = "#2fbf71" if v >= .7 else "#f5b942" if v >= .4 else "#ef5350"
        filled = round(v * 12)
        return f"[{color}]{'█' * filled}[/{color}][#3d3d3d]{'░' * (12 - filled)}[/#3d3d3d]"

    def _axis_state(self, val: float | None) -> str:
        if val is None:
            return "missing"
        if val >= .7:
            return "good"
        if val >= .4:
            return "warning"
        return "bad"

    def _state_color(self, state: str) -> str:
        return {
            "good": "#2fbf71",
            "warning": "#f5b942",
            "bad": "#ef5350",
            "missing": "#777777",
        }.get(state, "#777777")

    def _level_style(self, level: str) -> str:
        if level == "green":
            return "bold green"
        if level == "red":
            return "bold red"
        return "bold yellow"

    def _load(self):
        try:
            ov = self.query_one("#overview", Horizontal)
            ov.remove_children()
        except Exception:
            pass
        try:
            axes = self.query_one("#axes", Grid)
            axes.remove_children()
        except Exception:
            pass
        try:
            reco = self.query_one("#reco", Vertical)
            reco.remove_children()
        except Exception:
            pass
        try:
            foot = self.query_one("#footnote", Label)
        except Exception:
            foot = None

        assessment = self._build_assessment()

        if ReadinessAssessment is None or assessment is None:
            try:
                ov.mount(Static("Sem dados de prontidão disponíveis.\nUse 'r' para tentar novamente.", classes="ov-card"))
                if foot:
                    foot.update("Fonte: —")
            except Exception:
                pass
            return

        try:
            level = assessment.level()
            level_str = level.value if hasattr(level, "value") else str(level)
        except Exception:
            level_str = "yellow"

        overall = assessment.overall_readiness
        conf = assessment.confidence
        try:
            adj = assessment.adjustments()
        except Exception:
            adj = ()

        ov = self.query_one("#overview", Horizontal)
        level_state = {"green": "good", "yellow": "warning", "red": "bad"}.get(level_str, "missing")
        c1 = Vertical(classes=f"ov-card overview-{level_state}")
        ov.mount(c1)
        c1.mount(Label("NÍVEL", classes="ov-label"))
        c1.mount(Label(f"[{self._state_color(level_state)}]{level_str.upper()}[/{self._state_color(level_state)}]", classes="ov-value"))

        overall_state = self._axis_state(overall)
        c2 = Vertical(classes=f"ov-card overview-{overall_state}")
        ov.mount(c2)
        c2.mount(Label("PONTUAÇÃO GERAL", classes="ov-label"))
        if overall is None:
            c2.mount(Label("—", classes="ov-value"))
        else:
            color = self._state_color(overall_state)
            c2.mount(Label(f"[{color}]{overall:.2f} / 1.00[/{color}]", classes="ov-value"))

        confidence_state = self._axis_state(conf)
        c3 = Vertical(classes=f"ov-card overview-{confidence_state}")
        ov.mount(c3)
        c3.mount(Label("CONFIANÇA", classes="ov-label"))
        if conf is None:
            c3.mount(Label("—", classes="ov-value"))
        else:
            color = self._state_color(confidence_state)
            c3.mount(Label(f"[{color}]{conf*100:.0f}%[/{color}]", classes="ov-value"))

        axes = self.query_one("#axes", Grid)
        for name, label in READINESS_AXIS_SPECS:
            val = getattr(assessment, name, None)
            state = self._axis_state(val)
            card = Vertical(classes=f"axis-card axis-{state}")
            axes.mount(card)
            hdr = Horizontal(classes="axis-header")
            card.mount(hdr)
            hdr.mount(Label(label, classes="axis-name"))
            if val is None:
                hdr.mount(Label("—", classes="axis-score"))
            else:
                hdr.mount(Label(f"{val:.2f}", classes="axis-score"))
            card.mount(Static(self._bar(val), classes="axis-bar"))

        reco = self.query_one("#reco", Vertical)
        if not adj:
            reco.mount(Label("• Sem ajustes recomendados. Pode seguir o plano normalmente.", classes="reco-item"))
        else:
            for a in adj:
                if a == "intensity":
                    reco.mount(Label("• Reduzir intensidade dos blocos de qualidade.", classes="reco-item"))
                elif a == "volume":
                    reco.mount(Label("• Reduzir volume ou duração da sessão.", classes="reco-item"))
                elif a == "intervals":
                    reco.mount(Label("• Evitar ou adiar intervalos de alta intensidade.", classes="reco-item"))
                elif a == "recovery":
                    reco.mount(Label("• Priorizar recuperação ativa ou descanso.", classes="reco-item"))
                else:
                    reco.mount(Label(f"• Ajuste: {a}", classes="reco-item"))

        if foot:
            try:
                from ..utils import get_app
                app = get_app()
                client = app.client()
                inner = getattr(client, '_client', None) or getattr(client, 'client', None)
                if inner is None and hasattr(client, 'wellness'):
                    inner = client
                data = []
                try:
                    newest = date.today()
                    oldest = newest - timedelta(days=60)
                    data = inner.wellness(oldest=oldest.isoformat(), newest=newest.isoformat()) or []
                except Exception:
                    try:
                        data = inner.wellness() or []
                    except Exception:
                        data = []
                def _key(x):
                    if not isinstance(x, dict): return ""
                    return x.get('id') or x.get('date') or x.get('day') or ""
                ds = sorted([x for x in data if isinstance(x,dict)], key=_key, reverse=True)
                w = None
                for item in ds:
                    if any(item.get(k) is not None for k in ['restingHR','rhr','hrv','hrvSDNN','rmssd','sleepScore','sleepSecs','readiness','fatigue','soreness','stress','mood']):
                        w = item
                        break
                if w is None and ds: w = ds[0]
                d = w.get('id') or w.get('date') or '' if isinstance(w,dict) else ''
                foot.update(f"Fonte: Intervals.icu (wellness) • Dia: {d} • Prontidão = apoio à decisão, não diagnóstico clínico")
            except Exception:
                foot.update("Fonte: Intervals.icu (wellness) • Prontidão = apoio à decisão, não diagnóstico clínico")

    def _build_assessment(self):
        if ReadinessAssessment is None:
            return None
        try:
            from ..utils import get_app
            app = get_app()
            client = app.client()
            inner = getattr(client, '_client', None) or getattr(client, 'client', None)
            if inner is None and hasattr(client, 'wellness'):
                inner = client
            if inner is None or not hasattr(inner, 'wellness'):
                return None

            data = []
            try:
                newest = date.today()
                oldest = newest - timedelta(days=60)
                data = inner.wellness(oldest=oldest.isoformat(), newest=newest.isoformat()) or []
            except Exception:
                try:
                    data = inner.wellness() or []
                except Exception:
                    data = []

            if not data:
                return None

            # Ordenar por data mais recente
            def _key(x):
                if not isinstance(x, dict):
                    return ""
                return x.get('id') or x.get('date') or x.get('day') or ""
            data_sorted = sorted([x for x in data if isinstance(x, dict)], key=_key, reverse=True)

            w = None
            for item in data_sorted:
                if any(item.get(k) is not None for k in ['restingHR', 'rhr', 'hrv', 'hrvSDNN', 'rmssd', 'sleepScore', 'sleep_secs', 'sleepSecs', 'readiness', 'readiness_score', 'fatigue', 'soreness', 'stress', 'mood', 'motivation']):
                    w = item
                    break
            if w is None and data_sorted:
                w = data_sorted[0]
            if not isinstance(w, dict):
                return None

            def _f(v):
                try:
                    if v is None:
                        return None
                    f = float(v)
                    if f > 1.0 and f <= 100.0:
                        return f / 100.0
                    if f > 100.0:
                        return None
                    if f < 0.0:
                        return None
                    return f
                except Exception:
                    return None

            def _inv_f(v):
                try:
                    if v is None:
                        return None
                    f = float(v)
                    if f > 1.0 and f <= 100.0:
                        f = f / 100.0
                    if f < 0.0 or f > 1.0:
                        return None
                    return 1.0 - f
                except Exception:
                    return None

            hrv = _f(w.get('hrv') or w.get('hrvSDNN') or w.get('rmssd') or w.get('lnRmssd'))
            rhr = _inv_f(w.get('restingHR') or w.get('rhr') or w.get('resting_hr'))
            sleep = _f(w.get('sleepScore') or w.get('sleep_score'))
            if sleep is None and w.get('sleepSecs') is not None:
                try:
                    s = float(w.get('sleepSecs')) / 3600.0
                    if 4.0 <= s <= 9.5:
                        sleep = min(1.0, max(0.0, (s - 4.0) / 5.5))
                except Exception:
                    pass
            fatigue = _inv_f(w.get('fatigue') or w.get('soreness'))
            stress = _inv_f(w.get('stress'))
            mood = _f(w.get('mood') or w.get('motivation'))
            readiness_raw = _f(w.get('readiness') or w.get('readiness_score'))

            return ReadinessAssessment(
                hrv_score=hrv,
                rhr_score=rhr,
                sleep_score=sleep,
                subjective_fatigue_score=fatigue,
                recent_load_score=stress,
                performance_score=readiness_raw,
                consistency_score=mood,
            )
        except Exception:
            return None
        return None
