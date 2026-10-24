#!/usr/bin/env python3
"""PROTÓTIPO DESCARTÁVEL: compara VAR-01/02/03 sem chamar Intervals.

Gera CSVs que abrem em LibreOffice/Excel. Não lê .env, não grava plan.json e
não publica eventos. Serve apenas para decidir se as políticas de variedade
produzem a diferença esperada antes de entrarem no motor.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.plan import BLOCK_VARIANTS, FOCUS_VO2, QUALITY_FOCUSES, build_plan


FOCUSES = ("zone2", "sweetspot", "zone2", "sweetspot", FOCUS_VO2)


def signature(focus: str, variant: dict) -> tuple:
    return (focus, variant["repeats"], variant["on_sec"],
            variant["off_sec"], variant["on_power"])


def choose_baseline(focus: str, day_index: int, _week: int, _history: list) -> dict:
    return BLOCK_VARIANTS[focus][day_index % len(BLOCK_VARIANTS[focus])]


def choose_var01(focus: str, day_index: int, week: int, _history: list) -> dict:
    variants = BLOCK_VARIANTS[focus]
    return variants[(day_index + week) % len(variants)]


def choose_var02(focus: str, day_index: int, week: int, history: list) -> dict:
    """Prefere formato não usado nos últimos 14 dias; fallback = VAR-01."""
    variants = BLOCK_VARIANTS[focus]
    recent = {entry[1] for entry in history if week - entry[0] <= 2}
    preferred = (day_index + week) % len(variants)
    ordered = variants[preferred:] + variants[:preferred]
    return next((v for v in ordered if signature(focus, v) not in recent),
                ordered[0])


def validate_var03(plan: list[dict], race_date: date | None) -> list[tuple[str, str, str]]:
    """Protótipo da barreira VAR-03: só retorna vereditos, nunca reescreve."""
    results = []
    for workout in plan:
        day = date.fromisoformat(workout["day"])
        focus = workout["focus"]
        duration = workout["planned_duration"]
        if duration < 20 * 60:
            results.append((workout["day"], "duration", "FAIL: abaixo de 20 min"))
        else:
            results.append((workout["day"], "duration", "PASS"))
        if race_date and focus in QUALITY_FOCUSES and 0 < (race_date - day).days <= 2:
            results.append((workout["day"], "taper", "FAIL: qualidade D-1/D-2"))
        else:
            results.append((workout["day"], "taper", "PASS"))
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("/tmp/opencode/workout-variety"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    choices = {"baseline": choose_baseline, "VAR-01": choose_var01,
               "VAR-02": choose_var02}
    rows = []
    for label, choose in choices.items():
        history = []
        for week in range(4):
            for day_index, focus in enumerate(FOCUSES):
                variant = choose(focus, day_index, week, history)
                sig = signature(focus, variant)
                repeated = sig in {item[1] for item in history if week - item[0] <= 2}
                rows.append({"strategy": label, "week": week + 1,
                             "day_slot": day_index + 1, "focus": focus,
                             "signature": " | ".join(map(str, sig)),
                             "repeat_within_14d": repeated})
                history.append((week, sig))

    with (args.out / "variety-comparison.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    start = date(2026, 10, 26)
    valid = build_plan([], tsb=-5, ftp=250, days=14, start=start,
                       training_days=(0, 1, 2, 3, 4), goal="ftp-builder")
    results = validate_var03(valid, None)
    # Caso negativo deliberado: qualidade D-1 de uma prova.
    invalid = [dict(valid[0], day="2026-11-07", focus=FOCUS_VO2)]
    results.extend(validate_var03(invalid, date(2026, 11, 8)))
    with (args.out / "var03-sanity-check.csv").open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(("case", "day", "check", "verdict"))
        for day, check, verdict in results:
            writer.writerow(("generated" if verdict == "PASS" else "deliberately_invalid",
                             day, check, verdict))

    summary = args.out / "README.md"
    summary.write_text(
        "# Protótipo offline — variedade de treinos\n\n"
        "- `variety-comparison.csv`: baseline atual vs VAR-01 e VAR-02 em quatro semanas.\n"
        "- `var03-sanity-check.csv`: vereditos do protótipo de validação pré-push.\n"
        "- Nenhum arquivo foi enviado ao Intervals nem salvo como `plan.json`.\n"
        "- VAR-01/02/03 ainda não são comportamento produtivo; este artefato só testa a política.\n"
    )
    print(f"Relatório offline: {args.out}")


if __name__ == "__main__":
    main()
