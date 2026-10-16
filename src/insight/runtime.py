"""Runtime provider-neutral do INSIGHT M2-3.

Orquestra uma unica tentativa de inference de um ``InsightModelProvider`` sobre um
``InsightView`` ja resolvido, passa o texto devolvido exclusivamente pelo seam
validado M2-2 e devolve um ``InsightRuntimeResult`` com status fechado.

Este modulo nao constroi View, nao muta Application/plan/Prescription, nao le
ambiente, nao usa relogio oculto, nao faz rede, nao grava nada e nao seleciona
provider/model. ``provider``, ``requested_model``, ``prompt_version`` e
``executed_at`` entram explicitamente; ``builder``, ``decoder`` e ``fallback``
tem default canonico puro mas continuam injetaveis.

Fronteira de erro
-----------------
Falhas conhecidas do provider viram ``FALLBACK_PROVIDER``. Falhas do seam M2-2
(JSON estrito, schema fechado, grounding, caution, size) e inconsistencia de
provenance (echo de ``requested_model``) viram ``FALLBACK_INVALID_RESPONSE``.
Existe exatamente **uma** contencao externa ampla, no proprio seam do runtime, que
captura erro inesperado como ``FALLBACK_INTERNAL``. Os helpers puros (builder,
decoder/validator, renderer e factory de provenance) nao possuem contencao ampla.

O texto de modelo nunca bypassa o seam M2-2: o renderer M1 nao e chamado
diretamente aqui.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from enum import Enum
from typing import Callable, Optional

from .contract import InsightPresentation, InsightView
from .limits import InsightSizeLimitError
from .model_provider import (InsightModelProvider, InsightModelRequest,
                              InsightModelResponse,
                             InsightProvenanceError, InsightProviderError,
                             InsightRuntimeProvenance)
from .render import InsightRenderError, fallback_presentation
from .request_builder import build_insight_model_request
from .response_validation import (InsightResponseError,
                                   parse_validate_render_insight_response)


class InsightRuntimeStatus(str, Enum):
    """Status fechado do runtime M2-3; nunca serializa excecao nem payload."""

    SUCCESS = "success"
    FALLBACK_DISABLED = "fallback_disabled"
    FALLBACK_CONFIG = "fallback_config"
    FALLBACK_PROVIDER = "fallback_provider"
    FALLBACK_INVALID_RESPONSE = "fallback_invalid_response"
    FALLBACK_INTERNAL = "fallback_internal"


from .telemetry import (InsightTelemetrySink, record_insight_runtime_telemetry,
                        sample_telemetry_clock)


@dataclass(frozen=True)
class InsightRuntimeResult:
    """Saida do runtime: presentation, status fechado e provenance opcional.

    Nunca retem response bruta, ``input_text``, excecao, objeto de SDK, custo ou
    payload de telemetria. ``provenance`` existe somente em ``SUCCESS``.
    """

    presentation: InsightPresentation
    status: InsightRuntimeStatus
    provenance: Optional[InsightRuntimeProvenance] = None


_RequestBuilder = Callable[..., InsightModelRequest]
_ResponseDecoder = Callable[..., InsightPresentation]
_FallbackRenderer = Callable[[InsightView], InsightPresentation]


def run_insight_runtime(
    view: InsightView,
    *,
    provider: InsightModelProvider,
    requested_model: str,
    prompt_version: str,
    executed_at: datetime,
    harness_version: Optional[str] = None,
    harness_commit: Optional[str] = None,
    builder: _RequestBuilder = build_insight_model_request,
    decoder: _ResponseDecoder = parse_validate_render_insight_response,
    fallback: _FallbackRenderer = fallback_presentation,
    telemetry: Optional[InsightTelemetrySink] = None,
    telemetry_clock: Optional[Callable[[], Decimal]] = None,
) -> InsightRuntimeResult:
    """Executa no maximo uma tentativa e devolve sempre um resultado fechado.

    A ordem e: builder puro (M2-1) -> uma chamada a ``provider.generate`` -> seam
    validado (M2-2) -> factory canonica de provenance. Nenhum retry, fallback
    secundario, sleep ou reparo silencioso. O texto do provider passa somente por
    ``decoder`` (default: ``parse_validate_render_insight_response``).
    """
    response = None
    telemetry_started_at = (
        sample_telemetry_clock(telemetry_clock) if telemetry is not None else None)
    try:
        request = builder(
            view,
            requested_model=requested_model,
            prompt_version=prompt_version,
        )
        try:
            response = provider.generate(request)
        except InsightProviderError:
            return _fallback_result(
                view, InsightRuntimeStatus.FALLBACK_PROVIDER, fallback,
                telemetry=telemetry, telemetry_started_at=telemetry_started_at,
                telemetry_clock=telemetry_clock)
        except InsightSizeLimitError:
            # Resposta do provider rejeitada pelo proprio contrato de response
            # antes de virar texto: e resposta invalida, nunca truncada.
            return _fallback_result(
                view, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE, fallback,
                telemetry=telemetry, telemetry_started_at=telemetry_started_at,
                telemetry_clock=telemetry_clock)

        try:
            presentation = decoder(response.text, view=view)
        except (InsightResponseError, InsightRenderError,
                InsightSizeLimitError):
            return _fallback_result(
                view, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE, fallback,
                response=response, telemetry=telemetry,
                telemetry_started_at=telemetry_started_at,
                telemetry_clock=telemetry_clock)

        try:
            provenance = InsightRuntimeProvenance.from_execution(
                request,
                response,
                executed_at=executed_at,
                harness_version=harness_version,
                harness_commit=harness_commit,
            )
        except InsightProvenanceError:
            # Echo de requested_model inconsistente: a resposta e invalida.
            return _fallback_result(
                view, InsightRuntimeStatus.FALLBACK_INVALID_RESPONSE, fallback,
                response=response, telemetry=telemetry,
                telemetry_started_at=telemetry_started_at,
                telemetry_clock=telemetry_clock)

        result = InsightRuntimeResult(
            presentation=presentation,
            status=InsightRuntimeStatus.SUCCESS,
            provenance=provenance,
        )
        record_insight_runtime_telemetry(
            telemetry, status=result.status, response=response,
            started_at=telemetry_started_at, clock=telemetry_clock)
        return result
    except Exception:
        # Unica contencao externa ampla: builder/decoder/provider/provenance com
        # erro inesperado (inclusive executed_at/harness invalidos) viram
        # FALLBACK_INTERNAL, sem reter nem exibir payload ou excecao bruta.
        return _fallback_result(
            view, InsightRuntimeStatus.FALLBACK_INTERNAL, fallback,
            response=response, telemetry=telemetry,
            telemetry_started_at=telemetry_started_at,
            telemetry_clock=telemetry_clock)


def _fallback_result(
        view: InsightView,
        status: InsightRuntimeStatus,
        fallback: _FallbackRenderer,
        *,
        response: Optional[InsightModelResponse] = None,
        telemetry: Optional[InsightTelemetrySink] = None,
        telemetry_started_at: Optional[Decimal] = None,
        telemetry_clock: Optional[Callable[[], Decimal]] = None,
) -> InsightRuntimeResult:
    """Monta um resultado deterministico de fallback, sem provenance."""
    result = InsightRuntimeResult(
        presentation=fallback(view), status=status, provenance=None)
    record_insight_runtime_telemetry(
        telemetry, status=result.status, response=response,
        started_at=telemetry_started_at, clock=telemetry_clock)
    return result
