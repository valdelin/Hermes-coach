"""Renderer deterministico de placeholders para o contrato INSIGHT M1 v2."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional

from .contract import InsightFact, InsightPresentation, InsightView, validate_presentation_payload


_IDENTIFIER = r"[a-z][a-z0-9_]*"
_PLACEHOLDER = re.compile(r"\{\{(" + _IDENTIFIER + r")\}\}")
_TEMPLATE = re.compile(r"(?:[^{}]|\{\{" + _IDENTIFIER + r"\}\})*")
_MAX_TEMPLATE_LENGTH = 2000


class InsightRenderError(ValueError):
    """Falha fechada de template ou grounding."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class InsightPresentationTemplate:
    """Textos de apresentacao que podem conter apenas placeholders permitidos."""

    headline: str
    explanation: str
    next_action_text: str
    caution_text: Optional[str] = None


def render_template(template: str, view: InsightView) -> str:
    """Renderiza facts do View sem lookup externo, calculo ou valores default."""
    _validate_template(template)
    facts = _facts_by_key(view.facts)

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in facts:
            raise InsightRenderError("unknown_placeholder", f"placeholder desconhecido: {key}")
        return _render_value(facts[key].value)

    return _PLACEHOLDER.sub(replace, template)


def render_presentation(
        template: InsightPresentationTemplate, view: InsightView,
) -> InsightPresentation:
    """Renderiza uma estrutura fechada e valida a Presentation resultante."""
    if not isinstance(template, InsightPresentationTemplate):
        raise InsightRenderError("invalid_template", "template de presentation invalido")
    payload = {
        "headline": render_template(template.headline, view),
        "explanation": render_template(template.explanation, view),
        "next_action_text": render_template(template.next_action_text, view),
        "caution_text": (render_template(template.caution_text, view)
                         if template.caution_text is not None else None),
    }
    errors = validate_presentation_payload(payload)
    if errors:
        raise InsightRenderError("invalid_presentation", "; ".join(errors))
    return InsightPresentation(**payload)


def fallback_presentation(view: InsightView) -> InsightPresentation:
    """Apresentacao estatica, neutra e independente de policy ou facts."""
    if not isinstance(view, InsightView):
        raise InsightRenderError("invalid_view", "view invalida")
    return InsightPresentation(
        headline="Apresentacao indisponivel",
        explanation="Nao foi possivel gerar uma apresentacao detalhada.",
        next_action_text="Consulte o estado estruturado do Hermes.",
        caution_text=None,
    )


def _validate_template(template: object) -> None:
    if not isinstance(template, str):
        raise InsightRenderError("invalid_template", "template deve ser texto")
    if not template.strip():
        raise InsightRenderError("invalid_template", "template nao pode ser vazio")
    if len(template) > _MAX_TEMPLATE_LENGTH:
        raise InsightRenderError("invalid_template", "template excede tamanho maximo")
    if _TEMPLATE.fullmatch(template) is None:
        raise InsightRenderError("invalid_template", "sintaxe de placeholder invalida")


def _facts_by_key(facts: tuple[InsightFact, ...]) -> dict[str, InsightFact]:
    result: dict[str, InsightFact] = {}
    for fact in facts:
        if fact.key in result:
            raise InsightRenderError("duplicate_fact_key", f"fact duplicado: {fact.key}")
        result[fact.key] = fact
    return result


def _render_value(value: str | int | float) -> str:
    if isinstance(value, float):
        if not math.isfinite(value):
            raise InsightRenderError("invalid_fact_value", "float nao finito")
        return repr(value)
    return str(value)
