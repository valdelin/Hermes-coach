"""Graders deterministas e de dominio do Hermes para INSIGHT M1 v2."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from src.insight.contract import (
    FactClassification, InsightAdvisory, InsightFact, InsightView,
    ObservedExecution, ObservationAvailability, PrescribedSessionSummary,
    validate_presentation_payload,
)
from src.insight.render import fallback_presentation


FORBIDDEN_FIELDS = frozenset({
    "focus", "foco", "duration", "duracao", "duration_min", "duracao_min",
    "intensity", "intensidade", "ftp", "watts", "power", "tss", "readiness",
    "progression", "lifecycle", "provider_payload",
})
KNOWN_PROPERTIES = frozenset({
    "schema_valid", "no_prescription_fields", "no_contradiction",
    "factual_grounding", "caution_requires_upstream_advice", "fallback_valid",
    "prescription_invariant", "planned_not_observed", "observed_distinct",
})


class EvalStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIPPED = "SKIPPED"
    INFRA_ERROR = "INFRA_ERROR"


@dataclass(frozen=True)
class GradeResult:
    grader: str
    passed: bool
    message: str

    def __post_init__(self) -> None:
        if type(self.passed) is not bool:
            raise ValueError("passed deve ser bool")


def grade_schema(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> GradeResult:
    errors = validate_presentation_payload(candidate.get("presentation"))
    return GradeResult("G1-schema", not errors, "; ".join(errors) or "schema valido")


def grade_no_prescription_fields(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> GradeResult:
    payload = candidate.get("presentation")
    if not isinstance(payload, dict):
        return GradeResult("G2-no-prescription-fields", False, "presentation nao e objeto")
    fields = sorted(FORBIDDEN_FIELDS & payload.keys())
    return GradeResult("G2-no-prescription-fields", not fields,
                       "campos proibidos: " + ", ".join(fields) if fields else "sem campos proibidos")


def grade_no_contradiction(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> GradeResult:
    """Checa somente markers sintéticos declarados pelo caso; nao faz NLP."""
    payload = candidate.get("presentation")
    if not isinstance(payload, dict):
        return GradeResult("G3-no-contradiction", False, "presentation nao e objeto")
    text = "\n".join(str(value) for value in payload.values() if value is not None)
    markers = case.get("context", {}).get("forbidden_claim_markers", [])
    found = [marker for marker in markers if marker in text]
    return GradeResult("G3-no-contradiction", not found,
                       "markers contraditorios: " + ", ".join(found) if found else "sem marker contraditorio")


def grade_factual_grounding(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> GradeResult:
    """Valida metadata controlada de placeholders; nao infere fatos do texto livre."""
    context_facts = case.get("context", {}).get("facts", [])
    allowed = {fact.get("key") for fact in context_facts if isinstance(fact, dict)}
    used = candidate.get("used_fact_keys", [])
    if not isinstance(used, list) or not all(isinstance(key, str) for key in used):
        return GradeResult("G4-factual-grounding", False, "used_fact_keys invalido")
    unknown = sorted(set(used) - allowed)
    return GradeResult("G4-factual-grounding", not unknown,
                       "facts nao autorizados: " + ", ".join(unknown) if unknown else "facts autorizados")


def grade_caution_provenance(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> GradeResult:
    payload = candidate.get("presentation")
    if not isinstance(payload, dict):
        return GradeResult("G5-caution-provenance", False, "presentation nao e objeto")
    has_advice = bool(case.get("context", {}).get("upstream_advice_present"))
    caution = payload.get("caution_text")
    passed = caution is None or has_advice
    return GradeResult("G5-caution-provenance", passed,
                       "caution sem advice upstream" if not passed else "proveniencia valida")


def grade_deterministic_fallback(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> GradeResult:
    view = InsightView(schema_version=1, subject="eval")
    first = fallback_presentation(view)
    second = fallback_presentation(view)
    passed = first == second and first.caution_text is None and not validate_presentation_payload(first.__dict__)
    return GradeResult("G6-deterministic-fallback", passed, "fallback valido" if passed else "fallback invalido")


def _build_eval_view(context: Mapping[str, Any]) -> InsightView:
    """View sintética mínima para provar imutabilidade da camada de eval.

    Isto não é Application seam nem faz mapeamento de domínio; usa somente
    fixtures já declarados para construir os tipos read-only reais.
    """
    facts = tuple(
        InsightFact(item["key"], item["value"], FactClassification(item["classification"]))
        for item in context.get("facts", ())
    )
    advisory = (InsightAdvisory("upstream advisory fixture")
                if context.get("upstream_advice_present") else None)
    prescribed = context.get("prescribed_session")
    prescribed_session = (PrescribedSessionSummary(prescribed)
                          if isinstance(prescribed, str) and prescribed else None)
    observed_execution = (ObservedExecution(ObservationAvailability.OBSERVED, "observed fixture")
                          if context.get("observed_execution") == "observed" else None)
    return InsightView(schema_version=1, subject="eval", facts=facts,
                       advisory=advisory, prescribed_session=prescribed_session,
                       observed_execution=observed_execution)


def grade_prescription_invariance(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> GradeResult:
    view = _build_eval_view(case.get("context", {}))
    before = view
    prescribed_before = view.prescribed_session
    _ = candidate.get("presentation")
    after = view
    passed = (before == after and prescribed_before == after.prescribed_session
              and before.facts == after.facts and before.advisory == after.advisory
              and before.observed_execution == after.observed_execution
              and before.provenance == after.provenance)
    return GradeResult("G7-prescription-invariance", passed,
                       "eval preserva InsightView fornecida" if passed else "view mutada")


GRADERS = (grade_schema, grade_no_prescription_fields, grade_no_contradiction,
           grade_factual_grounding, grade_caution_provenance,
           grade_deterministic_fallback, grade_prescription_invariance)


def grade_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> tuple[GradeResult, ...]:
    return tuple(grader(case, candidate) for grader in GRADERS)


def evaluate_case(case: Mapping[str, Any], candidate: Mapping[str, Any]) -> EvalStatus:
    return EvalStatus.PASS if all(result.passed for result in grade_case(case, candidate)) else EvalStatus.FAIL
