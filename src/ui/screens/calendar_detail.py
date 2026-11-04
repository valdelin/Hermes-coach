# src/ui/screens/calendar_detail.py
"""Detalhe do treino do calendário (semelhante ao Intervals.icu)"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, Header, Label, Static

from ..training_review import day_comparison, day_plans, planned_workout_summary, zone_seconds_for_stream
from ..history import sample_power_steps

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

try:
    from src.plan import load_plan
except Exception:
    try:
        from plan import load_plan
    except Exception:
        load_plan = None

try:
    from src.coach import ZONE_BANDS, FOCUS_ZONE1_RECOVERY, FOCUS_ZONE2_ENDURANCE, FOCUS_ZONE3_TEMPO, FOCUS_ZONE4_LIMIAR, FOCUS_ZONE5_VO2MAX, FOCUS_ZONE6_ANAEROBICA, ZONE_SWEETSPOT
except Exception:
    try:
        from coach import ZONE_BANDS, FOCUS_ZONE1_RECOVERY, FOCUS_ZONE2_ENDURANCE, FOCUS_ZONE3_TEMPO, FOCUS_ZONE4_LIMIAR, FOCUS_ZONE5_VO2MAX, FOCUS_ZONE6_ANAEROBICA, ZONE_SWEETSPOT
    except Exception:
        ZONE_BANDS = {}
        FOCUS_ZONE1_RECOVERY = "z1_recovery"
        FOCUS_ZONE2_ENDURANCE = "zone2"
        FOCUS_ZONE3_TEMPO = "z3_tempo"
        FOCUS_ZONE4_LIMIAR = "threshold"
        FOCUS_ZONE5_VO2MAX = "vo2max"
        FOCUS_ZONE6_ANAEROBICA = "z6_anaerobica"
        ZONE_SWEETSPOT = "sweetspot"

# Cores por zona (respeitando Z1-Z6)
ZONE_COLORS = {
    FOCUS_ZONE1_RECOVERY: "#4d9bff",  # Z1 - azul
    FOCUS_ZONE2_ENDURANCE: "#ffd93b",  # Z2 - amarelo
    FOCUS_ZONE3_TEMPO: "#ff9f1a",      # Z3 - laranja
    ZONE_SWEETSPOT: "#ff6b35",         # Sweet Spot - laranja avermelhado
    FOCUS_ZONE4_LIMIAR: "#ff3b30",     # Z4 - vermelho
    FOCUS_ZONE5_VO2MAX: "#d946ef",     # Z5 - magenta/fúcsia
    FOCUS_ZONE6_ANAEROBICA: "#8b5cf6", # Z6 - violeta
}

HR_ZONE_COLORS = (
    "#4d9bff",  # Z1
    "#ffd93b",  # Z2
    "#ff9f1a",  # Z3
    "#ff3b30",  # Z4
    "#d946ef",  # Z5
    "#8b5cf6",  # Z6
    "#5b21b6",  # Z7
)


class CalendarDetailScreen(Screen):
    CSS = """
    CalendarDetailScreen {
        background: $surface;
    }

    #header-info {
        height: 3;
        layout: horizontal;
        align: center middle;
        padding: 0 2;
        background: $boost;
    }

    #date-label {
        width: 1fr;
        text-style: bold;
    }

    #status-label {
        width: auto;
        color: $text-muted;
    }

    .section {
        text-style: bold;
        padding: 1 2 0 2;
    }

    .box {
        padding: 0 3;
    }

    .kv {
        layout: horizontal;
        height: 1;
    }

    .k {
        width: 18;
        color: $text-muted;
    }

    .v {
        width: 1fr;
    }

    .profile-card {
        padding: 1 3;
        border: round $panel;
        margin: 0 2;
        height: auto;
    }

    .zone-card {
        width: 1fr;
        margin: 0 1;
        padding: 1 2;
        height: 12;
    }

    #detail-scroll {
        height: 1fr;
        overflow-y: scroll;
        scrollbar-gutter: stable;
    }

    .profile {
        padding: 0 1;
        width: 1fr;
    }

    .profile-meta {
        padding: 0 1;
        color: $text-muted;
    }

    .zones {
        padding: 0 3;
    }

    .zone-columns {
        layout: horizontal;
        padding: 0 2;
        height: 12;
    }

    .zone-column {
        width: 1fr;
        padding: 0 1;
    }

    .zone-column-title {
        text-style: bold;
        color: $text-muted;
    }

    .zone-row {
        layout: horizontal;
        height: 1;
    }

    .zone-dot {
        width: 2;
    }

    .zone-name {
        width: 1fr;
    }

    .zone-time {
        width: 11;
        color: $text-muted;
    }

    .zone-range {
        width: 13;
        color: $text-muted;
    }

    .hr-zone-name {
        width: 17;
    }

    .hr-zone-range {
        width: 13;
        color: $text-muted;
    }

    .hr-zone-bar {
        width: 16;
    }

    .hr-zone-time {
        width: 15;
        color: $text-muted;
    }

    .power-zone-name {
        width: 17;
    }

    .power-zone-range {
        width: 13;
        color: $text-muted;
    }

    .power-zone-bar {
        width: 16;
    }

    .power-zone-time {
        width: 15;
        color: $text-muted;
    }

    .desc {
        padding: 0 3;
        color: $text;
    }

    .comparison-columns {
        layout: horizontal;
        padding: 0 2;
    }

    .comparison-column {
        width: 1fr;
        padding: 0 1;
    }

    .comparison-title {
        text-style: bold;
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("escape", "back", "Voltar"),
        Binding("h", "back", "Voltar"),
        Binding("q", "quit", "Sair"),
    ]

    def __init__(self, day_iso: str, entry: dict | None = None):
        super().__init__()
        self.day_iso = day_iso
        self.entry = entry or {}
        self._activity_stream_cache = {}
        self._zone_update_callback = None
        self._reported_zones = set()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="header-info"):
            yield Label(self._format_date(), id="date-label")
            yield Label(self._status_text(), id="status-label")
        yield VerticalScroll(
            Vertical(id="content"),
            id="detail-scroll",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._build()

    def on_resize(self, event=None) -> None:
        """Redesenha os gráficos com a nova largura, sem novo fetch remoto."""
        try:
            self._build()
        except Exception:
            pass

    def _chart_width(self) -> int:
        """Largura útil do card, limitada para preservar legibilidade."""
        try:
            return max(24, min(160, self.size.width - 10))
        except Exception:
            return 96

    def _format_date(self) -> str:
        try:
            d = date.fromisoformat(self.day_iso)
            dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
            meses = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
            return f"{dias[d.weekday()]}, {d.day} {meses[d.month-1]} {d.year}"
        except Exception:
            return self.day_iso

    def _status_text(self) -> str:
        planned = self.entry.get("planned")
        done = self.entry.get("done")
        if self.entry.get("matching_unavailable") and (planned or done):
            return "STATUS INDISPONÍVEL"
        if len(day_plans(self.entry)) > 1:
            return "MÚLTIPLOS TREINOS • CONSULTE DETALHES"
        if planned and done and self.entry.get("matching_required"):
            matched = self.entry.get("matched_activity_id")
            if matched is None or str(done.get("id")) != str(matched):
                try:
                    status = "PENDENTE" if date.fromisoformat(self.day_iso) >= date.today() else "NÃO REALIZADO"
                except ValueError:
                    return "STATUS INDISPONÍVEL"
                return f"PLANEJADO • {status} • ATIVIDADE EXTRA"
        if planned and done:
            activities = self.entry.get("activities") or []
            if self.entry.get("matching_required") and any(
                    str(a.get("id")) != str(self.entry.get("matched_activity_id")) for a in activities):
                return "PLANEJADO • REALIZADO • ATIVIDADE EXTRA"
            return "PLANEJADO • REALIZADO"
        if done and not planned:
            return "REALIZADO FORA DO PLANO"
        if planned and not done:
            try:
                if date.fromisoformat(self.day_iso) >= date.today():
                    return "PLANEJADO • PENDENTE"
            except ValueError:
                return "STATUS INDISPONÍVEL"
            return "PLANEJADO • NÃO REALIZADO"
        return "DESCANSO"

    def _kv(self, container: Vertical, k: str, v: str):
        row = Horizontal(classes="kv")
        container.mount(row)
        row.mount(Label(k, classes="k"))
        row.mount(Label(str(v), classes="v"))

    def _render_structure(self, container: Vertical, planned: dict) -> None:
        summary = planned_workout_summary(planned)
        if not summary.blocks:
            return
        container.mount(Label("ESTRUTURA", classes="section"))
        box = Vertical(classes="box")
        container.mount(box)
        for block in summary.blocks:
            repetitions = f" × {block.repetitions}" if block.repetitions > 1 else ""
            intensity = f" @ {block.intensity * 100:.0f}% FTP" if block.intensity is not None else ""
            self._kv(box, block.label, f"{block.duration_seconds // 60} min{repetitions}{intensity}")

    def _render_comparison(self, container: Vertical, planned: dict, done: dict) -> None:
        comparison = day_comparison(planned, done)

        def minutes(seconds: int | None) -> str:
            return f"{seconds // 60} min" if seconds is not None else "—"

        def signed(value: float | int | None, unit: str = "") -> str:
            if value is None:
                return "—"
            number = f"{value:+.0f}" if float(value).is_integer() else f"{value:+.1f}"
            return f"{number}{unit}"

        container.mount(Label("COMPARAÇÃO FACTUAL", classes="section"))
        columns = Horizontal(classes="comparison-columns")
        container.mount(columns)
        planned_box = Vertical(classes="comparison-column")
        actual_box = Vertical(classes="comparison-column")
        delta_box = Vertical(classes="comparison-column")
        columns.mount(planned_box)
        columns.mount(actual_box)
        columns.mount(delta_box)
        planned_box.mount(Label("PLANEJADO", classes="comparison-title"))
        self._kv(planned_box, "Duração", minutes(comparison.planned_duration_seconds))
        self._kv(planned_box, "TSS", f"{comparison.planned_tss:.0f}" if comparison.planned_tss is not None else "—")
        actual_box.mount(Label("REALIZADO", classes="comparison-title"))
        self._kv(actual_box, "Duração", minutes(comparison.actual_duration_seconds))
        self._kv(actual_box, "TSS", f"{comparison.actual_tss:.0f}" if comparison.actual_tss is not None else "—")
        self._kv(actual_box, "Potência média", f"{comparison.average_watts:.0f} W" if comparison.average_watts is not None else "—")
        self._kv(actual_box, "Potência normalizada", f"{comparison.normalized_power:.0f} W" if comparison.normalized_power is not None else "—")
        delta_box.mount(Label("DIFERENÇA", classes="comparison-title"))
        self._kv(delta_box, "Δ duração", signed((comparison.duration_delta_seconds or 0) / 60 if comparison.duration_delta_seconds is not None else None, " min"))
        self._kv(delta_box, "Δ TSS", signed(comparison.tss_delta))

    def _zone_color_for_p(self, p: float) -> str:
        if p < 0.56:
            return ZONE_COLORS[FOCUS_ZONE1_RECOVERY]
        elif p < 0.76:
            return ZONE_COLORS[FOCUS_ZONE2_ENDURANCE]
        elif p < 0.84:
            return ZONE_COLORS[FOCUS_ZONE3_TEMPO]
        elif p <= 0.97:
            return ZONE_COLORS[ZONE_SWEETSPOT]
        elif p <= 1.05:
            return ZONE_COLORS[FOCUS_ZONE4_LIMIAR]
        elif p <= 1.20:
            return ZONE_COLORS[FOCUS_ZONE5_VO2MAX]
        else:
            return ZONE_COLORS[FOCUS_ZONE6_ANAEROBICA]

    def _zone_for_p(self, p: float) -> str:
        if p < 0.56:
            return FOCUS_ZONE1_RECOVERY
        if p < 0.76:
            return FOCUS_ZONE2_ENDURANCE
        if p < 0.84:
            return FOCUS_ZONE3_TEMPO
        if p <= 0.97:
            return ZONE_SWEETSPOT
        if p <= 1.05:
            return FOCUS_ZONE4_LIMIAR
        if p <= 1.20:
            return FOCUS_ZONE5_VO2MAX
        return FOCUS_ZONE6_ANAEROBICA

    def _load_activity_streams(self, done: dict) -> tuple[list, float | None, dict, dict]:
        """Obtém streams reais e FTP da atividade realizada no Intervals."""
        activity_id = done.get("id")
        if not activity_id:
            return [], None, {}, {}
        cached = self._activity_stream_cache.get(activity_id)
        if cached is not None:
            return cached
        try:
            from ..utils import get_app
            client = get_app().client()
            inner = getattr(client, "_client", None) or getattr(client, "client", None) or client
            detail = inner.activity(activity_id) or {}
            streams = inner.activity_streams(
                activity_id, types=("watts", "time", "heartrate", "cadence")
            ) or {}
            watts = streams.get("watts") or []
            times = streams.get("time") or []
            if not watts or not times:
                return [], None, {}, {}
            ftp = detail.get("icu_ftp") or detail.get("icu_pm_ftp")
            try:
                ftp = float(ftp) if ftp else None
            except (TypeError, ValueError):
                ftp = None
            points = []
            for t, watts_value in zip(times, watts):
                try:
                    points.append((float(t), max(0.0, float(watts_value))))
                except (TypeError, ValueError):
                    continue
            metrics = {}
            for name in ("heartrate", "cadence"):
                values = streams.get(name) or []
                samples = []
                for timestamp, value in zip(times, values):
                    try:
                        value = float(value)
                        if value > 0:
                            samples.append((float(timestamp), value))
                    except (TypeError, ValueError):
                        continue
                if samples:
                    metrics[name] = samples
            hr_zone_data = {
                "limits": detail.get("icu_hr_zones") or [],
                "times": detail.get("icu_hr_zone_times") or [],
                "max_hr": detail.get("athlete_max_hr"),
            }
            result = (points, ftp, metrics, hr_zone_data)
            self._activity_stream_cache[activity_id] = result
            return result
        except Exception:
            return [], None, {}, {}

    def _actual_profile(self, points: list, ftp: float | None, width: int = 96) -> str:
        """Downsample dos streams reais, preservando cor por zona e transições."""
        if not points or not ftp or ftp <= 0:
            return ""
        sample_count = min(width, len(points))
        samples = [
            points[round(i * (len(points) - 1) / max(1, sample_count - 1))]
            for i in range(sample_count)
        ]
        if len(samples) < 2:
            return ""
        powers = [watts / ftp for _, watts in samples]
        lo, hi = min(powers), max(powers)
        span = hi - lo if hi > lo else 1.0
        blocks = "▁▂▃▄▅▆▇█"
        output = []
        for p in powers:
            zone = self._zone_for_p(p)
            idx = max(0, min(7, round((p - lo) / span * 7)))
            color = ZONE_COLORS[zone]
            output.append(f"[{color}]{blocks[idx]}[/{color}]")
        return "".join(output)

    def _actual_zone_time(self, points: list, ftp: float | None):
        """Calcula tempo em zona a partir de cada amostra de potência real."""
        if not points or not ftp or ftp <= 0:
            return []
        seconds = {}
        for index, (current_time, watts) in enumerate(points):
            if index + 1 < len(points):
                duration = max(0.0, points[index + 1][0] - current_time)
            elif index:
                duration = max(0.0, current_time - points[index - 1][0])
            else:
                duration = 0.0
            zone = self._zone_for_p(watts / ftp)
            seconds[zone] = seconds.get(zone, 0.0) + duration
        return self._format_zone_time(seconds)

    def _metric_profile(self, points: list, color: str, width: int = 96) -> str:
        """Sparkline colorida de um stream fisiológico real."""
        if len(points) < 2:
            return ""
        sample_count = min(width, len(points))
        samples = [
            points[round(i * (len(points) - 1) / max(1, sample_count - 1))][1]
            for i in range(sample_count)
        ]
        lo, hi = min(samples), max(samples)
        span = hi - lo if hi > lo else 1.0
        blocks = "▁▂▃▄▅▆▇█"
        return "".join(
            f"[{color}]{blocks[max(0, min(7, round((value - lo) / span * 7)))]}[/{color}]"
            for value in samples
        )

    def _metric_summary(self, points: list, unit: str) -> str:
        values = [value for _, value in points]
        if not values:
            return ""
        return f"Média {sum(values) / len(values):.0f} {unit}  •  Máximo {max(values):.0f} {unit}"

    def _format_zone_time(self, seconds: dict):
        labels = {
            FOCUS_ZONE1_RECOVERY: "Z1 - Recuperação",
            FOCUS_ZONE2_ENDURANCE: "Z2 - Endurance",
            FOCUS_ZONE3_TEMPO: "Z3 - Tempo",
            ZONE_SWEETSPOT: "Sweet Spot",
            FOCUS_ZONE4_LIMIAR: "Z4 - Limiar",
            FOCUS_ZONE5_VO2MAX: "Z5 - VO₂max",
            FOCUS_ZONE6_ANAEROBICA: "Z6 - Anaeróbica",
        }
        order = list(labels)
        output = []
        total_seconds = sum(seconds.values())
        for zone in order:
            total = round(seconds.get(zone, 0.0))
            if total <= 0:
                continue
            band = ZONE_BANDS.get(zone)
            pct = f"{band[0]*100:.0f}-{band[1]*100:.0f}% FTP" if band else ""
            percentage = total / total_seconds * 100 if total_seconds else 0.0
            output.append((zone, labels[zone], f"{total // 60}m{total % 60:02d}s  {percentage:.1f}%", pct, percentage))
        return output

    def _hr_zone_time(self, hr_zone_data: dict):
        """Formata limites e tempos de FC retornados pelo Intervals.icu."""
        limits = hr_zone_data.get("limits") or []
        times = hr_zone_data.get("times") or []
        try:
            max_hr = float(hr_zone_data.get("max_hr") or limits[-1])
        except (TypeError, ValueError, IndexError):
            max_hr = None
        labels = (
            "Recovery", "Aerobic", "Tempo", "SubThreshold",
            "SuperThreshold", "Aerobic Capacity", "Anaerobic",
        )
        total = sum(float(t or 0) for t in times)
        rows = []
        lower = 0
        for index, upper in enumerate(limits[:7]):
            try:
                upper = int(float(upper))
            except (TypeError, ValueError):
                continue
            seconds = float(times[index]) if index < len(times) and times[index] is not None else 0.0
            lower_text = "0" if index == 0 else str(lower + 1)
            range_text = f"{lower_text}-{upper} bpm"
            pct = seconds / total * 100 if total > 0 else 0.0
            rows.append((f"Z{index + 1} {labels[index]}", range_text,
                         f"{int(seconds) // 60}m{int(seconds) % 60:02d}s  {pct:.1f}%", pct))
            lower = upper
        return rows

    def _progress_bar(self, pct: float, color: str, maximum: float, width: int = 14) -> str:
        """Barra proporcional à zona de maior duração, como no Intervals.icu."""
        ratio = pct / maximum if maximum > 0 else 0.0
        filled = max(0, min(width, round(width * ratio)))
        empty = width - filled
        return f"[{color}]{'█' * filled}[/{color}][#3d3d3d]{'░' * empty}[/#3d3d3d]"

    def _profile(self, w: dict, scale: float = 1.8, width: int | None = None) -> str:
        try:
            if w.get("origin") == "intervals":
                samples = sample_power_steps(w.get("historical_power_steps") or (), width or 60)
                if not samples:
                    return ""
                blocks = "▁▂▃▄▅▆▇█"
                lo, hi = min(samples), max(samples)
                span = hi - lo or 1.0
                return "".join(
                    f"[{self._zone_color_for_p(p)}]{blocks[round((p-lo)/span*(len(blocks)-1))]}[/{self._zone_color_for_p(p)}]"
                    for p in samples)
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

            blocks = " ▁▂▃▄▅▆▇█"
            segments = []
            if warmup > 0:
                steps = max(6, int(8 * scale))
                for i in range(steps):
                    p = 0.3 + 0.2 * (i / max(1, steps - 1))
                    segments.append((p, "warm"))
            for r in range(repeats):
                if on_sec > 0:
                    reps_on = max(2, int(3 * scale))
                    for _ in range(reps_on):
                        segments.append((min(1.0, on_p), "on"))
                if off_sec > 0 and r < repeats - 1:
                    reps_off = max(2, int(2 * scale))
                    for _ in range(reps_off):
                        segments.append((max(0.25, off_p), "off"))
            if cooldown > 0:
                steps = max(6, int(8 * scale))
                for i in range(steps):
                    p = 0.5 - 0.2 * (i / max(1, steps - 1))
                    segments.append((max(0.25, p), "cool"))
            if not segments:
                return ""
            if width and len(segments) != width:
                step = (len(segments) - 1) / max(1, width - 1)
                segments = [segments[round(i * step)] for i in range(width)]
            lo, hi = min(s[0] for s in segments), max(s[0] for s in segments)
            span = hi - lo if hi - lo > 0 else 1.0
            out = []
            for p, _ in segments:
                idx = int((p - lo) / span * (len(blocks) - 1))
                idx = max(0, min(len(blocks) - 1, idx))
                c = self._zone_color_for_p(p)
                out.append(f"[{c}]{blocks[idx]}[/{c}]")
            return "".join(out)
        except Exception:
            return ""

    def _zone_time(self, w: dict):
        try:
            params = w.get("params") or {}
            if not isinstance(params, dict):
                return []
            warmup = int(params.get("warmup_sec") or 0)
            cooldown = int(params.get("cooldown_sec") or 0)
            repeats = int(params.get("repeats") or 1)
            on_sec = int(params.get("on_sec") or 0)
            off_sec = int(params.get("off_sec") or 0)
            on_p = float(params.get("on_power") or 0.6)
            off_p = float(params.get("off_power") or on_p)

            def _zone_for(p: float):
                # Mapear por bandas
                if p < 0.56:
                    return FOCUS_ZONE1_RECOVERY
                elif p < 0.76:
                    return FOCUS_ZONE2_ENDURANCE
                elif p < 0.84:
                    return FOCUS_ZONE3_TEMPO
                elif p <= 0.97:
                    return ZONE_SWEETSPOT
                elif p <= 1.05:
                    return FOCUS_ZONE4_LIMIAR
                elif p <= 1.20:
                    return FOCUS_ZONE5_VO2MAX
                else:
                    return FOCUS_ZONE6_ANAEROBICA

            secs = {}
            if warmup > 0:
                secs[FOCUS_ZONE1_RECOVERY] = secs.get(FOCUS_ZONE1_RECOVERY, 0) + warmup
            if cooldown > 0:
                secs[FOCUS_ZONE1_RECOVERY] = secs.get(FOCUS_ZONE1_RECOVERY, 0) + cooldown
            for r in range(repeats):
                if on_sec > 0:
                    z = _zone_for(on_p)
                    secs[z] = secs.get(z, 0) + on_sec
                if off_sec > 0 and r < repeats - 1:
                    z = _zone_for(off_p)
                    secs[z] = secs.get(z, 0) + off_sec
            out = []
            total_seconds = sum(secs.values())
            for z, s in secs.items():
                if s <= 0:
                    continue
                m = s // 60
                rem = s % 60
                band = ZONE_BANDS.get(z)
                rng = ""
                if band:
                    rng = f"{band[0]*100:.0f}-{band[1]*100:.0f}% FTP"
                name_map = {
                    FOCUS_ZONE1_RECOVERY: "Z1 - Recuperação",
                    FOCUS_ZONE2_ENDURANCE: "Z2 - Endurance",
                    FOCUS_ZONE3_TEMPO: "Z3 - Tempo",
                    ZONE_SWEETSPOT: "Sweet Spot",
                    FOCUS_ZONE4_LIMIAR: "Z4 - Limiar",
                    FOCUS_ZONE5_VO2MAX: "Z5 - VO₂max",
                    FOCUS_ZONE6_ANAEROBICA: "Z6 - Anaeróbica",
                }
                percentage = s / total_seconds * 100 if total_seconds else 0.0
                out.append((z, name_map.get(z, z), f"{m}m{rem:02d}s  {percentage:.1f}%", rng, percentage))
            # ordenar por intensidade
            order = [FOCUS_ZONE1_RECOVERY, FOCUS_ZONE2_ENDURANCE, FOCUS_ZONE3_TEMPO, ZONE_SWEETSPOT, FOCUS_ZONE4_LIMIAR, FOCUS_ZONE5_VO2MAX, FOCUS_ZONE6_ANAEROBICA]
            out.sort(key=lambda x: order.index(x[0]) if x[0] in order else 99)
            return out
        except Exception:
            return []

    def _build(self):
        container = self.query_one("#content", Vertical)
        container.remove_children()

        planned = self.entry.get("planned") or {}
        done = self.entry.get("done") or {}

        activities = self.entry.get("activities") or []
        if self.entry.get("plan_divergence"):
            container.mount(Label("Plano local difere do evento remoto.", classes="section"))
            for remote in self.entry.get("remote_plans") or []:
                if remote.get("shadowed_by_local"):
                    container.mount(Label(f"Evento remoto: {remote.get('name') or 'Sem nome'} · {remote.get('day') or '—'}"))
                    remote_profile = self._profile(remote, width=self._chart_width())
                    if remote_profile:
                        container.mount(Static(remote_profile, classes="profile"))
                    else:
                        container.mount(Label("Perfil remoto indisponível."))
        if len(activities) > 1:
            container.mount(Label("ATIVIDADES DO DIA", classes="section"))
            for activity in activities:
                container.mount(Label(str(activity.get("name") or activity.get("id") or "Atividade")))

        if planned:
            container.mount(Label("TREINO PLANEJADO", classes="section"))
            box = Vertical(classes="box")
            container.mount(box)
            if planned.get("origin") == "intervals":
                self._kv(box, "Origem", "Intervals.icu")
            if self.entry.get("structure_comparison_unavailable"):
                box.mount(Label("Comparação da estrutura indisponível."))
            remote_plans = self.entry.get("remote_plans") or []
            for remote in remote_plans:
                if remote is not planned and remote.get("external_id") != planned.get("external_id"):
                    box.mount(Label(f"Outro evento planejado: {remote.get('name') or 'Sem nome'}"))
            name = planned.get("name") or planned.get("focus")
            if name:
                box.mount(Label(str(name)))
            focus = planned.get("focus")
            if focus not in (None, "", 0):
                self._kv(box, "Foco", str(focus))
            dur = planned.get("planned_duration")
            if dur not in (None, "", 0):
                try:
                    dur_m = int(int(dur) // 60)
                    self._kv(box, "Duração", f"{dur_m} min")
                except Exception:
                    pass
            tss = planned.get("tss")
            if tss not in (None, "", 0):
                try:
                    tss_s = f"{float(tss):.0f}"
                    self._kv(box, "TSS", tss_s)
                except Exception:
                    self._kv(box, "TSS", str(tss))
            if planned.get("external_id"):
                self._kv(box, "External ID", planned.get("external_id"))

        if planned and done and (not self.entry.get("matching_required") or
                                 str(done.get("id")) == str(self.entry.get("matched_activity_id"))):
            self._render_comparison(container, planned, done)

        # Mostrar perfil também para histórico (atividades realizadas) quando houver params?
        # Planos têm params; atividades do Intervals podem não ter. Mas vamos tentar montar
        # a partir de dados disponíveis ou pelo menos mostrar card se conseguirmos gerar.
        actual_points, actual_ftp, actual_metrics, hr_zone_data = (
            self._load_activity_streams(done) if done else ([], None, {}, {})
        )
        if done and actual_points and actual_ftp:
            try:
                zones = zone_seconds_for_stream(actual_points, actual_ftp)
                if zones:
                    activity_id = done.get("id") or done.get("activity_id")
                    if activity_id is not None:
                        activity_id = str(activity_id)
                    if activity_id and activity_id not in getattr(self, "_reported_zones", set()):
                        callback = getattr(self, "_zone_update_callback", None)
                        if callback:
                            callback({activity_id: zones})
                        reported = getattr(self, "_reported_zones", None)
                        if reported is None:
                            self._reported_zones = {activity_id}
                        else:
                            reported.add(activity_id)
            except Exception:
                pass
        # Atividade realizada tem precedência: o perfil representa os dados reais,
        # não a prescrição planejada.
        chart_width = self._chart_width()
        prof = self._actual_profile(actual_points, actual_ftp, width=chart_width) if actual_points else ""
        if planned and planned.get("origin") == "intervals" and done:
            planned_profile = self._profile(planned, scale=2.0, width=chart_width)
            if planned_profile:
                container.mount(Label("PERFIL PLANEJADO", classes="section"))
                planned_card = Vertical(classes="profile-card")
                container.mount(planned_card)
                planned_card.mount(Static(planned_profile, classes="profile"))
            else:
                container.mount(Label("Perfil planejado indisponível."))
        if not prof and not done:
            prof = self._profile(planned, scale=2.0, width=chart_width) if planned else ""
        elif not prof and done:
            container.mount(Label("Perfil realizado indisponível."))
        if prof:
            container.mount(Label("PERFIL DO TREINO", classes="section"))
            pcard = Vertical(classes="profile-card")
            container.mount(pcard)
            pcard.mount(Static(prof, classes="profile"))
        elif not done and planned and planned.get("origin") == "intervals":
            container.mount(Label("Perfil planejado indisponível."))
        if planned:
            self._render_structure(container, planned)
        for activity in activities:
            if activity is done or (activity.get("id") is not None and activity.get("id") == done.get("id")):
                continue
            container.mount(Label(f"ATIVIDADE: {activity.get('name') or 'Sem nome'}", classes="section"))
            activity_box = Vertical(classes="box")
            container.mount(activity_box)
            self._kv(activity_box, "Duração", f"{int(activity['duration']) // 60} min" if activity.get("duration") is not None else "—")
            self._kv(activity_box, "TSS", str(activity.get("tss") if activity.get("tss") is not None else "—"))
            points, ftp, _, _ = self._load_activity_streams(activity)
            extra_profile = self._actual_profile(points, ftp, width=chart_width) if points else ""
            if extra_profile:
                activity_card = Vertical(classes="profile-card")
                container.mount(activity_card)
                activity_card.mount(Static(extra_profile, classes="profile"))
            else:
                container.mount(Label("Perfil realizado indisponível."))
        for other in day_plans(self.entry):
            if other is planned:
                continue
            container.mount(Label(f"OUTRO TREINO: {other.get('name') or 'Sem nome'}", classes="section"))
            other_profile = self._profile(other, scale=2.0, width=chart_width)
            if other_profile:
                other_card = Vertical(classes="profile-card")
                container.mount(other_card)
                other_card.mount(Static(other_profile, classes="profile"))
            else:
                container.mount(Label("Perfil planejado indisponível."))
            self._render_structure(container, other)
        for metric, title, unit, color in (
            ("heartrate", "FREQUÊNCIA CARDÍACA", "bpm", "#ff4d4d"),
            ("cadence", "CADÊNCIA", "rpm", "#22d3ee"),
        ):
            points = actual_metrics.get(metric, [])
            chart = self._metric_profile(points, color, width=chart_width)
            if not chart:
                continue
            container.mount(Label(title, classes="section"))
            metric_card = Vertical(classes="profile-card")
            container.mount(metric_card)
            metric_card.mount(Static(chart, classes="profile"))
            metric_card.mount(Label(self._metric_summary(points, unit), classes="profile-meta"))
        zt = (self._actual_zone_time(actual_points, actual_ftp) if done and actual_points
              else self._zone_time(planned) if planned and not done else [])
        if done and not zt:
            container.mount(Label("Zonas de potência realizadas: indisponíveis"))
        hr_zt = self._hr_zone_time(hr_zone_data)
        if zt or hr_zt:
            container.mount(Label("TEMPO POR ZONA", classes="section"))
            zone_cards = Horizontal(classes="zone-columns")
            container.mount(zone_cards)
        if zt:
            zbox = Vertical(classes="profile-card zone-card")
            zone_cards.mount(zbox)
            zbox.mount(Label("POTÊNCIA", classes="zone-column-title"))
            max_power_pct = max(row[4] for row in zt)
            for z, zname, ztime, zrange, pct in zt:
                row = Horizontal(classes="zone-row")
                zbox.mount(row)
                color = ZONE_COLORS.get(z, "#ffffff")
                row.mount(Static(f"[{color}]●[/{color}]", classes="zone-dot"))
                row.mount(Label(zname, classes="power-zone-name"))
                row.mount(Label(zrange, classes="power-zone-range"))
                row.mount(Static(self._progress_bar(pct, color, max_power_pct), classes="power-zone-bar"))
                row.mount(Label(ztime, classes="power-zone-time"))
        if hr_zt:
            hrbox = Vertical(classes="profile-card zone-card")
            zone_cards.mount(hrbox)
            hrbox.mount(Label("FREQUÊNCIA CARDÍACA", classes="zone-column-title"))
            max_hr_pct = max(row[3] for row in hr_zt)
            for index, (label, hr_range, duration, pct) in enumerate(hr_zt):
                row = Horizontal(classes="zone-row")
                hrbox.mount(row)
                color = HR_ZONE_COLORS[index] if index < len(HR_ZONE_COLORS) else "#ffffff"
                row.mount(Static(f"[{color}]●[/{color}]", classes="zone-dot"))
                row.mount(Label(label, classes="hr-zone-name"))
                row.mount(Label(hr_range, classes="hr-zone-range"))
                row.mount(Static(self._progress_bar(pct, color, max_hr_pct), classes="hr-zone-bar"))
                row.mount(Label(duration, classes="hr-zone-time"))

        if done:
            container.mount(Label("TREINO REALIZADO", classes="section"))
            box = Vertical(classes="box")
            container.mount(box)
            box.mount(Label(done.get("name") or "Atividade"))
            tss = done.get("tss")
            try:
                tss_s = f"{float(tss):.0f}" if tss is not None else "—"
            except Exception:
                tss_s = str(tss)
            self._kv(box, "TSS", tss_s)
            dur = done.get("duration") or done.get("moving_time") or done.get("elapsed_time")
            try:
                if dur:
                    dur_m = int(float(dur) // 60)
                    self._kv(box, "Duração", f"{dur_m} min")
            except Exception:
                pass
            if done.get("type"):
                self._kv(box, "Tipo", str(done.get("type")))
            if done.get("icu_training_load") and tss is None:
                try:
                    self._kv(box, "Training Load", f"{float(done['icu_training_load']):.0f}")
                except Exception:
                    pass

        if not planned and not done:
            container.mount(Label("SEM TREINO", classes="section"))
            box = Vertical(classes="box")
            container.mount(box)
            box.mount(Label("Não há treino planejado nem realizado neste dia."))

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_quit(self) -> None:
        self.app.exit()
