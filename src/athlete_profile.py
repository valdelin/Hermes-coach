"""Perfil fisiológico explícito; marcadores ausentes permanecem desconhecidos."""
from dataclasses import dataclass
from enum import Enum

from .critical_power import CPConfidence, CPProtocol


class FtpSource(str, Enum):
    USER = "user"
    FTP20 = "ftp20"
    FTP60 = "ftp60"
    RAMP = "ramp"
    CP_ESTIMATE = "cp_estimate"
    PERFORMANCE_ESTIMATE = "performance_estimate"


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
