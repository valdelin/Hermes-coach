"""Gerador estruturado de treinos VO2max.

Os formatos 4x4, 5x3 e 3x5 são **templates de prescrição configuráveis**, não
protocolos universais. A faixa de intensidade é um intervalo ajustável
(inicial 106–120% FTP) e nunca um valor fixo de 115%.

A progressão é organizada por dimensão: cada degrau de uma escada altera
**uma** variável (duração do intervalo, repetições, tempo total ou intensidade).
É por isso que as escadas existem separadas — subir duração e repetições no
mesmo degrau é erro de prescrição, não progressão.

Limite conhecido deste módulo: com `DEFAULT_INTENSITY_RANGE` o lever
`INTENSITY` é **inoperante**, porque a faixa padrão já encosta no teto de Z5
(1,20) e o degrau de +2% é truncado. O lever só age sobre faixa prescrita mais
estreita que o teto. Ver `docs/EMBASAMENTO-CIENTIFICO.md` §12.
"""
from dataclasses import dataclass
from enum import Enum


class VO2Family(str, Enum):
    LONG_INTERVALS = "long_intervals"
    SHORT_INTERVALS = "short_intervals"
    VARIABLE_INTERVALS = "variable_intervals"


class ProgressionLever(str, Enum):
    INTERVAL_DURATION = "interval_duration"
    REPETITIONS = "repetitions"
    TOTAL_WORK_TIME = "total_work_time"
    INTENSITY = "intensity"


DEFAULT_INTENSITY_RANGE = (1.06, 1.20)
DEFAULT_RECOVERY_POWER = 0.40
STEP = 60  # granularidade de progressão, em segundos

# Duração de referência do intervalo por família.
BASELINE_INTERVAL = {
    VO2Family.LONG_INTERVALS: 4 * 60,
    VO2Family.SHORT_INTERVALS: 60,
    VO2Family.VARIABLE_INTERVALS: 3 * 60,
}

# Templates "clássicos": mudam a forma do bloco inteiro. Nem toda transição
# altera repetições E duração — `variable_intervals` é escada só de
# repetições (2x3 -> 3x3 -> 4x3), e a primeira transição de `short_intervals`
# (5x1 -> 10x1) só sobe repetições. Por isso existe à parte das escadas por
# dimensão, que são o caminho preferido. Verificado em
# `tests/scientific/test_vo2.py::test_templates_de_intervalos_curtos_e_variaveis_mudam_uma_dimensao`.
MIXED_TEMPLATES = {
    VO2Family.LONG_INTERVALS: ((4, 4 * 60), (5, 3 * 60), (3, 5 * 60)),
    VO2Family.SHORT_INTERVALS: ((5, 60), (10, 60), (6, 2 * 60)),
    VO2Family.VARIABLE_INTERVALS: ((2, 3 * 60), (3, 3 * 60), (4, 3 * 60)),
}

# Recuperacao por duracao de intervalo: 4 min -> 3 min, 3 min -> 2 min, o resto
# -> 90 s. Convencao do gerador: a evidencia nao sustenta uma exigencia.
RECOVERY_BY_INTERVAL = ((4 * 60, 3 * 60), (3 * 60, 2 * 60), (STEP, 90))


@dataclass(frozen=True)
class VO2Workout:
    family: VO2Family
    interval_duration: int
    repetitions: int
    work_power_range: tuple[float, float]
    recovery_duration: int
    recovery_power: float
    total_work_time: int
    progression_step: int
    lever: ProgressionLever

    @property
    def total_session_time(self):
        return self.total_work_time + self.recovery_duration * max(
            0, self.repetitions - 1)


def _recovery_for(interval_duration):
    for threshold, recovery in RECOVERY_BY_INTERVAL:
        if interval_duration >= threshold:
            return recovery
    return RECOVERY_BY_INTERVAL[-1][1]


def _ladder(family, lever):
    """Escada (repetições, duração) que altera uma única dimensão por degrau."""
    base = BASELINE_INTERVAL[VO2Family(family)]
    lever = ProgressionLever(lever)
    if lever is ProgressionLever.INTERVAL_DURATION:
        return ((4, base - STEP), (4, base), (4, base + STEP))
    if lever is ProgressionLever.REPETITIONS:
        return ((3, base), (4, base), (5, base))
    if lever is ProgressionLever.TOTAL_WORK_TIME:
        return ((4, base), (4, base + STEP), (5, base + STEP))
    return ((4, base), (4, base), (4, base))


# Degrau de intensidade por lever: sobe o teto da faixa de trabalho, sem
# tocar em repeticoes nem duracao. 115% nao e o destino — cada degrau e um
# ajuste pequeno e cumulativo sobre a faixa configurada.
#
# O teto e ZONE_BANDS[FOCUS_ZONE5_VO2MAX][1]: subir acima disso seria gerar
# Z6 (121-150%) com uma prescricao rotulada como VO2max. A faixa padrao ja
# encosta no teto, entao este lever so tem folga quando a faixa prescrita for
# mais estreita que a banda. Com `DEFAULT_INTENSITY_RANGE` nao ha folga e o
# lever nao produz efeito algum.
Z5_CEILING = 1.20
INTENSITY_STEP = 0.02


def generate(family, lever=ProgressionLever.TOTAL_WORK_TIME, progression_step=0,
             intensity_range=DEFAULT_INTENSITY_RANGE,
             recovery_power=DEFAULT_RECOVERY_POWER):
    """Treino VO2 do degrau `progression_step` na escada de `lever`."""
    family = VO2Family(family)
    lever = ProgressionLever(lever)
    steps = _ladder(family, lever)
    step = max(0, min(progression_step, len(steps) - 1))
    repetitions, duration = steps[step]
    if lever is ProgressionLever.INTENSITY:
        low, high = intensity_range
        intensity_range = (low, round(min(Z5_CEILING, high + INTENSITY_STEP * step), 4))
    return VO2Workout(family, duration, repetitions, tuple(intensity_range),
                      _recovery_for(duration), recovery_power,
                      duration * repetitions, step, lever)


def generate_mixed(family, progression_step=0,
                   intensity_range=DEFAULT_INTENSITY_RANGE,
                   recovery_power=DEFAULT_RECOVERY_POWER):
    """Traino pelo template clássico (4x4, 5x3, 3x5) da família."""
    family = VO2Family(family)
    steps = MIXED_TEMPLATES[family]
    step = max(0, min(progression_step, len(steps) - 1))
    repetitions, duration = steps[step]
    return VO2Workout(family, duration, repetitions, tuple(intensity_range),
                      _recovery_for(duration), recovery_power,
                      duration * repetitions, step,
                      ProgressionLever.INTERVAL_DURATION)


def next_step(family, lever, progression_step=0):
    """Avança um degrau; a escada satura no fim em vez de repetir trabalho."""
    depth = len(_ladder(family, lever))
    return min(progression_step + 1, depth - 1)


def progression_ledger(family, lever=ProgressionLever.TOTAL_WORK_TIME):
    """Escada completa de um lever; degraus consecutivos mudam uma dimensão só."""
    return [(step, generate(family, lever, step))
            for step in range(len(_ladder(family, lever)))]


def evaluate(workout, intensity_range=DEFAULT_INTENSITY_RANGE,
             work_range=(600, 2400), recovery_ratio=.5):
    """Avalia intensidade, duração, recuperação e trabalho acumulado.

    Os limites entram como parâmetros: os templates do gerador ficam dentro da
    faixa, então um treino excessivo só aparece quando montado à mão.
    """
    return {
        "intensity_ok": workout.work_power_range == tuple(intensity_range),
        "work_in_range": work_range[0] <= workout.total_work_time <= work_range[1],
        "recovery_proportional": workout.recovery_duration >= workout.interval_duration * recovery_ratio,
    }
