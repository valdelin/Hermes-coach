"""POL-1 — Advisory operacional para Form relativo.

Esta camada interpreta um `form_pct` JA DERIVADO por PMC-1. Ela nao conhece
provider, snapshot, CTL/ATL/TSB, readiness ou plano: recebe somente o valor e
um threshold configuravel. O resultado e advisory, nunca prescricao.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Optional


# Default operacional/advisory, nao verdade fisiologica nem regra de deload.
DEFAULT_FORM_ADVISORY_THRESHOLD = -30.0


class FormAdvisoryStatus(str, Enum):
    UNAVAILABLE = "unavailable"
    NORMAL = "normal"
    HIGH_NEGATIVE_FORM = "high_negative_form"


@dataclass(frozen=True)
class FormAdvisory:
    """Resultado de policy advisory, sem qualquer acao sobre o treino."""

    status: FormAdvisoryStatus
    form_pct: Optional[float]
    threshold: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data


def validate_form_advisory_threshold(threshold: Any) -> float:
    """Valida threshold configurado: finito e estritamente negativo.

    A policy se chama *high negative form*: zero/positivo inverteria a
    semantica e tornaria resultados normais advisory por acidente. A excecao e
    deliberada, em vez de aceitar configuracao absurda silenciosamente.
    """
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("form advisory threshold deve ser numero negativo finito")
    value = float(threshold)
    if not math.isfinite(value) or value >= 0:
        raise ValueError("form advisory threshold deve ser numero negativo finito")
    return value


def _form_pct(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    return numeric if math.isfinite(numeric) else None


def evaluate_form_advisory(
    form_pct: Any,
    *,
    threshold: Any = DEFAULT_FORM_ADVISORY_THRESHOLD,
) -> FormAdvisory:
    """Interpreta Form relativo sem recalcular, aconselhar ou prescrever.

    Regra minima de POL-1:
      - sem `form_pct` valido -> UNAVAILABLE;
      - `form_pct <= threshold` -> HIGH_NEGATIVE_FORM;
      - caso contrario -> NORMAL.

    A mensagem e deliberadamente neutra: consumidor decide como apresentar e
    qualquer decisao sobre treino pertence a uma policy composta futura.
    """
    configured = validate_form_advisory_threshold(threshold)
    value = _form_pct(form_pct)
    if value is None:
        return FormAdvisory(
            FormAdvisoryStatus.UNAVAILABLE, None, configured,
            "Form relativo indisponivel; advisory nao avaliado.")
    if value <= configured:
        return FormAdvisory(
            FormAdvisoryStatus.HIGH_NEGATIVE_FORM, value, configured,
            "Form relativo atingiu o limiar advisory configurado.")
    return FormAdvisory(
        FormAdvisoryStatus.NORMAL, value, configured,
        "Form relativo nao atingiu o limiar advisory configurado.")
