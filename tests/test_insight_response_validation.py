"""Testes offline do decoder/validator/render de resposta do INSIGHT M2-2."""
from __future__ import annotations

import dataclasses
import json
import pathlib
import unicodedata
import unittest

from src.insight.contract import (
    FactClassification, InsightAdvisory, InsightFact, InsightPresentation,
    InsightView, validate_presentation_payload,
)
from src.insight.limits import (
    MAX_PRESENTATION_TOTAL_BYTES, MAX_PROVIDER_RESPONSE_BYTES,
    MAX_HEADLINE_CHARS, InsightSizeLimitError, utf8_size,
)
from src.insight.render import InsightPresentationTemplate, InsightRenderError
from src.insight.response_validation import (
    InsightResponseError, decode_insight_presentation_template,
    parse_validate_render_insight_response, render_insight_presentation,
    validate_insight_presentation_template,
)

# Decimal_Number nao ASCII (ARABIC-INDIC DIGIT THREE), usado como prova Unicode.
NON_ASCII_ND = "\u0663"
SENTINEL = "SENTINEL_DO_PAYLOAD"


def make_view(*facts: InsightFact, advisory: InsightAdvisory | None = None) -> InsightView:
    return InsightView(
        schema_version=1, subject="athlete", facts=tuple(facts), advisory=advisory)


def fact(key: str, value: object, unit: str | None = None) -> InsightFact:
    return InsightFact(key, value, FactClassification.DERIVED, unit)


def text_of(payload: dict) -> str:
    return json.dumps(payload)


def payload(**overrides: object) -> dict:
    base: dict = {
        "headline": "Resumo do dia",
        "explanation": "Tudo em ordem",
        "next_action_text": "Siga o plano",
    }
    base.update(overrides)
    return base


class StrictDecodeTest(unittest.TestCase):
    def test_happy_path_decodes_closed_template(self) -> None:
        template = decode_insight_presentation_template(text_of(payload()))
        self.assertIsInstance(template, InsightPresentationTemplate)
        self.assertEqual(template.headline, "Resumo do dia")
        self.assertIsNone(template.caution_text)

    def test_absent_and_null_caution_become_none(self) -> None:
        self.assertIsNone(
            decode_insight_presentation_template(text_of(payload())).caution_text)
        self.assertIsNone(
            decode_insight_presentation_template(
                text_of(payload(caution_text=None))).caution_text)

    def test_rejects_extra_field(self) -> None:
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(text_of(payload(extra="x")))
        self.assertEqual(ctx.exception.code, "unknown_field")

    def test_rejects_missing_required_field(self) -> None:
        for name in ("headline", "explanation", "next_action_text"):
            with self.subTest(missing=name):
                body = payload()
                del body[name]
                with self.assertRaises(InsightResponseError) as ctx:
                    decode_insight_presentation_template(text_of(body))
                self.assertEqual(ctx.exception.code, "missing_field")

    def test_rejects_wrong_types_without_coercion(self) -> None:
        cases = (
            payload(headline=123),
            payload(explanation=None),
            payload(next_action_text=["a"]),
            payload(caution_text=[]),
            payload(caution_text=7),
        )
        for body in cases:
            with self.subTest(body=body):
                with self.assertRaises(InsightResponseError) as ctx:
                    decode_insight_presentation_template(text_of(body))
                self.assertEqual(ctx.exception.code, "invalid_field_type")

    def test_rejects_non_object_json(self) -> None:
        for body in ("[]", "1", '"texto"', "true", "null"):
            with self.subTest(body=body):
                with self.assertRaises(InsightResponseError) as ctx:
                    decode_insight_presentation_template(body)
                self.assertEqual(ctx.exception.code, "invalid_json_object")

    def test_rejects_invalid_json_variants(self) -> None:
        good = text_of(payload())
        cases = (
            '{"headline":"a","explanation":"b","next_action_text":"c",}',
            "{'headline':'a','explanation':'b','next_action_text':'c'}",
            "Segue: " + good,
            good + " fim",
            "```json\n" + good + "\n```",
            "",
        )
        for body in cases:
            with self.subTest(body=body[:24]):
                with self.assertRaises(InsightResponseError) as ctx:
                    decode_insight_presentation_template(body)
                self.assertEqual(ctx.exception.code, "invalid_json")

    def test_oversize_response_fails_closed_without_truncation(self) -> None:
        body = payload(explanation="x" * 9000)
        text = text_of(body)
        self.assertGreater(utf8_size(text), MAX_PROVIDER_RESPONSE_BYTES)
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(text)
        self.assertEqual(ctx.exception.code, "response_oversize")

    def test_response_at_byte_limit_is_accepted(self) -> None:
        body = payload(explanation="")
        pad = MAX_PROVIDER_RESPONSE_BYTES - utf8_size(text_of(body))
        body["explanation"] = "x" * pad
        text = text_of(body)
        self.assertEqual(utf8_size(text), MAX_PROVIDER_RESPONSE_BYTES)
        template = decode_insight_presentation_template(text)
        self.assertEqual(len(template.explanation), pad)
        with self.assertRaises(InsightResponseError):
            decode_insight_presentation_template(text.replace("xx", "xxx", 1))

    def test_rejects_non_text_input(self) -> None:
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(b"{}")  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "invalid_response")

    def test_decode_does_not_enforce_digit_rule(self) -> None:
        template = decode_insight_presentation_template(
            text_of(payload(explanation="Alvo 250 W")))
        self.assertEqual(template.explanation, "Alvo 250 W")
        with self.assertRaises(InsightResponseError):
            validate_insight_presentation_template(template, view=make_view())


class DuplicateMemberTest(unittest.TestCase):
    def test_duplicate_required_keys_rejected(self) -> None:
        cases = (
            '{"headline":"A","headline":"B","explanation":"X","next_action_text":"Y"}',
            '{"headline":"A","explanation":"X","explanation":"Z","next_action_text":"Y"}',
            '{"headline":"A","explanation":"X","next_action_text":"Y","next_action_text":"W"}',
        )
        for text in cases:
            with self.subTest(text=text[:40]):
                with self.assertRaises(InsightResponseError) as ctx:
                    decode_insight_presentation_template(text)
                self.assertEqual(ctx.exception.code, "duplicate_field")

    def test_duplicate_caution_key_rejected(self) -> None:
        cases = (
            '{"headline":"A","explanation":"X","next_action_text":"Y",'
            '"caution_text":null,"caution_text":"C"}',
            '{"headline":"A","explanation":"X","next_action_text":"Y",'
            '"caution_text":"C","caution_text":null}',
        )
        for text in cases:
            with self.subTest(text=text[-40:]):
                with self.assertRaises(InsightResponseError) as ctx:
                    decode_insight_presentation_template(text)
                self.assertEqual(ctx.exception.code, "duplicate_field")

    def test_duplicate_unknown_key_rejected(self) -> None:
        text = ('{"headline":"A","explanation":"X","next_action_text":"Y",'
                '"extra":"A","extra":"B"}')
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(text)
        self.assertEqual(ctx.exception.code, "duplicate_field")

    def test_known_plus_unknown_duplicate_fails_closed(self) -> None:
        text = ('{"headline":"A","headline":"B","explanation":"X",'
                '"next_action_text":"Y","extra":"Z"}')
        with self.assertRaises(InsightResponseError):
            decode_insight_presentation_template(text)

    def test_same_value_duplicate_rejected(self) -> None:
        text = '{"headline":"A","headline":"A","explanation":"X","next_action_text":"Y"}'
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(text)
        self.assertEqual(ctx.exception.code, "duplicate_field")

    def test_escaped_equivalent_key_is_duplicate(self) -> None:
        # "\u006c" decodifica para "l"; "head\u006cine" == "headline".
        text = r'{"headline":"A","head\u006cine":"B","explanation":"X","next_action_text":"Y"}'
        self.assertEqual(json.loads(r'"head\u006cine"'), "headline")
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(text)
        self.assertEqual(ctx.exception.code, "duplicate_field")

    def test_member_names_are_case_sensitive(self) -> None:
        text = '{"headline":"A","Headline":"B","explanation":"X","next_action_text":"Y"}'
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(text)
        self.assertEqual(ctx.exception.code, "unknown_field")

    def test_duplicate_error_does_not_retain_payload(self) -> None:
        sentinel = "__SECRET_DUPLICATE_VALUE_SENTINEL__"
        text = ('{"headline":"' + sentinel + '","headline":"' + sentinel
                + '","explanation":"X","next_action_text":"Y"}')
        with self.assertRaises(InsightResponseError) as ctx:
            decode_insight_presentation_template(text)
        error = ctx.exception
        self.assertEqual(error.code, "duplicate_field")
        for rendered in (str(error), repr(error), str(vars(error))):
            self.assertNotIn(sentinel, rendered)


class PlaceholderValidationTest(unittest.TestCase):
    def test_valid_known_and_repeated_placeholders_pass(self) -> None:
        state = make_view(fact("ctl", 42), fact("zone2_target", 200))
        body = payload(explanation="Zona {{zone2_target}} e {{ctl}} e {{ctl}}")
        result = parse_validate_render_insight_response(
            text_of(body), view=state)
        self.assertEqual(result.explanation, "Zona 200 e 42 e 42")

    def test_unknown_placeholder_is_rejected(self) -> None:
        state = make_view(fact("ctl", 42))
        with self.assertRaises(InsightResponseError) as ctx:
            parse_validate_render_insight_response(
                text_of(payload(explanation="Use {{ftp}}")), view=state)
        self.assertEqual(ctx.exception.code, "unknown_placeholder")

    def test_malformed_placeholders_are_rejected(self) -> None:
        state = make_view(fact("foo", 1))
        malformed = (
            "{{Bad2}}", "{{foo-bar}}", "{{foo.bar}}", "{{foo[0]}}", "{{ foo }}",
            "{{}}", "{{foo|bar}}", "{{foo()}}", "{{{foo}}}", "{{", "}}",
            "{foo}", "${foo}", "{{foo}",
        )
        for text in malformed:
            with self.subTest(text=text):
                with self.assertRaises(InsightResponseError) as ctx:
                    parse_validate_render_insight_response(
                        text_of(payload(explanation=text)), view=state)
                self.assertEqual(ctx.exception.code, "malformed_placeholder")

    def test_digit_inside_valid_identifier_is_allowed(self) -> None:
        state = make_view(fact("zone2_target", 200))
        result = parse_validate_render_insight_response(
            text_of(payload(explanation="Zona {{zone2_target}}")), view=state)
        self.assertEqual(result.explanation, "Zona 200")

    def test_validate_rejects_non_template_and_non_view(self) -> None:
        with self.assertRaises(InsightResponseError) as ctx:
            validate_insight_presentation_template("nao-template", view=make_view())
        self.assertEqual(ctx.exception.code, "invalid_template")
        with self.assertRaises(InsightResponseError) as ctx:
            validate_insight_presentation_template(
                InsightPresentationTemplate("H", "E", "N"), view=object())  # type: ignore[arg-type]
        self.assertEqual(ctx.exception.code, "invalid_view")

    def test_render_revalidates_untrusted_template(self) -> None:
        template = InsightPresentationTemplate("Alvo 250 W", "E", "N")
        with self.assertRaises(InsightResponseError) as ctx:
            render_insight_presentation(template, view=make_view())
        self.assertEqual(ctx.exception.code, "literal_digit")


class UnicodeNdTest(unittest.TestCase):
    def test_non_ascii_fixture_is_decimal_number(self) -> None:
        self.assertEqual(unicodedata.category(NON_ASCII_ND), "Nd")

    def test_ascii_digit_rejected_in_each_template_field(self) -> None:
        for field in ("headline", "explanation", "next_action_text", "caution_text"):
            with self.subTest(field=field):
                body = payload(caution_text=None)
                body[field] = f"valor {field} 3"
                state = make_view(advisory=InsightAdvisory("bloco"))
                with self.assertRaises(InsightResponseError) as ctx:
                    parse_validate_render_insight_response(text_of(body), view=state)
                self.assertEqual(ctx.exception.code, "literal_digit")

    def test_non_ascii_nd_rejected_in_literal(self) -> None:
        state = make_view()
        with self.assertRaises(InsightResponseError) as ctx:
            parse_validate_render_insight_response(
                text_of(payload(explanation=f"Zona {NON_ASCII_ND}")), view=state)
        self.assertEqual(ctx.exception.code, "literal_digit")

    def test_decimal_fragment_is_literal_digit(self) -> None:
        state = make_view(fact("power", 250))
        with self.assertRaises(InsightResponseError) as ctx:
            parse_validate_render_insight_response(
                text_of(payload(explanation="{{power}}.5")), view=state)
        self.assertEqual(ctx.exception.code, "literal_digit")

    def test_template_vs_final_presentation(self) -> None:
        state = make_view(fact("target_power", 250))
        result = parse_validate_render_insight_response(
            text_of(payload(explanation="Alvo {{target_power}} W")), view=state)
        self.assertEqual(result.explanation, "Alvo 250 W")
        with self.assertRaises(InsightResponseError) as ctx:
            parse_validate_render_insight_response(
                text_of(payload(explanation="Alvo 250 W")), view=state)
        self.assertEqual(ctx.exception.code, "literal_digit")

    def test_plain_units_without_digits_are_allowed_literals(self) -> None:
        state = make_view(fact("power", 250), fact("hr", 140))
        result = parse_validate_render_insight_response(
            text_of(payload(explanation="{{power}} W e {{hr}} bpm")), view=state)
        self.assertEqual(result.explanation, "250 W e 140 bpm")


class CautionProvenanceTest(unittest.TestCase):
    def test_caution_without_upstream_advisory_is_rejected(self) -> None:
        with self.assertRaises(InsightResponseError) as ctx:
            parse_validate_render_insight_response(
                text_of(payload(caution_text="Cuidado")), view=make_view())
        self.assertEqual(ctx.exception.code, "caution_without_advisory")

    def test_null_caution_without_advisory_is_allowed(self) -> None:
        result = parse_validate_render_insight_response(
            text_of(payload(caution_text=None)), view=make_view())
        self.assertIsNone(result.caution_text)

    def test_caution_with_advisory_is_allowed(self) -> None:
        state = make_view(advisory=InsightAdvisory("reduza carga"))
        result = parse_validate_render_insight_response(
            text_of(payload(caution_text="Reduza a carga")), view=state)
        self.assertEqual(result.caution_text, "Reduza a carga")

    def test_caution_placeholder_is_grounded_when_advisory_present(self) -> None:
        state = make_view(advisory=InsightAdvisory("bloco"))
        with self.assertRaises(InsightResponseError) as ctx:
            parse_validate_render_insight_response(
                text_of(payload(caution_text="Use {{ftp}}")), view=state)
        self.assertEqual(ctx.exception.code, "unknown_placeholder")


class LocalRenderTest(unittest.TestCase):
    def test_values_come_from_view_not_response(self) -> None:
        state = make_view(fact("token", SENTINEL))
        body = payload(explanation="Valor {{token}}")
        text = text_of(body)
        self.assertNotIn(SENTINEL, text)
        result = parse_validate_render_insight_response(text, view=state)
        self.assertEqual(result.explanation, f"Valor {SENTINEL}")

    def test_unit_literal_is_not_duplicated(self) -> None:
        state = make_view(fact("power", 250, unit="W"))
        result = parse_validate_render_insight_response(
            text_of(payload(explanation="{{power}} W")), view=state)
        self.assertEqual(result.explanation, "250 W")

    def test_none_fact_value_is_contract_impossible(self) -> None:
        with self.assertRaises(ValueError):
            InsightFact("x", None, FactClassification.OBSERVED)  # type: ignore[arg-type]

    def test_result_is_valid_presentation_and_preserves_none_caution(self) -> None:
        result = parse_validate_render_insight_response(
            text_of(payload(caution_text=None)), view=make_view())
        self.assertIsInstance(result, InsightPresentation)
        self.assertIsNone(result.caution_text)
        self.assertEqual(validate_presentation_payload(result.__dict__), ())

    def test_individual_char_limit_fails_closed(self) -> None:
        with self.assertRaises(InsightSizeLimitError):
            parse_validate_render_insight_response(
                text_of(payload(headline="x" * (MAX_HEADLINE_CHARS + 1))),
                view=make_view())

    def test_explanation_over_template_cap_fails_closed(self) -> None:
        with self.assertRaises((InsightRenderError, InsightSizeLimitError)):
            parse_validate_render_insight_response(
                text_of(payload(explanation="x" * 2001)), view=make_view())

    def test_total_presentation_bytes_fails_closed(self) -> None:
        body = payload(explanation="\u6f22" * 2000)
        text = json.dumps(body, ensure_ascii=False)
        self.assertLessEqual(utf8_size(text), MAX_PROVIDER_RESPONSE_BYTES)
        self.assertGreater(len(body["explanation"].encode("utf-8")),
                           MAX_PRESENTATION_TOTAL_BYTES)
        with self.assertRaises(InsightSizeLimitError):
            parse_validate_render_insight_response(text, view=make_view())


class SafetyTest(unittest.TestCase):
    def test_errors_do_not_retain_raw_response(self) -> None:
        texts = (
            '{"headline":"' + SENTINEL + '"',
            text_of(payload(explanation=SENTINEL, extra=SENTINEL)),
            "prosa " + SENTINEL,
        )
        for text in texts:
            with self.subTest(text=text[:20]):
                with self.assertRaises(InsightResponseError) as ctx:
                    decode_insight_presentation_template(text)
                error = ctx.exception
                for rendered in (str(error), repr(error), str(vars(error))):
                    self.assertNotIn(SENTINEL, rendered)

    def test_view_is_not_mutated(self) -> None:
        state = make_view(fact("ctl", 42), advisory=InsightAdvisory("bloco"))
        before = dataclasses.asdict(state)
        parse_validate_render_insight_response(
            text_of(payload(explanation="CTL {{ctl}}", caution_text="ok")),
            view=state)
        self.assertEqual(dataclasses.asdict(state), before)

    def test_output_is_deterministic(self) -> None:
        state = make_view(fact("ctl", 42))
        text = text_of(payload(explanation="CTL {{ctl}}"))
        first = parse_validate_render_insight_response(text, view=state)
        second = parse_validate_render_insight_response(text, view=state)
        self.assertEqual(first, second)


class ArchitectureTest(unittest.TestCase):
    def test_module_is_pure_and_provider_neutral(self) -> None:
        source = (pathlib.Path(__file__).resolve().parent.parent
                  / "src/insight/response_validation.py").read_text(encoding="utf-8")
        forbidden = (
            "requests", "httpx", "urllib", "socket", "subprocess", "dotenv",
            "os.environ", "datetime", "time.time", "monotonic", "perf_counter",
            "random", "open(", "eval(", "exec(", "jinja",
        )
        for token in forbidden:
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
