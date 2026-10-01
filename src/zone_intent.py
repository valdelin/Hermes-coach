"""Intencao e dose por familia: ENDURANCE, SWEET_SPOT e THRESHOLD.

Estas familias se sobrepoem em %FTP. `ZONE_BANDS` define
`sweetspot` = 0,84-0,97 e `threshold` = 0,91-1,05, que se cruzam em 0,91-0,97.
Nessa faixa a potencia **nao** distingue as duas: o que distingue e a intencao
declarada e a dose. Por isso `classify()` se recusa a adivinhar.

As bandas %FTP nao sao redefinidas aqui. Este modulo consome `ZONE_BANDS` como
invariante e acrescenta a dimensao que falta: para que serve a sessao e como a
dose progride.

Deliberadamente nao importa `ProgressionLever` de `vo2_generator`: aqui os
degraus sao de volume e dose de base (duracao, volume, repeticoes,
recuperacao), nao as escadas de intensidade do bloco VO2.
"""
from dataclasses import dataclass
from enum import Enum

from src.coach import (FOCUS_ENDURANCE, FOCUS_SWEETSPOT, FOCUS_THRESHOLD,
                       FOCUS_ZONE, FOCUS_ZONE2, FOCUS_ZONE2_ENDURANCE,
                       FOCUS_ZONE4_LIMIAR, ZONE_BANDS)


class DoseShape(str, Enum):
    CONTINUOUS = "continuous"
    INTERVAL = "interval"


class ZoneLever(str, Enum):
    DURATION = "duration"
    TOTAL_VOLUME = "total_volume"
    REPETITIONS = "repetitions"
    RECOVERY = "recovery"


class AmbiguousIntensity(ValueError):
    """A potencia cai em mais de uma familia: a intencao precisa ser declarada."""


@dataclass(frozen=True)
class FamilyProfile:
    focus: str
    intent: str
    dose: str
    dose_shape: DoseShape
    levers: tuple[ZoneLever, ...]
    not_claim: str
    criterion: str

    @property
    def band(self):
        return ZONE_BANDS[self.focus]


ENDURANCE = FamilyProfile(
    FOCUS_ZONE2_ENDURANCE,
    "Sustentar blocos continuos e treinos longos; construir base aerobica e "
    "capacidade deeload.",
    "Bloco continuo de 30 min a 4 h, sem lacunas internas.",
    DoseShape.CONTINUOUS,
    (ZoneLever.DURATION, ZoneLever.TOTAL_VOLUME),
    "Nao e zona de trabalho intervals: intervalos artificiais em Z2 nao tem "
    "finalidade de stimulus e fragmentam o volume que sustenta a base.",
    "Continuidade: o valor esta em acumular duracao sem lacunas, nao em "
    "trabalhar mais forte por pedacos.")

SWEET_SPOT = FamilyProfile(
    FOCUS_SWEETSPOT,
    "Alta densidade de stimulus com fadiga administravel, sobre o final de Z3 "
    "e o inicio de Z4.",
    "Blocos de 8-30 min, com folga suficiente para sustentar a repeticao.",
    DoseShape.INTERVAL,
    (ZoneLever.DURATION, ZoneLever.TOTAL_VOLUME),
    "Faixa de intensidade de treinamento, nao zona fisiologica universal. "
    "Nao e equivalente a limiar fisiologico (MLSS, VT2/RCP, LT).",
    "Sobreposicao de estacos com Z4: o que define a sessao e a relacao "
    "estimulo alto por volume gerado, nao a potencia isolada.")

THRESHOLD = FamilyProfile(
    FOCUS_ZONE4_LIMIAR,
    "Elevar a potencia de limiar e a capacidade de depreciar lactato em "
    "esforco maximo sustentavel.",
    "Blocos de 5-20 min com recuperacao em razao declarada (2:1 a 4:1).",
    DoseShape.INTERVAL,
    (ZoneLever.DURATION, ZoneLever.REPETITIONS, ZoneLever.RECOVERY),
    "Nao afirme que 95% FTP = MLSS. FTP e um marcador operacional; MLSS medido "
    "nao coincide com ele e responde a treino de forma diferente.",
    "Repeticoes e recuperacao: aqui a dose e fragmentada de proposito, com "
    "recuperacao em razao declarada — o oposto do perfil de Z2.")

PROFILES = {profile.focus: profile for profile in (ENDURANCE, SWEET_SPOT, THRESHOLD)}


def describe(focus):
    """Perfil da familia de um foco de prescricao ou de uma zona canonica.

    Aceita os aliases legados ('zone2', 'endurance', 'threshold'): eles passam
    por `FOCUS_ZONE` e chegam na mesma familia, como em `zone_band()`.
    """
    zone = focus if focus in PROFILES else FOCUS_ZONE.get(focus)
    if zone is None or zone not in PROFILES:
        raise KeyError(f"foco sem perfil de intencao: {focus!r}")
    return PROFILES[zone]


def band_overlap(first, second):
    """Trecho de %FTP comum as duas familias, ou None se disjuntas."""
    low_a, high_a = describe(first).band
    low_b, high_b = describe(second).band
    low, high = max(low_a, low_b), min(high_a, high_b)
    return (low, high) if low <= high else None


def families_at(power_fraction):
    """Todas as familias cuja banda declarada contém essa fracao de FTP."""
    return tuple(profile for profile in PROFILES.values()
                 if profile.band[0] <= power_fraction <= profile.band[1])


def classify(power_fraction):
    """Familia unica para uma fracao de FTP.

    Recusa-se a decidir quando a faixa e ambigua. Escolher a familia pelo
    numero so seria reescrever a sobreposição como se a potencia fosse
    suficiente — e ela nao e.
    """
    candidates = families_at(power_fraction)
    if len(candidates) > 1:
        names = ", ".join(sorted(profile.focus for profile in candidates))
        raise AmbiguousIntensity(
            f"{power_fraction:.2f} FTP cai em {names}: a intencao declarada "
            f"precisa ser informada, a potencia nao decide a familia.")
    if not candidates:
        raise KeyError(f"nenhuma familia declarada para {power_fraction:.2f} FTP")
    return candidates[0]


def describes_intent(focus, power_fraction):
    """Intencao da familia, dado o foco declarado (nao a potencia)."""
    profile = describe(focus)
    return (profile.band[0] <= power_fraction <= profile.band[1]
            and profile.intent)


def describes_dose(focus, power_fraction):
    """Dose da familia, dado o foco declarado (nao a potencia)."""
    profile = describe(focus)
    return (profile.band[0] <= power_fraction <= profile.band[1]
            and profile.dose)


def distinguishes(first, second):
    """Eixos em que as duas familias divergem, alem da potencia."""
    left, right = describe(first), describe(second)
    divergent = {}
    if left.intent != right.intent:
        divergent["intent"] = (left.intent, right.intent)
    if left.dose != right.dose:
        divergent["dose"] = (left.dose, right.dose)
    if left.dose_shape is not right.dose_shape:
        divergent["dose_shape"] = (left.dose_shape, right.dose_shape)
    if left.levers != right.levers:
        divergent["levers"] = (left.levers, right.levers)
    if left.not_claim != right.not_claim:
        divergent["not_claim"] = (left.not_claim, right.not_claim)
    return divergent


def aliases():
    """Focos que resolvem para o mesmo perfil, preservando os nomes legados."""
    resolved = {}
    for focus in (FOCUS_ZONE2_ENDURANCE, FOCUS_ENDURANCE, FOCUS_SWEETSPOT,
                  FOCUS_ZONE4_LIMIAR, FOCUS_THRESHOLD, FOCUS_ZONE2):
        bucket = resolved.setdefault(describe(focus).focus, [])
        if focus not in bucket:
            bucket.append(focus)
    return resolved
