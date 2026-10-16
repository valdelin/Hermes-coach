"""Contrato offline para futuros adapters de modelo do INSIGHT M1 v2."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Optional, Protocol, runtime_checkable

from .limits import (MAX_MODEL_INPUT_BYTES, MAX_PROVIDER_RESPONSE_BYTES,
                     require_max_utf8_bytes)


_SHA256 = re.compile(r"[0-9a-f]{64}")
_HARNESS_COMMIT = re.compile(r"[0-9a-f]{7,64}")


def _text(value: object, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} deve ser texto nao vazio")


def _sha256(value: object, name: str) -> None:
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} deve ser SHA-256 hexadecimal lowercase")


@dataclass(frozen=True)
class InsightModelRequest:
    """Pacote já preparado para invocacao futura, sem contexto de dominio bruto."""

    prompt_version: str
    prompt_sha256: str
    requested_model: str
    input_text: str
    schema_version: int

    def __post_init__(self) -> None:
        _text(self.prompt_version, "prompt_version")
        _sha256(self.prompt_sha256, "prompt_sha256")
        _text(self.requested_model, "requested_model")
        _text(self.input_text, "input_text")
        require_max_utf8_bytes(self.input_text, "model_input_bytes", MAX_MODEL_INPUT_BYTES)
        if (not isinstance(self.schema_version, int)
                or isinstance(self.schema_version, bool)
                or self.schema_version < 1):
            raise ValueError("schema_version deve ser inteiro positivo")


@dataclass(frozen=True)
class InsightModelResponse:
    """Resposta bruta controlada do provider; ainda nao e InsightPresentation."""

    text: str
    provider: str
    requested_model: str
    resolved_model: Optional[str] = None
    request_id: Optional[str] = None

    def __post_init__(self) -> None:
        _text(self.text, "text")
        require_max_utf8_bytes(
            self.text, "provider_response_bytes", MAX_PROVIDER_RESPONSE_BYTES)
        _text(self.provider, "provider")
        _text(self.requested_model, "requested_model")
        if self.resolved_model is not None:
            _text(self.resolved_model, "resolved_model")
        if self.request_id is not None:
            _text(self.request_id, "request_id")


@dataclass(frozen=True, init=False)
class InsightRuntimeProvenance:
    """Proveniencia derivada de uma execucao; este modulo nao cria relogio."""

    provider: str
    requested_model: str
    resolved_model: Optional[str]
    prompt_version: str
    prompt_sha256: str
    executed_at: datetime
    harness_version: Optional[str] = None
    harness_commit: Optional[str] = None

    def __init__(self) -> None:
        raise TypeError("use InsightRuntimeProvenance.from_execution")

    def __post_init__(self) -> None:
        _text(self.provider, "provider")
        _text(self.requested_model, "requested_model")
        if self.resolved_model is not None:
            _text(self.resolved_model, "resolved_model")
        _text(self.prompt_version, "prompt_version")
        _sha256(self.prompt_sha256, "prompt_sha256")
        if (not isinstance(self.executed_at, datetime)
                or self.executed_at.tzinfo is None
                or self.executed_at.utcoffset() is None):
            raise ValueError("executed_at deve ter timezone explicito")
        if self.harness_version is not None:
            _text(self.harness_version, "harness_version")
        if (self.harness_commit is not None
                and (not isinstance(self.harness_commit, str)
                     or _HARNESS_COMMIT.fullmatch(self.harness_commit) is None)):
            raise ValueError("harness_commit deve ser SHA hexadecimal lowercase")

    @classmethod
    def from_execution(
            cls,
            request: InsightModelRequest,
            response: InsightModelResponse,
            *,
            executed_at: datetime,
            harness_version: Optional[str] = None,
            harness_commit: Optional[str] = None,
    ) -> "InsightRuntimeProvenance":
        """Deriva provenance de ownerships distintos, sem reconciliacao silenciosa."""
        if response.requested_model != request.requested_model:
            raise InsightProvenanceError("requested_model_mismatch")
        provenance = cls.__new__(cls)
        object.__setattr__(provenance, "provider", response.provider)
        object.__setattr__(provenance, "requested_model", request.requested_model)
        object.__setattr__(provenance, "resolved_model", response.resolved_model)
        object.__setattr__(provenance, "prompt_version", request.prompt_version)
        object.__setattr__(provenance, "prompt_sha256", request.prompt_sha256)
        object.__setattr__(provenance, "executed_at", executed_at)
        object.__setattr__(provenance, "harness_version", harness_version)
        object.__setattr__(provenance, "harness_commit", harness_commit)
        provenance.__post_init__()
        return provenance


class InsightProvenanceError(ValueError):
    """Inconsistencia local entre request e response, sem payload retido."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class InsightInvocationStatus(str, Enum):
    SUCCESS = "success"
    PROVIDER_ERROR = "provider_error"
    INVALID_RESPONSE = "invalid_response"
    TIMEOUT = "timeout"
    AUTH_ERROR = "auth_error"
    RATE_LIMITED = "rate_limited"
    INFRA_ERROR = "infra_error"


class InsightProviderError(Exception):
    """Falha normalizada de um adapter futuro; nao executa retry."""

    code = "provider_error"
    retryable = False


class InsightProviderConfigError(InsightProviderError):
    """Configuracao local incompleta (ex.: credencial ausente), sem rede.

    Distinta de ``InsightProviderAuthError``: a primeira indica que o adapter
    nunca foi configurado; a segunda indica rejeicao de credencial pelo
    provider. Ambas sao contidas pelo runtime como falha de provider.
    """

    code = "config_error"


class InsightProviderAuthError(InsightProviderError):
    code = "auth_error"


class InsightProviderRateLimitError(InsightProviderError):
    code = "rate_limited"
    retryable = True


class InsightProviderTimeoutError(InsightProviderError):
    code = "timeout"
    retryable = True


class InsightProviderUnavailableError(InsightProviderError):
    code = "provider_unavailable"
    retryable = True


class InsightProviderInvalidResponseError(InsightProviderError):
    code = "invalid_response"


@runtime_checkable
class InsightModelProvider(Protocol):
    """Boundary sincrono e sem implementacao concreta para modelo futuro."""

    def generate(self, request: InsightModelRequest) -> InsightModelResponse:
        ...
