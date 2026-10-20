"""M2-8 — flags/configuração e rollout online sem rede real."""
from __future__ import annotations

from datetime import datetime, timezone
import unittest

from src.insight.config import (INSIGHT_ENABLED_ENV, INSIGHT_ONLINE_ENABLED_ENV,
                                InsightRuntimeConfig, load_insight_runtime_config,
                                parse_insight_flag)
from src.insight.contract import InsightView
from src.insight.model_provider import (InsightModelRequest, InsightModelResponse,
                                        InsightProviderConfigError,
                                        InsightProviderTimeoutError)
from src.insight.rollout import run_configured_insight
from src.insight.runtime import InsightRuntimeStatus


MODEL = "gpt-5.4-nano-2026-03-17"
TIMESTAMP = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
VALID_TEXT = (
    '{"headline":"Resumo","explanation":"Estado","next_action_text":'
    '"Siga o plano","caution_text":null}')


class _Provider:
    def __init__(self, *, text: str = VALID_TEXT, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[InsightModelRequest] = []

    def generate(self, request: InsightModelRequest) -> InsightModelResponse:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        return InsightModelResponse(
            text=self.text, provider="openai", requested_model=request.requested_model,
            resolved_model=MODEL, request_id="resp_123")


class _Factory:
    def __init__(self, provider: _Provider | None = None) -> None:
        self.provider = provider or _Provider()
        self.calls: list[str] = []

    def __call__(self, *, api_key: str) -> _Provider:
        self.calls.append(api_key)
        return self.provider


def _view() -> InsightView:
    return InsightView(schema_version=1, subject="athlete")


def _config(insight: bool, online: bool) -> InsightRuntimeConfig:
    return InsightRuntimeConfig(insight_enabled=insight, online_enabled=online)


class InsightConfigTest(unittest.TestCase):
    def test_parser_is_explicit_and_fail_closed(self) -> None:
        for value in (None, "", "0", "false", "off", "banana", "yesplease", "1abc", "truee"):
            with self.subTest(value=value):
                self.assertFalse(parse_insight_flag(value))
        for value in ("1", "true", "TRUE", " True ", "yes", "on"):
            with self.subTest(value=value):
                self.assertTrue(parse_insight_flag(value))

    def test_loader_requires_two_independent_flags(self) -> None:
        for environment, expected in (
                ({}, (False, False)),
                ({INSIGHT_ENABLED_ENV: "on"}, (True, False)),
                ({INSIGHT_ONLINE_ENABLED_ENV: "on"}, (False, True)),
                ({INSIGHT_ENABLED_ENV: "on", INSIGHT_ONLINE_ENABLED_ENV: "on"}, (True, True)),
        ):
            with self.subTest(environment=environment):
                config = load_insight_runtime_config(environment)
                self.assertEqual((config.insight_enabled, config.online_enabled), expected)
                self.assertEqual(config.online_permitted, all(expected))


class InsightRolloutTest(unittest.TestCase):
    def test_off_combinations_never_construct_or_invoke_provider(self) -> None:
        for config in (_config(False, False), _config(False, True), _config(True, False)):
            with self.subTest(config=config):
                factory = _Factory()
                result = run_configured_insight(
                    _view(), config=config,
                    environment={"OPENAI_API_KEY": "__SECRET_OPENAI_API_KEY__"},
                    executed_at=TIMESTAMP, provider_factory=factory)
                self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_DISABLED)
                self.assertEqual(factory.calls, [])
                self.assertEqual(factory.provider.calls, [])
                self.assertIsNone(result.provenance)

    def test_missing_or_blank_key_is_config_fallback_without_factory(self) -> None:
        for key in (None, "   "):
            with self.subTest(key=key):
                factory = _Factory()
                environment = {} if key is None else {"OPENAI_API_KEY": key}
                result = run_configured_insight(
                    _view(), config=_config(True, True), environment=environment,
                    executed_at=TIMESTAMP, provider_factory=factory)
                self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_CONFIG)
                self.assertEqual(factory.calls, [])
                self.assertEqual(factory.provider.calls, [])
                self.assertIsNone(result.provenance)

    def test_online_success_uses_exact_model_once(self) -> None:
        factory = _Factory()
        result = run_configured_insight(
            _view(), config=_config(True, True),
            environment={"OPENAI_API_KEY": "__SECRET_OPENAI_API_KEY__"},
            executed_at=TIMESTAMP, provider_factory=factory)
        self.assertEqual(result.status, InsightRuntimeStatus.SUCCESS)
        self.assertEqual(factory.calls, ["__SECRET_OPENAI_API_KEY__"])
        self.assertEqual(len(factory.provider.calls), 1)
        self.assertEqual(factory.provider.calls[0].requested_model, MODEL)
        self.assertIsNotNone(result.provenance)
        self.assertNotIn("__SECRET_OPENAI_API_KEY__", repr(result))

    def test_provider_and_invalid_response_keep_runtime_statuses_without_retry(self) -> None:
        scenarios = (
            (_Provider(error=InsightProviderTimeoutError()), InsightRuntimeStatus.FALLBACK_PROVIDER),
            (_Provider(text="__RAW_PROVIDER_RESPONSE__"), InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE),
        )
        for provider, expected in scenarios:
            with self.subTest(expected=expected):
                factory = _Factory(provider)
                result = run_configured_insight(
                    _view(), config=_config(True, True),
                    environment={"OPENAI_API_KEY": "key"}, executed_at=TIMESTAMP,
                    provider_factory=factory)
                self.assertEqual(result.status, expected)
                self.assertEqual(len(provider.calls), 1)
                self.assertIsNone(result.provenance)
                self.assertNotIn("__RAW_PROVIDER_RESPONSE__", repr(result))

    def test_provider_construction_failure_is_config_fallback_without_inference(self) -> None:
        for error in (InsightProviderConfigError("openai_api_key_ausente"),
                      ImportError("openai package not available")):
            with self.subTest(error=type(error).__name__):
                calls: list[str] = []

                def failing_factory(*, api_key: str) -> _Provider:
                    calls.append(api_key)
                    raise error

                result = run_configured_insight(
                    _view(), config=_config(True, True),
                    environment={"OPENAI_API_KEY": "__SECRET_OPENAI_API_KEY__"},
                    executed_at=TIMESTAMP, provider_factory=failing_factory)
                self.assertEqual(result.status, InsightRuntimeStatus.FALLBACK_CONFIG)
                self.assertEqual(calls, ["__SECRET_OPENAI_API_KEY__"])
                self.assertIsNone(result.provenance)
                self.assertNotIn("__SECRET_OPENAI_API_KEY__", repr(result))
                self.assertNotIn(str(error), repr(result))


if __name__ == "__main__":
    unittest.main()
