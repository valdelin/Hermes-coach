"""Testes offline do runtime provider-neutral do INSIGHT M2-3."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
import inspect
import json
from pathlib import Path
import unittest

from src.insight.contract import (
    FactClassification, InsightAdvisory, InsightFact, InsightPresentation,
    InsightView,
)
from src.insight.limits import MAX_PROVIDER_RESPONSE_BYTES, InsightSizeLimitError
from src.insight.model_provider import (
    InsightModelRequest, InsightModelResponse, InsightProviderAuthError,
    InsightProviderError, InsightProviderInvalidResponseError,
    InsightProviderRateLimitError, InsightProviderTimeoutError,
    InsightProviderUnavailableError, InsightRuntimeProvenance,
)
from src.insight.render import fallback_presentation
from src.insight.request_builder import (
    INSIGHT_PROMPT_VERSION, build_insight_model_request,
)
from src.insight.response_validation import (
    parse_validate_render_insight_response,
)
from src.insight.runtime import (
    InsightRuntimeResult, InsightRuntimeStatus, run_insight_runtime,
)


TIMESTAMP = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
REQUESTED_MODEL = "model-requested"
HARNESS_VERSION = "hermes-0.0.36"
HARNESS_COMMIT = "1c869c623b99bb9e150c3bd5f8b4bfcb94b5082b"


def make_view(*facts: InsightFact,
              advisory: InsightAdvisory | None = None) -> InsightView:
    return InsightView(
        schema_version=1, subject="athlete", facts=tuple(facts),
        advisory=advisory)


def fact(key: str, value: object, unit: str | None = None,
         classification: FactClassification = FactClassification.DERIVED,
         ) -> InsightFact:
    return InsightFact(key, value, classification, unit)


def transport(**overrides: object) -> str:
    payload: dict = {
        "headline": "Resumo do dia",
        "explanation": "Tudo em ordem",
        "next_action_text": "Siga o plano",
    }
    payload.update(overrides)
    return json.dumps(payload)


class FakeProvider:
    """Provider deterministico de teste; nao e exportado por producao."""

    def __init__(self, *, text: str | None = None, error: Exception | None = None,
                 provider: str = "future-provider",
                 resolved_model: str | None = None,
                 request_id: str | None = None,
                 echo_model: str | None = None) -> None:
        self.calls: list[InsightModelRequest] = []
        self.responses: list[InsightModelResponse] = []
        self._text = text
        self._error = error
        self._provider = provider
        self._resolved_model = resolved_model
        self._request_id = request_id
        self._echo_model = echo_model

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def generate(self, request: InsightModelRequest) -> InsightModelResponse:
        self.calls.append(request)
        if self._error is not None:
            raise self._error
        echo = request.requested_model if self._echo_model is None else self._echo_model
        response = InsightModelResponse(
            text=self._text,  # type: ignore[arg-type]
            provider=self._provider,
            requested_model=echo,
            resolved_model=self._resolved_model,
            request_id=self._request_id,
        )
        self.responses.append(response)
        return response


def run(view: InsightView, provider: FakeProvider, *, executed_at: datetime = TIMESTAMP,
        **kwargs: object) -> InsightRuntimeResult:
    return run_insight_runtime(
        view,
        provider=provider,
        requested_model=REQUESTED_MODEL,
        prompt_version=INSIGHT_PROMPT_VERSION,
        executed_at=executed_at,
        **kwargs,  # type: ignore[arg-type]
    )


class SuccessPathTest(unittest.TestCase):
    def test_success_renders_from_local_fact_values(self) -> None:
        view = make_view(fact("power_target", 250, "W"))
        provider = FakeProvider(text=transport(
            headline="Alvo {{power_target}} W",
            explanation="Mantenha o ritmo",
            next_action_text="Siga o plano"))
        result = run(view, provider, harness_version=HARNESS_VERSION,
                     harness_commit=HARNESS_COMMIT)
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertEqual(result.presentation, InsightPresentation(
            "Alvo 250 W", "Mantenha o ritmo", "Siga o plano", None))
        self.assertIsNotNone(result.provenance)
        self.assertEqual(provider.call_count, 1)

    def test_resolved_model_may_differ_from_requested(self) -> None:
        view = make_view(fact("ctl", 42))
        provider = FakeProvider(text=transport(), resolved_model="model-resolved")
        result = run(view, provider)
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertEqual(result.provenance.requested_model, REQUESTED_MODEL)
        self.assertEqual(result.provenance.resolved_model, "model-resolved")

    def test_caution_is_allowed_with_advisory(self) -> None:
        view = make_view(advisory=InsightAdvisory("Reduza se necessario"))
        provider = FakeProvider(text=transport(caution_text="Reduza se necessario"))
        result = run(view, provider)
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertEqual(result.presentation.caution_text, "Reduza se necessario")

    def test_request_capture_is_exactly_the_builder_output(self) -> None:
        view = make_view(fact("ctl", 42), fact("atl", 30))
        provider = FakeProvider(text=transport())
        run(view, provider)
        self.assertEqual(provider.call_count, 1)
        expected = build_insight_model_request(
            view, requested_model=REQUESTED_MODEL,
            prompt_version=INSIGHT_PROMPT_VERSION)
        self.assertEqual(provider.calls[0], expected)
        self.assertEqual(provider.calls[0].requested_model, REQUESTED_MODEL)
        self.assertEqual(provider.calls[0].prompt_version, INSIGHT_PROMPT_VERSION)
        self.assertEqual(provider.calls[0].schema_version, 1)
        self.assertEqual(len(provider.calls[0].prompt_sha256), 64)

    def test_provenance_matches_canonical_factory(self) -> None:
        view = make_view(fact("ctl", 42))
        provider = FakeProvider(text=transport(), resolved_model="model-resolved")
        result = run(view, provider, harness_version=HARNESS_VERSION,
                     harness_commit=HARNESS_COMMIT)
        expected = InsightRuntimeProvenance.from_execution(
            provider.calls[0], provider.responses[0], executed_at=TIMESTAMP,
            harness_version=HARNESS_VERSION, harness_commit=HARNESS_COMMIT)
        self.assertEqual(result.provenance, expected)

    def test_success_always_carries_provenance(self) -> None:
        result = run(make_view(fact("ctl", 42)), FakeProvider(text=transport()))
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertIsInstance(result.provenance, InsightRuntimeProvenance)

    def test_dependencies_default_to_canonical_seams(self) -> None:
        signature = inspect.signature(run_insight_runtime)
        self.assertIs(signature.parameters["builder"].default,
                      build_insight_model_request)
        self.assertIs(signature.parameters["decoder"].default,
                      parse_validate_render_insight_response)
        self.assertIs(signature.parameters["fallback"].default,
                      fallback_presentation)

    def test_same_inputs_are_deterministic(self) -> None:
        view = make_view(fact("ctl", 42))
        first = run(view, FakeProvider(text=transport()))
        second = run(view, FakeProvider(text=transport()))
        self.assertEqual(first, second)

    def test_result_is_frozen_and_closed(self) -> None:
        result = run(make_view(fact("ctl", 42)), FakeProvider(text=transport()))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.status = InsightRuntimeStatus.FALLBACK_INTERNAL  # type: ignore[misc]
        self.assertEqual(
            [field.name for field in dataclasses.fields(InsightRuntimeResult)],
            ["presentation", "status", "provenance"])


class ProviderFailureTest(unittest.TestCase):
    def test_controlled_provider_errors_fall_back_without_retry(self) -> None:
        errors = (
            InsightProviderError("x"), InsightProviderAuthError("x"),
            InsightProviderRateLimitError("x"), InsightProviderTimeoutError("x"),
            InsightProviderUnavailableError("x"),
            InsightProviderInvalidResponseError("x"),
        )
        for error in errors:
            with self.subTest(error=type(error).__name__):
                view = make_view()
                provider = FakeProvider(error=error)
                result = run(view, provider)
                self.assertEqual(
                    result.status, InsightRuntimeStatus.FALLBACK_PROVIDER)
                self.assertEqual(result.presentation, fallback_presentation(view))
                self.assertIsNone(result.provenance)
                self.assertEqual(provider.call_count, 1)


class InvalidResponseTest(unittest.TestCase):
    INVALID_TEXTS = {
        "not_json": "not-json",
        "duplicate_key": ('{"headline":"A","headline":"B",'
                          '"explanation":"X","next_action_text":"Y"}'),
        "literal_ascii_digit": transport(headline="Alvo 250 W"),
        "literal_unicode_nd": transport(headline="Alvo \u0663 W"),
        "unknown_placeholder": transport(headline="{{nonexistent_fact}}"),
        "malformed_placeholder": transport(headline="{{Bad2}}"),
        "unknown_field": json.dumps({
            "headline": "A", "explanation": "X",
            "next_action_text": "Y", "extra": "z"}),
        "wrong_field_type": json.dumps({
            "headline": 5, "explanation": "X", "next_action_text": "Y"}),
    }

    def test_invalid_model_responses_fall_back(self) -> None:
        for name, text in self.INVALID_TEXTS.items():
            with self.subTest(case=name):
                view = make_view()
                provider = FakeProvider(text=text)
                result = run(view, provider)
                self.assertEqual(
                    result.status, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE)
                self.assertEqual(result.presentation, fallback_presentation(view))
                self.assertIsNone(result.provenance)
                self.assertEqual(provider.call_count, 1)

    def test_caution_without_advisory_falls_back(self) -> None:
        view = make_view()  # advisory ausente
        provider = FakeProvider(text=transport(caution_text="Cuidado"))
        result = run(view, provider)
        self.assertEqual(
            result.status, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE)
        self.assertIsNone(result.provenance)
        self.assertEqual(provider.call_count, 1)

    def test_oversize_response_falls_back_without_truncation(self) -> None:
        view = make_view()
        provider = FakeProvider(text="x" * (MAX_PROVIDER_RESPONSE_BYTES + 1))
        result = run(view, provider)
        self.assertEqual(
            result.status, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE)
        self.assertEqual(result.presentation, fallback_presentation(view))
        self.assertIsNone(result.provenance)
        self.assertEqual(provider.call_count, 1)

    def test_requested_model_echo_mismatch_falls_back(self) -> None:
        view = make_view()
        provider = FakeProvider(text=transport(), echo_model="model-other")
        result = run(view, provider)
        self.assertEqual(
            result.status, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE)
        self.assertIsNone(result.provenance)
        self.assertEqual(provider.call_count, 1)

    def test_invalid_harness_commit_falls_back_internal(self) -> None:
        view = make_view()
        provider = FakeProvider(text=transport())
        result = run(view, provider, harness_commit="ZZZ")
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INTERNAL)
        self.assertIsNone(result.provenance)
        self.assertEqual(provider.call_count, 1)


class UnexpectedExceptionTest(unittest.TestCase):
    def test_provider_unexpected_exception_is_contained(self) -> None:
        sentinel = "__SECRET_PROVIDER_EXCEPTION__"
        view = make_view()
        provider = FakeProvider(error=RuntimeError(sentinel))
        result = run(view, provider)
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INTERNAL)
        self.assertEqual(result.presentation, fallback_presentation(view))
        self.assertIsNone(result.provenance)
        self.assertEqual(provider.call_count, 1)
        for rendered in (str(result), repr(result), str(result.status),
                         repr(result.presentation), repr(result.provenance)):
            self.assertNotIn(sentinel, rendered)

    def test_builder_failure_never_calls_provider(self) -> None:
        view = make_view()

        def failing_builder(view, **kwargs):  # noqa: ANN001
            raise InsightSizeLimitError("model_input_bytes", 9000, 8192)

        provider = FakeProvider(text=transport())
        result = run(view, provider, builder=failing_builder)
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INTERNAL)
        self.assertEqual(provider.call_count, 0)
        self.assertIsNone(result.provenance)

    def test_builder_unexpected_exception_never_calls_provider(self) -> None:
        view = make_view()

        def exploding_builder(view, **kwargs):  # noqa: ANN001
            raise RuntimeError("boom")

        provider = FakeProvider(text=transport())
        result = run(view, provider, builder=exploding_builder)
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INTERNAL)
        self.assertEqual(provider.call_count, 0)

    def test_decoder_unexpected_exception_is_contained(self) -> None:
        view = make_view()

        def exploding_decoder(text, *, view):  # noqa: ANN001
            raise RuntimeError("boom")

        provider = FakeProvider(text=transport())
        result = run(view, provider, decoder=exploding_decoder)
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INTERNAL)
        self.assertIsNone(result.provenance)
        self.assertEqual(provider.call_count, 1)

    def test_naive_timestamp_is_contained(self) -> None:
        view = make_view()
        provider = FakeProvider(text=transport())
        result = run(view, provider, executed_at=datetime(2026, 10, 16, 12, 0))
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INTERNAL)
        self.assertIsNone(result.provenance)
        self.assertEqual(provider.call_count, 1)

    def test_raw_response_sentinel_never_reaches_result(self) -> None:
        sentinel = "__SECRET_RAW_RESPONSE__"
        view = make_view()
        provider = FakeProvider(text=sentinel)
        result = run(view, provider)
        self.assertEqual(
            result.status, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE)
        for rendered in (str(result), repr(result), repr(result.presentation)):
            self.assertNotIn(sentinel, rendered)


class InvarianceTest(unittest.TestCase):
    def test_view_is_not_mutated_on_any_path(self) -> None:
        scenarios = {
            "success": FakeProvider(text=transport()),
            "provider": FakeProvider(error=InsightProviderError("x")),
            "invalid_response": FakeProvider(text="not-json"),
            "internal": FakeProvider(error=RuntimeError("x")),
        }
        for name, provider in scenarios.items():
            with self.subTest(case=name):
                view = make_view(fact("ctl", 42), fact("atl", 30))
                snapshot = dataclasses.replace(view)
                run(view, provider)
                self.assertEqual(view, snapshot)
                self.assertEqual(view.facts, snapshot.facts)

    def test_every_fallback_status_has_no_provenance(self) -> None:
        cases = (
            InsightRuntimeStatus.FALLBACK_PROVIDER,
            InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE,
            InsightRuntimeStatus.FALLBACK_INTERNAL,
        )
        results = (
            run(make_view(), FakeProvider(error=InsightProviderError("x"))),
            run(make_view(), FakeProvider(text="not-json")),
            run(make_view(), FakeProvider(error=RuntimeError("x"))),
        )
        self.assertEqual([r.status for r in results], list(cases))
        for result in results:
            self.assertIsNone(result.provenance)


class ArchitectureTest(unittest.TestCase):
    SOURCE = (Path(__file__).resolve().parent.parent
              / "src/insight/runtime.py").read_text(encoding="utf-8")

    def test_exactly_one_outer_broad_exception_boundary(self) -> None:
        self.assertEqual(self.SOURCE.count("except Exception"), 1)

    def test_no_m1_render_bypass_for_model_text(self) -> None:
        self.assertIn("parse_validate_render_insight_response", self.SOURCE)
        self.assertNotIn("render_presentation", self.SOURCE)

    def test_no_env_network_clock_random_filesystem_or_domain(self) -> None:
        forbidden = (
            "import os", "os.environ", "getenv", "import random", "import uuid",
            "random.", "uuid", "import socket", "import subprocess",
            "import requests", "import httpx", "urllib", "open(", "pathlib",
            "datetime.now", "datetime.utcnow", "time.time", "time.sleep",
            "perf_counter", "monotonic", "src.application", "src.plan",
            "src.readiness", "src.provider", "src.ftp_history", "src.lifecycle",
            "from .application", "from .plan",
        )
        for token in forbidden:
            with self.subTest(token=token):
                self.assertNotIn(token, self.SOURCE)

    def test_status_enum_is_closed(self) -> None:
        self.assertEqual(InsightRuntimeStatus.SUCCESS.value, "success")
        with self.assertRaises(ValueError):
            InsightRuntimeStatus("unknown")


if __name__ == "__main__":
    unittest.main()
