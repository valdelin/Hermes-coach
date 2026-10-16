"""Custo estimado, puro e conservador do INSIGHT M2-6.

O modulo usa somente usage observado e uma tabela local versionada. Ausencia ou
inconsistencia de qualquer insumo necessario resulta em ``None``; custo nunca e
inferido de tamanho de texto nem fabricado como zero.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .model_provider import InsightModelUsage


_TOKENS_PER_MILLION = Decimal("1000000")


@dataclass(frozen=True)
class InsightCostEstimate:
    """Estimativa monetaria derivada, separada de provenance e dominio."""

    estimated_cost_usd: Decimal
    currency: str
    pricing_source: str

    def __post_init__(self) -> None:
        if (not isinstance(self.estimated_cost_usd, Decimal)
                or not self.estimated_cost_usd.is_finite()
                or self.estimated_cost_usd < 0):
            raise ValueError("estimated_cost_usd deve ser Decimal finito nao negativo")
        if self.currency != "USD":
            raise ValueError("currency deve ser USD")
        if not isinstance(self.pricing_source, str) or not self.pricing_source.strip():
            raise ValueError("pricing_source deve ser texto nao vazio")


@dataclass(frozen=True)
class _ModelPricing:
    input_usd_per_million: Decimal
    output_usd_per_million: Decimal
    cached_input_usd_per_million: Optional[Decimal]
    source: str


# ADR-007 e documentacao oficial do modelo consultada em 2026-10-16.
_PRICING: dict[tuple[str, str], _ModelPricing] = {
    ("openai", "gpt-5.4-nano-2026-03-17"): _ModelPricing(
        input_usd_per_million=Decimal("0.20"),
        output_usd_per_million=Decimal("1.25"),
        cached_input_usd_per_million=Decimal("0.02"),
        source="openai_api_pricing_2026-10-16_adr-007",
    ),
}


def estimate_insight_model_cost(
        *,
        provider: str,
        requested_model: str,
        resolved_model: Optional[str],
        usage: Optional[InsightModelUsage],
) -> Optional[InsightCostEstimate]:
    """Retorna custo somente quando todos os insumos exatos sao conhecidos.

    O modelo resolvido tem precedencia quando observado; o solicitado e usado
    apenas quando o provider nao reportou modelo resolvido. Nunca ha fallback por
    familia ou para o modelo solicitado quando um resolvido desconhecido existe.
    """
    if usage is None:
        return None
    if (usage.input_tokens is None or usage.output_tokens is None
            or usage.cached_input_tokens is None):
        return None
    if usage.cached_input_tokens > usage.input_tokens:
        return None
    model = resolved_model if resolved_model is not None else requested_model
    pricing = _PRICING.get((provider, model))
    if pricing is None:
        return None
    if usage.cached_input_tokens > 0:
        if pricing.cached_input_usd_per_million is None:
            return None
        non_cached_input = usage.input_tokens - usage.cached_input_tokens
        input_cost = (
            Decimal(non_cached_input) * pricing.input_usd_per_million
            + Decimal(usage.cached_input_tokens)
            * pricing.cached_input_usd_per_million
        ) / _TOKENS_PER_MILLION
    else:
        input_cost = (
            Decimal(usage.input_tokens) * pricing.input_usd_per_million
        ) / _TOKENS_PER_MILLION
    output_cost = (
        Decimal(usage.output_tokens) * pricing.output_usd_per_million
    ) / _TOKENS_PER_MILLION
    return InsightCostEstimate(
        estimated_cost_usd=input_cost + output_cost,
        currency="USD",
        pricing_source=pricing.source,
    )
