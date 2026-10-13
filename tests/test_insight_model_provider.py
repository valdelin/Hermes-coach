"""Contrato offline da boundary de modelo do INSIGHT-3."""
from __future__ import annotations

import dataclasses
from pathlib import Path
import unittest

from src.insight.model_provider import (
    InsightInvocationStatus, InsightModelProvider, InsightModelRequest,
    InsightModelResponse, InsightProviderAuthError, InsightProviderError,
    InsightProviderInvalidResponseError, InsightProviderRateLimitError,
    InsightProviderTimeoutError, InsightProviderUnavailableError,
    InsightRuntimeProvenance,
)


SHA = "a" * 64
TIMESTAMP = "2026-10-13T12:00:00+00:00"


class FakeProvider:
    def generate(self, request: InsightModelRequest) -> InsightModelResponse:
        return InsightModelResponse("{}", "fake", "requested")


class RequestTest(unittest.TestCase):
    def test_valid_request_is_frozen(self) -> None:
        request = InsightModelRequest("v1", SHA, "prepared input", 1)
        self.assertEqual(request.schema_version, 1)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            request.input_text = "other"  # type: ignore[misc]

    def test_request_rejects_invalid_fields(self) -> None:
        cases = (
            (" ", SHA, "input", 1), ("v1", "A" * 64, "input", 1),
            ("v1", SHA, " ", 1), ("v1", SHA, "input", True),
            ("v1", SHA, "input", 0),
        )
        for case in cases:
            with self.subTest(case=case):
                with self.assertRaises(ValueError):
                    InsightModelRequest(*case)  # type: ignore[arg-type]


class ResponseAndProvenanceTest(unittest.TestCase):
    def test_response_is_frozen_and_resolved_model_is_optional(self) -> None:
        response = InsightModelResponse("raw text", "future-provider", "model-alias")
        self.assertIsNone(response.resolved_model)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            response.text = "other"  # type: ignore[misc]

    def test_response_rejects_empty_text_provider_and_model(self) -> None:
        for args in ((" ", "provider", "model"), ("text", " ", "model"), ("text", "provider", " ")):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    InsightModelResponse(*args)

    def test_provenance_is_frozen_and_caller_supplies_aware_timestamp(self) -> None:
        provenance = InsightRuntimeProvenance("future-provider", "model", None, "v1", SHA, TIMESTAMP, "h1", "abcdef0")
        with self.assertRaises(dataclasses.FrozenInstanceError):
            provenance.provider = "other"  # type: ignore[misc]
        for timestamp in ("", "not-a-time", "2026-10-13T12:00:00"):
            with self.subTest(timestamp=timestamp):
                with self.assertRaises(ValueError):
                    InsightRuntimeProvenance("p", "m", None, "v1", SHA, timestamp)


class ErrorAndProtocolTest(unittest.TestCase):
    def test_error_taxonomy_has_stable_code_and_no_retry_execution(self) -> None:
        expected = (
            (InsightProviderError, "provider_error", False),
            (InsightProviderAuthError, "auth_error", False),
            (InsightProviderRateLimitError, "rate_limited", True),
            (InsightProviderTimeoutError, "timeout", True),
            (InsightProviderUnavailableError, "provider_unavailable", True),
            (InsightProviderInvalidResponseError, "invalid_response", False),
        )
        for error_type, code, retryable in expected:
            with self.subTest(error_type=error_type):
                error = error_type("failure")
                self.assertEqual(error.code, code)
                self.assertEqual(error.retryable, retryable)

    def test_fake_provider_satisfies_protocol_and_returns_typed_response(self) -> None:
        provider = FakeProvider()
        self.assertIsInstance(provider, InsightModelProvider)
        self.assertIsInstance(provider.generate(InsightModelRequest("v1", SHA, "input", 1)), InsightModelResponse)

    def test_status_is_closed(self) -> None:
        self.assertEqual(InsightInvocationStatus.SUCCESS.value, "success")
        with self.assertRaises(ValueError):
            InsightInvocationStatus("unknown")


class ArchitectureTest(unittest.TestCase):
    def test_contract_has_no_tools_memory_network_clock_or_domain_imports(self) -> None:
        root = Path(__file__).resolve().parent.parent
        source = (root / "src/insight/model_provider.py").read_text(encoding="utf-8")
        for forbidden in (
            "src.application", "src.plan", "src.readiness", "src.provider",
            "src.ftp_history", "src.ftp_evidence", "TrainingMetricsProvider",
            "datetime.now", "os.environ", "getenv", "requests", "httpx",
            "tools", "function_call", "tool_choice", "messages", "thread_id",
            "assistant_id", "input_token_price", "usd_cost",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, source)

    def test_core_modules_do_not_import_model_provider(self) -> None:
        root = Path(__file__).resolve().parent.parent
        for relative in ("src/application.py", "src/plan.py", "src/readiness.py",
                         "src/provider.py", "src/ftp_history.py", "src/ftp_evidence.py"):
            with self.subTest(path=relative):
                self.assertNotIn("model_provider", (root / relative).read_text(encoding="utf-8"))
