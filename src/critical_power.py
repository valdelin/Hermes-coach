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
