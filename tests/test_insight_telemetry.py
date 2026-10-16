"""Eventos sanitizados e observacionais do INSIGHT M2-6."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from decimal import Decimal
import json
import unittest

from src.insight.contract import InsightView
from src.insight.model_provider import InsightModelRequest, InsightModelResponse, InsightModelUsage
from src.insight.runtime import InsightRuntimeStatus, run_insight_runtime
from src.insight.telemetry import (
    InMemoryInsightTelemetrySink,
    InsightRuntimeTelemetry,
    build_insight_runtime_telemetry,
)


MODEL = "gpt-5.4-nano-2026-03-17"
TIMESTAMP = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)


class _Provider:
    def __init__(self, text: str, *, usage: InsightModelUsage | None = None) -> None:
        self.text = text
        self.usage = usage
        self.calls = 0

    def generate(self, request: InsightModelRequest) -> InsightModelResponse:
        self.calls += 1
        return InsightModelResponse(
            text=self.text,
            provider="openai",
            requested_model=request.requested_model,
            resolved_model=MODEL,
            request_id="resp_123",
            usage=self.usage,
        )


@dataclasses.dataclass(frozen=True)
class _LeakyUsage(InsightModelUsage):
    secret: str = "__SECRET__"
    raw_response: str = "__RAW__"
    subject: str = "__SUBJECT__"
    api_key: str = "__APIKEY__"

    @property
    def unexpected_extra(self) -> str:
        raise AssertionError("telemetry nao pode ler atributos extras")


def _view() -> InsightView:
    return InsightView(schema_version=1, subject="athlete")


def _transport() -> str:
    return json.dumps({
        "headline": "Resumo",
        "explanation": "Estado estavel",
        "next_action_text": "Siga o plano",
    })


def _run(provider: _Provider, sink: InMemoryInsightTelemetrySink):
    return run_insight_runtime(
        _view(),
        provider=provider,
        requested_model=MODEL,
        prompt_version="insight-m2-prompt-v1",
        executed_at=TIMESTAMP,
        telemetry=sink,
    )


class TelemetryContractTest(unittest.TestCase):
    def test_success_event_is_closed_safe_and_provider_neutral(self) -> None:
        usage = InsightModelUsage(input_tokens=100, output_tokens=20,
                                  cached_input_tokens=0)
        response = InsightModelResponse(
            text="__RAW_PROVIDER_RESPONSE_SENTINEL__",
            provider="openai",
            requested_model=MODEL,
            resolved_model=MODEL,
            request_id="resp_123",
            usage=usage,
        )
        event = build_insight_runtime_telemetry(
            status=InsightRuntimeStatus.SUCCESS, response=response)
        self.assertTrue(dataclasses.is_dataclass(event))
        self.assertEqual(event.status, InsightRuntimeStatus.SUCCESS)
        self.assertEqual(event.provider, "openai")
        self.assertEqual(event.requested_model, MODEL)
        self.assertEqual(event.resolved_model, MODEL)
        self.assertEqual(event.request_id, "resp_123")
        self.assertEqual(event.usage, usage)
        fields = {field.name for field in dataclasses.fields(InsightRuntimeTelemetry)}
        for forbidden in ("prompt", "input_text", "response_text", "raw", "secret",
                          "api_key", "view", "subject", "facts", "exception", "traceback"):
            self.assertNotIn(forbidden, fields)
        rendered = str(event) + repr(event) + repr(vars(event))
        self.assertNotIn("__RAW_PROVIDER_RESPONSE_SENTINEL__", rendered)
        self.assertNotIn("__SECRET_PROMPT_SENTINEL__", rendered)
        self.assertNotIn("__SECRET_OPENAI_API_KEY_SENTINEL__", rendered)

    def test_unsafe_response_metadata_is_omitted_before_event_construction(self) -> None:
        raw = "__RAW_PROVIDER_RESPONSE_SENTINEL__"
        response = InsightModelResponse(
            text="{}",
            provider=raw,
            requested_model=raw,
            resolved_model=raw,
            request_id=raw,
            usage=InsightModelUsage(input_tokens=10, output_tokens=2,
                                    cached_input_tokens=0),
        )
        event = build_insight_runtime_telemetry(
            status=InsightRuntimeStatus.SUCCESS, response=response)
        self.assertIsNone(event.provider)
        self.assertIsNone(event.requested_model)
        self.assertIsNone(event.resolved_model)
        self.assertIsNone(event.request_id)
        self.assertIsNone(event.estimated_cost_usd)
        self.assertNotIn(raw, repr(event))

    def test_usage_subclass_is_canonicalized_without_extra_payload_or_primary_effect(self) -> None:
        usage = _LeakyUsage(input_tokens=100, output_tokens=20,
                            cached_input_tokens=0)
        response = InsightModelResponse(
            text="{}", provider="openai", requested_model=MODEL,
            resolved_model=MODEL, request_id="resp_123", usage=usage)
        event = build_insight_runtime_telemetry(
            status=InsightRuntimeStatus.SUCCESS, response=response)
        self.assertFalse(event.usage is usage)
        self.assertIs(type(event.usage), InsightModelUsage)
        self.assertEqual(event.usage, InsightModelUsage(
            input_tokens=100, output_tokens=20, cached_input_tokens=0))
        rendered = repr(event) + repr(event.usage) + repr(vars(event.usage))
        for sentinel in ("__SECRET__", "__RAW__", "__SUBJECT__", "__APIKEY__"):
            self.assertNotIn(sentinel, rendered)

        direct_event = InsightRuntimeTelemetry(
            status=InsightRuntimeStatus.SUCCESS, usage=usage)
        self.assertFalse(direct_event.usage is usage)
        self.assertIs(type(direct_event.usage), InsightModelUsage)
        self.assertNotIn("__SECRET__", repr(direct_event))

        sink = InMemoryInsightTelemetrySink()
        result = _run(_Provider(_transport(), usage=usage), sink)
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertIs(type(sink.events[0].usage), InsightModelUsage)
        self.assertEqual(sink.events[0].usage, event.usage)

    def test_missing_usage_and_cost_remain_none(self) -> None:
        response = InsightModelResponse(
            text="{}", provider="openai", requested_model=MODEL,
            resolved_model=MODEL, request_id="resp_123", usage=None)
        event = build_insight_runtime_telemetry(
            status=InsightRuntimeStatus.SUCCESS, response=response)
        self.assertIsNone(event.usage)
        self.assertIsNone(event.estimated_cost_usd)
        self.assertIsNone(event.currency)
        self.assertIsNone(event.pricing_source)

    def test_known_usage_survives_unknown_pricing(self) -> None:
        usage = InsightModelUsage(input_tokens=10, output_tokens=2,
                                  cached_input_tokens=0)
        response = InsightModelResponse(
            text="{}", provider="openai", requested_model="unknown-model",
            resolved_model="unknown-model", usage=usage)
        event = build_insight_runtime_telemetry(
            status=InsightRuntimeStatus.SUCCESS, response=response)
        self.assertEqual(event.usage, usage)
        self.assertIsNone(event.estimated_cost_usd)

    def test_explicit_zero_usage_is_preserved_and_cost_is_exact(self) -> None:
        response = InsightModelResponse(
            text="{}", provider="openai", requested_model=MODEL,
            resolved_model=MODEL,
            usage=InsightModelUsage(input_tokens=0, output_tokens=0,
                                    cached_input_tokens=0))
        event = build_insight_runtime_telemetry(
            status=InsightRuntimeStatus.SUCCESS, response=response)
        self.assertEqual(event.usage.input_tokens, 0)
        self.assertEqual(event.usage.output_tokens, 0)
        self.assertEqual(event.usage.cached_input_tokens, 0)
        self.assertEqual(str(event.estimated_cost_usd), "0.00")
        self.assertEqual(event.currency, "USD")

    def test_runtime_emits_success_event_without_changing_result_contract(self) -> None:
        sink = InMemoryInsightTelemetrySink()
        provider = _Provider(_transport(), usage=InsightModelUsage(
            input_tokens=100, output_tokens=20, cached_input_tokens=0))
        result = _run(provider, sink)
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertIsNotNone(result.provenance)
        self.assertEqual(provider.calls, 1)
        self.assertEqual([field.name for field in dataclasses.fields(type(result))],
                         ["presentation", "status", "provenance"])
        self.assertEqual(len(sink.events), 1)
        self.assertEqual(sink.events[0].status, result.status)
        self.assertEqual(sink.events[0].request_id, "resp_123")
        self.assertNotIn("request_id", {field.name for field in dataclasses.fields(result.provenance)})

    def test_runtime_measures_latency_only_from_injected_decimal_clock(self) -> None:
        sink = InMemoryInsightTelemetrySink()
        readings = iter((Decimal("10.0"), Decimal("11.25")))
        result = run_insight_runtime(
            _view(), provider=_Provider(_transport()), requested_model=MODEL,
            prompt_version="insight-m2-prompt-v1", executed_at=TIMESTAMP,
            telemetry=sink, telemetry_clock=lambda: next(readings))
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertEqual(sink.events[0].latency_seconds, Decimal("1.25"))

    def test_runtime_emits_safe_invalid_response_event_without_provenance(self) -> None:
        sink = InMemoryInsightTelemetrySink()
        provider = _Provider("__RAW_PROVIDER_RESPONSE_SENTINEL__", usage=InsightModelUsage(
            input_tokens=10, output_tokens=5, cached_input_tokens=0))
        result = _run(provider, sink)
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE)
        self.assertIsNone(result.provenance)
        self.assertEqual(len(sink.events), 1)
        event = sink.events[0]
        self.assertEqual(event.status, result.status)
        self.assertEqual(event.request_id, "resp_123")
        self.assertNotIn("__RAW_PROVIDER_RESPONSE_SENTINEL__", repr(event))

    def test_fallback_without_response_fabricates_no_provider_usage_or_cost(self) -> None:
        event = build_insight_runtime_telemetry(
            status=InsightRuntimeStatus.FALLBACK_PROVIDER, response=None)
        self.assertEqual(event.status, InsightRuntimeStatus.FALLBACK_PROVIDER)
        self.assertIsNone(event.provider)
        self.assertIsNone(event.usage)
        self.assertIsNone(event.estimated_cost_usd)

    def test_runtime_never_copies_prompt_subject_or_raw_response_into_event(self) -> None:
        prompt = "__SECRET_PROMPT_SENTINEL__"
        subject = "__ATHLETE_IDENTITY_SENTINEL__"
        raw_response = "__RAW_PROVIDER_RESPONSE_SENTINEL__"
        sink = InMemoryInsightTelemetrySink()
        provider = _Provider(raw_response)

        def builder(view, **kwargs):  # noqa: ANN001
            return InsightModelRequest(
                prompt_version=kwargs["prompt_version"],
                prompt_sha256="a" * 64,
                requested_model=kwargs["requested_model"],
                input_text=prompt,
                schema_version=view.schema_version,
            )

        result = run_insight_runtime(
            InsightView(schema_version=1, subject=subject),
            provider=provider, requested_model=MODEL,
            prompt_version="insight-m2-prompt-v1", executed_at=TIMESTAMP,
            builder=builder, telemetry=sink)
        self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE)
        rendered = str(sink.events[0]) + repr(sink.events[0]) + repr(vars(sink.events[0]))
        for sentinel in (prompt, subject, raw_response, "__SECRET_OPENAI_API_KEY_SENTINEL__"):
            self.assertNotIn(sentinel, rendered)

    def test_sink_failure_never_changes_valid_presentation_or_provider_attempts(self) -> None:
        class FailingSink:
            def record(self, telemetry: InsightRuntimeTelemetry) -> None:
                raise RuntimeError("telemetry failure")

        provider = _Provider(_transport())
        result = run_insight_runtime(
            _view(), provider=provider, requested_model=MODEL,
            prompt_version="insight-m2-prompt-v1", executed_at=TIMESTAMP,
            telemetry=FailingSink())
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertEqual(provider.calls, 1)


if __name__ == "__main__":
    unittest.main()
