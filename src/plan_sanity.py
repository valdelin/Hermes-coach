# -*- coding: utf-8 -*-
"""Pre-push sanity checks (VAR-03). Alert/block only, never auto-correct."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, Iterable, List, Optional

from . import coach


FOCUS_SWEETSPOT = getattr(coach, "FOCUS_SWEETSPOT", "sweetspot")
FOCUS_THRESHOLD = getattr(coach, "FOCUS_THRESHOLD", "threshold")
FOCUS_VO2 = getattr(coach, "FOCUS_VO2", "vo2max")


def _is_quality(focus: str) -> bool:
    f = str(focus)
    return f in (FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2, "sweetspot", "threshold", "vo2max")


@dataclass
class Issue:
    level: str
    code: str
    day: Optional[date]
    focus: Optional[str]
    message: str
    details: Dict[str, Any]

    def __str__(self) -> str:
        prefix = "BLOQUEIO" if self.level == "BLOCK" else "AVISO"
        day_s = self.day.isoformat() if self.day else "-"
        focus_s = self.focus or "-"
        return f"[{prefix}:{self.code}] {day_s} | {focus_s} | {self.message}"


@dataclass
class Report:
    issues: List[Issue]

    def has_block(self) -> bool:
        return any(i.level == "BLOCK" for i in self.issues)

    def has_warn(self) -> bool:
        return any(i.level == "WARN" for i in self.issues)

    def blocks(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "BLOCK"]

    def warns(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "WARN"]


def _parse_race_date(val: Optional[str]) -> Optional[date]:
    if not val:
        return None
    try:
        return date.fromisoformat(str(val).strip())
    except Exception:
        return None


def _get_env_int(name: str) -> Optional[int]:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return None
    try:
        v = int(str(raw).strip())
        if v <= 0:
            return None
        return v
    except Exception:
        return None


def _duration_sec(w: Dict[str, Any]) -> int:
    try:
        if "planned_duration" in w and w["planned_duration"] is not None:
            return int(w["planned_duration"])
    except Exception:
        pass
    try:
        p = w.get("params")
        if p is not None:
            warm = getattr(p, "warmup_sec", 0) or 0
            cool = getattr(p, "cooldown_sec", 0) or 0
            reps = getattr(p, "repeats", 0) or 0
            on_s = getattr(p, "on_sec", 0) or 0
            off_s = getattr(p, "off_sec", 0) or 0
            return int(warm + reps * (on_s + off_s) + cool)
    except Exception:
        pass
    return 0


def _get_params(w: Dict[str, Any]):
    return w.get("params")


def _zone_floor_for_focus(focus: str) -> Optional[float]:
    f = str(focus)
    z = None
    if f in (FOCUS_SWEETSPOT, "sweetspot"):
        z = "sweetspot"
    elif f in (FOCUS_THRESHOLD, "threshold"):
        z = "threshold"
    elif f in (FOCUS_VO2, "vo2max"):
        z = "vo2max"
    if not z:
        return None
    try:
        bands = getattr(coach, "ZONE_BANDS", {}) or {}
        b = bands.get(z)
        if not b:
            return None
        # new format: (low, high); old-like might be different but in this repo it's (low, high)
        low = b[0]
        if isinstance(low, (tuple, list)) and len(low) == 2:
            return float(low[0])
        # if it's already a float
        if isinstance(low, (int, float)):
            return float(low)
    except Exception:
        pass
    return None


def check_push(plan_list: Iterable[Dict[str, Any]], race_date: Optional[date] = None) -> Report:
    issues: List[Issue] = []

    race_d = race_date if race_date is not None else _parse_race_date(os.environ.get("RACE_DATE"))
    max_min = _get_env_int("MAX_WORKOUT_DURATION_MINUTES") or 180
    max_sec = int(max_min) * 60
    min_reg_min = _get_env_int("MIN_REGULAR_DURATION_MINUTES")
    min_reg_sec = int(min_reg_min) * 60 if min_reg_min and min_reg_min > 0 else None

    for w in plan_list or []:
        day_raw = w.get("day")
        try:
            if isinstance(day_raw, date):
                d = day_raw
            elif isinstance(day_raw, str):
                d = date.fromisoformat(day_raw)
            else:
                d = None
        except Exception:
            d = None

        focus = w.get("focus") or ""
        dur = _duration_sec(w)
        p = _get_params(w)
        qual = _is_quality(focus)

        if dur > max_sec:
            issues.append(Issue(level="BLOCK", code="SAN-02", day=d, focus=focus,
                                message=f"Duração {dur // 60} min excede teto configurado {max_min} min.",
                                details={"duration_sec": dur, "max_sec": max_sec}))

        if min_reg_sec and qual and dur < min_reg_sec:
            issues.append(Issue(level="WARN", code="SAN-06", day=d, focus=focus,
                                message=f"Duração {dur // 60} min abaixo da preferência individual {min_reg_min} min (esperado >= {min_reg_min} min).",
                                details={"duration_sec": dur, "min_regular_sec": min_reg_sec}))

        if race_d and d and qual:
            delta = (race_d - d).days
            if delta >= 0 and delta <= 2:
                issues.append(Issue(level="BLOCK", code="SAN-03", day=d, focus=focus,
                                    message=f"Sessão qualitativa a {delta} dia(s) da prova ({race_d.isoformat()}). Evitar qualidade em D-0/D-1/D-2 de prova.",
                                    details={"race_date": race_d.isoformat(), "delta_days": delta}))

        if qual and p is not None:
            warm = getattr(p, "warmup_sec", 0) or 0
            cool = getattr(p, "cooldown_sec", 0) or 0
            reps = getattr(p, "repeats", 0) or 0
            on_s = getattr(p, "on_sec", 0) or 0
            on_p = getattr(p, "on_power", 0.0) or 0.0

            if warm <= 0 or cool <= 0 or reps <= 0 or on_s <= 0:
                issues.append(Issue(level="BLOCK", code="SAN-04", day=d, focus=focus,
                                    message="Estrutura mínima inválida (aquecimento/resfriamento/blocos de trabalho ausentes ou zerados).",
                                    details={"warmup_sec": warm, "cooldown_sec": cool, "repeats": reps, "on_sec": on_s}))

            floor = _zone_floor_for_focus(focus)
            if floor is not None and on_p > 0.0 and on_p < floor - 1e-9:
                issues.append(Issue(level="BLOCK", code="SAN-05", day=d, focus=focus,
                                    message=f"Potência alvo ({on_p:.3f} FTP) abaixo do piso declarado da zona ({floor:.3f} FTP).",
                                    details={"on_power": on_p, "zone_floor": floor}))

    return Report(issues)
