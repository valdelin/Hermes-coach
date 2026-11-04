"""Projeções de leitura dos vínculos entre eventos e atividades."""

from __future__ import annotations

from dataclasses import dataclass
import math


@dataclass(frozen=True)
class ActivityLinks:
    activities: tuple[dict, ...]
    event_activity: dict[str, str]
    activity_event: dict[str, str]


def link_activities(events: list[dict], activities: list[dict]) -> ActivityLinks:
    """Vincula apenas IDs explícitos, preservando manuais sem duplicata comprovada."""
    by_id = {str(a["id"]): a for a in activities if a.get("id") is not None}
    event_activity = {}
    activity_event = {}
    for event in events:
        event_id = event.get("id")
        activity_id = event.get("paired_activity_id")
        if event_id is None or activity_id is None or str(activity_id) not in by_id:
            continue
        eid, aid = str(event_id), str(activity_id)
        event_activity[eid] = aid
        activity_event[aid] = eid

    kept = []
    seen_ids = set()
    for activity in activities:
        activity_id = activity.get("id")
        if activity_id is not None and str(activity_id) in seen_ids:
            continue
        event_id = activity.get("paired_event_id")
        paired_id = event_activity.get(str(event_id)) if event_id is not None else None
        paired = by_id.get(paired_id) if paired_id else None
        if (str(activity.get("source") or "").upper() == "MANUAL"
                and paired is not None
                and str(activity.get("id")) != paired_id):
            continue
        kept.append(activity)
        if activity_id is not None:
            seen_ids.add(str(activity_id))
    return ActivityLinks(tuple(kept), event_activity, activity_event)


def historical_power_steps(event: dict) -> tuple[tuple[int, float, float], ...] | None:
    """Retorna apenas passos simples explícitos em %FTP; rejeita perfis parciais."""
    doc = event.get("workout_doc")
    steps = doc.get("steps") if isinstance(doc, dict) else None
    if not isinstance(steps, list) or not steps:
        return None
    result = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("power"), dict):
            return None
        power = step["power"]
        if power.get("units") != "%ftp" or any(k in step for k in ("steps", "repeat", "repeats")):
            return None
        if "value" in power and ("start" in power or "end" in power):
            return None
        try:
            duration = float(step["duration"])
            start = float(power["value"] if "value" in power else power["start"])
            end = float(power["value"] if "value" in power else power["end"])
        except (KeyError, TypeError, ValueError):
            return None
        if not all(math.isfinite(x) for x in (duration, start, end)) or duration <= 0 or start < 0 or end < 0 or not duration.is_integer():
            return None
        result.append((int(duration), start / 100, end / 100))
    return tuple(result)


def sample_power_steps(steps: tuple, width: int) -> list[float]:
    """Amostra linearmente no tempo os passos históricos já validados."""
    if not steps or width < 1:
        return []
    total = sum(step[0] for step in steps)
    samples = []
    for index in range(width):
        position = (index + 0.5) * total / width
        for duration, start, end in steps:
            if position <= duration:
                samples.append(start + (end - start) * position / duration)
                break
            position -= duration
    return samples


def compare_power_structure(local: dict, remote: tuple | None) -> bool | None:
    """Compara passos explícitos; formatos não representáveis retornam None."""
    if not remote or local.get("hr_mode"):
        return None
    params = local.get("params")
    if not isinstance(params, dict):
        return None
    try:
        repeats = params["repeats"]
        if isinstance(repeats, bool) or not isinstance(repeats, int) or not 1 <= repeats <= 100:
            return None
        steps = []
        def append(duration, start, end):
            duration, start, end = float(duration), float(start), float(end)
            if not all(math.isfinite(x) for x in (duration, start, end)) or duration <= 0 or duration % 60 or start < 0 or end < 0:
                raise ValueError("passo não comparável")
            steps.append((int(duration), round(start * 100) / 100, round(end * 100) / 100))
        append(params["warmup_sec"], params["warmup_power_low"], params["warmup_power_high"])
        for _ in range(repeats):
            append(params["on_sec"], params["on_power"], params["on_power"])
            if params["off_sec"]:
                append(params["off_sec"], params["off_power"], params["off_power"])
        append(params["cooldown_sec"], params["cooldown_power_low"], params["cooldown_power_high"])
        return tuple(steps) == remote
    except (KeyError, TypeError, ValueError, OverflowError):
        return None
