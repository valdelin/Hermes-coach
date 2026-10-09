"""HR-1 — Advisory opt-in para velocidade de mudanca de CTL.

Recebe apenas uma taxa ja derivada e um limite explicitamente configurado. Nao
conhece CTL historico, provider, snapshot, readiness ou plano.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Optional


class CtlRampAdvisoryStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    WITHIN_ADVISORY_RANGE = "within_advisory_range"
    HIGH_RAMP = "high_ramp"


@dataclass(frozen=True)
class CtlRampAdvisory:
    """Resultado advisory-only para uma taxa de CTL observada."""

    status: CtlRampAdvisoryStatus
    ramp_rate: Optional[float]
    max_ramp_points: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


def validate_max_ramp_points(value: Any) -> float:
    """Limite configurado deve ser numero finito e nao-negativo.

    HR-1 nao estabelece default: nao ha limiar absoluto documentado no projeto
    que seja defensavel para todos os niveis de CTL. O chamador deve injetar a
    configuracao operacional/advisory de seu contexto.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("max_ramp_points deve ser numero finito nao-negativo")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("max_ramp_points deve ser numero finito nao-negativo")
    return number


def _rate(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def evaluate_ctl_ramp_advisory(ramp_rate: Any, *,
                               max_ramp_points: Any) -> CtlRampAdvisory:
    """Interpreta uma taxa ja derivada, sem alterar treino ou readiness.

    `ramp_rate >= max_ramp_points` produz HIGH_RAMP. Taxas negativas ficam
    dentro da faixa; nenhuma acao e inferida delas. A mensagem e neutra e a
    unidade do limite e a mesma da metrica: pontos de CTL por janela.
    """
    limit = validate_max_ramp_points(max_ramp_points)
    rate = _rate(ramp_rate)
    if rate is None:
        return CtlRampAdvisory(
            CtlRampAdvisoryStatus.UNAVAILABLE, None, limit,
            "CTL ramp rate indisponivel; advisory nao avaliado.")
    if rate >= limit:
        return CtlRampAdvisory(
            CtlRampAdvisoryStatus.HIGH_RAMP, rate, limit,
            "CTL ramp rate atingiu o limite advisory configurado.")
    return CtlRampAdvisory(
        CtlRampAdvisoryStatus.WITHIN_ADVISORY_RANGE, rate, limit,
        "CTL ramp rate esta dentro do limite advisory configurado.")
