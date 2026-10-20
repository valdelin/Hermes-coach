"""Composição segura de configuração, adapter concreto e runtime INSIGHT M2-8."""
from __future__ import annotations

from datetime import datetime
from typing import Callable, Mapping, Optional

from .config import InsightRuntimeConfig, read_openai_api_key
from .contract import InsightView
from .model_provider import InsightModelProvider, InsightProviderConfigError
from .openai_provider import OpenAIInsightModelProvider
from . import render as _render
from .request_builder import INSIGHT_PROMPT_VERSION
from .runtime import InsightRuntimeResult, InsightRuntimeStatus, run_insight_runtime
from .telemetry import InsightTelemetrySink


_ProviderFactory = Callable[..., InsightModelProvider]


def run_configured_insight(
        view: InsightView,
        *,
        config: InsightRuntimeConfig,
        environment: Mapping[str, str],
        executed_at: datetime,
        provider_factory: _ProviderFactory = OpenAIInsightModelProvider,
        telemetry: Optional[InsightTelemetrySink] = None,
) -> InsightRuntimeResult:
    """Executa online somente sob autorização dupla; todo outro caso é fallback local."""
    if not config.insight_enabled or not config.online_enabled:
        return _fallback(view, InsightRuntimeStatus.FALLBACK_DISABLED)
    api_key = read_openai_api_key(environment)
    if api_key is None:
        return _fallback(view, InsightRuntimeStatus.FALLBACK_CONFIG)
    try:
        provider = provider_factory(api_key=api_key)
    except (InsightProviderConfigError, ImportError):
        # Falha de construcao (credencial/SDK ausente) e configuracao, nunca
        # status de modelo: nenhuma tentativa chega a existir.
        return _fallback(view, InsightRuntimeStatus.FALLBACK_CONFIG)
    return run_insight_runtime(
        view,
        provider=provider,
        requested_model=config.requested_model,
        prompt_version=INSIGHT_PROMPT_VERSION,
        executed_at=executed_at,
        telemetry=telemetry,
    )


def _fallback(view: InsightView, status: InsightRuntimeStatus) -> InsightRuntimeResult:
    return InsightRuntimeResult(
        presentation=_render.fallback_presentation(view), status=status, provenance=None)
