# src/ui/screens/calendar.py
"""Tela Calendário - Visão em cards (Mensal / Semanal)"""

from __future__ import annotations

import calendar
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Dict

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Header, Label

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

try:
    from src.plan import load_plan
except Exception:
    try:
        from plan import load_plan
    except Exception:
        load_plan = None

from .calendar_detail import CalendarDetailScreen

PLAN = ROOT / "plan.json"
WEEKDAYS = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


BLOCKS = " ▁▂▃▄▅▆▇█"


class CalendarScreen(Screen):
    CSS = """
    CalendarScreen {
        layout: vertical;
        background: $surface;
    }

    #nav {
        height: 3;
        layout: horizontal;
        align: center middle;
        padding: 0 2;
    }

    #title {
        width: 1fr;
        content-align: center middle;
        text-style: bold;
    }

    #view-label {
        width: auto;
        padding: 0 2;
        content-align: center middle;
        color: $text-muted;
    }

    #body {
        height: 1fr;
        padding: 1 2;
    }

    .month-grid {
        layout: grid;
        grid-size: 7;
        grid-gutter: 1 1;
    }

    .week-grid {
        layout: grid;
        grid-size: 7;
        grid-gutter: 1 1;
    }

    .week-summary {
        height: 7;
        border: round $panel;
        padding: 0 1;
        margin-bottom: 1;
    }

    .week-summary-title {
        text-style: bold;
    }

    .week-summary-muted {
        color: $text-muted;
    }

    .weekday-header {
        height: 1;
        content-align: center middle;
        text-style: bold;
        color: $text-muted;
    }

    .day-card {
        height: 10;
        border: round $panel;
        padding: 0 1;
        layout: vertical;
    }

    .day-card.today {
        border: round $accent;
    }

    .day-card.has-workout {
        border: round $success;
    }

    .day-card.selected {
        border: heavy $warning;
    }

    .day-card.outside {
        border: round $surface-darken-1;
        color: $text-disabled;
    }

    .day-header {
        height: 1;
        layout: horizontal;
    }

    .day-number {
        width: 1fr;
        text-style: bold;
    }

    .day-dow {
        width: auto;
        color: $text-muted;
    }

    .workout-name {
        height: auto;
    }

    .workout-meta {
        height: auto;
        color: $text-muted;
    }

    .workout-profile {
        height: auto;
        color: $warning;
        padding-top: 1;
    }

    .rest-label {
        height: 1fr;
        content-align: center middle;
        color: $text-disabled;
    }

    .legend {
        height: 2;
        layout: horizontal;
        align: center middle;
        dock: bottom;
    }

    .legend-item {
        margin: 0 1;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("left", "nav_left", "Anterior/Navegar"),
        Binding("right", "nav_right", "Próximo/Navegar"),
        Binding("up", "nav_up", "Cima"),
        Binding("down", "nav_down", "Baixo"),
        Binding("enter", "open_detail", "Detalhes"),
        Binding("space", "open_detail", "Detalhes"),
        Binding("v", "toggle_view", "Mês/Semana"),
        Binding("m", "month_view", "Mensal"),
        Binding("w", "week_view", "Semanal"),
        Binding("escape", "back", "Voltar"),
        Binding("h", "back", "Dashboard"),
        Binding("q", "quit", "Sair"),
    ]

    def __init__(self):
        super().__init__()
        self.view_mode = "month"
        self.current_date = date.today()
        self.selected_date = date.today()
        self._workouts_cache = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="nav"):
            yield Button("<", id="btn_prev", variant="default")
            yield Label("", id="title")
            yield Button(">", id="btn_next", variant="default")
            yield Label("", id="view-label")
        yield Container(id="body")
        with Horizontal(classes="legend"):
            yield Label("● Hoje", classes="legend-item")
            yield Label("● Com treino", classes="legend-item")
            yield Label("● Descanso", classes="legend-item")
            yield Label("[v/m/w] Alternar | [←/→/↑/↓] Navegar | [Enter] Detalhes", classes="legend-item")
        yield Footer()

    def on_mount(self) -> None:
        self._refresh()
        try:
            for b in self.query(Button):
                try:
                    b.can_focus = False
                    b.disabled = True
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.focus()
        except Exception:
            pass

    def on_show(self) -> None:
        try:
            self.focus()
        except Exception:
            pass
        try:
            for b in self.query(Button):
                try:
                    b.can_focus = False
                    b.disabled = True
                except Exception:
                    pass
        except Exception:
            pass

    def on_focus(self) -> None:
        try:
            for b in self.query(Button):
                try:
                    b.can_focus = False
                    b.disabled = True
                except Exception:
                    pass
        except Exception:
            pass

    def on_blur(self) -> None:
        try:
            self.focus()
        except Exception:
            pass

    def _get_title(self) -> str:
        if self.view_mode == "month":
            return f"{calendar.month_name[self.current_date.month]} {self.current_date.year}"
        ws = self._week_start(self.current_date)
        we = ws + timedelta(days=6)
        if ws.month == we.month and ws.year == we.year:
            return f"Semana {ws.day} - {we.day} de {calendar.month_name[ws.month]} {ws.year}"
        if ws.year == we.year:
            return f"Semana {ws.day}/{ws.month} - {we.day}/{we.month} {ws.year}"
        return f"Semana {ws.day}/{ws.month}/{ws.year} - {we.day}/{we.month}/{we.year}"

    def _week_start(self, d: date) -> date:
        return d - timedelta(days=d.weekday())

    def _load_workouts(self) -> Dict[str, dict]:
        out = {}
        try:
            plan = None
            if load_plan is not None:
                plan = load_plan(PLAN)
            if plan is None:
                import json
                try:
                    with open(PLAN) as f:
                        plan = json.load(f)
                except Exception:
                    pass
            if isinstance(plan, dict):
                workouts = plan.get("workouts") or plan.get("plan") or plan.get("items") or []
            elif isinstance(plan, list):
                workouts = plan
            else:
                workouts = []
            if isinstance(workouts, list):
                for w in workouts:
                    if not isinstance(w, dict):
                        continue
                    day = w.get("day") or w.get("date")
                    if day:
                        dkey = str(day)
                        if dkey not in out:
                            out[dkey] = {}
                        out[dkey]["planned"] = w

            # Carregar histórico do Intervals.icu (activities)
            try:
                from ..utils import get_app
                from datetime import date, timedelta
                app = get_app()
                client = app.client()
                inner = getattr(client, '_client', None) or getattr(client, 'client', None)
                if inner is None and hasattr(client, 'activities'):
                    inner = client
                if inner is not None and hasattr(inner, 'activities'):
                    newest = date.today()
                    oldest = newest - timedelta(days=365)
                    acts = inner.activities(oldest=oldest.isoformat(), newest=newest.isoformat()) or []
                    for a in acts:
                        if not isinstance(a, dict):
                            continue
                        start = a.get("start_date_local") or a.get("start_date") or ""
                        if not start:
                            continue
                        dkey = start[:10]
                        if dkey not in out:
                            out[dkey] = {}
                        # Só considerar atividades com treino/carga
                        tss = a.get("icu_training_load") or a.get("training_load") or a.get("tss")
                        name = a.get("name") or a.get("type") or "Atividade"
                        candidate = {
                            "id": a.get("id"),
                            "name": name,
                            "tss": tss,
                            "duration": a.get("moving_time") or a.get("elapsed_time") or a.get("icu_training_time"),
                            "type": a.get("type"),
                            "source": a.get("source") or "intervals",
                            "icu_training_load": a.get("icu_training_load"),
                            "average_watts": a.get("average_watts"),
                            "normalized_power": a.get("icu_weighted_avg_watts") or a.get("normalized_power"),
                            "max_watts": a.get("max_watts"),
                            "distance": a.get("distance"),
                        }
                        # Podem existir dois registros no mesmo dia (por exemplo,
                        # um evento/manual e o FIT do Zwift). Mantemos a atividade
                        # com maior evidência de dados reais, nunca a última resposta
                        # arbitrariamente recebida da API.
                        existing = out[dkey].get("done")
                        def evidence_score(activity):
                            if not activity:
                                return -1
                            score = 0
                            if activity.get("tss") is not None:
                                score += 4
                            if activity.get("duration") is not None:
                                score += 3
                            if activity.get("average_watts") is not None:
                                score += 2
                            if activity.get("source") not in (None, "MANUAL"):
                                score += 1
                            return score
                        if evidence_score(candidate) > evidence_score(existing):
                            out[dkey]["done"] = candidate
            except Exception:
                pass
        except Exception:
            return out
        return out

    def _profile_sparkline(self, w: dict, width: int = 14) -> str:
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

            # Build normalized profile
            profile = []
            if warmup > 0:
                # ramp up
                for i in range(min(warmup // 60 or 1, 3)):
                    profile.append(0.4 + 0.2 * i)
            for r in range(repeats):
                if on_sec > 0:
                    profile.append(min(1.0, on_p))
                if off_sec > 0 and r < repeats - 1:
                    profile.append(max(0.3, off_p))
            if cooldown > 0:
                for i in range(min(cooldown // 60 or 1, 3)):
                    profile.append(0.6 - 0.2 * i)

            if not profile:
                return ""

            # Normalize to blocks
            lo, hi = min(profile), max(profile)
            span = hi - lo if hi - lo > 0 else 1.0
            out = []
            for v in profile[:width]:
                idx = int((v - lo) / span * (len(BLOCKS) - 1))
                idx = max(0, min(len(BLOCKS) - 1, idx))
                out.append(BLOCKS[idx])
            return "".join(out)
        except Exception:
            return ""

    def _render_week_summary(self, body: Container, workouts: dict) -> None:
        from ..training_review import week_summary

        summary = week_summary(workouts, self._week_start(self.current_date), date.today())

        def minutes(seconds: int) -> int:
            return seconds // 60

        def zones(values: dict[str, float]) -> str:
            if not values:
                return "—"
            return " · ".join(f"{zone} {int(seconds // 60)}m" for zone, seconds in values.items())

        box = Vertical(classes="week-summary")
        body.mount(box)
        box.mount(Label("RESUMO SEMANAL", classes="week-summary-title"))
        box.mount(Label(f"Planejado: {minutes(summary.planned_duration_seconds)}m · TSS{summary.planned_tss:.0f}"))
        box.mount(Label(f"Realizado: {minutes(summary.actual_duration_seconds)}m · TSS{summary.actual_tss:.0f}"))
        box.mount(Label(
            f"{summary.completed} realizado · {summary.missed} perdido · "
            f"{summary.pending} pendente · {summary.extra} extra",
            classes="week-summary-muted",
        ))
        box.mount(Label("Zonas planejadas:", classes="week-summary-muted"))
        box.mount(Label(zones(summary.planned_zone_seconds), classes="week-summary-muted"))
        actual = zones(summary.actual_zone_seconds) if summary.actual_zone_seconds is not None else "indisponível"
        box.mount(Label(f"Zonas realizadas: {actual}", classes="week-summary-muted"))

    def _refresh(self) -> None:
        try:
            title = self.query_one("#title", Label)
            title.update(self._get_title())
        except Exception:
            pass
        try:
            vl = self.query_one("#view-label", Label)
            vl.update("[ MENSAL ]" if self.view_mode == "month" else "[ SEMANAL ]")
        except Exception:
            pass

        try:
            body = self.query_one("#body", Container)
            body.remove_children()
        except Exception:
            return

        workouts = self._load_workouts()
        self._workouts_cache = workouts
        today = date.today()
        if not hasattr(self, 'selected_date') or self.selected_date is None:
            self.selected_date = today
        if not hasattr(self, 'current_date') or self.current_date is None:
            self.current_date = today

        if self.view_mode == "month":
            grid = Grid(classes="month-grid")
            body.mount(grid)
            for wd in WEEKDAYS:
                grid.mount(Label(wd, classes="weekday-header"))
            cal = calendar.Calendar(firstweekday=0)
            for week in cal.monthdayscalendar(self.current_date.year, self.current_date.month):
                for day_num in week:
                    if day_num == 0:
                        card = Vertical(classes="day-card outside")
                        grid.mount(card)
                        hdr = Horizontal(classes="day-header")
                        card.mount(hdr)
                        hdr.mount(Label("—", classes="day-number"))
                        card.mount(Label("—", classes="rest-label"))
                        continue

                    d = date(self.current_date.year, self.current_date.month, day_num)
                    iso = d.isoformat()
                    cls = "day-card"
                    if d == today:
                        cls += " today"
                    if d == getattr(self, 'selected_date', today):
                        cls += " selected"
                    entry = workouts.get(iso)
                    if entry:
                        cls += " has-workout"
                    card = Vertical(classes=cls)
                    grid.mount(card)
                    hdr = Horizontal(classes="day-header")
                    card.mount(hdr)
                    hdr.mount(Label(str(day_num), classes="day-number"))
                    hdr.mount(Label(WEEKDAYS[d.weekday()], classes="day-dow"))

                    entry = workouts.get(iso)
                    if entry:
                        planned = entry.get("planned")
                        done = entry.get("done")
                        if planned and done:
                            w = planned
                            name = str(w.get("name", "Treino"))
                            focus = w.get("focus", "")
                            dur = int(w.get("planned_duration", 0) or 0) // 60
                            tss = w.get("tss", 0)
                            try:
                                tss_s = f"{float(tss):.0f}"
                            except Exception:
                                tss_s = str(tss)
                            card.mount(Label(name[:24], classes="workout-name"))
                            prof = self._profile_sparkline(w, width=12)
                            if prof:
                                card.mount(Label(prof, classes="workout-profile"))
                            card.mount(Label(f"[REALIZADO] {dur}m TSS{tss_s}", classes="workout-meta"))
                        elif done and not planned:
                            dname = str(done.get("name", "Atividade"))
                            tss = done.get("tss") or 0
                            dur = done.get("duration") or 0
                            try:
                                tss_s = f"{float(tss):.0f}" if tss else "—"
                            except Exception:
                                tss_s = str(tss)
                            try:
                                dur_m = int(float(dur) // 60)
                            except Exception:
                                dur_m = 0
                            card.mount(Label(dname[:24], classes="workout-name"))
                            card.mount(Label(f"[EXTRA] {dur_m}m TSS{tss_s}", classes="workout-meta"))
                        elif planned and not done:
                            w = planned
                            name = str(w.get("name", "Treino"))
                            focus = w.get("focus", "")
                            dur = int(w.get("planned_duration", 0) or 0) // 60
                            tss = w.get("tss", 0)
                            try:
                                tss_s = f"{float(tss):.0f}"
                            except Exception:
                                tss_s = str(tss)
                            card.mount(Label(name[:24], classes="workout-name"))
                            prof = self._profile_sparkline(w, width=12)
                            if prof:
                                card.mount(Label(prof, classes="workout-profile"))
                            card.mount(Label(f"[PLANEJADO • NÃO REALIZADO] {dur}m", classes="workout-meta"))
                    else:
                        card.mount(Label("Descanso", classes="rest-label"))
        else:
            self._render_week_summary(body, workouts)
            grid = Grid(classes="week-grid")
            body.mount(grid)
            for wd in WEEKDAYS:
                grid.mount(Label(wd, classes="weekday-header"))
            ws = self._week_start(self.current_date)
            for i in range(7):
                d = ws + timedelta(days=i)
                iso = d.isoformat()
                cls = "day-card"
                if d == today:
                    cls += " today"
                if d == getattr(self, 'selected_date', today):
                    cls += " selected"
                entry = workouts.get(iso)
                if entry:
                    cls += " has-workout"
                card = Vertical(classes=cls)
                grid.mount(card)
                hdr = Horizontal(classes="day-header")
                card.mount(hdr)
                hdr.mount(Label(f"{d.day}/{d.month}", classes="day-number"))
                hdr.mount(Label(WEEKDAYS[d.weekday()], classes="day-dow"))

                entry = workouts.get(iso)
                if entry:
                    planned = entry.get("planned")
                    done = entry.get("done")
                    if planned and done:
                        w = planned
                        name = str(w.get("name", "Treino"))
                        focus = w.get("focus", "")
                        dur = int(w.get("planned_duration", 0) or 0) // 60
                        tss = w.get("tss", 0)
                        try:
                            tss_s = f"{float(tss):.0f}"
                        except Exception:
                            tss_s = str(tss)
                        card.mount(Label(name[:22], classes="workout-name"))
                        prof = self._profile_sparkline(w, width=14)
                        if prof:
                            card.mount(Label(prof, classes="workout-profile"))
                        card.mount(Label(f"[REALIZADO] {dur}m TSS{tss_s}", classes="workout-meta"))
                    elif done and not planned:
                        dname = str(done.get("name", "Atividade"))
                        tss = done.get("tss") or 0
                        dur = done.get("duration") or 0
                        try:
                            tss_s = f"{float(tss):.0f}" if tss else "—"
                        except Exception:
                            tss_s = str(tss)
                        try:
                            dur_m = int(float(dur) // 60)
                        except Exception:
                            dur_m = 0
                        card.mount(Label(dname[:22], classes="workout-name"))
                        card.mount(Label(f"[EXTRA] {dur_m}m TSS{tss_s}", classes="workout-meta"))
                    elif planned and not done:
                        w = planned
                        name = str(w.get("name", "Treino"))
                        focus = w.get("focus", "")
                        dur = int(w.get("planned_duration", 0) or 0) // 60
                        tss = w.get("tss", 0)
                        try:
                            tss_s = f"{float(tss):.0f}"
                        except Exception:
                            tss_s = str(tss)
                        card.mount(Label(name[:22], classes="workout-name"))
                        prof = self._profile_sparkline(w, width=14)
                        if prof:
                            card.mount(Label(prof, classes="workout-profile"))
                        card.mount(Label(f"[PLANEJADO • NÃO REALIZADO] {dur}m", classes="workout-meta"))
                else:
                    card.mount(Label("Descanso", classes="rest-label"))

    def action_prev(self) -> None:
        if not hasattr(self, 'selected_date'):
            self.selected_date = self.current_date
        if self.view_mode == "month":
            m = self.current_date.month - 1
            y = self.current_date.year
            if m == 0:
                m = 12
                y -= 1
            self.current_date = self.current_date.replace(year=y, month=m, day=1)
            try:
                self.selected_date = self.selected_date.replace(year=y, month=m, day=min(self.selected_date.day, calendar.monthrange(y, m)[1]))
            except Exception:
                self.selected_date = date(y, m, 1)
        else:
            self.current_date = self.current_date - timedelta(days=7)
            self.selected_date = self.selected_date - timedelta(days=7)
        self._refresh()

    def action_next(self) -> None:
        if not hasattr(self, 'selected_date'):
            self.selected_date = self.current_date
        if self.view_mode == "month":
            m = self.current_date.month + 1
            y = self.current_date.year
            if m == 13:
                m = 1
                y += 1
            self.current_date = self.current_date.replace(year=y, month=m, day=1)
            try:
                self.selected_date = self.selected_date.replace(year=y, month=m, day=min(self.selected_date.day, calendar.monthrange(y, m)[1]))
            except Exception:
                self.selected_date = date(y, m, 1)
        else:
            self.current_date = self.current_date + timedelta(days=7)
            self.selected_date = self.selected_date + timedelta(days=7)
        self._refresh()

    def action_nav_left(self) -> None:
        if not hasattr(self, 'selected_date'):
            self.selected_date = self.current_date
        self.selected_date = self.selected_date - timedelta(days=1)
        if self.view_mode == "month" and self.selected_date.month != self.current_date.month:
            self.current_date = self.selected_date.replace(day=1)
        elif self.view_mode == "week":
            ws = self._week_start(self.selected_date)
            if ws != self._week_start(self.current_date):
                self.current_date = self.selected_date
        self._refresh()

    def action_nav_right(self) -> None:
        if not hasattr(self, 'selected_date'):
            self.selected_date = self.current_date
        self.selected_date = self.selected_date + timedelta(days=1)
        if self.view_mode == "month" and self.selected_date.month != self.current_date.month:
            self.current_date = self.selected_date.replace(day=1)
        elif self.view_mode == "week":
            ws = self._week_start(self.selected_date)
            if ws != self._week_start(self.current_date):
                self.current_date = self.selected_date
        self._refresh()

    def action_nav_up(self) -> None:
        if not hasattr(self, 'selected_date'):
            self.selected_date = self.current_date
        self.selected_date = self.selected_date - timedelta(days=7)
        if self.view_mode == "month" and self.selected_date.month != self.current_date.month:
            self.current_date = self.selected_date.replace(day=1)
        elif self.view_mode == "week":
            self.current_date = self.selected_date
        self._refresh()

    def action_nav_down(self) -> None:
        if not hasattr(self, 'selected_date'):
            self.selected_date = self.current_date
        self.selected_date = self.selected_date + timedelta(days=7)
        if self.view_mode == "month" and self.selected_date.month != self.current_date.month:
            self.current_date = self.selected_date.replace(day=1)
        elif self.view_mode == "week":
            self.current_date = self.selected_date
        self._refresh()

    def action_open_detail(self) -> None:
        if not hasattr(self, 'selected_date'):
            self.selected_date = getattr(self, 'current_date', date.today())
        iso = self.selected_date.isoformat()
        entry = getattr(self, '_workouts_cache', {}).get(iso) or {}
        self.app.push_screen(CalendarDetailScreen(iso, entry))

    def action_toggle_view(self) -> None:
        self.view_mode = "week" if self.view_mode == "month" else "month"
        self._refresh()

    def action_month_view(self) -> None:
        self.view_mode = "month"
        self._refresh()

    def action_week_view(self) -> None:
        self.view_mode = "week"
        self._refresh()

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        try:
            event.stop()
        except Exception:
            pass
        if event.button.id == "btn_prev":
            self.action_prev()
        elif event.button.id == "btn_next":
            self.action_next()
