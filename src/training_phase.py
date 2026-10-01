"""Fases de treinamento configuráveis, separadas dos sinais diários.

Esta é uma arquitetura de periodização para o plano. Não descreve uma sequência
fisiológica universal nem substitui decisão de treinador.
"""
from dataclasses import dataclass
from enum import Enum


class TrainingPhase(str, Enum):
    BASE = "base"
    BUILD = "build"
    SPECIFIC = "specific"
    PEAK = "peak"
    RECOVERY = "recovery"
    TEST = "test"


@dataclass(frozen=True)
class PhaseDefinition:
    objective: str
    duration: int
    priority_stimuli: tuple[str, ...]
    secondary_stimuli: tuple[str, ...]
    load_limits: tuple[float, float]
    progression_criteria: str
    deload_criteria: str
    exit_criteria: str


@dataclass(frozen=True)
class PhaseState:
    phase: TrainingPhase
    week: int = 1


def _definition(objective, duration, priority, secondary, limits,
                progression, deload, exit_criteria):
    return PhaseDefinition(objective, duration, priority, secondary, limits,
                           progression, deload, exit_criteria)


DEFAULT_PHASES = {
    TrainingPhase.BASE: _definition("base aeróbica", 4, ("zone2",), ("sweetspot",),
                                    (0.6, 0.9), "aderência estável", "fadiga acumulada",
                                    "base concluída"),
    TrainingPhase.BUILD: _definition("elevar capacidade", 4, ("sweetspot", "threshold"),
                                     ("zone2",), (0.8, 1.1), "carga tolerada",
                                     "fadiga acumulada", "bloco concluído"),
    TrainingPhase.SPECIFIC: _definition("especificidade da meta", 3,
                                        ("threshold", "vo2max"), ("zone2",),
                                        (0.8, 1.15), "estímulo específico concluído",
                                        "fadiga acumulada", "pronto para pico"),
    TrainingPhase.PEAK: _definition("chegar fresco à meta", 2, ("threshold",),
                                    ("zone2",), (0.5, 0.9), "manter intensidade",
                                    "fadiga acumulada", "prova ou transição"),
    TrainingPhase.RECOVERY: _definition("absorver carga", 1, ("zone2",), (),
                                        (0.3, 0.6), "recuperação concluída",
                                        "sinais persistentes", "readiness normal"),
    TrainingPhase.TEST: _definition("avaliar referência", 1, ("test",), ("zone2",),
                                    (0.3, 0.7), "teste concluído", "fadiga alta",
                                    "resultado registrado"),
}


class TrainingPhaseEngine:
    """Transições explícitas; TSB/readiness não selecionam fase diretamente."""

    def __init__(self, definitions=None):
        self.definitions = dict(DEFAULT_PHASES if definitions is None else definitions)
        missing = set(TrainingPhase) - set(self.definitions)
        if missing:
            raise ValueError(f"fases sem definição: {', '.join(p.value for p in missing)}")

    def create(self, phase=TrainingPhase.BASE):
        return PhaseState(TrainingPhase(phase))

    def definition(self, phase):
        return self.definitions[TrainingPhase(phase)]

    def remain(self, state):
        return PhaseState(state.phase, state.week + 1)

    def transition(self, state, progression_met=False, deload=False):
        if deload:
            return PhaseState(TrainingPhase.RECOVERY)
        definition = self.definition(state.phase)
        if not progression_met or state.week < definition.duration:
            return self.remain(state)
        next_phase = {
            TrainingPhase.BASE: TrainingPhase.BUILD,
            TrainingPhase.BUILD: TrainingPhase.SPECIFIC,
            TrainingPhase.SPECIFIC: TrainingPhase.PEAK,
            TrainingPhase.PEAK: TrainingPhase.RECOVERY,
            TrainingPhase.RECOVERY: TrainingPhase.BASE,
            TrainingPhase.TEST: TrainingPhase.RECOVERY,
        }[state.phase]
        return PhaseState(next_phase)

    def recovery(self):
        return self.create(TrainingPhase.RECOVERY)

    def test(self):
        return self.create(TrainingPhase.TEST)
