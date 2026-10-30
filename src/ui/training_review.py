"""Projeções factuais compartilhadas para revisão de treinos na TUI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from src.coach import (
    FOCUS_ZONE1_RECOVERY,
    FOCUS_ZONE2_ENDURANCE,
    FOCUS_ZONE3_TEMPO,
    FOCUS_ZONE4_LIMIAR,
    FOCUS_ZONE5_VO2MAX,
    FOCUS_ZONE6_ANAEROBICA,
    ZONE_SWEETSPOT,
)


@dataclass(frozen=True)
class WorkoutBlock:
    label: str
    duration_seconds: int
    repetitions: int
    intensity: float | None


@dataclass(frozen=True)
class PlannedWorkoutSummary:
    focus: str
    duration_seconds: int | None
    tss: float | None
    blocks: tuple[WorkoutBlock, ...]
    zone_seconds: dict[str, float]


@dataclass(frozen=True)
class DayComparison:
    planned_duration_seconds: int | None
    actual_duration_seconds: int | None
    duration_delta_seconds: int | None
    planned_tss: float | None
    actual_tss: float | None
    tss_delta: float | None
    average_watts: float | None
    normalized_power: float | None


@dataclass(frozen=True)
class WeekSummary:
    planned_duration_seconds: int
    actual_duration_seconds: int
    planned_tss: float
    actual_tss: float
    completed: int
    missed: int
    pending: int
    extra: int
    planned_zone_seconds: dict[str, float]
    actual_zone_seconds: dict[str, float] | None


def _number(value: object, *, positive: bool = False) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if positive and number <= 0:
        return None
    return number


def _seconds(value: object) -> int | None:
    number = _number(value, positive=True)
    return int(number) if number is not None else None


def zone_for_intensity(intensity: float) -> str:
    if intensity < 0.56:
        return FOCUS_ZONE1_RECOVERY
    if intensity < 0.76:
        return FOCUS_ZONE2_ENDURANCE
    if intensity < 0.84:
        return FOCUS_ZONE3_TEMPO
    if intensity <= 0.97:
        return ZONE_SWEETSPOT
    if intensity <= 1.05:
        return FOCUS_ZONE4_LIMIAR
    if intensity <= 1.20:
        return FOCUS_ZONE5_VO2MAX
    return FOCUS_ZONE6_ANAEROBICA


def zone_seconds_for_plan(workout: dict) -> dict[str, float]:
    params = workout.get("params") or {}
    if not isinstance(params, dict):
        return {}
    seconds: dict[str, float] = {}

    def add(duration: object, intensity: object, repeats: int = 1) -> None:
        duration_seconds = _seconds(duration)
        power = _number(intensity)
        if duration_seconds is None or power is None:
            return
        zone = zone_for_intensity(power)
        seconds[zone] = seconds.get(zone, 0.0) + duration_seconds * repeats

    add(params.get("warmup_sec"), 0.50)
    repeats = _seconds(params.get("repeats")) or 1
    add(params.get("on_sec"), params.get("on_power"), repeats)
    if repeats > 1:
        add(params.get("off_sec"), params.get("off_power"), repeats - 1)
    add(params.get("cooldown_sec"), 0.50)
    return seconds


def planned_workout_summary(workout: dict) -> PlannedWorkoutSummary:
    params = workout.get("params") or {}
    params = params if isinstance(params, dict) else {}
    blocks = []

    def block(label: str, duration: object, repetitions: int, intensity: object) -> None:
        duration_seconds = _seconds(duration)
        if duration_seconds is not None:
            blocks.append(WorkoutBlock(label, duration_seconds, repetitions, _number(intensity)))

    repeats = _seconds(params.get("repeats")) or 1
    block("Aquecimento", params.get("warmup_sec"), 1, 0.50)
    block("Trabalho", params.get("on_sec"), repeats, params.get("on_power"))
    if repeats > 1:
        block("Recuperação", params.get("off_sec"), repeats - 1, params.get("off_power"))
    block("Desaquecimento", params.get("cooldown_sec"), 1, 0.50)
    return PlannedWorkoutSummary(
        str(workout.get("focus") or "—"),
        _seconds(workout.get("planned_duration")),
        _number(workout.get("tss"), positive=True),
        tuple(blocks),
        zone_seconds_for_plan(workout),
    )


def day_comparison(planned: dict, done: dict) -> DayComparison:
    planned_duration = _seconds(planned.get("planned_duration"))
    actual_duration = _seconds(done.get("duration") or done.get("moving_time") or done.get("elapsed_time"))
    planned_tss = _number(planned.get("tss"), positive=True)
    actual_tss = _number(done.get("tss") or done.get("icu_training_load"), positive=True)
    return DayComparison(
        planned_duration, actual_duration,
        actual_duration - planned_duration if actual_duration is not None and planned_duration is not None else None,
        planned_tss, actual_tss,
        actual_tss - planned_tss if actual_tss is not None and planned_tss is not None else None,
        _number(done.get("average_watts"), positive=True),
        _number(done.get("normalized_power"), positive=True),
    )


def zone_seconds_for_stream(points: list[tuple[float, float]], ftp: float | None) -> dict[str, float] | None:
    if ftp is None or ftp <= 0 or len(points) < 2:
        return None
    seconds: dict[str, float] = {}
    for index, (timestamp, watts) in enumerate(points):
        if index + 1 < len(points):
            duration = points[index + 1][0] - timestamp
        else:
            duration = timestamp - points[index - 1][0]
        if duration <= 0:
            continue
        zone = zone_for_intensity(max(0.0, watts) / ftp)
        seconds[zone] = seconds.get(zone, 0.0) + duration
    return seconds


def week_summary(
    entries: dict[str, dict],
    week_start: date,
    today: date,
    actual_zone_seconds: dict[str, dict[str, float]] | None = None,
) -> WeekSummary:
    planned_duration = actual_duration = 0
    planned_tss = actual_tss = 0.0
    completed = missed = pending = extra = 0
    planned_zones: dict[str, float] = {}
    actual_zones: dict[str, float] = {}
    has_actual_zones = False

    for offset in range(7):
        day = week_start + timedelta(days=offset)
        entry = entries.get(day.isoformat(), {})
        planned = entry.get("planned")
        done = entry.get("done")
        if planned:
            summary = planned_workout_summary(planned)
            planned_duration += summary.duration_seconds or 0
            planned_tss += summary.tss or 0.0
            for zone, seconds in summary.zone_seconds.items():
                planned_zones[zone] = planned_zones.get(zone, 0.0) + seconds
            if done:
                completed += 1
            elif day < today:
                missed += 1
            else:
                pending += 1
        elif done:
            extra += 1
        if done:
            actual_duration += _seconds(done.get("duration") or done.get("moving_time") or done.get("elapsed_time")) or 0
            actual_tss += _number(done.get("tss") or done.get("icu_training_load"), positive=True) or 0.0
        if actual_zone_seconds and day.isoformat() in actual_zone_seconds:
            has_actual_zones = True
            for zone, seconds in actual_zone_seconds[day.isoformat()].items():
                actual_zones[zone] = actual_zones.get(zone, 0.0) + seconds

    return WeekSummary(
        planned_duration, actual_duration, planned_tss, actual_tss,
        completed, missed, pending, extra, planned_zones,
        actual_zones if has_actual_zones else None,
    )
