"""Telemetria sanitizada, provider-neutral e sem persistencia do INSIGHT M2-6."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
import re
from typing import Callable, Optional, Protocol, runtime_checkable

from .cost import estimate_insight_model_cost
from .model_provider import InsightModelResponse, InsightModelUsage
from .runtime import InsightRuntimeStatus


_PROVIDER_ID = re.compile(r"[a-z][a-z0-9-]{0,31}")
_MODEL_ID = re.compile(r"[a-z0-9][a-z0-9.:-]{0,127}")
_REQUEST_ID = re.compile(r"(?:resp|req)_[A-Za-z0-9-]{1,124}")
_TelemetryClock = Callable[[], Decimal]


@dataclass(frozen=True)
class InsightRuntimeTelemetry:
    """Evento fechado, sem prompt, payload, View, segredo ou objeto SDK."""

    status: InsightRuntimeStatus
    provider: Optional[str] = None
    requested_model: Optional[str] = None
    resolved_model: Optional[str] = None
    request_id: Optional[str] = None
    usage: Optional[InsightModelUsage] = None
    estimated_cost_usd: Optional[Decimal] = None
    currency: Optional[str] = None
    pricing_source: Optional[str] = None
    latency_seconds: Optional[Decimal] = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, InsightRuntimeStatus):
            raise ValueError("status deve ser InsightRuntimeStatus")
        for value, name in (
                (self.provider, "provider"),
                (self.requested_model, "requested_model"),
                (self.resolved_model, "resolved_model"),
                (self.request_id, "request_id"),
                (self.currency, "currency"),
                (self.pricing_source, "pricing_source")):
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise ValueError(f"{name} deve ser texto nao vazio ou None")
        if self.usage is not None:
            object.__setattr__(self, "usage", _canonical_usage(self.usage))
        if self.estimated_cost_usd is None:
            if self.currency is not None or self.pricing_source is not None:
                raise ValueError("custo ausente nao possui metadata de preco")
        elif (not isinstance(self.estimated_cost_usd, Decimal)
              or not self.estimated_cost_usd.is_finite()
              or self.estimated_cost_usd < 0
              or self.currency != "USD" or self.pricing_source is None):
            raise ValueError("custo requer Decimal valido, currency USD e pricing_source")
        if (self.latency_seconds is not None
                and (not isinstance(self.latency_seconds, Decimal)
                     or not self.latency_seconds.is_finite()
                     or self.latency_seconds < 0)):
            raise ValueError("latency_seconds deve ser Decimal finito nao negativo ou None")


@runtime_checkable
class InsightTelemetrySink(Protocol):
    """Destino opcional de evento seguro; persistencia pertence a outro gate."""

    def record(self, telemetry: InsightRuntimeTelemetry) -> None:
        ...


@dataclass
class InMemoryInsightTelemetrySink:
    """Coletor deterministico para composicao futura e testes offline."""

    events: list[InsightRuntimeTelemetry] = field(default_factory=list)

    def record(self, telemetry: InsightRuntimeTelemetry) -> None:
        if not isinstance(telemetry, InsightRuntimeTelemetry):
            raise ValueError("telemetry deve ser InsightRuntimeTelemetry")
        self.events.append(telemetry)


def build_insight_runtime_telemetry(
        *,
        status: InsightRuntimeStatus,
        response: Optional[InsightModelResponse],
        latency_seconds: Optional[Decimal] = None,
) -> InsightRuntimeTelemetry:
    """Projeta somente metadata segura da response observada para telemetria."""
    if response is None:
        return InsightRuntimeTelemetry(status=status, latency_seconds=latency_seconds)
    provider = _safe_provider_id(response.provider)
    requested_model = _safe_model_id(response.requested_model)
    resolved_model = _safe_model_id(response.resolved_model)
    request_id = _safe_request_id(response.request_id)
    usage = _canonical_usage(response.usage)
    estimate = None
    if (provider is not None and requested_model is not None
            and (response.resolved_model is None or resolved_model is not None)):
        estimate = estimate_insight_model_cost(
            provider=provider,
            requested_model=requested_model,
            resolved_model=resolved_model,
            usage=usage,
        )
    return InsightRuntimeTelemetry(
        status=status,
        provider=provider,
        requested_model=requested_model,
        resolved_model=resolved_model,
        request_id=request_id,
        usage=usage,
        estimated_cost_usd=(None if estimate is None else estimate.estimated_cost_usd),
        currency=None if estimate is None else estimate.currency,
        pricing_source=None if estimate is None else estimate.pricing_source,
        latency_seconds=latency_seconds,
    )


def record_insight_runtime_telemetry(
        sink: Optional[InsightTelemetrySink],
        *,
        status: InsightRuntimeStatus,
        response: Optional[InsightModelResponse],
        started_at: Optional[Decimal] = None,
        clock: Optional[_TelemetryClock] = None,
) -> None:
    """Emite um evento seguro; observabilidade opcional nunca muda o runtime."""
    if sink is None:
        return
    try:
        sink.record(build_insight_runtime_telemetry(
            status=status,
            response=response,
            latency_seconds=_elapsed_seconds(started_at, clock),
        ))
    except Exception:
        # O sink e observacional; sua falha nao pode bloquear presentation/fallback.
        return


def sample_telemetry_clock(clock: Optional[_TelemetryClock]) -> Optional[Decimal]:
    """Le clock injetado sem deixar observabilidade bloquear o runtime."""
    if clock is None:
        return None
    try:
        value = clock()
    except Exception:
        return None
    if (not isinstance(value, Decimal) or not value.is_finite() or value < 0):
        return None
    return value


def _elapsed_seconds(
        started_at: Optional[Decimal], clock: Optional[_TelemetryClock],
) -> Optional[Decimal]:
    if started_at is None:
        return None
    ended_at = sample_telemetry_clock(clock)
    if ended_at is None or ended_at < started_at:
        return None
    return ended_at - started_at


def _safe_provider_id(value: object) -> Optional[str]:
    return value if isinstance(value, str) and _PROVIDER_ID.fullmatch(value) else None


def _safe_model_id(value: object) -> Optional[str]:
    return value if isinstance(value, str) and _MODEL_ID.fullmatch(value) else None


def _safe_request_id(value: object) -> Optional[str]:
    return value if isinstance(value, str) and _REQUEST_ID.fullmatch(value) else None


def _canonical_usage(value: object) -> Optional[InsightModelUsage]:
    """Copia somente os tres campos fechados, sem reter subclasses do adapter."""
    if value is None:
        return None
    try:
        return InsightModelUsage(
            input_tokens=value.input_tokens,
            output_tokens=value.output_tokens,
            cached_input_tokens=value.cached_input_tokens,
        )
    except (AttributeError, TypeError, ValueError):
        return None
