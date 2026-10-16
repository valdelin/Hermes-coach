"""Adapter concreto OpenAI para o INSIGHT M2-5.

Implementa ``InsightModelProvider`` usando a Responses API (``openai-python``).
A credencial e resolvida apenas na fronteira do adapter; o runtime M2-3 continua
livre de ambiente. O adapter faz no maximo uma tentativa, com timeout explicito,
``max_retries=0``, sem streaming, sem tools, sem memoria de provider e sem
reparo de payload. Tipos do vendor (SDK/resposta/excecao) nunca escapam da
fronteira: somente ``InsightModelResponse`` e excecoes provider-neutral saem.
"""
from __future__ import annotations

import os
from typing import Optional

from .limits import MAX_PROVIDER_RESPONSE_BYTES, require_max_utf8_bytes
from .model_provider import (
    InsightModelProvider,
    InsightModelRequest,
    InsightModelResponse,
    InsightModelUsage,
    InsightProviderAuthError,
    InsightProviderConfigError,
    InsightProviderError,
    InsightProviderInvalidResponseError,
    InsightProviderRateLimitError,
    InsightProviderTimeoutError,
    InsightProviderUnavailableError,
)

OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_MAX_RETRIES = 0
DEFAULT_MAX_OUTPUT_TOKENS = 2048

try:
    import openai as _openai
    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        AuthenticationError,
        BadRequestError,
        OpenAIError,
        RateLimitError,
    )

    _OPENAI_AVAILABLE = True
except Exception:  # pragma: no cover - dependencia opcional
    _openai = None  # type: ignore[assignment]
    _OPENAI_AVAILABLE = False

    # Placeholders distintos para que cada clausula ``except`` continue
    # mapeavel quando o SDK opcional esta ausente (testes injetam fakes).
    class APIConnectionError(Exception):
        pass

    class APIError(Exception):
        pass

    class APITimeoutError(Exception):
        pass

    class AuthenticationError(Exception):
        pass

    class BadRequestError(Exception):
        pass

    class OpenAIError(Exception):
        pass

    class RateLimitError(Exception):
        pass


# Esquema fechado do transporte M2 (4 campos). Defesa em profundidade apenas:
# a validacao local M2-2 continua canonica. ``caution_text`` preserva
# string-ou-null, sem forcar caution fabricada.
_INSIGHT_TRANSPORT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "explanation": {"type": "string"},
        "next_action_text": {"type": "string"},
        "caution_text": {"type": ["string", "null"]},
    },
    "required": [
        "headline",
        "explanation",
        "next_action_text",
        "caution_text",
    ],
    "additionalProperties": False,
}


class OpenAIInsightModelProvider(InsightModelProvider):
    """Adapter OpenAI (Responses API) implementando ``InsightModelProvider``.

    Parameters
    ----------
    api_key:
        Chave explicita. Se ausente/vazia, resolve ``OPENAI_API_KEY`` na
        fronteira do adapter. Nunca entra em request/response/provenance.
    timeout_seconds:
        Timeout finito explicito (default 30.0).
    max_retries:
        Retries do SDK (default 0, desabilitado).
    max_output_tokens:
        Limite defensivo de tokens de saida no lado do provider (default 2048).
        Nao substitui ``MAX_PROVIDER_RESPONSE_BYTES`` (8192) local.
    client:
        Cliente SDK injetavel (testes). Quando informado, nenhum cliente de
        rede e construido.
    """

    provider_id = "openai"

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        client: Optional[object] = None,
    ) -> None:
        if api_key is not None and api_key.strip() == "":
            api_key = None
        self._api_key = api_key if api_key is not None else os.environ.get(
            OPENAI_API_KEY_ENV)
        self._timeout_seconds = float(timeout_seconds)
        self._max_retries = int(max_retries)
        self._max_output_tokens = int(max_output_tokens)
        if client is not None:
            # Fronteira injetavel: nenhum cliente de rede e criado.
            self._client = client
            return
        if not self._api_key:
            # Credencial ausente falha antes de qualquer tentativa de rede.
            raise InsightProviderConfigError("openai_api_key_ausente")
        if not _OPENAI_AVAILABLE:  # pragma: no cover - ambiente sem SDK
            raise ImportError("openai package not available")
        # Configuracao explicita: nao confiar nos defaults do SDK.
        self._client = _openai.OpenAI(
            api_key=self._api_key,
            timeout=self._timeout_seconds,
            max_retries=self._max_retries,
        )

    def generate(self, request: InsightModelRequest) -> InsightModelResponse:
        try:
            response = self._client.responses.create(
                model=request.requested_model,
                input=request.input_text,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "insight_transport",
                        "schema": _INSIGHT_TRANSPORT_SCHEMA,
                        "strict": True,
                    }
                },
                max_output_tokens=self._max_output_tokens,
                stream=False,
                store=False,
            )
        except AuthenticationError:
            raise InsightProviderAuthError() from None
        except RateLimitError:
            raise InsightProviderRateLimitError() from None
        except APITimeoutError:
            raise InsightProviderTimeoutError() from None
        except APIConnectionError:
            raise InsightProviderUnavailableError() from None
        except BadRequestError:
            raise InsightProviderInvalidResponseError() from None
        except APIError:
            raise InsightProviderError() from None
        except OpenAIError:
            raise InsightProviderError() from None

        text = self._extract_text(response)
        if not isinstance(text, str) or text.strip() == "":
            raise InsightProviderInvalidResponseError()

        # Autoridade local de tamanho: rejeita (nunca trunca) antes de devolver.
        require_max_utf8_bytes(
            text, "provider_response_bytes", MAX_PROVIDER_RESPONSE_BYTES)

        resolved_model = getattr(response, "model", None)
        if resolved_model is not None and not isinstance(resolved_model, str):
            resolved_model = None
        request_id = getattr(response, "id", None)
        if request_id is not None and not isinstance(request_id, str):
            request_id = None
        usage = self._extract_usage(response)

        return InsightModelResponse(
            text=text,
            provider=self.provider_id,
            requested_model=request.requested_model,
            resolved_model=resolved_model,
            request_id=request_id,
            usage=usage,
        )

    @staticmethod
    def _extract_text(response: object) -> str:
        """Extrai o texto bruto do provider, sem reparo nem reinterpretacao."""
        output_text = getattr(response, "output_text", None)
        if isinstance(output_text, str):
            return output_text

        output = getattr(response, "output", None)
        if output:
            for item in output:
                content = getattr(item, "content", None)
                if not content:
                    continue
                for block in content:
                    text = getattr(block, "text", None)
                    if isinstance(text, str):
                        return text
                    value = getattr(block, "value", None)
                    if isinstance(value, str):
                        return value

        resp_text = getattr(response, "text", None)
        if isinstance(resp_text, str):
            return resp_text

        return ""

    @staticmethod
    def _extract_usage(response: object) -> Optional[InsightModelUsage]:
        """Traduz usage documentado para contrato neutro, sem coercoes."""
        raw_usage = getattr(response, "usage", None)
        if raw_usage is None:
            return None
        input_tokens = getattr(raw_usage, "input_tokens", None)
        output_tokens = getattr(raw_usage, "output_tokens", None)
        details = getattr(raw_usage, "input_tokens_details", None)
        cached_input_tokens = getattr(details, "cached_tokens", None)
        values = (input_tokens, output_tokens, cached_input_tokens)
        if all(value is None for value in values):
            return None
        if any(not isinstance(value, int) or isinstance(value, bool) or value < 0
               for value in values if value is not None):
            return None
        return InsightModelUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_input_tokens=cached_input_tokens,
        )
