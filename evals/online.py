"""Runner online controlado do INSIGHT M2-7, sem payloads ou segredos no report."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Mapping, Optional, Sequence

from evals.graders import (EvalStatus, GradeResult, _build_eval_view,
                           evaluate_case, grade_case)
from src.insight.model_provider import InsightModelProvider
from src.insight.request_builder import INSIGHT_PROMPT_VERSION
from src.insight.runtime import InsightRuntimeStatus, run_insight_runtime
from src.insight.telemetry import InMemoryInsightTelemetrySink, InsightRuntimeTelemetry


ONLINE_MODEL = "gpt-5.4-nano-2026-03-17"
_TelemetryClock = Callable[[], Decimal]


@dataclass(frozen=True)
class OnlineEvalCaseResult:
    """Resultado seguro de um caso; nunca retém View, prompt, response ou exceção."""

    case_id: str
    status: EvalStatus
    runtime_status: Optional[InsightRuntimeStatus]
    grades: tuple[GradeResult, ...] = ()
    telemetry: Optional[InsightRuntimeTelemetry] = None
    reason: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.case_id, str) or not self.case_id.strip():
            raise ValueError("case_id deve ser texto nao vazio")
        if not isinstance(self.status, EvalStatus):
            raise ValueError("status deve ser EvalStatus")
        if self.runtime_status is not None and not isinstance(
                self.runtime_status, InsightRuntimeStatus):
            raise ValueError("runtime_status invalido")
        if not isinstance(self.grades, tuple) or not all(
                isinstance(grade, GradeResult) for grade in self.grades):
            raise ValueError("grades deve ser tuple de GradeResult")
        if self.telemetry is not None and not isinstance(
                self.telemetry, InsightRuntimeTelemetry):
            raise ValueError("telemetry invalida")
        if self.reason is not None and (not isinstance(self.reason, str)
                                        or not self.reason.strip()):
            raise ValueError("reason deve ser texto nao vazio ou None")

    def to_safe_dict(self) -> dict[str, object]:
        """Serializa somente scalars seguros e grades determinísticos."""
        payload: dict[str, object] = {
            "case_id": self.case_id,
            "status": self.status.value,
            "runtime_status": (
                None if self.runtime_status is None else self.runtime_status.value),
            "grades": [
                {"grader": grade.grader, "passed": grade.passed,
                 "message": grade.message}
                for grade in self.grades
            ],
            "reason": self.reason,
            "telemetry": _safe_telemetry(self.telemetry),
        }
        return payload


@dataclass(frozen=True)
class OnlineEvalReport:
    """Agregado fechado de um run online; custos desconhecidos seguem explícitos."""

    status: EvalStatus
    cases: tuple[OnlineEvalCaseResult, ...]
    pass_count: int
    fail_count: int
    skipped_count: int
    infra_error_count: int
    known_cost_usd: Decimal
    known_cost_case_count: int
    unknown_cost_case_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.status, EvalStatus):
            raise ValueError("status deve ser EvalStatus")
        if not isinstance(self.cases, tuple) or not all(
                isinstance(case, OnlineEvalCaseResult) for case in self.cases):
            raise ValueError("cases deve ser tuple de OnlineEvalCaseResult")
        counts = (self.pass_count, self.fail_count, self.skipped_count,
                  self.infra_error_count, self.known_cost_case_count,
                  self.unknown_cost_case_count)
        if any(type(value) is not int or value < 0 for value in counts):
            raise ValueError("contagens devem ser inteiros nao negativos")
        if self.pass_count + self.fail_count + self.skipped_count + self.infra_error_count != len(self.cases):
            raise ValueError("contagens de status inconsistentes")
        if self.known_cost_case_count + self.unknown_cost_case_count != len(self.cases):
            raise ValueError("contagens de custo inconsistentes")
        if (not isinstance(self.known_cost_usd, Decimal)
                or not self.known_cost_usd.is_finite()
                or self.known_cost_usd < 0):
            raise ValueError("known_cost_usd deve ser Decimal finito nao negativo")

    @property
    def cost_complete(self) -> bool:
        return self.unknown_cost_case_count == 0

    def to_safe_dict(self) -> dict[str, object]:
        return {
            "status": self.status.value,
            "counts": {
                "PASS": self.pass_count,
                "FAIL": self.fail_count,
                "SKIPPED": self.skipped_count,
                "INFRA_ERROR": self.infra_error_count,
            },
            "cost": {
                "known_cost_usd": str(self.known_cost_usd),
                "known_cost_case_count": self.known_cost_case_count,
                "unknown_cost_case_count": self.unknown_cost_case_count,
                "complete": self.cost_complete,
            },
            "cases": [case.to_safe_dict() for case in self.cases],
        }


def run_online_evaluation(
        cases: Sequence[Mapping[str, Any]],
        *,
        provider: InsightModelProvider,
        executed_at: datetime,
        telemetry_clock: Optional[_TelemetryClock] = None,
) -> OnlineEvalReport:
    """Executa no máximo uma inferência por caso pelo runtime canônico.

    Os fixtures ``candidate``/``expected_status`` pertencem ao auto-teste offline.
    Aqui somente ``context`` gera a View; o status vem do resultado real do
    runtime e dos graders Hermes sobre a Presentation local resultante.
    """
    results: list[OnlineEvalCaseResult] = []
    for case in cases:
        results.append(_run_case(
            case, provider=provider, executed_at=executed_at,
            telemetry_clock=telemetry_clock))
    return _build_report(tuple(results))


def skipped_online_evaluation(
        cases: Sequence[Mapping[str, Any]], *, reason: str,
) -> OnlineEvalReport:
    """Materializa skip explícito sem construir provider nem fazer rede."""
    results = tuple(OnlineEvalCaseResult(
        case_id=_case_id(case),
        status=EvalStatus.SKIPPED,
        runtime_status=None,
        reason=reason,
    ) for case in cases)
    return _build_report(results)


def _run_case(
        case: Mapping[str, Any],
        *,
        provider: InsightModelProvider,
        executed_at: datetime,
        telemetry_clock: Optional[_TelemetryClock],
) -> OnlineEvalCaseResult:
    if not _fixture_matches_expected_status(case):
        return OnlineEvalCaseResult(
            case_id=_case_id(case), status=EvalStatus.INFRA_ERROR,
            runtime_status=None, reason="offline_fixture_inconsistent")
    view = _build_eval_view(case.get("context", {}))
    sink = InMemoryInsightTelemetrySink()
    result = run_insight_runtime(
        view,
        provider=provider,
        requested_model=ONLINE_MODEL,
        prompt_version=INSIGHT_PROMPT_VERSION,
        executed_at=executed_at,
        telemetry=sink,
        telemetry_clock=telemetry_clock,
    )
    telemetry = sink.events[0] if sink.events else None
    if result.status in (
            InsightRuntimeStatus.FALLBACK_PROVIDER,
            InsightRuntimeStatus.FALLBACK_INTERNAL):
        return OnlineEvalCaseResult(
            case_id=_case_id(case), status=EvalStatus.INFRA_ERROR,
            runtime_status=result.status, telemetry=telemetry,
            reason="provider_infrastructure_failure")
    if result.status is not InsightRuntimeStatus.SUCCESS:
        return OnlineEvalCaseResult(
            case_id=_case_id(case), status=EvalStatus.FAIL,
            runtime_status=result.status, telemetry=telemetry,
            reason="model_contract_failure")
    candidate = {
        "presentation": {
            "headline": result.presentation.headline,
            "explanation": result.presentation.explanation,
            "next_action_text": result.presentation.next_action_text,
            "caution_text": result.presentation.caution_text,
        },
        # M2-2 já validou os placeholders contra a View antes do render local.
        "used_fact_keys": [],
    }
    grades = grade_case(case, candidate)
    status = EvalStatus.PASS if all(grade.passed for grade in grades) else EvalStatus.FAIL
    return OnlineEvalCaseResult(
        case_id=_case_id(case), status=status,
        runtime_status=result.status, grades=grades, telemetry=telemetry,
        reason=None if status is EvalStatus.PASS else "domain_grader_failure")


def _build_report(results: tuple[OnlineEvalCaseResult, ...]) -> OnlineEvalReport:
    counts = {status: sum(case.status is status for case in results) for status in EvalStatus}
    known_costs = [
        case.telemetry.estimated_cost_usd
        for case in results
        if case.telemetry is not None and case.telemetry.estimated_cost_usd is not None
    ]
    if counts[EvalStatus.FAIL]:
        status = EvalStatus.FAIL
    elif counts[EvalStatus.INFRA_ERROR]:
        status = EvalStatus.INFRA_ERROR
    elif counts[EvalStatus.PASS]:
        status = EvalStatus.PASS
    else:
        status = EvalStatus.SKIPPED
    return OnlineEvalReport(
        status=status,
        cases=results,
        pass_count=counts[EvalStatus.PASS],
        fail_count=counts[EvalStatus.FAIL],
        skipped_count=counts[EvalStatus.SKIPPED],
        infra_error_count=counts[EvalStatus.INFRA_ERROR],
        known_cost_usd=sum(known_costs, Decimal("0")),
        known_cost_case_count=len(known_costs),
        unknown_cost_case_count=len(results) - len(known_costs),
    )


def _case_id(case: Mapping[str, Any]) -> str:
    value = case.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError("caso de eval sem id seguro")
    return value


def _fixture_matches_expected_status(case: Mapping[str, Any]) -> bool:
    """Confere G1–G7 no fixture Hermes antes da inferência não determinística."""
    expected = case.get("expected_status")
    candidate = case.get("candidate")
    if not isinstance(expected, str) or not isinstance(candidate, Mapping):
        return False
    try:
        return evaluate_case(case, candidate).value == expected
    except (TypeError, ValueError):
        return False


def _safe_telemetry(telemetry: Optional[InsightRuntimeTelemetry]) -> Optional[dict[str, object]]:
    if telemetry is None:
        return None
    usage = telemetry.usage
    return {
        "provider": telemetry.provider,
        "requested_model": telemetry.requested_model,
        "resolved_model": telemetry.resolved_model,
        "request_id": telemetry.request_id,
        "runtime_status": telemetry.status.value,
        "usage": None if usage is None else {
            "input_tokens": usage.input_tokens,
            "output_tokens": usage.output_tokens,
            "cached_input_tokens": usage.cached_input_tokens,
        },
        "estimated_cost_usd": (
            None if telemetry.estimated_cost_usd is None
            else str(telemetry.estimated_cost_usd)),
        "currency": telemetry.currency,
        "pricing_source": telemetry.pricing_source,
        "latency_seconds": (
            None if telemetry.latency_seconds is None
            else str(telemetry.latency_seconds)),
    }
