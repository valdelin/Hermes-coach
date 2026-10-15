"""INSIGHT M1.1-A — limites operacionais, bytes canônicos e fallback."""
from __future__ import annotations

import json
import unittest

from src.insight.contract import (FactClassification, InsightFact,
                                  InsightPresentation, InsightSource, InsightView)
from src.insight.limits import (
    MAX_CAUTION_TEXT_CHARS, MAX_EXPLANATION_CHARS, MAX_FACT_COUNT,
    MAX_FACT_KEY_BYTES, MAX_FACT_STRING_VALUE_BYTES, MAX_FACT_UNIT_BYTES,
    MAX_HEADLINE_CHARS, MAX_INSIGHT_VIEW_BYTES, MAX_MODEL_INPUT_BYTES,
    MAX_NEXT_ACTION_TEXT_CHARS, MAX_PRESENTATION_TOTAL_BYTES,
    MAX_PROVENANCE_COUNT, MAX_PROVIDER_RESPONSE_BYTES, InsightSizeLimitError,
    presentation_bytes, utf8_size,
)
from src.insight.model_provider import InsightModelRequest, InsightModelResponse
from src.insight.render import (InsightPresentationTemplate, fallback_presentation,
                                render_presentation)
from src.insight.serialization import serialize_insight_view


SHA = "a" * 64


def fact(index: int, value: str = "x") -> InsightFact:
    return InsightFact(f"fact_{index}", value, FactClassification.OBSERVED)


def view_with_serialized_size(target: int) -> InsightView:
    """Preenche values ASCII de 32 facts; cada byte adicional é controlável."""
    values = ["x"] * MAX_FACT_COUNT

    def build() -> InsightView:
        return InsightView(
            schema_version=1,
            subject="athlete",
            facts=tuple(fact(index, value) for index, value in enumerate(values)),
        )

    baseline = len(serialize_insight_view(build()))
    remaining = target - baseline
    if remaining < 0:
        raise AssertionError("target abaixo do tamanho base")
    for index in range(len(values)):
        extra = min(remaining, MAX_FACT_STRING_VALUE_BYTES - len(values[index]))
        values[index] += "x" * extra
        remaining -= extra
    if remaining:
        raise AssertionError("target excede capacidade de fixture")
    return build()


def presentation_fields_for_size(target: int) -> tuple[str, str, str, str]:
    values = ["x", "x", "x", "x"]
    maxima = (
        MAX_HEADLINE_CHARS,
        MAX_EXPLANATION_CHARS,
        MAX_NEXT_ACTION_TEXT_CHARS,
        MAX_CAUTION_TEXT_CHARS,
    )
    baseline = len(presentation_bytes(*values))
    remaining = target - baseline
    if remaining < 0:
        raise AssertionError("target abaixo do tamanho base")
    for index, maximum in enumerate(maxima):
        extra = min(remaining, maximum - len(values[index]))
        values[index] += "x" * extra
        remaining -= extra
    if remaining:
        raise AssertionError("target excede capacidade de fixture")
    return tuple(values)  # type: ignore[return-value]


class LimitsModuleTest(unittest.TestCase):
    def test_constants_match_m1_1_spec(self) -> None:
        self.assertEqual(MAX_FACT_COUNT, 32)
        self.assertEqual(MAX_PROVENANCE_COUNT, 16)
        self.assertEqual(MAX_FACT_KEY_BYTES, 64)
        self.assertEqual(MAX_FACT_STRING_VALUE_BYTES, 512)
        self.assertEqual(MAX_FACT_UNIT_BYTES, 32)
        self.assertEqual(MAX_INSIGHT_VIEW_BYTES, 16_384)
        self.assertEqual(MAX_MODEL_INPUT_BYTES, 24_576)
        self.assertEqual(MAX_PROVIDER_RESPONSE_BYTES, 8_192)
        self.assertEqual(MAX_PRESENTATION_TOTAL_BYTES, 4_096)

    def test_utf8_size_and_error_metadata_do_not_retain_payload(self) -> None:
        self.assertEqual(utf8_size("é"), 2)
        secret = "SECRET_SENTINEL_DO_NOT_EXPOSE"
        error = InsightSizeLimitError("model_input_bytes", 24_577, 24_576)
        self.assertEqual((error.limit_name, error.actual_size, error.max_size),
                         ("model_input_bytes", 24_577, 24_576))
        self.assertNotIn(secret, str(error))
        self.assertNotIn(secret, repr(error))
        self.assertNotIn(secret, repr(vars(error)))
        for args in (("", 1, 1), ("x", True, 1), ("x", 1, -1)):
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    InsightSizeLimitError(*args)  # type: ignore[arg-type]


class StructuralLimitTest(unittest.TestCase):
    def test_fact_and_provenance_counts_are_bounded(self) -> None:
        for count in (MAX_FACT_COUNT - 1, MAX_FACT_COUNT):
            with self.subTest(facts=count):
                self.assertEqual(len(InsightView(1, "athlete", tuple(fact(i) for i in range(count))).facts), count)
        with self.assertRaisesRegex(InsightSizeLimitError, "fact_count"):
            InsightView(1, "athlete", tuple(fact(i) for i in range(MAX_FACT_COUNT + 1)))

        for count in (MAX_PROVENANCE_COUNT - 1, MAX_PROVENANCE_COUNT):
            with self.subTest(provenance=count):
                self.assertEqual(len(InsightView(
                    1, "athlete", provenance=tuple(InsightSource(f"source-{i}") for i in range(count)),
                ).provenance), count)
        with self.assertRaisesRegex(InsightSizeLimitError, "provenance_count"):
            InsightView(
                1, "athlete",
                provenance=tuple(InsightSource(f"source-{i}") for i in range(MAX_PROVENANCE_COUNT + 1)),
            )

    def test_fact_text_boundaries_use_utf8_bytes(self) -> None:
        cases = (
            ("key", MAX_FACT_KEY_BYTES, "fact_key_bytes", lambda text: InsightFact(text, "x", FactClassification.OBSERVED)),
            ("value", MAX_FACT_STRING_VALUE_BYTES, "fact_string_value_bytes", lambda text: InsightFact("x", text, FactClassification.OBSERVED)),
            ("unit", MAX_FACT_UNIT_BYTES, "fact_unit_bytes", lambda text: InsightFact("x", "value", FactClassification.OBSERVED, text)),
        )
        for name, maximum, limit_name, constructor in cases:
            for size in (maximum - 1, maximum):
                with self.subTest(field=name, size=size):
                    constructor("x" * size)
            with self.subTest(field=name, size=maximum + 1):
                with self.assertRaisesRegex(InsightSizeLimitError, limit_name):
                    constructor("x" * (maximum + 1))

        InsightFact("é" * 32, "x", FactClassification.OBSERVED)
        with self.assertRaisesRegex(InsightSizeLimitError, "fact_key_bytes"):
            InsightFact("é" * 33, "x", FactClassification.OBSERVED)
        InsightFact("x", "é" * 256, FactClassification.OBSERVED)
        with self.assertRaisesRegex(InsightSizeLimitError, "fact_string_value_bytes"):
            InsightFact("x", "é" * 257, FactClassification.OBSERVED)
        InsightFact("x", "value", FactClassification.OBSERVED, "é" * 16)
        with self.assertRaisesRegex(InsightSizeLimitError, "fact_unit_bytes"):
            InsightFact("x", "value", FactClassification.OBSERVED, "é" * 17)

    def test_numeric_fact_contract_remains_finite_without_physiology_threshold(self) -> None:
        self.assertEqual(InsightFact("large", 10 ** 500, FactClassification.DERIVED).value, 10 ** 500)
        self.assertEqual(InsightFact("large_float", 1e308, FactClassification.DERIVED).value, 1e308)


class SerializationLimitTest(unittest.TestCase):
    def test_canonical_json_shape_unicode_and_ordering(self) -> None:
        view = InsightView(
            schema_version=1,
            subject="atleta é",
            facts=(fact(2, "two"), fact(1, "one")),
            provenance=(InsightSource("second"), InsightSource("first")),
        )
        first = serialize_insight_view(view)
        second = serialize_insight_view(view)
        self.assertIsInstance(first, bytes)
        self.assertEqual(first, second)
        self.assertIn("atleta é".encode("utf-8"), first)
        self.assertNotIn(b"\\u00e9", first)
        self.assertNotIn(b": ", first)
        payload = json.loads(first.decode("utf-8"))
        self.assertEqual(payload["facts"], [
            {"classification": "observed", "key": "fact_2", "unit": None, "value": "two"},
            {"classification": "observed", "key": "fact_1", "unit": None, "value": "one"},
        ])
        self.assertEqual(payload["provenance"], [{"name": "second"}, {"name": "first"}])
        self.assertIsNone(payload["advisory"])
        self.assertIsNone(payload["prescribed_session"])
        self.assertIsNone(payload["observed_execution"])
        reversed_view = InsightView(1, "atleta é", tuple(reversed(view.facts)), provenance=view.provenance)
        self.assertNotEqual(first, serialize_insight_view(reversed_view))

    def test_serialized_view_budget_is_exact_and_non_mutating(self) -> None:
        for size in (MAX_INSIGHT_VIEW_BYTES - 1, MAX_INSIGHT_VIEW_BYTES):
            with self.subTest(size=size):
                view = view_with_serialized_size(size)
                self.assertEqual(len(serialize_insight_view(view)), size)
        oversized = view_with_serialized_size(MAX_INSIGHT_VIEW_BYTES + 1)
        before = (
            oversized.facts,
            oversized.provenance,
            oversized.subject,
            oversized.advisory,
            oversized.prescribed_session,
            oversized.observed_execution,
        )
        with self.assertRaises(InsightSizeLimitError) as caught:
            serialize_insight_view(oversized)
        self.assertEqual(caught.exception.limit_name, "serialized_view_bytes")
        self.assertEqual(caught.exception.actual_size, MAX_INSIGHT_VIEW_BYTES + 1)
        after = (
            oversized.facts,
            oversized.provenance,
            oversized.subject,
            oversized.advisory,
            oversized.prescribed_session,
            oversized.observed_execution,
        )
        self.assertEqual(before, after)


class ModelBoundaryLimitTest(unittest.TestCase):
    def test_request_and_response_utf8_boundaries(self) -> None:
        for size in (MAX_MODEL_INPUT_BYTES - 1, MAX_MODEL_INPUT_BYTES):
            with self.subTest(request=size):
                InsightModelRequest("v1", SHA, "requested", "x" * size, 1)
        with self.assertRaisesRegex(InsightSizeLimitError, "model_input_bytes"):
            InsightModelRequest("v1", SHA, "requested", "x" * (MAX_MODEL_INPUT_BYTES + 1), 1)
        InsightModelRequest("v1", SHA, "requested", "é" * (MAX_MODEL_INPUT_BYTES // 2), 1)
        with self.assertRaisesRegex(InsightSizeLimitError, "model_input_bytes"):
            InsightModelRequest("v1", SHA, "requested", "é" * (MAX_MODEL_INPUT_BYTES // 2 + 1), 1)

        for size in (MAX_PROVIDER_RESPONSE_BYTES - 1, MAX_PROVIDER_RESPONSE_BYTES):
            with self.subTest(response=size):
                InsightModelResponse("x" * size, "provider", "requested")
        with self.assertRaisesRegex(InsightSizeLimitError, "provider_response_bytes"):
            InsightModelResponse("x" * (MAX_PROVIDER_RESPONSE_BYTES + 1), "provider", "requested")
        InsightModelResponse("é" * (MAX_PROVIDER_RESPONSE_BYTES // 2), "provider", "requested")
        with self.assertRaisesRegex(InsightSizeLimitError, "provider_response_bytes"):
            InsightModelResponse("é" * (MAX_PROVIDER_RESPONSE_BYTES // 2 + 1), "provider", "requested")

    def test_real_oversize_error_does_not_retain_input_text(self) -> None:
        secret = "SECRET_SENTINEL_DO_NOT_EXPOSE"
        text = secret + "x" * MAX_MODEL_INPUT_BYTES
        with self.assertRaises(InsightSizeLimitError) as caught:
            InsightModelRequest("v1", SHA, "requested", text, 1)
        self.assertNotIn(secret, str(caught.exception))
        self.assertNotIn(secret, repr(caught.exception))
        self.assertNotIn(secret, repr(vars(caught.exception)))


class PresentationLimitTest(unittest.TestCase):
    def test_existing_character_limits_remain_and_total_budget_is_exact(self) -> None:
        for maximum, index in (
                (MAX_HEADLINE_CHARS, 0), (MAX_EXPLANATION_CHARS, 1),
                (MAX_NEXT_ACTION_TEXT_CHARS, 2), (MAX_CAUTION_TEXT_CHARS, 3)):
            values = ["H", "E", "N", "C"]
            values[index] = "x" * maximum
            InsightPresentation(*values)
            values[index] = "x" * (maximum + 1)
            with self.subTest(maximum=maximum):
                with self.assertRaises(InsightSizeLimitError):
                    InsightPresentation(*values)

        for size in (MAX_PRESENTATION_TOTAL_BYTES - 1, MAX_PRESENTATION_TOTAL_BYTES):
            with self.subTest(total=size):
                values = presentation_fields_for_size(size)
                self.assertEqual(len(presentation_bytes(*values)), size)
                InsightPresentation(*values)
        values = presentation_fields_for_size(MAX_PRESENTATION_TOTAL_BYTES + 1)
        with self.assertRaises(InsightSizeLimitError) as caught:
            InsightPresentation(*values)
        self.assertEqual(caught.exception.limit_name, "presentation_total_bytes")
        self.assertEqual(caught.exception.actual_size, MAX_PRESENTATION_TOTAL_BYTES + 1)

    def test_renderer_expansion_fails_closed_and_composes_with_existing_fallback(self) -> None:
        view = InsightView(1, "athlete", (fact(0, "x" * MAX_FACT_STRING_VALUE_BYTES),))
        template = InsightPresentationTemplate("H", "{{fact_0}}" * 4, "N")
        with self.assertRaises(InsightSizeLimitError):
            render_presentation(template, view)

        oversized = view_with_serialized_size(MAX_INSIGHT_VIEW_BYTES + 1)
        with self.assertRaises(InsightSizeLimitError):
            serialize_insight_view(oversized)
        fallback = fallback_presentation(oversized)
        self.assertEqual(fallback, fallback_presentation(oversized))
        self.assertEqual(fallback.headline, "Apresentacao indisponivel")
        self.assertEqual(oversized, oversized)


if __name__ == "__main__":
    unittest.main()
