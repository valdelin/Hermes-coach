"""Progressão de estímulos: heurísticas configuráveis, não protocolos universais."""
from dataclasses import dataclass
from enum import Enum


class StimulusFamily(str, Enum):
    SWEET_SPOT = "sweet_spot"
    THRESHOLD = "threshold"
    VO2MAX = "vo2max"
    ENDURANCE = "endurance"
    ANAEROBIC = "anaerobic"


class Completion(str, Enum):
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    EASY = "easy"


@dataclass(frozen=True)
class CompletionScore:
    target_power: float
    completed_power: float
    planned_sec: int
    completed_sec: int
    rpe: int | None
    heart_rate: int | None
    interruptions: int = 0

    def classify(self):
        power_ratio = self.completed_power / self.target_power if self.target_power else 0
        time_ratio = self.completed_sec / self.planned_sec if self.planned_sec else 0
        if self.interruptions or power_ratio < .80 or time_ratio < .60:
            return Completion.FAILED
        if power_ratio < .95 or time_ratio < .90:
            return Completion.PARTIAL
        if self.rpe is not None and self.rpe <= 3:
            return Completion.EASY
        return Completion.COMPLETED


@dataclass(frozen=True)
class ProgressionStep:
    repeats: int
    work_sec: int
    intensity: float
    recovery_sec: int


SEQUENCES = {
    StimulusFamily.SWEET_SPOT: ((3, 8), (3, 10), (3, 12), (2, 15), (3, 15)),
    StimulusFamily.THRESHOLD: ((3, 8), (3, 10), (3, 12), (2, 15), (3, 15)),
    StimulusFamily.VO2MAX: ((4, 3), (5, 3), (4, 4), (5, 4)),
    StimulusFamily.ENDURANCE: ((1, 60), (1, 75), (1, 90)),
    StimulusFamily.ANAEROBIC: ((6, 1), (8, 1), (6, 2)),
}


class ProgressionEngine:
    def __init__(self, sequences=None):
        self.sequences = dict(SEQUENCES if sequences is None else sequences)

    def step(self, family, index):
        repeats, minutes = self.sequences[StimulusFamily(family)][index]
        return ProgressionStep(repeats, minutes * 60, 0.90,
                               180 if minutes >= 8 else 120)

    def next(self, family, index, score):
        outcome = score.classify()
        if outcome == Completion.FAILED:
            return "reduce", max(0, index - 1)
        if outcome == Completion.PARTIAL:
            return "repeat", index
        return "advance", min(index + 1, len(self.sequences[StimulusFamily(family)]) - 1)
