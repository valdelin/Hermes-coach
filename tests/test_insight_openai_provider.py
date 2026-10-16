"""Testes offline do adapter OpenAI (INSIGHT M2-5).

Nenhum teste toca a rede, exige ``OPENAI_API_KEY`` ou consome quota. O cliente
SDK e sempre injetado por um fake; as excecoes do SDK sao substituidas por
classes locais restauradas em ``cleanup``.
"""
from __future__ import annotations

import types
import unittest
from typing import Any, List

from src.insight import openai_provider as mod
from src.insight.limits import MAX_PROVIDER_RESPONSE_BYTES
from src.insight.model_provider import (
    InsightModelRequest,
    InsightProviderAuthError,
    InsightProviderConfigError,
    InsightProviderError,
    InsightProviderInvalidResponseError,
    InsightProviderRateLimitError,
    InsightProviderTimeoutError,
    InsightProviderUnavailableError,
)
from src.insight.openai_provider import OpenAIInsightModelProvider

REQUESTED = "gpt-5.4-nano-2026-03-17"
VALID_TEXT = (
    '{"headline": "H", "explanation": "E", '
    '"next_action_text": "N", "caution_text": null}'
)


class _FakeResponse:
    def __init__(self, text: str = VALID_TEXT, model: Any = REQUESTED,
                 request_id: Any = "req_123") -> None:
        self.output_text = text
        self.model = model
        self.id = request_id


class _FakeResponses:
    def __init__(self, responses: List[object]) -> None:
        self._responses = list(responses)
        self._idx = 0
        self.calls: List[dict] = []

    def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self._responses:
            raise AssertionError("nenhuma resposta fake configurada")
        resp = self._responses[min(self._idx, len(self._responses) - 1)]
        self._idx += 1
        if isinstance(resp, Exception):
            raise resp
        if callable(resp) and not isinstance(resp, type):
            return resp(**kwargs)
        return resp


class _FakeClient:
    def __init__(self, responses: _FakeResponses) -> None:
        self.responses = responses


class OpenAIProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_env = mod.os.environ.pop("OPENAI_API_KEY", None)

    def tearDown(self) -> None:
        if self._saved_env is not None:
            mod.os.environ["OPENAI_API_KEY"] = self._saved_env
        else:
            mod.os.environ.pop("OPENAI_API_KEY", None)

    def _patch_exception(self, name: str, fake: type) -> None:
        original = getattr(mod, name)
        setattr(mod, name, fake)
        self.addCleanup(setattr, mod, name, original)

    def _make_request(self, input_text: str = "headline: H") -> InsightModelRequest:
        return InsightModelRequest(
            prompt_version="v2-test",
            prompt_sha256="a" * 64,
            requested_model=REQUESTED,
            input_text=input_text,
            schema_version=1,
        )

    def _provider(self, responses: List[object], **kwargs: Any):
        client = _FakeClient(_FakeResponses(responses))
        kwargs.setdefault("api_key", "sk-test")
        provider = OpenAIInsightModelProvider(client=client, **kwargs)
        return provider, client

    # ---- credentials / config ------------------------------------------

    def test_missing_key_raises_config_before_network(self) -> None:
        mod.os.environ.pop("OPENAI_API_KEY", None)
        with self.assertRaises(InsightProviderConfigError):
            OpenAIInsightModelProvider(api_key="")

    def test_blank_key_falls_back_to_env_or_config(self) -> None:
        mod.os.environ.pop("OPENAI_API_KEY", None)
        with self.assertRaises(InsightProviderConfigError):
            OpenAIInsightModelProvider(api_key="   ")

    def test_config_error_is_provider_neutral_and_not_retryable(self) -> None:
        # Config error e subclasse do erro provider-neutral: o runtime M2-3 o
        # contem como FALLBACK_PROVIDER (nenhuma alteracao de runtime).
        self.assertTrue(issubclass(InsightProviderConfigError, InsightProviderError))
        self.assertFalse(InsightProviderConfigError.retryable)
        self.assertEqual(InsightProviderConfigError.code, "config_error")

    def test_env_key_resolved_at_boundary(self) -> None:
        mod.os.environ["OPENAI_API_KEY"] = "sk-env"
        try:
            provider = OpenAIInsightModelProvider()
        except ImportError:
            self.skipTest("SDK openai ausente; resolucao de env coberta pela fronteira")
        self.assertEqual(provider._api_key, "sk-env")

    def test_injected_client_requires_no_key(self) -> None:
        client = _FakeClient(_FakeResponses([_FakeResponse()]))
        provider = OpenAIInsightModelProvider(client=client)
        self.assertIs(provider._client, client)

    def test_timeout_and_retries_defaults(self) -> None:
        provider, _ = self._provider([_FakeResponse()])
        self.assertEqual(provider._timeout_seconds, 30.0)
        self.assertEqual(provider._max_retries, 0)

    def test_timeout_and_retries_are_explicit_config(self) -> None:
        # A construcao do cliente real usa valores explicitos; aqui verificamos
        # que os defaults do contrato nao dependem de default do SDK.
        client = _FakeClient(_FakeResponses([_FakeResponse()]))
        provider = OpenAIInsightModelProvider(
            client=client, timeout_seconds=30.0, max_retries=0)
        self.assertEqual(provider._timeout_seconds, 30.0)
        self.assertEqual(provider._max_retries, 0)

    # ---- request shape --------------------------------------------------

    def test_responses_api_call_shape(self) -> None:
        provider, client = self._provider([_FakeResponse()])
        provider.generate(self._make_request())
        call = client.responses.calls[0]
        self.assertEqual(call["model"], REQUESTED)
        self.assertEqual(call["stream"], False)
        self.assertEqual(call["store"], False)
        self.assertEqual(call["max_output_tokens"], 2048)
        self.assertNotIn("temperature", call)
        self.assertNotIn("top_p", call)
        self.assertNotIn("tools", call)
        self.assertNotIn("tool_choice", call)
        self.assertNotIn("previous_response_id", call)
        self.assertNotIn("conversation", call)

    def test_exact_input_transmitted(self) -> None:
        sentinel = "__EXACT_CANONICAL_INPUT_SENTINEL__"
        provider, client = self._provider([_FakeResponse()])
        provider.generate(self._make_request(input_text=sentinel))
        self.assertEqual(client.responses.calls[0]["input"], sentinel)

    def test_only_one_provider_call_per_generate(self) -> None:
        provider, client = self._provider([_FakeResponse()])
        provider.generate(self._make_request())
        self.assertEqual(len(client.responses.calls), 1)

    def test_structured_output_strict_schema(self) -> None:
        provider, client = self._provider([_FakeResponse()])
        provider.generate(self._make_request())
        fmt = client.responses.calls[0]["text"]["format"]
        self.assertEqual(fmt["type"], "json_schema")
        self.assertTrue(fmt["strict"])
        schema = fmt["schema"]
        self.assertEqual(schema["type"], "object")
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(
            set(schema["properties"]),
            {"headline", "explanation", "next_action_text", "caution_text"},
        )
        self.assertEqual(
            set(schema["required"]),
            {"headline", "explanation", "next_action_text", "caution_text"},
        )
        # caution_text e string ou null (nao forca caution fabricada)
        self.assertIn("null", schema["properties"]["caution_text"]["type"])
        # nenhum campo de prescricao/dominio no schema de transporte
        for forbidden in ("prescription", "ftp", "readiness", "progression"):
            self.assertNotIn(forbidden, schema["properties"])

    def test_max_output_tokens_configured(self) -> None:
        provider, client = self._provider([_FakeResponse()], max_output_tokens=2048)
        provider.generate(self._make_request())
        self.assertEqual(client.responses.calls[0]["max_output_tokens"], 2048)

    # ---- response conversion -------------------------------------------

    def test_response_conversion(self) -> None:
        provider, _ = self._provider(
            [_FakeResponse(model=REQUESTED, request_id="req_9")])
        result = provider.generate(self._make_request())
        self.assertEqual(result.text, VALID_TEXT)
        self.assertEqual(result.provider, "openai")
        self.assertEqual(result.requested_model, REQUESTED)
        self.assertEqual(result.resolved_model, REQUESTED)
        self.assertEqual(result.request_id, "req_9")

    def test_requested_and_resolved_may_differ(self) -> None:
        provider, _ = self._provider(
            [_FakeResponse(model="gpt-5.4-nano-2026-03-17-other")])
        result = provider.generate(self._make_request())
        self.assertEqual(result.requested_model, REQUESTED)
        self.assertNotEqual(result.resolved_model, result.requested_model)
        self.assertEqual(result.resolved_model, "gpt-5.4-nano-2026-03-17-other")

    def test_output_array_extraction(self) -> None:
        block = types.SimpleNamespace(text=VALID_TEXT)
        item = types.SimpleNamespace(content=[block])
        resp = types.SimpleNamespace(output=[item], model=REQUESTED, id="r")
        provider, _ = self._provider([resp])
        result = provider.generate(self._make_request())
        self.assertEqual(result.text, VALID_TEXT)

    def test_no_json_repair_in_adapter(self) -> None:
        raw = "not-json"
        provider, _ = self._provider([_FakeResponse(text=raw)])
        result = provider.generate(self._make_request())
        self.assertEqual(result.text, raw)

    def test_empty_output_is_invalid_response(self) -> None:
        provider, _ = self._provider([_FakeResponse(text="")])
        with self.assertRaises(InsightProviderInvalidResponseError):
            provider.generate(self._make_request())

    def test_oversize_output_rejected_not_truncated(self) -> None:
        huge = "x" * (MAX_PROVIDER_RESPONSE_BYTES + 1)
        provider, _ = self._provider([_FakeResponse(text=huge)])
        from src.insight.limits import InsightSizeLimitError

        with self.assertRaises(InsightSizeLimitError):
            provider.generate(self._make_request())

    def test_request_id_optional(self) -> None:
        provider, _ = self._provider([_FakeResponse(request_id=None)])
        result = provider.generate(self._make_request())
        self.assertIsNone(result.request_id)

    # ---- error mapping --------------------------------------------------

    def _map_case(self, module_name: str, fake_exc: type,
                  expected: type) -> None:
        self._patch_exception(module_name, fake_exc)

        def _boom(**kwargs: Any) -> Any:
            raise fake_exc()

        client = _FakeClient(_FakeResponses([_boom]))
        provider = OpenAIInsightModelProvider(client=client, api_key="sk-test")
        with self.assertRaises(expected):
            provider.generate(self._make_request())

    def test_map_auth(self) -> None:
        class E(Exception):
            pass

        self._map_case("AuthenticationError", E, InsightProviderAuthError)

    def test_map_rate_limit(self) -> None:
        class E(Exception):
            pass

        self._map_case("RateLimitError", E, InsightProviderRateLimitError)

    def test_map_timeout(self) -> None:
        class E(Exception):
            pass

        self._map_case("APITimeoutError", E, InsightProviderTimeoutError)

    def test_map_connection(self) -> None:
        class E(Exception):
            pass

        self._map_case("APIConnectionError", E, InsightProviderUnavailableError)

    def test_map_bad_request(self) -> None:
        class E(Exception):
            pass

        self._map_case("BadRequestError", E, InsightProviderInvalidResponseError)

    def test_map_generic_api_error(self) -> None:
        class E(Exception):
            pass

        self._map_case("APIError", E, InsightProviderError)

    def test_map_openai_error(self) -> None:
        class E(Exception):
            pass

        self._map_case("OpenAIError", E, InsightProviderError)

    def test_sdk_types_do_not_escape(self) -> None:
        class Weird(Exception):
            pass

        # Uma excecao nao mapeada deve propagar; nao ha catch amplo ampliando
        # tipos vendor. O runtime M2-3 contem o inesperado como FALLBACK_INTERNAL.
        def _boom(**kwargs: Any) -> Any:
            raise Weird("nope")

        client = _FakeClient(_FakeResponses([_boom]))
        provider = OpenAIInsightModelProvider(client=client, api_key="sk-test")
        with self.assertRaises(Weird):
            provider.generate(self._make_request())

    # ---- secret safety --------------------------------------------------

    def test_secret_not_leaked_in_exception(self) -> None:
        secret = "__SECRET_OPENAI_API_KEY_SENTINEL__"
        original = mod.os.environ.get("OPENAI_API_KEY")
        mod.os.environ["OPENAI_API_KEY"] = secret
        try:
            class E(Exception):
                pass

            self._patch_exception("AuthenticationError", E)

            def _boom(**kwargs: Any) -> Any:
                raise E("auth failed")

            client = _FakeClient(_FakeResponses([_boom]))
            provider = OpenAIInsightModelProvider(client=client)
            self.assertEqual(provider._api_key, secret)
            try:
                provider.generate(self._make_request())
            except Exception as exc:  # noqa: BLE001
                blob = str(exc) + repr(exc) + repr(vars(exc))
                self.assertNotIn(secret, blob)
        finally:
            if original is None:
                mod.os.environ.pop("OPENAI_API_KEY", None)
            else:
                mod.os.environ["OPENAI_API_KEY"] = original

    # ---- module import safety ------------------------------------------

    def test_import_performs_no_network(self) -> None:
        # Importar o modulo nao resolve credencial nem cria cliente global.
        self.assertIsNone(getattr(mod, "_GLOBAL_CLIENT", None))
        self.assertEqual(mod.OPENAI_API_KEY_ENV, "OPENAI_API_KEY")


if __name__ == "__main__":
    unittest.main()
