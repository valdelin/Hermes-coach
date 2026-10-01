"""Prontidão multimodal: suporte ao treino, não diagnóstico clínico."""
from dataclasses import dataclass
from enum import Enum


class ReadinessLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


@dataclass(frozen=True)
class ReadinessAssessment:
    hrv_score: float | None = None
    rhr_score: float | None = None
    sleep_score: float | None = None
    subjective_fatigue_score: float | None = None
    recent_load_score: float | None = None
    performance_score: float | None = None
    consistency_score: float | None = None

    @property
    def overall_readiness(self):
        values = [value for value in self.__dict__.values() if value is not None]
        return sum(values) / len(values) if values else None

    @property
    def confidence(self):
        return sum(value is not None for value in self.__dict__.values()) / 7

    def level(self):
        score = self.overall_readiness
        if score is None:
            return ReadinessLevel.YELLOW
        poor_signals = sum(value is not None and value < .4 for value in self.__dict__.values())
        if poor_signals >= 3 and score < .5:
            return ReadinessLevel.RED
        if poor_signals or score < .7:
            return ReadinessLevel.YELLOW
        return ReadinessLevel.GREEN

    def adjustments(self):
        return {ReadinessLevel.GREEN: (),
                ReadinessLevel.YELLOW: ("intensity", "volume"),
                ReadinessLevel.RED: ("intensity", "volume", "intervals", "recovery")}[self.level()]
