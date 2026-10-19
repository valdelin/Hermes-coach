"""Testes offline do runner online isolado INSIGHT M2-7."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from evals.graders import EvalStatus
from evals.online import ONLINE_MODEL, run_online_evaluation, skipped_online_evaluation
from scripts.run_insight_evals import load_cases
from src.insight.model_provider import (
    InsightModelRequest, InsightModelResponse, InsightModelUsage,
    InsightProviderTimeoutError,
)


ROOT = Path(__file__).resolve().parent.parent
TIMESTAMP = datetime(2026, 10, 19, 12, tzinfo=timezone.utc)
VALID_TEXT = json.dumps({
    "headline": "Resumo",
    "explanation": "Estado estruturado",
    "next_action_text": "Siga o plano",
    "caution_text": None,
})


class _Provider:
    def __init__(self, text: str = VALID_TEXT, *, error: Exception | None = None,
                 usage: InsightModelUsage | None = None) -> None:
        self.text = text
        self.error = error
        self.usage = usage
        self.calls: list[InsightModelRequest] = []

    def generate(self, request: InsightModelRequest) -> InsightModelResponse:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return InsightModelResponse(
            text=self.text,
            provider="openai",
            requested_model=request.requested_model,
            resolved_model=ONLINE_MODEL,
            request_id="resp_123",
            usage=self.usage,
        )


def _case(case_id: str) -> dict:
    return next(case for case in load_cases(ROOT / "evals/cases.jsonl") if case["id"] == case_id)


class OnlineEvalTest(unittest.TestCase):
    def _run(self, case: dict, provider: _Provider):
        return run_online_evaluation(
            [case], provider=provider, executed_at=TIMESTAMP,
            telemetry_clock=lambda: Decimal("1"))

    def test_success_uses_runtime_graders_safe_telemetry_and_one_call(self) -> None:
        provider = _Provider(usage=InsightModelUsage(
            input_tokens=1_000_000, cached_input_tokens=200_000,
            output_tokens=1_000_000))
        report = self._run(_case("simple-fact"), provider)
        result = report.cases[0]
        self.assertEqual(report.status, EvalStatus.PASS)
        self.assertEqual(result.status, EvalStatus.PASS)
        self.assertEqual(result.runtime_status.value, "success")
        self.assertTrue(all(grade.passed for grade in result.grades))
        self.assertEqual(provider.calls[0].requested_model, ONLINE_MODEL)
        self.assertEqual(len(provider.calls), 1)
        self.assertEqual(report.known_cost_usd, Decimal("1.414"))
        self.assertTrue(report.cost_complete)
        serialized = json.dumps(report.to_safe_dict(), sort_keys=True)
        for sentinel in ("__SECRET_PROMPT__", "__RAW_RESPONSE__", "__OPENAI_KEY__", "__ATHLETE_SUBJECT__"):
            self.assertNotIn(sentinel, serialized)

    def test_all_hermes_fixtures_are_checked_before_online_calls(self) -> None:
        cases = load_cases(ROOT / "evals/cases.jsonl")
        provider = _Provider()
        report = run_online_evaluation(
            cases, provider=provider, executed_at=TIMESTAMP,
            telemetry_clock=lambda: Decimal("1"))
        self.assertEqual(report.status, EvalStatus.PASS)
        self.assertEqual(report.pass_count, len(cases))
        self.assertEqual(len(provider.calls), len(cases))

    def test_inconsistent_offline_fixture_is_infra_error_without_provider_call(self) -> None:
        case = dict(_case("advice-absent-caution-fails"))
        case["candidate"] = {
            "presentation": {
                "headline": "Resumo",
                "explanation": "Estado",
                "next_action_text": "Siga o plano",
                "caution_text": None,
            },
            "used_fact_keys": [],
        }
        provider = _Provider()
        report = self._run(case, provider)
        self.assertEqual(report.status, EvalStatus.INFRA_ERROR)
        self.assertEqual(report.cases[0].reason, "offline_fixture_inconsistent")
        self.assertEqual(len(provider.calls), 0)

    def test_domain_grader_failure_is_fail_not_infra(self) -> None:
        provider = _Provider(text=json.dumps({
            "headline": "Resumo",
            "explanation": "[claim:prescribed_session]",
            "next_action_text": "Siga o plano",
            "caution_text": None,
        }))
        report = self._run(_case("contradiction-marker-fails"), provider)
        self.assertEqual(report.status, EvalStatus.FAIL)
        self.assertEqual(report.cases[0].status, EvalStatus.FAIL)
        self.assertEqual(len(provider.calls), 1)

    def test_invalid_model_response_is_fail_not_infra(self) -> None:
        report = self._run(_case("simple-fact"), _Provider(text="not-json"))
        self.assertEqual(report.status, EvalStatus.FAIL)
        self.assertEqual(report.cases[0].runtime_status.value, "fallback_invalid_response")
        self.assertNotIn("not-json", json.dumps(report.to_safe_dict(), sort_keys=True))

    def test_provider_failure_is_infra_error_without_retry(self) -> None:
        provider = _Provider(error=InsightProviderTimeoutError())
        report = self._run(_case("simple-fact"), provider)
        self.assertEqual(report.status, EvalStatus.INFRA_ERROR)
        self.assertEqual(report.cases[0].status, EvalStatus.INFRA_ERROR)
        self.assertEqual(len(provider.calls), 1)
        self.assertIsNone(report.cases[0].telemetry.usage)
        self.assertIsNone(report.cases[0].telemetry.estimated_cost_usd)

    def test_unexpected_runtime_failure_is_infra_error_not_model_fail(self) -> None:
        provider = _Provider(error=RuntimeError("transport harness failure"))
        report = self._run(_case("simple-fact"), provider)
        self.assertEqual(report.status, EvalStatus.INFRA_ERROR)
        self.assertEqual(report.cases[0].runtime_status.value, "fallback_internal")
        self.assertEqual(len(provider.calls), 1)

    def test_missing_credential_path_is_explicit_skip_without_provider(self) -> None:
        report = skipped_online_evaluation([_case("simple-fact")],
                                           reason="online_credential_unavailable")
        self.assertEqual(report.status, EvalStatus.SKIPPED)
        self.assertEqual(report.cases[0].status, EvalStatus.SKIPPED)
        self.assertEqual(report.unknown_cost_case_count, 1)

    def test_unknown_cost_remains_unknown_in_safe_report(self) -> None:
        report = self._run(_case("simple-fact"), _Provider(usage=InsightModelUsage(
            input_tokens=1, cached_input_tokens=None, output_tokens=1)))
        self.assertEqual(report.status, EvalStatus.PASS)
        self.assertEqual(report.known_cost_usd, Decimal("0"))
        self.assertEqual(report.unknown_cost_case_count, 1)
        self.assertFalse(report.cost_complete)

    def test_script_import_and_missing_credential_are_explicit_skip_without_network(self) -> None:
        script_path = ROOT / "scripts/run_insight_online_eval.py"
        spec = importlib.util.spec_from_file_location("online_eval_script", script_path)
        module = importlib.util.module_from_spec(spec)
        old_argv = sys.argv
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        try:
            spec.loader.exec_module(module)  # type: ignore[union-attr]
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "report.json"
                sys.argv = [str(script_path), "--output", str(output)]
                self.assertEqual(module.main(), 0)
                report = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(report["status"], EvalStatus.SKIPPED.value)
            self.assertEqual(report["counts"]["SKIPPED"], 10)
        finally:
            sys.argv = old_argv
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key


class WorkflowTest(unittest.TestCase):
    def test_online_workflow_is_manual_secret_gated_and_isolated(self) -> None:
        path = ROOT / ".github/workflows/insight-online-eval.yml"
        text = path.read_text(encoding="utf-8")
        self.assertIn("on:\n  workflow_dispatch:", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("secrets.OPENAI_API_KEY", text)
        self.assertIn("pip install -r requirements.txt", text)
        self.assertIn("insight-online-eval.json", text)
        self.assertNotIn("push:", text)
        self.assertNotIn("pull_request:", text)
        self.assertIn("--model gpt-5.4-nano-2026-03-17", text)


if __name__ == "__main__":
    unittest.main()
