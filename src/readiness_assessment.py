"""Prontidão multimodal: suporte ao treino, não diagnóstico clínico."""
from dataclasses import dataclass
from enum import Enum


# Contrato canônico dos eixos do modelo. Consumidores de UI devem derivar desta
# lista, em vez de repetir os sete nomes e rótulos em cada renderer.
READINESS_AXIS_SPECS = (
    ("hrv_score", "HRV"),
    ("rhr_score", "Frequência cardíaca de repouso"),
    ("sleep_score", "Sono"),
    ("subjective_fatigue_score", "Fadiga subjetiva"),
    ("recent_load_score", "Carga recente"),
    ("performance_score", "Desempenho"),
    ("consistency_score", "Consistência"),
)
READINESS_AXIS_NAMES = tuple(name for name, _ in READINESS_AXIS_SPECS)


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
