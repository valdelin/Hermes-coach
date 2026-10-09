"""Perfil fisiológico explícito; marcadores ausentes permanecem desconhecidos."""
from dataclasses import dataclass
from enum import Enum

try:
    from .critical_power import CPConfidence, CPProtocol
    from .ftp_history import FtpReferenceSource
except ImportError:  # execucao direta por application no modo script
    from critical_power import CPConfidence, CPProtocol
    from ftp_history import FtpReferenceSource


class FtpSource(str, Enum):
    USER = "user"
    FTP20 = "ftp20"
    FTP60 = "ftp60"
    RAMP = "ramp"
    CP_ESTIMATE = "cp_estimate"
    PERFORMANCE_ESTIMATE = "performance_estimate"
    CONFIRMED = "confirmed"


class FtpConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class AthletePhysiologicalProfile:
    ftp: float | None = None
    ftp_source: FtpSource | None = None
    ftp_confidence: FtpConfidence | None = None
    critical_power: float | None = None
    w_prime: float | None = None
    vo2max: float | None = None
    max_hr: int | None = None
    threshold_hr: int | None = None
    resting_hr: int | None = None
    hrv_baseline: float | None = None
    weekly_training_hours: float | None = None
    training_days: tuple[int, ...] = ()
    training_age: float | None = None
    preferred_long_day: int | None = None
    cp_protocol: CPProtocol | None = None
    cp_source: str | None = None
    cp_model: str | None = None
    cp_n_efforts: int | None = None
    cp_min_duration_sec: float | None = None
    cp_max_duration_sec: float | None = None
    cp_duration_span_sec: float | None = None
    cp_fit_r2: float | None = None
    cp_fit_rmse: float | None = None
    cp_confidence: CPConfidence | None = None
    w_prime_confidence: CPConfidence | None = None
    cp_test_dates: tuple[str, ...] = ()
    cp_last_updated: str | None = None


def ftp_source_from_reference(source: FtpReferenceSource | str) -> FtpSource:
    """Projeta a origem de uma `FtpReference` confirmada em `FtpSource`.

    So ha dois destados honestos neste enum: `USER_ENTERED` preserva a
    granularidade ja coberta por `USER`; qualquer outra origem
    (`HERMES_TEST`, `ZWIFT_TEST`, `OTHER_PLATFORM_TEST`, `COACH_DEFINED` ou
    uma futura) vira `CONFIRMED`, porque mapea-la para `RAMP`/`FTP20`/`USER`
    misturaria protocolo ou autoria com origem. Granularidade completa
    continua em `FtpReference.source`/`protocol`; o profile carrega apenas a
    dimensao que consegue declarar sem mentir.
    """
    value = getattr(source, "value", source)
    if value == FtpReferenceSource.USER_ENTERED.value:
        return FtpSource.USER
    return FtpSource.CONFIRMED


def build_athlete_profile(
        *, canonical_ftp: float | None = None,
        canonical_source: FtpReferenceSource | str | None = None,
        threshold_hr: int | None = None,
        weekly_training_hours: float | None = None,
        training_days: tuple[int, ...] = (),
        preferred_long_day: int | None = None,
        resting_hr: int | float | None = None,
) -> AthletePhysiologicalProfile:
    """Monta o contexto fisiologico/configurado conhecido em runtime.

    Esta e uma View, nao policy nem prescricao. `canonical_ftp` chega ja
    resolvido pela Application a partir de `FtpHistory.resolve_ftp_at`; esta
    funcao nao conhece repository, relogio nem `.env`. Ausencia fica
    ``None``; nunca se usa fallback operacional de FTP, estimativa de VO2,
    CP/W' ou uma segunda baseline de HRV. Sem origem declarada ao lado de um
    `canonical_ftp`, a origem declarada e `CONFIRMED` — o proprio contrato de
    entrada ja diz que o valor foi confirmado. `ftp_confidence` permanece
    ``None`` sempre: confirmacao do usuario e estado canonico, nao qualidade
    cientifica medida.
    """
    if canonical_ftp is None:
        ftp_source = None
    elif canonical_source is None:
        ftp_source = FtpSource.CONFIRMED
    else:
        ftp_source = ftp_source_from_reference(canonical_source)
    return AthletePhysiologicalProfile(
        ftp=canonical_ftp,
        ftp_source=ftp_source,
        ftp_confidence=None,
        threshold_hr=threshold_hr,
        resting_hr=resting_hr,
        weekly_training_hours=weekly_training_hours,
        training_days=tuple(training_days),
        preferred_long_day=preferred_long_day,
    )
