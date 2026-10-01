"""Distribuição de intensidade por tempo efetivo, independente da periodização."""
from dataclasses import dataclass
from enum import Enum


class IntensityDistributionModel(str, Enum):
    POLARIZED = "polarized"
    PYRAMIDAL = "pyramidal"
    THRESHOLD_HEAVY = "threshold_heavy"
    CUSTOM = "custom"


@dataclass(frozen=True)
class IntensityMinutes:
    low: float = 0
    moderate: float = 0
    high: float = 0

    @property
    def total(self):
        return self.low + self.moderate + self.high

    def __add__(self, other):
        return IntensityMinutes(self.low + other.low, self.moderate + other.moderate,
                                self.high + other.high)


@dataclass(frozen=True)
class WeeklyIntensityReport:
    minutes: IntensityMinutes

    @property
    def percentages(self):
        total = self.minutes.total
        if not total:
            return {"low": 0, "moderate": 0, "high": 0}
        return {"low": self.minutes.low / total * 100,
                "moderate": self.minutes.moderate / total * 100,
                "high": self.minutes.high / total * 100}


class IntensityDistributionEngine:
    """Agrega minutos reais; modelos são rótulos, não proporções prescritas."""
    def __init__(self, model=IntensityDistributionModel.CUSTOM, custom=None):
        self.model = IntensityDistributionModel(model)
        self.custom = custom

    def weekly_report(self, sessions):
        total = IntensityMinutes()
        for session in sessions:
            total += session
        return WeeklyIntensityReport(total)
