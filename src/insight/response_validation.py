"""Decoder estrito, validacao de template e render local da resposta (INSIGHT M2-2).

Este modulo cobre o subset determinista de M2-2 descrito em
``docs/SPEC-insight-m2.md`` secao 5 e 5.1:

1. decodifica a resposta textual do provider em um
   ``InsightPresentationTemplate`` de schema fechado (JSON estrito, sem repair);
2. valida os quatro campos de template: placeholders, grounding contra as fact
   keys da View, regra Unicode ``Nd`` nos segmentos literais e caution provenance;
3. renderiza localmente a ``InsightPresentation`` reutilizando o renderer M1
   (``render_presentation``), sem duplicar a materializacao de valores.

O modulo e puro e provider-neutral: nao faz rede, nao le ambiente, nao usa
relogio, nao escreve arquivos e nao invoca provider. Falhas sao *fail closed*
(``InsightResponseError``); fallback pertence ao runtime do M2-3.
"""
from __future__ import annotations

import json
import re
import unicodedata

from .contract import InsightPresentation, InsightView
from .limits import MAX_PROVIDER_RESPONSE_BYTES, utf8_size
from .render import InsightPresentationTemplate, render_presentation


# Gramatica normativa do identificador de placeholder (SPEC M2 secao 5).
_IDENTIFIER_GRAMMAR = r"[a-z][a-z0-9_]*"
_PLACEHOLDER = re.compile(r"\{\{(" + _IDENTIFIER_GRAMMAR + r")\}\}")

_REQUIRED_FIELDS = ("headline", "explanation", "next_action_text")
_KNOWN_FIELDS = frozenset(_REQUIRED_FIELDS + ("caution_text",))


class _DuplicateMemberError(Exception):
    """Marcador interno: nome de membro JSON repetido no objeto (fail closed).

    Nao e ``ValueError`` de proposito, para nao ser confundido com falha de
    sintaxe JSON no ``except ValueError`` do decode.
    """


class InsightResponseError(ValueError):
    """Falha fechada de decode/validacao da resposta, sem reter payload bruto.

    Carrega apenas ``code`` (metadata segura). Nunca armazena a resposta bruta, o
    template completo, a View, o subject ou valores de fact.
    """

    def __init__(self, code: str, message: str) -> None:
        if not isinstance(code, str) or not code.strip():
            raise ValueError("code deve ser texto nao vazio")
        super().__init__(message)
        self.code = code


def decode_insight_presentation_template(text: str) -> InsightPresentationTemplate:
    """Decodifica texto estrito em um template fechado, sem reparo.

    Aceita apenas um unico objeto JSON com os quatro campos conhecidos. Rejeita
    oversize (utf-8), JSON invalido, objeto ausente, membro duplicado, campo
    desconhecido, campo obrigatorio ausente e tipos incorretos. Nomes de membro
    repetidos falham fechado **antes** do schema, sem semantica last-wins/first-wins
    e sem descartar ocorrencias. ``caution_text`` e opcional/nulo.
    """
    if not isinstance(text, str):
        raise InsightResponseError("invalid_response", "resposta deve ser texto")
    if utf8_size(text) > MAX_PROVIDER_RESPONSE_BYTES:
        raise InsightResponseError("response_oversize", "resposta excede o limite")
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_members)
    except _DuplicateMemberError:
        raise InsightResponseError(
            "duplicate_field", "resposta contem campo duplicado") from None
    except ValueError:
        raise InsightResponseError(
            "invalid_json", "resposta nao e um JSON estrito") from None
    if not isinstance(payload, dict):
        raise InsightResponseError(
            "invalid_json_object", "resposta deve ser um objeto JSON")
    if any(key not in _KNOWN_FIELDS for key in payload):
        raise InsightResponseError(
            "unknown_field", "resposta contem campo desconhecido")
    for name in _REQUIRED_FIELDS:
        if name not in payload:
            raise InsightResponseError(
                "missing_field", "campo obrigatorio ausente na resposta")
    for name in _REQUIRED_FIELDS:
        if not isinstance(payload[name], str):
            raise InsightResponseError(
                "invalid_field_type", f"campo {name} deve ser string")
    caution = payload.get("caution_text")
    if caution is not None and not isinstance(caution, str):
        raise InsightResponseError(
            "invalid_field_type", "caution_text deve ser string ou null")
    return InsightPresentationTemplate(
        headline=payload["headline"],
        explanation=payload["explanation"],
        next_action_text=payload["next_action_text"],
        caution_text=caution,
    )


def _reject_duplicate_members(pairs: list[tuple[str, object]]) -> dict[str, object]:
    """Reconstroi o objeto JSON rejeitando nomes de membro repetidos.

    Aplicado por ``json.loads`` a cada objeto (inclusive aninhado). Nao retem o
    nome nem o valor do membro duplicado: apenas sinaliza o marcador interno.
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise _DuplicateMemberError()
        seen.add(key)
    return dict(pairs)


def validate_insight_presentation_template(
        template: InsightPresentationTemplate, *, view: InsightView,
) -> None:
    """Valida placeholders, regra Unicode ``Nd``, grounding e caution provenance.

    Nao repara nem normaliza: qualquer desvio falha fechado. Os valores factuais
    permitidos sao derivados exclusivamente das fact keys da View.
    """
    if not isinstance(template, InsightPresentationTemplate):
        raise InsightResponseError("invalid_template", "template de resposta invalido")
    if not isinstance(view, InsightView):
        raise InsightResponseError("invalid_view", "view invalida")
    allowed_keys = frozenset(fact.key for fact in view.facts)
    for name, value in (
        ("headline", template.headline),
        ("explanation", template.explanation),
        ("next_action_text", template.next_action_text),
    ):
        if not isinstance(value, str):
            raise InsightResponseError(
                "invalid_field_type", f"campo {name} deve ser string")
        _validate_template_field(value, allowed_keys)
    caution = template.caution_text
    if caution is not None:
        if not isinstance(caution, str):
            raise InsightResponseError(
                "invalid_field_type", "caution_text deve ser string ou null")
        _validate_template_field(caution, allowed_keys)
    if caution is not None and view.advisory is None:
        raise InsightResponseError(
            "caution_without_advisory", "caution_text sem advisory upstream")


def render_insight_presentation(
        template: InsightPresentationTemplate, *, view: InsightView,
) -> InsightPresentation:
    """Valida e renderiza o template localmente a partir do estado do Hermes.

    Reutiliza o renderer determinista M1 (``render_presentation``). Nao injeta
    unidades, nao arredonda e nao calcula valores: apenas materializa os facts
    referenciados pelos placeholders validados.
    """
    validate_insight_presentation_template(template, view=view)
    return render_presentation(template, view)


def parse_validate_render_insight_response(
        text: str, *, view: InsightView,
) -> InsightPresentation:
    """Seam composta pura: decode -> validate -> render local determinista."""
    template = decode_insight_presentation_template(text)
    return render_insight_presentation(template, view=view)


def _split_placeholders(text: str) -> tuple[list[str], list[str]]:
    """Separa segmentos literais de placeholders validos, preservando a ordem."""
    literals: list[str] = []
    names: list[str] = []
    position = 0
    for match in _PLACEHOLDER.finditer(text):
        literals.append(text[position:match.start()])
        names.append(match.group(1))
        position = match.end()
    literals.append(text[position:])
    return literals, names


def _contains_decimal_digit(text: str) -> bool:
    """Verdadeiro se algum code point pertence a Unicode General Category ``Nd``."""
    return any(unicodedata.category(character) == "Nd" for character in text)


def _validate_template_field(value: str, allowed_keys: frozenset[str]) -> None:
    literals, names = _split_placeholders(value)
    for literal in literals:
        if "{" in literal or "}" in literal:
            raise InsightResponseError(
                "malformed_placeholder", "placeholder malformado na resposta")
    for literal in literals:
        if _contains_decimal_digit(literal):
            raise InsightResponseError(
                "literal_digit", "digito literal nao permitido no template")
    for name in names:
        if name not in allowed_keys:
            raise InsightResponseError(
                "unknown_placeholder", "placeholder nao permitido na resposta")
