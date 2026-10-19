#!/usr/bin/env python3
"""Entrada explícita para avaliação online M2-7; nunca roda no import."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.online import ONLINE_MODEL, run_online_evaluation, skipped_online_evaluation  # noqa: E402
from scripts.run_insight_evals import load_cases  # noqa: E402
from src.insight.openai_provider import OpenAIInsightModelProvider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=ROOT / "evals/cases.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default=ONLINE_MODEL)
    args = parser.parse_args()
    if args.model != ONLINE_MODEL:
        parser.error("model deve ser o snapshot M2-4 aprovado")
    cases = load_cases(args.cases)
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        report = skipped_online_evaluation(
            cases, reason="online_credential_unavailable")
    else:
        provider = OpenAIInsightModelProvider(api_key=api_key)
        report = run_online_evaluation(
            cases,
            provider=provider,
            executed_at=datetime.now(timezone.utc),
            telemetry_clock=lambda: Decimal(str(time.monotonic())),
        )
    payload = report.to_safe_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0 if report.status.value in ("PASS", "SKIPPED") else 1


if __name__ == "__main__":
    raise SystemExit(main())
