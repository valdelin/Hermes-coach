"""Contrato offline para futuros adapters de modelo do INSIGHT M1 v2."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Optional, Protocol, runtime_checkable


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
    input_text: str
    schema_version: int

    def __post_init__(self) -> None:
        _text(self.prompt_version, "prompt_version")
        _sha256(self.prompt_sha256, "prompt_sha256")
        _text(self.input_text, "input_text")
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
        _text(self.provider, "provider")
        _text(self.requested_model, "requested_model")
        if self.resolved_model is not None:
            _text(self.resolved_model, "resolved_model")
        if self.request_id is not None:
            _text(self.request_id, "request_id")


@dataclass(frozen=True)
class InsightRuntimeProvenance:
    """Proveniencia fornecida pelo caller; este modulo nao cria relogio."""

    provider: str
    requested_model: str
    resolved_model: Optional[str]
    prompt_version: str
    prompt_sha256: str
    executed_at: str
    harness_version: Optional[str] = None
    harness_commit: Optional[str] = None

    def __post_init__(self) -> None:
        _text(self.provider, "provider")
        _text(self.requested_model, "requested_model")
        if self.resolved_model is not None:
            _text(self.resolved_model, "resolved_model")
        _text(self.prompt_version, "prompt_version")
        _sha256(self.prompt_sha256, "prompt_sha256")
        _text(self.executed_at, "executed_at")
        try:
            parsed = datetime.fromisoformat(self.executed_at)
        except ValueError as exc:
            raise ValueError("executed_at deve ser ISO-8601") from exc
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            raise ValueError("executed_at deve ter timezone explicito")
        if self.harness_version is not None:
            _text(self.harness_version, "harness_version")
        if (self.harness_commit is not None
                and (not isinstance(self.harness_commit, str)
                     or _HARNESS_COMMIT.fullmatch(self.harness_commit) is None)):
            raise ValueError("harness_commit deve ser SHA hexadecimal lowercase")


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
