import dataclasses
import json
import pathlib
from datetime import date, datetime, timedelta

try:
    from coach import (WorkoutParams, estimate_tss,
                       FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2)
except ImportError:
    from .coach import (WorkoutParams, estimate_tss,
                        FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2)

START_TIME = "07:30:00"
REST = "rest"
DEFAULT_FTP = 182
EXTERNAL_ID_PREFIX = "hermes-plan"


@dataclasses.dataclass(frozen=True)
class PlannedWorkout:
    day: str
    focus: str
    planned_duration: int
    name: str
    params: dict
    tss: float
    external_id: str


def templates():
    return {
        FOCUS_ZONE2: _block(1, 1800, 0, 0.70),
        "endurance": _block(1, 3600, 0, 0.75),
        FOCUS_SWEETSPOT: _block(3, 480, 240, 0.88),
        FOCUS_THRESHOLD: _block(3, 480, 240, 0.98),
        FOCUS_VO2: _block(4, 180, 180, 1.15),
    }


def _block(repeats, on_sec, off_sec, on_power):
    return {
        "repeats": repeats, "on_sec": on_sec, "off_sec": off_sec,
        "on_power": on_power, "off_power": 0.55, "cadence": 90,
        "cadence_rest": 85 if off_sec else 90,
    }


# Indice = dia da semana (seg=0 .. sex=4). Sabado/domingo nunca treinam;
# informar o Hermes para agendar por fora. Barra de carga e aplicada apos
# (ver build_plan / weekly_budget).
WEEKLY_BY_TSB = [
    (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
    (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_VO2]),
    (5, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
    (10**9, [FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
]

FOCUS_LABELS_PT = {
    REST: "Descanso",
    FOCUS_ZONE2: "Zona 2",
    FOCUS_SWEETSPOT: "Sweet Spot",
    FOCUS_THRESHOLD: "Limiar FTP",
    FOCUS_VO2: "VO2 Max",
    "endurance": "Endurance",
}


def workout_name(day, focus):
    """Nome mostrado no Intervals, com a data do treino na frente."""
    return f"{day} - Treino de {FOCUS_LABELS_PT[focus]}"


def weekly_template(tsb):
    for threshold, template in WEEKLY_BY_TSB:
        if tsb < threshold:
            return template
    return WEEKLY_BY_TSB[-1][1]


def avg_load(events, window_days=60):
    loads = []
    cutoff = date.today() - timedelta(days=window_days)
    for item in events:
        day = _day(item)
        load = _num(item.get("icu_training_load"))
        if day and load and load > 0 and day >= cutoff:
            loads.append(load)
    return sum(loads) / len(loads) if loads else 40.0


def daily_tss_cap(avg):
    return max(35, min(200, int(avg * 0.95)))


def weekly_budget(avg):
    """Orcamento de TSS para um janela de 7 dias (7x o cap diario)."""
    return daily_tss_cap(avg) * 7


def build_plan(events, tsb, ftp=DEFAULT_FTP, days=14, start=None):
    start = start or date.today() + timedelta(days=1)
    base = templates()
    weekly = weekly_template(tsb)
    cap = daily_tss_cap(avg_load(events))
    budget = weekly_budget(avg_load(events))
    plan = []
    recent = []  # (day, tss) dos ultimos 7 dias
    for i in range(days):
        day = start + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        focus = weekly[day.weekday()]
        params = WorkoutParams(focus=focus, **base[focus])
        tss = estimate_tss(params, ftp)
        if tss > cap:
            factor = max(0.4, cap / tss)
            params = WorkoutParams(**{**params.__dict__,
                                      "on_sec": max(120, int(params.on_sec * factor))})
            tss = estimate_tss(params, ftp)
        params, tss = _fit_budget(params, tss, recent, budget, ftp)
        duration = sum((params.warmup_sec,
                        params.repeats * (params.on_sec + params.off_sec),
                        params.cooldown_sec))
        plan.append(PlannedWorkout(
            day=day.isoformat(), focus=focus,
            planned_duration=duration,
            name=workout_name(day.isoformat(), focus),
            params=_params_dict(params), tss=float(tss),
            external_id=f"{EXTERNAL_ID_PREFIX}-{day.isoformat()}",
        ))
        recent.append((day, tss))
        while recent and day - recent[0][0] >= timedelta(days=7):
            recent.pop(0)
    return [_as_dict(w) for w in plan]


def _fit_budget(params, tss, recent, budget, ftp):
    """Reduz a carga deste dia (e por consequencia os subsequentes) para que a
    soma rolante de 7 dias nao estoure o orcamento semanal."""
    used = sum(t for _, t in recent)
    if used + tss <= budget:
        return params, tss
    on_sec, on_power = params.on_sec, params.on_power
    for _ in range(20):
        if used + tss <= budget:
            break
        if on_sec > 120:
            on_sec = max(120, int(on_sec * 0.8))
        elif on_power > 0.55:
            on_power = max(0.55, round(on_power - 0.05, 2))
        else:
            break
        params = WorkoutParams(**{**params.__dict__,
                                  "on_sec": on_sec, "on_power": on_power})
        tss = estimate_tss(params, ftp)
    return params, tss


def _params_dict(params):
    return {
        "focus": params.focus,
        "warmup_sec": params.warmup_sec, "warmup_cadence": params.warmup_cadence,
        "warmup_power_low": params.warmup_power_low,
        "warmup_power_high": params.warmup_power_high,
        "repeats": params.repeats, "on_sec": params.on_sec,
        "off_sec": params.off_sec, "on_power": params.on_power,
        "off_power": params.off_power, "cadence": params.cadence,
        "cadence_rest": params.cadence_rest, "cooldown_sec": params.cooldown_sec,
        "cooldown_cadence": params.cooldown_cadence,
        "cooldown_power_low": params.cooldown_power_low,
        "cooldown_power_high": params.cooldown_power_high,
    }


def _as_dict(w):
    return dataclasses.asdict(w)


def _day(item):
    raw = item.get("start_date_local") or item.get("start_time_local")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:19]).date()
    except ValueError:
        return None


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def event_payload(workout, ftp=DEFAULT_FTP, desc=None):
    return {
        "start_date_local": f"{workout['day']}T{START_TIME}",
        "category": "WORKOUT", "type": "Ride",
        "name": workout["name"],
        "description": desc or workout_text(workout, ftp),
        "planned_duration": workout["planned_duration"],
        "target": "POWER", "external_id": workout["external_id"],
    }


def workout_text(workout, ftp=DEFAULT_FTP):
    """Descricao nativa do Intervals (workout builder): a primeira linha e o
    titulo do treino e cada passo e `duracao percentual%`. Os watts (ex:
    `83% (151w)`) sao calculados pelo Intervals a partir do FTP."""
    params = workout["params"]
    lines = [workout["name"], ""]
    lines.append(f"- {_hm(params['warmup_sec'])} "
                 f"{_pct(params['warmup_power_low'])}-{_pct(params['warmup_power_high'])}% "
                 "Aquecimento")
    if params["repeats"] > 1:
        lines += ["", f"{params['repeats']}x"]
    lines.append(f"- {_hm(params['on_sec'])} "
                 f"{_pct(params['on_power'])}% Bloco principal")
    if params["off_sec"]:
        lines.append(f"- {_hm(params['off_sec'])} "
                     f"{_pct(params['off_power'])}% Recuperacao")
    lines += ["",
              f"- {_hm(params['cooldown_sec'])} "
              f"{_pct(params['cooldown_power_low'])}-{_pct(params['cooldown_power_high'])}% "
              "Desaquecimento"]
    return "\n".join(lines)


def _pct(frac):
    return str(int(round(frac * 100)))


def _hm(seconds):
    h, rem = divmod(seconds, 3600)
    m = round(rem / 60)
    if m == 60:
        h, m = h + 1, 0
    if h:
        return f"{h}h{m:02d}" if m else f"{h}h"
    return f"{m}m"


def _zone(frac):
    if frac >= 1.05:
        return "Z4"
    if frac >= 0.84:
        return "Z3"
    if frac >= 0.55:
        return "Z2"
    return "Z1"


def reconcile(plan, events, ftp=DEFAULT_FTP):
    done_ids = set()
    for item in events:
        eid = item.get("external_id")
        if eid and item.get("paired_activity_id"):
            done_ids.add(eid)
    today = date.today().isoformat()
    missed = [w for w in plan
              if w["day"] < today and w["external_id"] not in done_ids]
    if missed:
        for m in missed:
            plan = _insert_recovery(plan, m["day"], ftp)
            plan = _reduce_next_hard(plan, m["day"], ftp)
    return plan, missed


def _insert_recovery(plan, day, ftp):
    next_day = _next_weekday(day)
    base = templates()[FOCUS_ZONE2]
    params = WorkoutParams(focus=FOCUS_ZONE2, **dict(base, on_sec=1200, on_power=0.60))
    duration = sum((params.warmup_sec, params.repeats * (params.on_sec + params.off_sec),
                    params.cooldown_sec))
    recovery = PlannedWorkout(
        day=next_day, focus=FOCUS_ZONE2, planned_duration=duration,
        name=f"{next_day} - Recuperacao (plano ajustado)",
        params=_params_dict(params), tss=float(estimate_tss(params, ftp)),
        external_id=f"{EXTERNAL_ID_PREFIX}-{next_day}",
    )
    return [w for w in plan if w["day"] != next_day] + [_as_dict(recovery)]


def _reduce_next_hard(plan, day, ftp):
    out = []
    reduced = False
    for w in sorted(plan, key=lambda x: x["day"]):
        if not reduced and w["day"] > day and w["focus"] == FOCUS_THRESHOLD:
            params = dict(w["params"])
            params["on_power"] = round(params["on_power"] * 0.95, 3)
            tss = estimate_tss(WorkoutParams(**params), ftp)
            w = PlannedWorkout(day=w["day"], focus=w["focus"],
                               planned_duration=w["planned_duration"],
                               name=w["name"], params=params,
                               tss=float(tss), external_id=w["external_id"])
            w = _as_dict(w)
            reduced = True
        out.append(w)
    return out


def _next_weekday(day):
    d = date.fromisoformat(day) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def orphan_external_ids(plan, events, start=None):
    """external_ids hermes-plan presentes em `events` que nao pertencem ao
    plano atual (ou que ficam fora da janela iniciada em `start`)."""
    keep = {w["external_id"] for w in plan
            if not start or w["day"] >= start}
    return [e["external_id"] for e in events
            if (e.get("external_id") or "").startswith(EXTERNAL_ID_PREFIX)
            and e["external_id"] not in keep]


def save_plan(plan, path="plan.json"):
    out = pathlib.Path(path)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
    return out


def load_plan(path="plan.json"):
    with open(pathlib.Path(path), "r", encoding="utf-8") as fh:
        return json.load(fh)