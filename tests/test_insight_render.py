"""Testes offline do renderer deterministico do INSIGHT-2."""
from __future__ import annotations

import unittest

from src.insight.contract import FactClassification, InsightFact, InsightView, validate_presentation_payload
from src.insight.render import (
    InsightPresentationTemplate, InsightRenderError, fallback_presentation,
    render_presentation, render_template,
)


def view(*facts: InsightFact) -> InsightView:
    return InsightView(schema_version=1, subject="athlete", facts=tuple(facts))


class PlaceholderRendererTest(unittest.TestCase):
    def test_known_multiple_and_repeated_placeholders(self) -> None:
        state = view(InsightFact("session_name", "Sessao", FactClassification.PRESCRIPTION),
                     InsightFact("planned_duration", 45, FactClassification.PRESCRIPTION, "min"))
        self.assertEqual(render_template("{{session_name}}: {{planned_duration}}/{{planned_duration}}", state), "Sessao: 45/45")

    def test_unknown_missing_and_duplicate_facts_fail_closed(self) -> None:
        with self.assertRaisesRegex(InsightRenderError, "desconhecido"):
            render_template("{{missing}}", view())
        with self.assertRaisesRegex(InsightRenderError, "duplicado"):
            render_template("{{name}}", view(
                InsightFact("name", "a", FactClassification.OBSERVED),
                InsightFact("name", "b", FactClassification.OBSERVED)))

    def test_invalid_templates_fail_closed(self) -> None:
        for template in ("", "   ", "{{foo.bar}}", "{{foo[0]}}", "{{__class__}}", "{{x|upper}}", "{{1+1}}", "{foo}", "${foo}"):
            with self.subTest(template=template):
                with self.assertRaises(InsightRenderError):
                    render_template(template, view())

    def test_int_and_finite_float_render_deterministically(self) -> None:
        state = view(InsightFact("integer", 12, FactClassification.DERIVED),
                     InsightFact("decimal", 1.25, FactClassification.DERIVED))
        self.assertEqual(render_template("{{integer}} {{decimal}}", state), "12 1.25")

    def test_missing_never_becomes_default_value(self) -> None:
        with self.assertRaises(InsightRenderError):
            render_template("{{unavailable}}", view())


class PresentationRenderTest(unittest.TestCase):
    def test_complete_template_produces_valid_presentation_and_preserves_view(self) -> None:
        state = view(InsightFact("name", "Sessao", FactClassification.PRESCRIPTION))
        template = InsightPresentationTemplate("{{name}}", "Estado {{name}}", "Veja {{name}}")
        output = render_presentation(template, state)
        self.assertEqual(output.headline, "Sessao")
        self.assertIsNone(output.caution_text)
        self.assertEqual(validate_presentation_payload(output.__dict__), ())
        self.assertEqual(state.facts[0].value, "Sessao")

    def test_caution_none_is_preserved(self) -> None:
        output = render_presentation(InsightPresentationTemplate("H", "E", "N", None), view())
        self.assertIsNone(output.caution_text)


class FallbackTest(unittest.TestCase):
    def test_fallback_is_valid_deterministic_neutral_and_non_mutating(self) -> None:
        state = view(InsightFact("physiological_fact", 99, FactClassification.OBSERVED))
        first = fallback_presentation(state)
        second = fallback_presentation(state)
        self.assertEqual(first, second)
        self.assertIsNone(first.caution_text)
        self.assertEqual(validate_presentation_payload(first.__dict__), ())
        self.assertEqual(state.facts[0].value, 99)


class ArchitectureTest(unittest.TestCase):
    def test_renderer_depends_only_on_contract_and_stdlib(self) -> None:
        source = (__import__("pathlib").Path(__file__).resolve().parent.parent / "src/insight/render.py").read_text(encoding="utf-8")
        for forbidden in ("src.plan", "src.readiness", "src.ftp_history", "src.ftp_evidence", "src.provider"):
            self.assertNotIn(forbidden, source)
