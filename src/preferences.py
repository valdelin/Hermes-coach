"""Preferências do usuário (dias de treino, etc.)."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
PREFS_PATH = DATA_DIR / "user_prefs.json"

DEFAULT_TRAINING_DAYS = (0, 1, 2, 3, 4)
DAY_LABELS = [
    ("SEG", 0),
    ("TER", 1),
    ("QUA", 2),
    ("QUI", 3),
    ("SEX", 4),
    ("SÁB", 5),
    ("DOM", 6),
]


def _load_json(path: Path | None = None) -> dict[str, Any]:
    try:
        source = path if path is not None else PREFS_PATH
        if source.exists():
            return json.loads(source.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def load_training_days() -> tuple[int, ...]:
    """Carrega dias de treino das preferências do usuário.

    Prioridade: user_prefs.json > TRAINING_DAYS (env) > default (seg-sex).
    """
    prefs = _load_json()
    if prefs.get("training_days") is not None:
        try:
            days = []
            for d in prefs["training_days"]:
                days.append(int(d))
            days = tuple(sorted(set(days)))
            if days:
                return days
        except Exception:
            pass

    raw = os.environ.get("TRAINING_DAYS") or os.environ.get("TRAINING_DAYS") or ""
    try:
        from . import plan

        return plan.parse_training_days(raw)
    except Exception:
        try:
            import plan

            return plan.parse_training_days(raw)
        except Exception:
            return DEFAULT_TRAINING_DAYS


def load_preferred_long_day() -> int | None:
    prefs = _load_json()
    if prefs.get("preferred_long_day") is not None:
        try:
            v = prefs["preferred_long_day"]
            if v == "" or v is None:
                return None
            return int(v)
        except Exception:
            pass

    raw = os.environ.get("LONG_DAY")
    if not raw:
        return None
    try:
        from . import plan

        return plan.parse_long_day(raw)
    except Exception:
        try:
            import plan

            return plan.parse_long_day(raw)
        except Exception:
            return None


def save_training_days(days: list[int] | tuple[int, ...]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prefs = _load_json()
    cleaned = []
    for d in days:
        try:
            v = int(d)
            if 0 <= v <= 6:
                cleaned.append(v)
        except Exception:
            continue
    cleaned = sorted(set(cleaned))
    if not cleaned:
        cleaned = list(DEFAULT_TRAINING_DAYS)
    prefs["training_days"] = cleaned
    try:
        PREFS_PATH.write_text(json.dumps(prefs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        raise


def save_preferred_long_day(day: int | None) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    prefs = _load_json()
    if day is None or day == "":
        prefs.pop("preferred_long_day", None)
    else:
        try:
            v = int(day)
            if 0 <= v <= 6:
                prefs["preferred_long_day"] = v
            else:
                prefs.pop("preferred_long_day", None)
        except Exception:
            prefs.pop("preferred_long_day", None)
    try:
        PREFS_PATH.write_text(json.dumps(prefs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception:
        raise
