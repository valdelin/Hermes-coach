"""Testes offline do dataset e graders de dominio INSIGHT-4."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

from evals import graders
from evals.graders import (EvalStatus, GRADERS, GradeResult, KNOWN_PROPERTIES,
                           evaluate_case, grade_case, grade_prescription_invariance)
from scripts.run_insight_evals import load_cases, run_self_test


ROOT = Path(__file__).resolve().parent.parent
CASES = ROOT / "evals/cases.jsonl"


class DatasetTest(unittest.TestCase):
    def test_cases_are_valid_independent_and_safe(self) -> None:
        cases = load_cases(CASES)
        self.assertGreaterEqual(len(cases), 8)
        ids = set()
        for case in cases:
            self.assertIn("id", case); self.assertNotIn(case["id"], ids); ids.add(case["id"])
            self.assertTrue(all(key in case for key in ("context", "expected_properties", "forbidden_properties", "candidate", "notes")))
            self.assertTrue(set(case["expected_properties"]) <= KNOWN_PROPERTIES)
            self.assertTrue(all(isinstance(item, str) and item for item in case["forbidden_properties"]))
            self.assertNotIn("raw_payload", json.dumps(case).lower())
            self.assertNotRegex(json.dumps(case).lower(), r"api[_-]?key|authorization|bearer|@")

    def test_fixture_outcomes_cover_pass_and_fail(self) -> None:
        outcomes = [evaluate_case(case, case["candidate"]).value for case in load_cases(CASES)]
        self.assertIn(EvalStatus.PASS.value, outcomes)
        self.assertIn(EvalStatus.FAIL.value, outcomes)


class GraderTest(unittest.TestCase):
    def test_grade_result_requires_real_bool(self) -> None:
        self.assertTrue(GradeResult("g", True, "ok").passed)
        self.assertFalse(GradeResult("g", False, "fail").passed)
        for value in (1, 0, "true", None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "bool"):
                    GradeResult("g", value, "invalid")  # type: ignore[arg-type]

    def test_all_g1_to_g7_are_registered_and_deterministic(self) -> None:
        self.assertEqual(len(GRADERS), 7)
        case = load_cases(CASES)[0]
        self.assertEqual(grade_case(case, case["candidate"]), grade_case(case, case["candidate"]))

    def test_each_grader_has_a_passing_case_and_failures_are_covered(self) -> None:
        cases = load_cases(CASES)
        results = [grade_case(case, case["candidate"]) for case in cases]
        for index, grader in enumerate(GRADERS):
            with self.subTest(grader=grader.__name__):
                self.assertTrue(any(result[index].passed for result in results))
        self.assertTrue(any(not result.passed for row in results for result in row))

    def test_caution_and_grounding_fail_closed(self) -> None:
        cases = {case["id"]: case for case in load_cases(CASES)}
        self.assertEqual(evaluate_case(cases["advice-absent-caution-fails"], cases["advice-absent-caution-fails"]["candidate"]), EvalStatus.FAIL)
        self.assertEqual(evaluate_case(cases["unknown-fact-fails"], cases["unknown-fact-fails"]["candidate"]), EvalStatus.FAIL)

    def test_g7_preserves_a_real_insight_view_and_prescribed_session(self) -> None:
        case = next(case for case in load_cases(CASES) if case["id"] == "simple-fact")
        view = graders._build_eval_view(case["context"])
        before = view
        result = grade_prescription_invariance(case, case["candidate"])
        self.assertIs(type(result.passed), bool)
        self.assertTrue(result.passed)
        self.assertEqual(view, before)
        self.assertEqual(view.prescribed_session, before.prescribed_session)


class RunnerTest(unittest.TestCase):
    def test_self_test_passes_and_fail_fixture_fails(self) -> None:
        cases = load_cases(CASES)
        self.assertEqual(run_self_test(cases), EvalStatus.PASS)
        self.assertEqual(run_self_test(cases, fail_fixture=True), EvalStatus.FAIL)
