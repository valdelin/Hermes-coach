"""Critical Power / W' como métricas complementares ao FTP.

CP e W' não equivalem a FTP, MLSS, LT ou RCP, e não substituem o FTP
automaticamente. Estimativas exigem dados suficientes; sem eles, o resultado
é `None`, nunca um chute.
"""
from dataclasses import dataclass, field
from enum import Enum


class CPConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CPProtocol(str, Enum):
    RAMP = "ramp"
    STEP = "step"
    MULTI_BROKEN = "multi_broken"
    FIELD_ESTIMATE = "field_estimate"


@dataclass(frozen=True)
class CriticalPowerProfile:
    critical_power: float | None = None
    w_prime: float | None = None
    protocol: CPProtocol | None = None
    confidence: CPConfidence | None = None
    test_dates: tuple[str, ...] = field(default_factory=tuple)
    source: str | None = None
    model: str | None = None
    n_efforts: int | None = None
    min_duration_sec: float | None = None
    max_duration_sec: float | None = None
    duration_span_sec: float | None = None
    fit_r2: float | None = None
    fit_rmse: float | None = None
    cp_confidence: CPConfidence | None = None
    w_prime_confidence: CPConfidence | None = None
    last_updated: str | None = None

    @property
    def known(self):
        return self.critical_power is not None and self.w_prime is not None


def _power_slope(points):
    """Regressão P = CP + W'/t sobre durações em segundos."""
    transformed = [(1 / t, p) for t, p in points if t > 0]
    if len(transformed) < 2:
        return None
    n = len(transformed)
    mean_x = sum(x for x, _ in transformed) / n
    mean_y = sum(y for _, y in transformed) / n
    denominator = sum((x - mean_x) ** 2 for x, _ in transformed)
    if denominator <= 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in transformed) / denominator
    intercept = mean_y - slope * mean_x
    if intercept <= 0:
        return None
    return intercept, slope


def estimate_cp(efforts):
    """CP em watts a partir de (duracao_sec, potencia_w). None sem dados."""
    fit = _power_slope(efforts)
    return fit[0] if fit else None


def estimate_w_prime(efforts):
    """W' em joules. None sem dados suficientes."""
    fit = _power_slope(efforts)
    return fit[1] if fit else None


def _fit_metrics(points, critical_power, w_prime):
    """R² e RMSE (watts) para P = CP + W'/t no espaco (1/t, P)."""
    transformed = [(1 / t, p) for t, p in points if t > 0]
    if not transformed:
        return None, None
    observed = [p for _, p in transformed]
    residual_sum = sum(
        (p - (critical_power + w_prime * inverse_duration)) ** 2
        for inverse_duration, p in transformed
    )
    rmse = (residual_sum / len(transformed)) ** 0.5
    mean_power = sum(observed) / len(observed)
    total_sum = sum((p - mean_power) ** 2 for p in observed)
    # R² e indefinido quando toda potencia observada e igual. Como o ajuste
    # valido reproduz esse caso exatamente, registramos 1.0 por convencao.
    r2 = 1.0 if total_sum == 0 else 1.0 - residual_sum / total_sum
    return r2, rmse


def _data_quality(points):
    """Metadados objetivos dos esforcos validos para a regressao."""
    durations = [t for t, _ in points if t > 0]
    if not durations:
        return None, None, None, None
    minimum = min(durations)
    maximum = max(durations)
    return len(durations), minimum, maximum, maximum - minimum


def _informative_confidence(n_efforts):
    """Politica conservadora da Fase 2, sem thresholds de qualidade inventados.

    Dois pontos distintos resolvem a reta e podem ter R² perfeito, mas recebem
    LOW. Com tres ou mais esforcos ainda nao ha criterio defensavel para elevar
    automaticamente MEDIUM/HIGH; ambos os parametros ficam LOW por enquanto.
    """
    if n_efforts is None or n_efforts < 2:
        return None, None
    return CPConfidence.LOW, CPConfidence.LOW


def estimate_cp_profile(efforts, protocol=None, source=None,
                        model="linear_1_over_t", test_dates=(),
                        last_updated=None):
    """Estima CP/W' e devolve metadados informativos, sem ativar prescricao.

    `confidence` legado permanece reservado ao valor fornecido por chamadores
    existentes. As confidences novas sao especificas de CP e W' e sao
    deliberadamente conservadoras nesta fase.
    """
    points = tuple(efforts)
    fit = _power_slope(points)
    n_efforts, minimum, maximum, span = _data_quality(points)
    if not fit:
        return CriticalPowerProfile(
            protocol=protocol,
            source=source,
            model=model,
            n_efforts=n_efforts,
            min_duration_sec=minimum,
            max_duration_sec=maximum,
            duration_span_sec=span,
            test_dates=tuple(test_dates),
            last_updated=last_updated,
        )
    critical_power, w_prime = fit
    fit_r2, fit_rmse = _fit_metrics(points, critical_power, w_prime)
    cp_confidence, w_prime_confidence = _informative_confidence(n_efforts)
    return CriticalPowerProfile(
        critical_power=critical_power,
        w_prime=w_prime,
        protocol=protocol,
        source=source,
        model=model,
        n_efforts=n_efforts,
        min_duration_sec=minimum,
        max_duration_sec=maximum,
        duration_span_sec=span,
        fit_r2=fit_r2,
        fit_rmse=fit_rmse,
        cp_confidence=cp_confidence,
        w_prime_confidence=w_prime_confidence,
        test_dates=tuple(test_dates),
        last_updated=last_updated,
    )


def work_above_cp(duration_sec, power, cp, w_prime):
    """Trabalho acima de CP em joules, limitado pelo W' disponível."""
    if not cp or not w_prime or power <= cp or duration_sec <= 0:
        return 0.0
    excess = power - cp
    return min(excess * duration_sec, w_prime)


def w_prime_balance(profile, work_above):
    """W' restante (joules) após consumir `work_above`."""
    if profile.w_prime is None:
        return None
    return max(0.0, profile.w_prime - work_above)


def w_prime_reconstitution(deficit, time_sec, rate=0.1):
    """Reconstitui o déficit de W' no ritmo configurado (W/s).

    O ritmo padrão de 0,1 W/s (~6 W por minuto) é uma heurística do sistema,
    não um valor fisiológico universal; deve ser ajustado por atleta.
    """
    if deficit <= 0 or time_sec <= 0:
        return 0.0
    return max(0.0, deficit - time_sec * rate)
