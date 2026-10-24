#!/usr/bin/env python3
"""PROTÓTIPO DESCARTÁVEL: avalia teto por treino sem Intervals ou plan.json.

Compara o cap parcial atual (reduz somente trabalho) com a política candidata
que consegue acomodar qualquer sessão em 30 minutos comprimindo tempos, sem
mudar potência/zona. Não é código produtivo.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.plan import BLOCK_VARIANTS


CAPS_MINUTES = (30, 45, 60, 90)
CASES = ((focus, variants[0]) for focus, variants in BLOCK_VARIANTS.items())


def duration_min(parts: dict) -> float:
    return (parts["warmup_sec"] + parts["cooldown_sec"] +
            parts["repeats"] * (parts["on_sec"] + parts["off_sec"])) / 60


def baseline(focus: str, variant: dict) -> dict:
    return {"focus": focus, "warmup_sec": 600, "cooldown_sec": 600,
            "repeats": variant["repeats"], "on_sec": variant["on_sec"],
            "off_sec": variant["off_sec"], "on_power": variant["on_power"]}


def current_partial_cap(parts: dict, cap_minutes: int) -> tuple[dict, str]:
    """Espelha a intenção da implementação WIP: só reduz on_sec."""
    copied = dict(parts)
    fixed = copied["warmup_sec"] + copied["cooldown_sec"] + copied["repeats"] * copied["off_sec"]
    available = cap_minutes * 60 - fixed
    if available < copied["repeats"] * 60:
        return copied, "não cabe: cap não aplicado"
    copied["on_sec"] = max(60, available // copied["repeats"])
    return copied, "cap aplicado"


def compressed_cap(parts: dict, cap_minutes: int) -> tuple[dict, str]:
    """Candidato: WU/CD >=5 min; trabalho/recuperação >=1 min quando existem."""
    copied = dict(parts)
    repeats = copied["repeats"]
    min_warmup = min(copied["warmup_sec"], 300)
    min_cooldown = min(copied["cooldown_sec"], 300)
    min_on = 60
    min_off = 60 if copied["off_sec"] else 0
    minimum = min_warmup + min_cooldown + repeats * (min_on + min_off)
    target = cap_minutes * 60
    if target < minimum:
        return copied, f"inválido: mínimo estrutural {minimum // 60} min"

    original_variable = (copied["warmup_sec"] - min_warmup +
                         copied["cooldown_sec"] - min_cooldown +
                         repeats * ((copied["on_sec"] - min_on) +
                                    max(0, copied["off_sec"] - min_off)))
    extra = target - minimum
    ratio = min(1.0, extra / original_variable) if original_variable else 0
    copied["warmup_sec"] = int(min_warmup + (parts["warmup_sec"] - min_warmup) * ratio)
    copied["cooldown_sec"] = int(min_cooldown + (parts["cooldown_sec"] - min_cooldown) * ratio)
    copied["on_sec"] = int(min_on + (parts["on_sec"] - min_on) * ratio)
    if parts["off_sec"]:
        copied["off_sec"] = int(min_off + (parts["off_sec"] - min_off) * ratio)
    return copied, "cap aplicado; potência/zona preservadas"


def main() -> None:
    out = Path("/tmp/opencode/max-workout-duration")
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for focus, variant in CASES:
        source = baseline(focus, variant)
        for cap in CAPS_MINUTES:
            for policy, function in (("WIP: reduz só trabalho", current_partial_cap),
                                     ("Candidata: comprime estrutura", compressed_cap)):
                result, verdict = function(source, cap)
                rows.append({
                    "focus": focus,
                    "cap_minutes": cap,
                    "policy": policy,
                    "baseline_minutes": round(duration_min(source), 1),
                    "result_minutes": round(duration_min(result), 1),
                    "warmup_minutes": round(result["warmup_sec"] / 60, 1),
                    "work_minutes_each": round(result["on_sec"] / 60, 1),
                    "recovery_minutes_each": round(result["off_sec"] / 60, 1),
                    "cooldown_minutes": round(result["cooldown_sec"] / 60, 1),
                    "power_pct_ftp": result["on_power"],
                    "verdict": verdict,
                })
    path = out / "max-workout-duration-simulation.csv"
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    (out / "README.md").write_text(
        "# Simulação offline de duração máxima\n\n"
        "A política candidata usa floors de 5min warm-up/cooldown e 1min por trecho de "
        "trabalho/recuperação. Esses valores são hipótese de produto, não regra fisiológica.\n"
    )
    print(path)


if __name__ == "__main__":
    main()
