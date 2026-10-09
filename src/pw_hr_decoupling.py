"""Pw:HR observacional sobre streams temporais ja normalizados (HR-2)."""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Optional, Sequence

try:
    from provider import ActivityStream, ActivityStreamPoint
except ImportError:  # execucao como pacote (src.pw_hr_decoupling)
    from .provider import ActivityStream, ActivityStreamPoint  # type: ignore


NORMALIZED_POWER_WINDOW_SECONDS = 30
ELIGIBLE = "eligible"
NOT_ELIGIBLE = "not_eligible"
CALCULATED = "calculated"
UNAVAILABLE = "unavailable"
PHYSIOLOGICAL_CONTEXT_UNVERIFIED = "unverified"
METHODOLOGICAL_CONTEXT_UNVERIFIED = PHYSIOLOGICAL_CONTEXT_UNVERIFIED


@dataclass(frozen=True)
class PwHrEligibility:
    """Qualidade estrutural para o metodo computacional, nao fisiologia."""

    status: str
    reason: Optional[str]
    sample_count: int
    analyzed_duration_seconds: Optional[float]
    first_half: tuple[ActivityStreamPoint, ...] = ()
    second_half: tuple[ActivityStreamPoint, ...] = ()
    methodological_context: str = METHODOLOGICAL_CONTEXT_UNVERIFIED


@dataclass(frozen=True)
class PwHrHalf:
    """Sinais observados agregados em uma metade temporal."""

    normalized_power: float
    mean_heart_rate: float
    efficiency_factor: float


@dataclass(frozen=True)
class PwHrDerivedMetric:
    """Metrica Hermes derivada de duas metades ja elegiveis."""

    decoupling_pct: float
    first_half: PwHrHalf
    second_half: PwHrHalf


@dataclass(frozen=True)
class PwHrDecouplingView:
    """Resultado local: sinais sao observados; metrica e elegibilidade, Hermes."""

    provider: str
    activity_id: str
    status: str
    reason: Optional[str]
    decoupling_pct: Optional[float]
    first_half: Optional[PwHrHalf]
    second_half: Optional[PwHrHalf]
    sample_count: int
    analyzed_duration_seconds: Optional[float]
    computable: bool
    methodological_context: str
    captured_at: Optional[str]

    @property
    def physiological_context(self) -> str:
        """Alias de leitura para o campo introduzido em HR-2B."""
        return self.methodological_context

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def unavailable(cls, *, provider: str, activity_id: str) -> "PwHrDecouplingView":
        return cls(provider=provider, activity_id=activity_id, status=UNAVAILABLE,
                   reason="stream_not_cached", decoupling_pct=None,
                   first_half=None, second_half=None, sample_count=0,
                    analyzed_duration_seconds=None,
                   computable=False,
                   methodological_context=METHODOLOGICAL_CONTEXT_UNVERIFIED,
                   captured_at=None)


def _finite(value: object) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def evaluate_pw_hr_eligibility(stream: ActivityStream) -> PwHrEligibility:
    """Avalia somente requisitos estruturais do calculo Pw:HR.

    O algoritmo exige amostras contiguas de um segundo para calcular Normalized
    Power sem interpolar. Isso nao identifica um esforco aerobico estavel: o
    contexto fisiologico continua explicitamente nao verificado.
    """
    if stream.alignment != "aligned":
        return _not_eligible("stream_not_aligned", stream)
    if not stream.points:
        return _not_eligible("empty_stream", stream)

    indexed = list(enumerate(stream.points))
    normalized = []
    for index, point in indexed:
        elapsed = _finite(point.elapsed_seconds)
        if elapsed is None:
            return _not_eligible("invalid_elapsed_seconds", stream)
        normalized.append((elapsed, index, point))
    normalized.sort(key=lambda item: (item[0], item[1]))
    points = tuple(item[2] for item in normalized)
    elapsed = tuple(item[0] for item in normalized)

    if any(later == earlier for earlier, later in zip(elapsed, elapsed[1:])):
        return _not_eligible("duplicate_elapsed_seconds", stream)
    if any(later - earlier != 1.0 for earlier, later in zip(elapsed, elapsed[1:])):
        return _not_eligible("non_contiguous_one_second_samples", stream)
    if any(_finite(point.power) is None or _finite(point.heart_rate) is None
           for point in points):
        return _not_eligible("missing_joint_samples", stream)
    if any(_finite(point.power) < 0 or _finite(point.heart_rate) < 0
           for point in points):
        return _not_eligible("negative_observed_signal", stream)

    midpoint = (elapsed[0] + elapsed[-1]) / 2.0
    first_half = tuple(point for time, point in zip(elapsed, points)
                       if time <= midpoint)
    second_half = tuple(point for time, point in zip(elapsed, points)
                        if time > midpoint)
    if (len(first_half) < NORMALIZED_POWER_WINDOW_SECONDS or
            len(second_half) < NORMALIZED_POWER_WINDOW_SECONDS):
        return _not_eligible("insufficient_samples_for_normalized_power", stream)

    if _mean_heart_rate(first_half) is None or _mean_heart_rate(second_half) is None:
        return _not_eligible("zero_mean_heart_rate", stream)
    return PwHrEligibility(
        status=ELIGIBLE, reason=None, sample_count=len(points),
        analyzed_duration_seconds=elapsed[-1] - elapsed[0], first_half=first_half,
        second_half=second_half)


def _not_eligible(reason: str, stream: ActivityStream) -> PwHrEligibility:
    return PwHrEligibility(status=NOT_ELIGIBLE, reason=reason,
                           sample_count=len(stream.points),
                           analyzed_duration_seconds=None)


def _mean_heart_rate(points: Sequence[ActivityStreamPoint]) -> Optional[float]:
    values = [_finite(point.heart_rate) for point in points]
    if not values or any(value is None for value in values):
        return None
    mean = sum(values) / len(values)  # type: ignore[arg-type]
    return mean if mean > 0 else None


def _normalized_power(points: Sequence[ActivityStreamPoint]) -> Optional[float]:
    values = [_finite(point.power) for point in points]
    if len(values) < NORMALIZED_POWER_WINDOW_SECONDS or any(value is None for value in values):
        return None
    rolling = [sum(values[index - NORMALIZED_POWER_WINDOW_SECONDS + 1:index + 1]) /
               NORMALIZED_POWER_WINDOW_SECONDS
               for index in range(NORMALIZED_POWER_WINDOW_SECONDS - 1, len(values))]
    return (sum(value ** 4 for value in rolling) / len(rolling)) ** 0.25


def derive_pw_hr_decoupling(
    first_half: Sequence[ActivityStreamPoint], second_half: Sequence[ActivityStreamPoint],
) -> Optional[PwHrDerivedMetric]:
    """Deriva Pw:HR de metades previamente elegiveis, sem I/O ou policy.

    EF = Normalized Power / FC media; decoupling (%) =
    ((EF_primeira - EF_segunda) / EF_primeira) * 100.
    """
    first_power = _normalized_power(first_half)
    second_power = _normalized_power(second_half)
    first_hr = _mean_heart_rate(first_half)
    second_hr = _mean_heart_rate(second_half)
    if (first_power is None or second_power is None or first_hr is None or
            second_hr is None):
        return None
    first_ef = first_power / first_hr
    second_ef = second_power / second_hr
    if first_ef <= 0:
        return None
    return PwHrDerivedMetric(
        decoupling_pct=((first_ef - second_ef) / first_ef) * 100.0,
        first_half=PwHrHalf(first_power, first_hr, first_ef),
        second_half=PwHrHalf(second_power, second_hr, second_ef))


def build_pw_hr_decoupling_view(stream: ActivityStream) -> PwHrDecouplingView:
    """Combina eligibility e metrica para um stream local ja carregado."""
    eligibility = evaluate_pw_hr_eligibility(stream)
    if eligibility.status != ELIGIBLE:
        return PwHrDecouplingView(
            provider=stream.provider, activity_id=stream.activity_id,
            status=NOT_ELIGIBLE, reason=eligibility.reason, decoupling_pct=None,
            first_half=None, second_half=None, sample_count=eligibility.sample_count,
            analyzed_duration_seconds=eligibility.analyzed_duration_seconds,
            computable=False,
            methodological_context=eligibility.methodological_context,
            captured_at=stream.captured_at)
    metric = derive_pw_hr_decoupling(eligibility.first_half, eligibility.second_half)
    if metric is None:
        return PwHrDecouplingView(
            provider=stream.provider, activity_id=stream.activity_id,
            status=NOT_ELIGIBLE, reason="undefined_efficiency_factor",
            decoupling_pct=None, first_half=None, second_half=None,
            sample_count=eligibility.sample_count,
            analyzed_duration_seconds=eligibility.analyzed_duration_seconds,
            computable=False,
            methodological_context=eligibility.methodological_context,
            captured_at=stream.captured_at)
    return PwHrDecouplingView(
        provider=stream.provider, activity_id=stream.activity_id, status=CALCULATED,
        reason=None, decoupling_pct=metric.decoupling_pct,
        first_half=metric.first_half, second_half=metric.second_half,
        sample_count=eligibility.sample_count,
        analyzed_duration_seconds=eligibility.analyzed_duration_seconds,
        computable=True,
        methodological_context=eligibility.methodological_context,
        captured_at=stream.captured_at)
