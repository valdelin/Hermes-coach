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
from textual.containers import Container, Grid, Horizontal, Vertical, VerticalScroll
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
from ..training_review import planned_workout_summary, week_summary
from ..history import compare_power_structure, historical_power_steps, link_activities, sample_power_steps
try:
    from src.coach import (
        FOCUS_ZONE1_RECOVERY,
        FOCUS_ZONE2_ENDURANCE,
        FOCUS_ZONE3_TEMPO,
        FOCUS_ZONE4_LIMIAR,
        FOCUS_ZONE5_VO2MAX,
        FOCUS_ZONE6_ANAEROBICA,
        ZONE_SWEETSPOT,
    )
except Exception:
    FOCUS_ZONE1_RECOVERY = "z1_recovery"
    FOCUS_ZONE2_ENDURANCE = "zone2"
    FOCUS_ZONE3_TEMPO = "z3_tempo"
    FOCUS_ZONE4_LIMIAR = "threshold"
    FOCUS_ZONE5_VO2MAX = "vo2max"
    FOCUS_ZONE6_ANAEROBICA = "z6_anaerobica"
    ZONE_SWEETSPOT = "sweetspot"

PLAN = ROOT / "plan.json"
WEEKDAYS = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


BLOCKS = "▁▂▃▄▅▆▇█"

ZONE_COLORS = (
    "#4d9bff",  # Z1
    "#ffd93b",  # Z2
    "#ff9f1a",  # Z3
    "#ff6b35",  # Sweet Spot
    "#ff3b30",  # Z4
    "#d946ef",  # Z5
    "#8b5cf6",  # Z6
)


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

    .month-scroll {
        height: 1fr;
        width: 1fr;
    }

    .month-grid {
        layout: grid;
        grid-size: 7;
        grid-gutter: 0 1;
        /* Sem `grid-rows` as 7 linhas viram 1fr cada e a semana que sobra
           encolhe os cartoes: o perfil era cortado nas linhas mais baixas.
           A primeira linha e o cabecalho (SEG..DOM); as outras sao semanas. */
        grid-rows: 1 6 6 6 6 6 6;
    }

    .week-grid {
        layout: grid;
        grid-size: 7;
        grid-gutter: 1 1;
        /* Mesmo motivo do mes: sem `grid-rows` o cabecalho SEG..DOM vira
           uma linha 1fr e rouba metade da altura dos cartoes. */
        grid-rows: 1 10;
    }

    .day-card.week-cell {
        height: 10;
    }

    .week-summary {
        height: auto;
        min-height: 9;
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

    .day-card.month-cell {
        height: 6;
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
        height: 1;
        overflow: hidden;
    }

    .workout-meta {
        height: 1;
        overflow: hidden;
        color: $text-muted;
    }

    .workout-profile {
        height: 1;
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
        self._activity_profile_cache = {}
        self._activity_zone_cache = {}
        self._intervals_client = None

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

    def _today(self) -> date:
        """Data de referência do resumo semanal; sobrescrita em teste."""
        return date.today()

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
                        out[dkey].setdefault("local_plans", []).append(w)
                        out[dkey].setdefault("planned", w)
                        out[dkey]["matching_required"] = True

            # Consulta de histórico é somente leitura; a falha não apaga o plano.
            self._history_unavailable = False
            try:
                from ..utils import get_app
                app = get_app()
                client = app.client()
                inner = getattr(client, '_client', None) or getattr(client, 'client', None)
                if inner is None:
                    inner = client
                if inner is not None and hasattr(client, 'events'):
                    self._intervals_client = inner
                    newest = max(date.today(), self.current_date.replace(day=1) + timedelta(days=41))
                    oldest = min(date.today() - timedelta(days=365), self.current_date.replace(day=1) - timedelta(days=6))
                    try:
                        acts = inner.activities(oldest=oldest.isoformat(), newest=newest.isoformat()) or []
                    except Exception:
                        acts = []
                        self._history_unavailable = True
                    try:
                        events = client.events(oldest=oldest.isoformat(), newest=newest.isoformat()) or []
                    except Exception:
                        events = []
                        self._history_unavailable = True
                    events = [e if isinstance(e, dict) else getattr(e, "raw", None)
                              for e in events]
                    events = [e for e in events if isinstance(e, dict)
                              and str(e.get("external_id") or "").startswith("hermes-plan-")]
                    external_counts = {}
                    for event in events:
                        external_id = event.get("external_id")
                        external_counts[external_id] = external_counts.get(external_id, 0) + 1
                    acts = [a for a in acts if isinstance(a, dict)]
                    links = link_activities(events, acts)
                    by_id = {str(a.get("id")): a for a in links.activities if a.get("id") is not None}
                    local_days = {}
                    for local_day, local_entry in out.items():
                        for local_plan in local_entry.get("local_plans", []):
                            if local_plan.get("external_id"):
                                local_days.setdefault(local_plan["external_id"], set()).add(local_day)
                    event_days = {}
                    for event in events:
                        day = str(event.get("start_date_local") or "")[:10]
                        if not day:
                            continue
                        eid = str(event.get("id"))
                        event_days[eid] = day
                        entry = out.setdefault(day, {})
                        entry["matching_required"] = True
                        other_days = local_days.get(event.get("external_id"), set()) - {day}
                        if other_days:
                            entry["plan_divergence"] = True
                            for other_day in other_days:
                                out[other_day]["plan_divergence"] = True
                        planned = {"day": day, "name": event.get("name"),
                                   "planned_duration": event.get("moving_time"),
                                   "tss": event.get("icu_training_load"),
                                   "origin": "intervals", "event_id": eid,
                                   "external_id": event.get("external_id"),
                                   "historical_power_steps": historical_power_steps(event)}
                        if other_days:
                            planned["shadowed_by_local"] = True
                        entry.setdefault("remote_plans", []).append(planned)
                        for local in entry.get("local_plans", []):
                            if not local.get("external_id") or local.get("external_id") != planned["external_id"]:
                                continue
                            equal_structure = compare_power_structure(local, planned["historical_power_steps"])
                            if equal_structure is None:
                                entry["structure_comparison_unavailable"] = True
                            if equal_structure is False or any(
                                    local.get(k) is not None and planned.get(k) is not None
                                    and local[k] != planned[k]
                                    for k in ("name", "planned_duration", "tss")):
                                entry["plan_divergence"] = True
                        if not other_days:
                            entry.setdefault("planned", planned)
                        if (entry.get("planned", {}).get("origin") != "intervals" and
                                external_counts.get(planned["external_id"], 0) > 1):
                            entry["matching_unavailable"] = True
                        aid = links.event_activity.get(eid)
                        activity = by_id.get(aid) if aid else None
                        actual_day = str(activity.get("start_date_local") or "")[:10] if activity else ""
                        if actual_day and actual_day != day:
                            entry["linked_activity_day"] = actual_day
                        elif actual_day == day and aid:
                            primary = entry.get("planned", {})
                            if ((primary.get("origin") == "intervals" and primary.get("event_id") == eid)
                                    or (primary.get("origin") != "intervals" and
                                        primary.get("external_id") == planned["external_id"] and
                                        external_counts.get(planned["external_id"], 0) == 1)):
                                entry["matched_activity_id"] = aid
                        if actual_day == day and aid:
                            entry.setdefault("matches_by_event", {})[eid] = aid
                            if external_counts.get(planned["external_id"], 0) == 1:
                                entry.setdefault("matches_by_external", {})[planned["external_id"]] = aid
                    for a in links.activities:
                        if not isinstance(a, dict):
                            continue
                        start = a.get("start_date_local") or ""
                        if not start:
                            self._history_unavailable = True
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
                        eid = links.activity_event.get(str(a.get("id")))
                        if eid and eid in event_days:
                            candidate["planned_day"] = event_days[eid]
                            candidate["planned_event_id"] = eid
                        out[dkey].setdefault("activities", []).append(candidate)
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
                        matched = out[dkey].get("matched_activity_id")
                        candidate_matched = matched is not None and str(candidate.get("id")) == str(matched)
                        existing_matched = matched is not None and existing is not None and str(existing.get("id")) == str(matched)
                        if candidate_matched or (not existing_matched and evidence_score(candidate) > evidence_score(existing)):
                            out[dkey]["done"] = candidate
                else:
                    self._history_unavailable = True
            except Exception:
                self._history_unavailable = True
        except Exception:
            return out
        if self._history_unavailable:
            for entry in out.values():
                entry["matching_unavailable"] = True
        return out

    def _zone_color(self, intensity: float) -> str:
        if intensity < .56:
            return ZONE_COLORS[0]
        if intensity < .76:
            return ZONE_COLORS[1]
        if intensity < .84:
            return ZONE_COLORS[2]
        if intensity <= .97:
            return ZONE_COLORS[3]
        if intensity <= 1.05:
            return ZONE_COLORS[4]
        if intensity <= 1.20:
            return ZONE_COLORS[5]
        return ZONE_COLORS[6]

    def _render_profile(self, intensities: list[float]) -> str:
        if not intensities:
            return ""
        lo, hi = min(intensities), max(intensities)
        span = hi - lo if hi > lo else 1.0
        output = []
        for intensity in intensities:
            index = max(0, min(len(BLOCKS) - 1,
                               round((intensity - lo) / span * (len(BLOCKS) - 1))))
            color = self._zone_color(intensity)
            output.append(f"[{color}]{BLOCKS[index]}[/{color}]")
        return "".join(output)

    def _activity_profile_sparkline(self, activity: dict, width: int = 14) -> str:
        """Mini-perfil real de potência de uma atividade do Intervals.icu."""
        activity_id = activity.get("id")
        if not activity_id:
            return ""
        cache_key = (activity_id, width)
        if cache_key in self._activity_profile_cache:
            return self._activity_profile_cache[cache_key]
        try:
            client = self._intervals_client
            if client is None:
                from ..utils import get_app
                app_client = get_app().client()
                client = getattr(app_client, "_client", None) or getattr(app_client, "client", None) or app_client
                self._intervals_client = client
            detail = client.activity(activity_id) or {}
            streams = client.activity_streams(activity_id, types=("watts", "time")) or {}
            watts = streams.get("watts") or []
            ftp = detail.get("icu_ftp") or detail.get("icu_pm_ftp")
            ftp = float(ftp) if ftp else None
            if not watts or not ftp or ftp <= 0:
                result = ""
            else:
                sample_count = min(width, len(watts))
                intensities = []
                for i in range(sample_count):
                    value = watts[round(i * (len(watts) - 1) / max(1, sample_count - 1))]
                    intensities.append(max(0.0, float(value)) / ftp)
                result = self._render_profile(intensities)
        except Exception:
            result = ""
        self._activity_profile_cache[cache_key] = result
        return result

    def _profile_sparkline(self, w: dict, width: int = 14) -> str:
        try:
            if w.get("origin") == "intervals":
                samples = sample_power_steps(w.get("historical_power_steps") or (), width)
                return self._render_profile(samples) if samples else ""
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

            if len(profile) != width:
                step = (len(profile) - 1) / max(1, width - 1)
                profile = [profile[round(i * step)] for i in range(width)]
            return self._render_profile(profile)
        except Exception:
            return ""

    @staticmethod
    def _short_name(raw) -> str:
        """Nome do treino sem o prefixo `YYYY-MM-DD - `, que o cartão já mostra."""
        name = str(raw if raw is not None else "Treino")
        if len(name) > 13 and name[4] == "-" and name[7] == "-" and name[10:13] == " - ":
            return name[13:]
        return name

    @staticmethod
    def _tss_text(tss, empty: str = "—") -> str:
        try:
            return f"{float(tss):.0f}"
        except (TypeError, ValueError):
            return str(tss) if tss not in (None, "") else empty

    def _mount_workout_cell(self, card: Vertical, entry: dict, width: int,
                            with_meta: bool = True) -> None:
        """Desenha um dia com treino: nome, perfil de potência e (opcional) meta."""
        planned = entry.get("planned") if isinstance(entry, dict) else None
        done = entry.get("done") if isinstance(entry, dict) else None
        unmatched_activity = False
        if (planned and done and entry.get("matching_required") and
                str(done.get("id")) != str(entry.get("matched_activity_id"))):
            unmatched_activity = True
            done = None
        prof = ""
        meta = ""
        if planned and entry.get("matching_unavailable"):
            name = self._short_name(planned.get("name", "Treino"))
            meta = "Status indisponível"
            prof = self._profile_sparkline(planned, width=width)
        elif planned and done:
            w = planned
            name = self._short_name(w.get("name", "Treino"))
            dur = int(w.get("planned_duration", 0) or 0) // 60
            extra = entry.get("matching_required") and any(
                str(a.get("id")) != str(entry.get("matched_activity_id"))
                for a in (entry.get("activities") or []))
            meta = f"Realizado{' + extra' if extra else ''} · {dur}m · TSS{self._tss_text(w.get('tss', 0))}"
            prof = self._activity_profile_sparkline(done, width=width)
        elif done and not planned:
            name = self._short_name(done.get("name", "Atividade"))
            dur_m = 0
            try:
                dur_m = int(float(done.get("duration") or 0) // 60)
            except (TypeError, ValueError):
                dur_m = 0
            tss = done.get("tss") or 0
            meta = f"Extra · {dur_m}m · TSS{self._tss_text(tss) if tss else '—'}"
            prof = self._activity_profile_sparkline(done, width=width)
        elif planned:
            w = planned
            name = self._short_name(w.get("name", "Treino"))
            dur = w.get("planned_duration")
            dur_text = f"{int(dur) // 60}m" if dur is not None else "—"
            day = w.get("day")
            status = "Não realizado" if day and day < date.today().isoformat() else "Planejado"
            if unmatched_activity:
                status += " + extra"
            meta = f"{status} · {dur_text} · TSS{self._tss_text(w.get('tss'))}"
            prof = self._profile_sparkline(w, width=width)
        else:
            card.mount(Label("Divergência remota" if entry.get("plan_divergence") else "Descanso", classes="rest-label"))
            return

        card.mount(Label(name[:width + 10], classes="workout-name"))
        if prof:
            card.mount(Label(prof, classes="workout-profile"))
        elif done:
            card.mount(Label("Perfil real indisponível", classes="workout-profile"))
        elif planned and planned.get("origin") == "intervals":
            card.mount(Label("Perfil indisponível", classes="workout-profile"))
        if with_meta:
            card.mount(Label(meta, classes="workout-meta"))

    def _render_week_summary(self, body: Container, workouts: dict) -> None:
        actual_zones = getattr(self, "_activity_zone_cache", None) or {}
        zones_by_day = {}
        zone_coverage_incomplete = False
        for iso, entry in (workouts or {}).items():
            try:
                entry_day = date.fromisoformat(iso)
            except ValueError:
                continue
            if not self._week_start(self.current_date) <= entry_day < self._week_start(self.current_date) + timedelta(days=7):
                continue
            done = entry.get("done") if isinstance(entry, dict) else None
            activities = entry.get("activities") if isinstance(entry, dict) else None
            if isinstance(activities, list) and len(activities) > 1:
                zone_coverage_incomplete = True
            if not isinstance(done, dict):
                continue
            activity_id = done.get("id") or done.get("activity_id")
            if activity_id is None:
                zone_coverage_incomplete = True
                continue
            activity_id = str(activity_id)
            zone_map = actual_zones.get(activity_id) or actual_zones.get(iso)
            if zone_map:
                zones_by_day[iso] = zone_map
            else:
                zone_coverage_incomplete = True
        week_start = self._week_start(self.current_date)
        summary = week_summary(
            workouts,
            week_start,
            self._today(),
            actual_zone_seconds=zones_by_day if zones_by_day else None,
        )

        def minutes(seconds: int) -> int:
            return seconds // 60

        zone_labels = {
            FOCUS_ZONE1_RECOVERY: "Z1",
            FOCUS_ZONE2_ENDURANCE: "Z2",
            FOCUS_ZONE3_TEMPO: "Z3",
            ZONE_SWEETSPOT: "Sweet Spot",
            FOCUS_ZONE4_LIMIAR: "Z4",
            "threshold": "Limiar",
            FOCUS_ZONE5_VO2MAX: "Z5",
            "vo2max": "VO2",
            FOCUS_ZONE6_ANAEROBICA: "Z6",
            "z6_anaerobica": "Z6",
        }

        def zones(values: dict[str, float]) -> str:
            if not values:
                return "—"
            parts = []
            for zone, seconds in values.items():
                try:
                    sec = float(seconds)
                except Exception:
                    continue
                if sec <= 0:
                    continue
                label = zone_labels.get(zone) or zone_labels.get(str(zone)) or str(zone)
                parts.append(f"{label} {int(sec // 60)}m")
            return " · ".join(parts) if parts else "—"

        planned_zones = dict(getattr(summary, "planned_zone_seconds", None) or {})
        if not planned_zones:
            for offset in range(7):
                day = week_start + timedelta(days=offset)
                entry = (workouts or {}).get(day.isoformat(), {})
                if not isinstance(entry, dict):
                    continue
                planned = entry.get("planned")
                if not isinstance(planned, dict):
                    if entry.get("params") or entry.get("focus") or entry.get("planned_duration") or entry.get("on_sec"):
                        planned = dict(entry)
                    else:
                        continue
                try:
                    from ..training_review import zone_seconds_for_plan
                    pz = zone_seconds_for_plan(planned)
                    if not pz:
                        pz = planned_workout_summary(planned).zone_seconds
                    for zone, seconds in pz.items():
                        planned_zones[zone] = planned_zones.get(zone, 0.0) + float(seconds)
                except Exception:
                    continue

        box = Vertical(classes="week-summary")
        body.mount(box)
        box.mount(Label("RESUMO SEMANAL", classes="week-summary-title"))
        box.mount(Label(f"Planejado: {minutes(summary.planned_duration_seconds)}m · TSS{summary.planned_tss:.0f}"))
        if getattr(self, "_history_unavailable", False):
            box.mount(Label("Realizado: indisponível"))
        else:
            box.mount(Label(f"Realizado: {minutes(summary.actual_duration_seconds)}m · TSS{summary.actual_tss:.0f}"))
        box.mount(Label(
            f"{summary.completed} realizado · {summary.missed} perdido · "
            f"{summary.pending} pendente · {summary.extra} extra",
            classes="week-summary-muted",
        ))
        if summary.unknown:
            box.mount(Label(f"{summary.unknown} status indisponível", classes="week-summary-muted"))
        box.mount(Label("Zonas planejadas:", classes="week-summary-muted"))
        box.mount(Label(zones(planned_zones), classes="week-summary-muted"))
        actual_zs = getattr(summary, "actual_zone_seconds", None)
        actual = zones(actual_zs) if actual_zs is not None else "indisponível"
        if actual_zs is not None and zone_coverage_incomplete:
            actual += " (parcial)"
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
        if getattr(self, "_history_unavailable", False):
            body.mount(Label("Histórico remoto indisponível; exibindo dados locais."))
        today = date.today()
        if not hasattr(self, 'selected_date') or self.selected_date is None:
            self.selected_date = today
        if not hasattr(self, 'current_date') or self.current_date is None:
            self.current_date = today

        if self.view_mode == "month":
            # A grade mensal rola quando nao cabe; antes ela era espremida em
            # 7 linhas 1fr e o perfil de potencia era recortado nas semanas
            # mais baixas.
            scroll = VerticalScroll(classes="month-scroll")
            body.mount(scroll)
            grid = Grid(classes="month-grid")
            scroll.mount(grid)
            for wd in WEEKDAYS:
                grid.mount(Label(wd, classes="weekday-header"))
            cal = calendar.Calendar(firstweekday=0)
            for week in cal.monthdayscalendar(self.current_date.year, self.current_date.month):
                for day_num in week:
                    if day_num == 0:
                        card = Vertical(classes="day-card month-cell outside")
                        grid.mount(card)
                        hdr = Horizontal(classes="day-header")
                        card.mount(hdr)
                        hdr.mount(Label("—", classes="day-number"))
                        card.mount(Label("—", classes="rest-label"))
                        continue

                    d = date(self.current_date.year, self.current_date.month, day_num)
                    iso = d.isoformat()
                    cls = "day-card month-cell"
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
                        self._mount_workout_cell(card, entry, width=12)
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
                cls = "day-card week-cell"
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
                    self._mount_workout_cell(card, entry, width=14, with_meta=True)
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

        screen = CalendarDetailScreen(iso, entry)

        def _on_zone_update(zones_by_activity):
            if not zones_by_activity:
                return
            cache = getattr(self, "_activity_zone_cache", None)
            if cache is None:
                cache = {}
                self._activity_zone_cache = cache
            for activity_id, zone_map in zones_by_activity.items():
                if zone_map:
                    cache[activity_id] = zone_map
            if self.view_mode == "week":
                self._refresh()

        screen._zone_update_callback = _on_zone_update
        self.app.push_screen(screen)

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
