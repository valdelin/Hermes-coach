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
    for activity in activities:
        event_id = activity.get("paired_event_id")
        paired_id = event_activity.get(str(event_id)) if event_id is not None else None
        paired = by_id.get(paired_id) if paired_id else None
        if (str(activity.get("source") or "").upper() == "MANUAL"
                and paired is not None
                and str(paired.get("source") or "").upper() != "MANUAL"
                and str(activity.get("id")) != paired_id):
            continue
        kept.append(activity)
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
