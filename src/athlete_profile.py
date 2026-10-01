"""Perfil fisiológico explícito; marcadores ausentes permanecem desconhecidos."""
from dataclasses import dataclass
from enum import Enum


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
