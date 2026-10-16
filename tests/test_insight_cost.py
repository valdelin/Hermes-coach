"""Calculo puro e conservador de custo do INSIGHT M2-6."""
from __future__ import annotations

from decimal import Decimal
import unittest

from src.insight.cost import estimate_insight_model_cost
from src.insight.model_provider import InsightModelUsage


MODEL = "gpt-5.4-nano-2026-03-17"


def estimate(*, provider: str = "openai", requested_model: str = MODEL,
             resolved_model: str | None = None,
             usage: InsightModelUsage | None = None):
    return estimate_insight_model_cost(
        provider=provider,
        requested_model=requested_model,
        resolved_model=resolved_model,
        usage=usage,
    )


class InsightCostTest(unittest.TestCase):
    def test_known_exact_model_uses_decimal_without_rounding(self) -> None:
        result = estimate(usage=InsightModelUsage(
            input_tokens=1_000_000, output_tokens=1_000_000,
            cached_input_tokens=0))
        self.assertIsNotNone(result)
        self.assertEqual(result.estimated_cost_usd, Decimal("1.45"))
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.pricing_source, "openai_api_pricing_2026-10-16_adr-007")

    def test_resolved_exact_model_has_precedence(self) -> None:
        result = estimate(
            requested_model="configured-alias",
            resolved_model=MODEL,
            usage=InsightModelUsage(input_tokens=10, output_tokens=20,
                                    cached_input_tokens=0),
        )
        self.assertIsNotNone(result)

    def test_unknown_resolved_model_never_falls_back_to_requested_price(self) -> None:
        result = estimate(
            resolved_model="unknown-resolved-model",
            usage=InsightModelUsage(input_tokens=10, output_tokens=20,
                                    cached_input_tokens=0),
        )
        self.assertIsNone(result)

    def test_unknown_model_and_missing_usage_have_no_cost(self) -> None:
        self.assertIsNone(estimate(requested_model="unknown", usage=InsightModelUsage(
            input_tokens=10, output_tokens=20, cached_input_tokens=0)))
        self.assertIsNone(estimate())

    def test_missing_cached_usage_is_not_silently_zero(self) -> None:
        self.assertIsNone(estimate(usage=InsightModelUsage(
            input_tokens=10, output_tokens=20, cached_input_tokens=None)))

    def test_cached_tokens_use_their_explicit_rate_without_double_counting(self) -> None:
        result = estimate(usage=InsightModelUsage(
            input_tokens=1_000_000, output_tokens=1_000_000,
            cached_input_tokens=200_000))
        self.assertIsNotNone(result)
        self.assertEqual(result.estimated_cost_usd, Decimal("1.414"))

    def test_inconsistent_cached_count_has_no_cost(self) -> None:
        self.assertIsNone(estimate(usage=InsightModelUsage(
            input_tokens=5, output_tokens=20, cached_input_tokens=6)))


if __name__ == "__main__":
    unittest.main()
