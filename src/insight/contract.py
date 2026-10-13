"""Contrato offline e read-only do INSIGHT M1 v2.

Os tipos deste modulo carregam somente estado upstream ja resolvido. Eles nao
leem ambiente, nao chamam providers e nao participam de Prescription. Grounding
numerico e renderer/fallback sao decisoes posteriores (INSIGHT-2).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class FactClassification(str, Enum):
    """Autoridade declarada de um fato recebido pelo insight."""

    OBSERVED = "observed"
    DERIVED = "derived"
    HEURISTIC = "heuristic"
    ADVICE = "advice"
    PRESCRIPTION = "prescription"


class ObservationAvailability(str, Enum):
    """Disponibilidade factual de execucao, sem inferir a partir do planejado."""

    OBSERVED = "observed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class InsightFact:
    """Fato estruturado, sem promocao de autoridade ou interpretacao propria."""

    key: str
    value: str | int | float
    classification: FactClassification
    unit: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.key, str) or not self.key.strip():
            raise ValueError("key deve ser texto nao vazio")
        if isinstance(self.value, bool) or not isinstance(self.value, (str, int, float)):
            raise ValueError("value deve ser str, int ou float")
        if self.unit is not None and (not isinstance(self.unit, str) or not self.unit.strip()):
            raise ValueError("unit deve ser None ou texto nao vazio")
        try:
            object.__setattr__(self, "classification", FactClassification(self.classification))
        except (TypeError, ValueError) as exc:
            raise ValueError("classification invalida") from exc


@dataclass(frozen=True)
class InsightAdvisory:
    """Advice upstream já produzido; o contrato nao o deriva nem altera."""

    text: str

    def __post_init__(self) -> None:
        _require_text(self.text, "advisory.text", 1, 2000)


@dataclass(frozen=True)
class PrescribedSessionSummary:
    """Identificacao textual da sessao planejada, distinta de execucao observada."""

    summary: str

    def __post_init__(self) -> None:
        _require_text(self.summary, "prescribed_session.summary", 1, 1000)


@dataclass(frozen=True)
class ObservedExecution:
    """Evidencia observada ou indisponivel; planejado nunca implica observado."""

    availability: ObservationAvailability
    summary: Optional[str] = None

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "availability", ObservationAvailability(self.availability))
        except (TypeError, ValueError) as exc:
            raise ValueError("availability invalida") from exc
        if self.summary is not None:
            _require_text(self.summary, "observed_execution.summary", 1, 1000)
        if self.availability is ObservationAvailability.UNAVAILABLE and self.summary is not None:
            raise ValueError("execucao indisponivel nao possui summary")


@dataclass(frozen=True)
class InsightSource:
    """Proveniencia declarada, sem payload bruto de provider."""

    name: str

    def __post_init__(self) -> None:
        _require_text(self.name, "source.name", 1, 200)


@dataclass(frozen=True)
class InsightView:
    """Input read-only do insight, composto pela Application em etapa futura."""

    schema_version: int
    subject: str
    facts: tuple[InsightFact, ...] = ()
    advisory: Optional[InsightAdvisory] = None
    prescribed_session: Optional[PrescribedSessionSummary] = None
    observed_execution: Optional[ObservedExecution] = None
    provenance: tuple[InsightSource, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, int) or isinstance(self.schema_version, bool) or self.schema_version < 1:
            raise ValueError("schema_version deve ser inteiro positivo")
        _require_text(self.subject, "subject", 1, 200)
        if not isinstance(self.facts, tuple) or not all(isinstance(item, InsightFact) for item in self.facts):
            raise ValueError("facts deve ser tuple de InsightFact")
        if self.advisory is not None and not isinstance(self.advisory, InsightAdvisory):
            raise ValueError("advisory deve ser InsightAdvisory ou None")
        if self.prescribed_session is not None and not isinstance(self.prescribed_session, PrescribedSessionSummary):
            raise ValueError("prescribed_session invalida")
        if self.observed_execution is not None and not isinstance(self.observed_execution, ObservedExecution):
            raise ValueError("observed_execution invalida")
        if not isinstance(self.provenance, tuple) or not all(isinstance(item, InsightSource) for item in self.provenance):
            raise ValueError("provenance deve ser tuple de InsightSource")


@dataclass(frozen=True)
class InsightPresentation:
    """Saida textual sem campos de Prescription ou qualquer acao mutavel."""

    headline: str
    explanation: str
    next_action_text: str
    caution_text: Optional[str] = None

    def __post_init__(self) -> None:
        _validate_presentation_values(
            self.headline, self.explanation, self.next_action_text, self.caution_text)


_PRESENTATION_FIELDS = frozenset({
    "headline", "explanation", "next_action_text", "caution_text",
})


def validate_presentation_payload(payload: Any) -> tuple[str, ...]:
    """Valida o schema fechado sem reparar payload invalido."""
    if not isinstance(payload, dict):
        return ("payload deve ser objeto",)
    errors: list[str] = []
    missing = sorted(_PRESENTATION_FIELDS - payload.keys())
    extra = sorted(payload.keys() - _PRESENTATION_FIELDS)
    errors.extend(f"campo obrigatorio ausente: {name}" for name in missing)
    errors.extend(f"campo extra: {name}" for name in extra)
    if errors:
        return tuple(errors)
    try:
        _validate_presentation_values(
            payload["headline"], payload["explanation"],
            payload["next_action_text"], payload["caution_text"])
    except ValueError as exc:
        return (str(exc),)
    return ()


def _validate_presentation_values(
        headline: Any, explanation: Any, next_action_text: Any,
        caution_text: Any,
) -> None:
    _require_text(headline, "headline", 1, 240)
    _require_text(explanation, "explanation", 1, 2000)
    _require_text(next_action_text, "next_action_text", 1, 1000)
    if caution_text is not None:
        _require_text(caution_text, "caution_text", 1, 1000)


def _require_text(value: Any, name: str, minimum: int, maximum: int) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{name} deve ser texto")
    if not value.strip():
        raise ValueError(f"{name} nao pode ser vazio")
    if not minimum <= len(value) <= maximum:
        raise ValueError(f"{name} deve ter entre {minimum} e {maximum} caracteres")
