#!/usr/bin/env python3
"""Runner offline dos fixtures de eval do INSIGHT M1 v2."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evals.graders import EvalStatus, evaluate_case  # noqa: E402


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_self_test(cases: list[dict], fail_fixture: bool = False) -> EvalStatus:
    passed = True
    for index, case in enumerate(cases):
        candidate = case["candidate"]
        if fail_fixture and index == 0:
            candidate = {**candidate, "presentation": {**candidate["presentation"], "focus": "forbidden"}}
            expected = EvalStatus.FAIL.value
        else:
            expected = case["expected_status"]
        actual = evaluate_case(case, candidate).value
        print(f"{case['id']}: {actual}")
        passed = passed and actual == expected
    return EvalStatus.PASS if passed and not fail_fixture else EvalStatus.FAIL


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=ROOT / "evals/cases.jsonl")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--fail-fixture", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        print(EvalStatus.SKIPPED.value + ": use --self-test for offline fixtures")
        return 0
    status = run_self_test(load_cases(args.cases), args.fail_fixture)
    print(status.value)
    return 0 if status is EvalStatus.PASS else 1


if __name__ == "__main__":
    raise SystemExit(main())
