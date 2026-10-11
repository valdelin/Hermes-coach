import dataclasses
import json
import pathlib
from datetime import date, datetime, timedelta

try:
    from coach import (WorkoutParams, estimate_tss,
                       FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2,
                       zone_floor, zone_ceiling, ZONE_BANDS)
except ImportError:
    from .coach import (WorkoutParams, estimate_tss,
                        FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2,
                        zone_floor, zone_ceiling, ZONE_BANDS)

try:
    from . import readiness as readiness_mod
    from .readiness import ReadinessAction, ReadinessDecision
    from . import zone_intent
    from . import lifecycle
    from . import training_phase as training_phase_mod
    from .training_phase import TrainingPhase
except ImportError:  # pragma: no cover - execucao como script solto
    import readiness as readiness_mod
    from readiness import ReadinessAction, ReadinessDecision
    import zone_intent
    import lifecycle
    import training_phase as training_phase_mod
    from training_phase import TrainingPhase

try:
    from provider_fields import field as _field, is_completed as _is_completed
except ImportError:  # execucao como pacote (src.plan)
    from .provider_fields import (field as _field,  # type: ignore
                                  is_completed as _is_completed)

# TSB abaixo disso conta como fadiga acumulada e dispara a adaptacao da sessao
# de qualidade. Regra historica, inalterada pelo Passo A da #58 — o nome serve
# para explicitar a precedencia contra a decisao de prontidao.
TSB_ADAPT_LIMIT = -15

START_TIME = "07:30:00"
REST = "rest"
DEFAULT_FTP = 182
EXTERNAL_ID_PREFIX = "hermes-plan"

# Dias de treino padrao (seg-sex). Configuravel via TRAINING_DAYS no .env.
DEFAULT_TRAINING_DAYS = (0, 1, 2, 3, 4)  # date.weekday(): seg=0 .. sex=4

DAY_NAMES = {
    "mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6,
    "seg": 0, "ter": 1, "qua": 2, "qui": 3, "sex": 4, "sab": 5, "dom": 6,
}


def parse_training_days(value):
    """Converte TRAINING_DAYS ('mon,tue,...' ou 'seg,ter,...') em tupla de
    weekday (date.weekday()). Vazio/ausente ou invalido -> default seg-sex."""
    if not value:
        return DEFAULT_TRAINING_DAYS
    days = []
    for token in str(value).split(","):
        token = token.strip().lower()
        if token in DAY_NAMES:
            days.append(DAY_NAMES[token])
        else:
            return DEFAULT_TRAINING_DAYS
    return tuple(sorted(set(days))) or DEFAULT_TRAINING_DAYS


def parse_active_recovery_days(value, training_days):
    """Converte ACTIVE_RECOVERY_DAYS e exige que sejam slots de treino."""
    if not value:
        return ()
    days = []
    for token in str(value).split(","):
        token = token.strip().lower()
        if token not in DAY_NAMES:
            raise ValueError("ACTIVE_RECOVERY_DAYS invalido; use seg..dom ou mon..sun")
        days.append(DAY_NAMES[token])
    result = tuple(sorted(set(days)))
    if not set(result).issubset(training_days):
        raise ValueError("ACTIVE_RECOVERY_DAYS deve estar contido em TRAINING_DAYS")
    return result


def parse_weekly_hours(value):
    """Converte WEEKLY_HOURS do .env em float (horas disponiveis por semana) ou
    None se ausente/invalido. Aceita '5', '5.5', '5h' ou '300min'."""
    if not value:
        return None
    raw = str(value).strip().lower().replace(" ", "")
    if raw.endswith("h"):
        raw = raw[:-1]
    elif raw.endswith("min"):
        try:
            return round(float(raw[:-3]) / 60.0, 1)
        except ValueError:
            return None
    try:
        hours = float(raw)
    except ValueError:
        return None
    if hours <= 0 or hours > 24 * 7:
        return None
    return hours


def parse_min_regular_duration_minutes(value):
    """Converte preferencia opcional de duracao minima regular em segundos."""
    if not value:
        return None
    try:
        minutes = int(str(value).strip())
    except ValueError:
        return None
    if minutes <= 0 or minutes > 24 * 60:
        return None
    return minutes * 60


def parse_long_day(value):
    """Converte LONG_DAY do .env (dia preferido para treinos longos, ex. 'sun'
    ou 'dom') em weekday (date.weekday()) ou None se ausente/invalido."""
    if not value:
        return None
    return DAY_NAMES.get(str(value).strip().lower())


@dataclasses.dataclass(frozen=True)
class PlannedWorkout:
    day: str
    focus: str
    planned_duration: int
    name: str
    params: dict
    tss: float
    external_id: str
    ftp_watts: int = DEFAULT_FTP


@dataclasses.dataclass(frozen=True)
class TrainingPlanState:
    """Estado calculado que separa periodizacao de autoregulacao diaria."""
    goal: str | None
    phase: str
    week_in_phase: int
    cycle_week: int
    planned_load: float
    current_load: float
    tsb: float
    readiness: object | None = None


def templates():
    return {
        FOCUS_ZONE2: _block(1, 1800, 0, 0.70),
        "endurance": _block(1, 3600, 0, 0.75),
        FOCUS_SWEETSPOT: _block(3, 480, 240, 0.88),
        FOCUS_THRESHOLD: _block(3, 480, 240, 0.98),
        FOCUS_VO2: _block(4, 180, 180, 1.15),
    }


def _block(repeats, on_sec, off_sec, on_power):
    return {
        "repeats": repeats, "on_sec": on_sec, "off_sec": off_sec,
        "on_power": on_power, "off_power": 0.55, "cadence": 90,
        "cadence_rest": 85 if off_sec else 90,
    }


# Disponibilidade semanal (perguntada no 1o uso e salva no .env):
# - WEEKLY_HOURS: horas por semana disponiveis para treinar; o build escala a
#   duracao dos treinos (on_sec) para caber nas horas, respeitando TSS budget.
# - LONG_DAY: dia preferido para o treino longo (endurance/maior volume); o
#   build rotaciona o ciclo semanal para esse treino cair no dia escolhido.
VOLUME_SCALE_MIN = 0.5
VOLUME_SCALE_MAX = 1.5
MIN_REGULAR_DURATION_SEC = 3600
ACTIVE_RECOVERY_POWER = 0.60
ACTIVE_RECOVERY_ON_SEC = 2400


def _workout_duration(block):
    """Duracao total (s) de um bloco com warmup/cooldown padroes (600s cada)."""
    return 600 + block["repeats"] * (block["on_sec"] + block["off_sec"]) + 600


def _long_focus(weekly):
    """Foco 'longo' do ciclo semanal: endurance quando presente; senao o foco
    com maior duracao default (templates())."""
    if ENDURANCE in weekly:
        return ENDURANCE
    best, best_dur = None, -1
    for focus in weekly:
        dur = _workout_duration(templates()[focus])
        if dur > best_dur:
            best, best_dur = focus, dur
    return best


def _closest_training_day(long_day, slots):
    """Dia de treino mais proximo de long_day (distancia circular)."""
    return min(slots, key=lambda wd: (wd - long_day) % 7)


def _place_long_day(weekly, long_day, slots):
    """Rotaciona o ciclo semanal para que o treino longo (endurance ou o foco
    de maior volume) caia no slot do dia preferido (LONG_DAY). Se LONG_DAY nao
    for dia de treino, usa o dia de treino mais proximo."""
    if long_day is None or not slots or len(weekly) < 2:
        return weekly
    target = long_day if long_day in slots else _closest_training_day(long_day, slots)
    target_pos = slots.index(target)
    focus = _long_focus(weekly)
    if focus is None:
        return weekly
    cur_pos = weekly.index(focus) % len(weekly)
    shift = (cur_pos - target_pos) % len(weekly)
    if shift == 0:
        return weekly
    return weekly[shift:] + weekly[:shift]


def _volume_scale(weekly, weekly_hours, slots):
    """Fator aplicado a on_sec dos treinos para a semana caber nas horas
    disponiveis (WEEKLY_HOURS). Baseline = duracao da semana com os templates
    default sobre os slots configurados. Retorna None (sem ajuste) quando
    WEEKLY_HOURS ausente/invalido."""
    if not weekly_hours or weekly_hours <= 0 or not slots:
        return None
    baseline = sum(_workout_duration(templates()[weekly[p % len(weekly)]])
                   for p in range(len(slots)))
    if baseline <= 0:
        return None
    scale = (weekly_hours * 3600) / baseline
    return round(max(VOLUME_SCALE_MIN, min(VOLUME_SCALE_MAX, scale)), 3)


def _scale_duration(params, scale):
    """Aplica o fator de volume a on_sec (minimo 120s), mantendo o resto."""
    if scale is None or abs(scale - 1.0) < 1e-9:
        return params
    return WorkoutParams(**{**params.__dict__,
                            "on_sec": max(120, int(params.on_sec * scale))})


def _active_recovery_params():
    """Sessao de 60min em Z2 leve; active recovery e intencao, nao foco Z1."""
    return WorkoutParams(focus=FOCUS_ZONE2,
                         **_block(1, ACTIVE_RECOVERY_ON_SEC, 0,
                                  ACTIVE_RECOVERY_POWER))


# Indice = posicao do dia dentro da agenda de treino (build_plan). O template
# de 5 focos e cortado/cirado ao tamanho da agenda configurada (TRAINING_DAYS,
# default seg-sex). A carga e aplicada apos (ver build_plan / weekly_budget).
WEEKLY_BY_TSB = [
    (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
    (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_VO2]),
    (5, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
    (10**9, [FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
]

# Tipos de plano (GOAL no .env). Cada tipo define a distribuicao de focos por
# TSB (weekly templates) e uma escala do orcamento semanal (budget_scale) para
# calibrar volume/carga conforme o tipo — os numeros de TSS/sem alvo sao
# inspirados nos planos oficiais do Zwift (whatsonzwift.com), usados apenas
# como calibracao, sem replicar workouts deles. A prescricao e propria.
GOALS = ("back-to-fitness", "ftp-builder", "gran-fondo", "time-trial",
         "climbing", "active-off-season", "race")

# Modelos de periodizacao (PERIODIZATION no .env, opcional): ajustam a
# distribuicao de focos na semana quando ativos (senao vale GOAL/TEMPLATES).
# Referencia: IntervalCoach oferece 5 modelos selecionaveis (26/09); aqui cada
# modelo faz sentido com o TSB do dia:
#   polarized  -> muito Z2 + VO2 curto, quase nada de sweet spot/limiar;
#   pyramidal  -> base Z2 com progressao ate sweet spot (pouco VO2);
#   undulating -> alterna qualidade/recuperacao dentro da semana;
#   linear     -> progressao simples por semana (Z2 -> SS -> T -> VO2);
#   block      -> semanas em bloco (tudo Z2 no TSB baixo; qualidade quando ok).
PERIODIZATIONS = ("polarized", "pyramidal", "undulating", "linear", "block")

PERIODIZATION_TEMPLATES = {
    "polarized": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_VO2]),
        (0, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_VO2, FOCUS_ZONE2, FOCUS_VO2]),
        (10**9, [FOCUS_VO2, FOCUS_ZONE2, FOCUS_VO2, FOCUS_ZONE2, FOCUS_VO2]),
    ],
    "pyramidal": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2,
               FOCUS_SWEETSPOT]),
        (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT,
             FOCUS_THRESHOLD]),
        (10**9, [FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_THRESHOLD,
                 FOCUS_SWEETSPOT, FOCUS_THRESHOLD]),
    ],
    "undulating": [
        (-15, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT,
               FOCUS_ZONE2]),
        (0, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_ZONE2, FOCUS_SWEETSPOT,
             FOCUS_THRESHOLD]),
        (10**9, [FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_ZONE2, FOCUS_THRESHOLD,
                 FOCUS_VO2]),
    ],
    "linear": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2,
               FOCUS_SWEETSPOT]),
        (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_SWEETSPOT, FOCUS_THRESHOLD,
             FOCUS_THRESHOLD]),
        (10**9, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_THRESHOLD, FOCUS_VO2,
                 FOCUS_VO2]),
    ],
    "block": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2,
               FOCUS_ZONE2]),
        (0, [FOCUS_SWEETSPOT, FOCUS_SWEETSPOT, FOCUS_SWEETSPOT,
             FOCUS_SWEETSPOT, FOCUS_SWEETSPOT]),
        (10**9, [FOCUS_THRESHOLD, FOCUS_THRESHOLD, FOCUS_VO2,
                 FOCUS_THRESHOLD, FOCUS_VO2]),
    ],
}

PERIODIZATION_LABELS = {
    "polarized": "Polarizado (Z2 + VO2)",
    "pyramidal": "Piramidal (base Z2 + progressao)",
    "undulating": "Ondulante (alterna qualidade/leve)",
    "linear": "Linear (progressao na semana)",
    "block": "Blocos (semanas em bloco)",
}

ENDURANCE = "endurance"

GOAL_TEMPLATES = {
    None: WEEKLY_BY_TSB,
    "back-to-fitness": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
        (0, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
        (10**9, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2]),
    ],
    "ftp-builder": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
        (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD]),
        (5, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
        (10**9, [FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
    ],
    "gran-fondo": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, ENDURANCE]),
        (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT, ENDURANCE]),
        (5, [FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, ENDURANCE]),
        (10**9, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, ENDURANCE]),
    ],
    "time-trial": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
        (0, [FOCUS_ZONE2, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
        (5, [FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_THRESHOLD]),
        (10**9, [FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_THRESHOLD]),
    ],
    "climbing": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
        (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_VO2, FOCUS_SWEETSPOT, FOCUS_VO2]),
        (5, [FOCUS_SWEETSPOT, FOCUS_VO2, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_VO2]),
        (10**9, [FOCUS_VO2, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_VO2, FOCUS_THRESHOLD]),
    ],
    "active-off-season": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2]),
        (0, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_ZONE2]),
        (10**9, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2]),
    ],
    "race": [
        (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
        (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD]),
        (5, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
        (10**9, [FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
    ],
}

# Escala do orcamento semanal por tipo (1.0 = comportamento atual). Ex.:
# back-to-fitness/off-season bem mais leves que tt-builder/race.
GOAL_BUDGET_SCALE = {
    None: 1.0,
    "back-to-fitness": 0.60,
    "ftp-builder": 1.0,
    "gran-fondo": 1.15,
    "time-trial": 1.15,
    "climbing": 1.10,
    "active-off-season": 0.60,
    "race": 1.20,
}

GOAL_LABELS = {
    None: "TSB (padrao)",
    "back-to-fitness": "Back to Fitness",
    "ftp-builder": "FTP Builder",
    "gran-fondo": "Gran Fondo",
    "time-trial": "Time Trial",
    "climbing": "Climbing",
    "active-off-season": "Active Off-Season",
    "race": "Race",
}

# Fase semantica advisory inicial por GOAL (integracao #58-A). Tabela explicita,
# nao inferida pelo nome do GOAL. Classificacao conservadora sobre a semantica
# atual dos GOALS (ver GOAL_TEMPLATES/GOAL_BUDGET_SCALE):
#  - retorno/base          -> BASE   (back-to-fitness, active-off-season);
#  - construcao de perf.   -> BUILD  (ftp-builder, gran-fondo, time-trial,
#                                     climbing, race);
#  - sem GOAL explicito    -> BUILD, espelhando a fase legada do build.
# `race` sai de BUILD para PEAK apenas na janela de taper (derive_plan_phase).
GOAL_START_PHASE = {
    None: TrainingPhase.BUILD,
    "back-to-fitness": TrainingPhase.BASE,
    "ftp-builder": TrainingPhase.BUILD,
    "gran-fondo": TrainingPhase.BUILD,
    "time-trial": TrainingPhase.BUILD,
    "climbing": TrainingPhase.BUILD,
    "active-off-season": TrainingPhase.BASE,
    "race": TrainingPhase.BUILD,
}

# Variedade de formato por foco (o build rotaciona as variantes quando um
# GOAL esta ativo, para o plano nao ficar monotonico). A variante 0 de cada
# foco e identica ao template atual (comportamento sem GOAL preservado).
BLOCK_VARIANTS = {
    FOCUS_ZONE2: [
        {"repeats": 1, "on_sec": 1800, "off_sec": 0, "on_power": 0.70},
        {"repeats": 2, "on_sec": 810, "off_sec": 180, "on_power": 0.75},
        {"repeats": 3, "on_sec": 540, "off_sec": 120, "on_power": 0.72},
    ],
    FOCUS_SWEETSPOT: [
        {"repeats": 3, "on_sec": 480, "off_sec": 240, "on_power": 0.88},
        {"repeats": 2, "on_sec": 720, "off_sec": 180, "on_power": 0.88},
        {"repeats": 4, "on_sec": 360, "off_sec": 180, "on_power": 0.90},
    ],
    FOCUS_THRESHOLD: [
        {"repeats": 3, "on_sec": 480, "off_sec": 240, "on_power": 0.98},
        {"repeats": 2, "on_sec": 840, "off_sec": 300, "on_power": 0.97},
        {"repeats": 4, "on_sec": 300, "off_sec": 180, "on_power": 1.00},
    ],
    FOCUS_VO2: [
        {"repeats": 4, "on_sec": 180, "off_sec": 180, "on_power": 1.15},
        {"repeats": 5, "on_sec": 150, "off_sec": 150, "on_power": 1.14},
        {"repeats": 3, "on_sec": 240, "off_sec": 240, "on_power": 1.12},
    ],
    ENDURANCE: [
        {"repeats": 1, "on_sec": 3600, "off_sec": 0, "on_power": 0.75},
        {"repeats": 2, "on_sec": 1500, "off_sec": 180, "on_power": 0.75},
        {"repeats": 3, "on_sec": 1020, "off_sec": 120, "on_power": 0.72},
    ],
}

# Janela de taper antes da prova (GOAL=race): os treinos dentro destes dias
# antes de RACE_DATE viram preparacao progressiva (ver _taper_focus). Baseado
# na periodizacao do Joe Friel (case study 2010): ultimo estimulo de qualidade
# ~uma semana antes, depois recuperacao, com D-2/D-1 muito leves para
# descarregar fatigue sem derreter o fitness (CTL decai devagar no EWMA 42).
TAPER_DAYS = 7
# Estimulo de qualidade da semana pre-prova: quantos dias antes da prova.
RACE_SHARPENING_DELTA = 6
# Faixa-alvo de projecao de TSB no dia da prova (Science to Sport: `-5..+5` a
# `+10..+20` por atleta; Joe Friel usa ~+20 no dia). Personalizavel = #16.
RACE_TSB_LOW = -10.0
RACE_TSB_HIGH = 20.0

RACE_PHASE_LABELS = {
    "sharpening": "Ultimo estimulo (pre-prova)",
    "recovery": "Recuperacao (pre-prova)",
    "spin": "Spin leve (pre-prova)",
}


def _tsb_race_verdict(tsb):
    """Veredito da preparacao pelo TSB projetado no dia da prova:
    - 'cansado': TSB < RACE_TSB_LOW (chega a prova fatigado; aumentar taper);
    - 'ok'     : dentro da faixa-alvo (RACE_TSB_LOW..RACE_TSB_HIGH);
    - 'acima'  : TSB > RACE_TSB_HIGH (passou do pico).
    A faixa e individual (#16); aqui usa-se o default da literatura."""
    if tsb < RACE_TSB_LOW:
        return "cansado"
    if tsb > RACE_TSB_HIGH:
        return "acima"
    return "ok"


def parse_goal(value):
    """Converte GOAL do .env ('ftp-builder', etc.) em chave valida. Ausente ou
    invalido -> None (comportamento padrao por TSB)."""
    if not value:
        return None
    goal = str(value).strip().lower().replace("_", "-")
    return goal if goal in GOALS else None


def parse_periodization(value):
    """Converte PERIODIZATION do .env ('polarized', 'block', etc.) em chave
    valida. Ausente ou invalido -> None (usa GOAL/template padrao)."""
    if not value:
        return None
    p = str(value).strip().lower().replace("_", "-")
    return p if p in PERIODIZATIONS else None


def parse_ftp_test_date(value):
    """Converte FTP_TEST_DATE ('YYYY-MM-DD') em date, ou None se ausente/
    invalido."""
    if not value:
        return None
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        return None


def parse_fthr(value):
    """Converte FTHR do .env (frequencia cardiaca no limiar, em bpm) em int, ou
    None se ausente/invalido. Valores fora do intervalo humano (30-250 bpm) sao
    descartados. O FTHR e usado na prescricao sem medidor de potencia (#3):
    alvos em %FTHR + RPE e carga estimada via icu_training_load do Intervals."""
    if not value:
        return None
    try:
        fthr = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    if fthr < 30 or fthr > 250:
        return None
    return fthr


FOCUS_LABELS_PT = {
    REST: "Descanso",
    FOCUS_ZONE2: "Zona 2",
    FOCUS_SWEETSPOT: "Sweet Spot",
    FOCUS_THRESHOLD: "Limiar FTP",
    FOCUS_VO2: "VO2 Max",
    "endurance": "Endurance",
}


def workout_name(day, focus):
    """Nome mostrado no Intervals, com a data do treino na frente."""
    return f"{day} - Treino de {FOCUS_LABELS_PT[focus]}"


def weekly_template(tsb, goal=None, periodization=None):
    """Template semanal de focos: PERIODIZATION (quando valida) tem prioridade
    sobre GOAL — o modelo de periodizacao molda a distribuicao da semana; sem
    ela vale GOAL_TEMPLATES (ou WEEKLY_BY_TSB sem GOAL)."""
    if periodization and periodization in PERIODIZATION_TEMPLATES:
        templates = PERIODIZATION_TEMPLATES[periodization]
    else:
        templates = GOAL_TEMPLATES.get(goal, WEEKLY_BY_TSB)
    for threshold, template in templates:
        if tsb < threshold:
            return template
    return templates[-1][1]


def training_phase(goal, race_date, day):
    """Fase do plano: GOAL e data da prova a definem, nunca o TSB."""
    if goal == "race" and race_date:
        try:
            days_to_race = (date.fromisoformat(race_date) - day).days
        except (TypeError, ValueError):
            days_to_race = None
        if days_to_race is not None and 0 <= days_to_race < TAPER_DAYS:
            return "taper"
    if goal == "back-to-fitness":
        return "base"
    if goal == "active-off-season":
        return "transition"
    return "build"


def training_plan_state(goal, race_date, day, planned_load, current_load, tsb,
                        readiness=None):
    """Monta o estado transitório usado por um build, sem mudar plan.json."""
    return TrainingPlanState(
        goal=goal,
        phase=training_phase(goal, race_date, day),
        week_in_phase=1,
        cycle_week=(day.isocalendar().week - 1) % 4 + 1,
        planned_load=float(planned_load),
        current_load=float(current_load),
        tsb=float(tsb),
        readiness=readiness,
    )


def phase_weekly_template(state, periodization=None):
    """Alvo semanal da fase, independente dos sinais diarios do atleta."""
    if periodization and periodization in PERIODIZATION_TEMPLATES:
        templates_by_phase = PERIODIZATION_TEMPLATES[periodization]
    else:
        templates_by_phase = GOAL_TEMPLATES.get(state.goal, WEEKLY_BY_TSB)
    index = {"base": 0, "transition": 0, "build": 2, "taper": 0}.get(
        state.phase, 0)
    return templates_by_phase[min(index, len(templates_by_phase) - 1)][1]


def _readiness_applies_on(decisao, day):
    """O sinal de prontidao vale para o dia que ele DESCREVE, e so.

    `decisao.applies_to_day` e o dia do ultimo registro de wellness. Uma
    leitura descreve o dia em que foi medida; extrapola-la para um dia futuro
    seria inventar um sinal. E a ancora que substitui um prazo de validade
    arbitrario:

    - leitura de hoje -> adapta a sessao de hoje;
    - leitura de ontem -> nao toca na sessao de amanha;
    - leitura de 9 dias atras -> nao toca em nada, porque o dia que ela
      descreve ja passou e nao esta no plano.

    `None` (decisao montada a mao, sem ancora) mantem o comportamento legado e
    aplica onde for. O produtor sempre preenche o campo.

    TSB NAO passa por aqui: a regra de TSB continua valendo para a primeira
    sessao de qualidade do plano, como sempre.
    """
    alvo = getattr(decisao, "applies_to_day", None)
    return alvo is None or alvo == day


# --- Elegibilidade da sessao de hoje para a avaliacao de prontidao -----------
# A avaliacao so pode agir sobre a sessao do dia que a LEITURA DESCREVE, e so
# enquanto essa sessao nao comecou. Estas funcoes formalizam as tres perguntas
# que a CLI precisa responder antes de tocar no plan.json:
#
#   1. o que o Intervals efetivamente sabe sobre esta sessao (estado);
#   2. se a sessao e elegivel a uma intervencao (politica);
#   3. qual proposta a intervencao produziria (motor unico).
#
# Elas moram aqui, e nao no CLI, porque `START_TIME` e o criterio de "feito"
# (`paired_activity_id`, em `_done_and_extra`) ja sao politica deste modulo.

QUALITY_FOCUSES = (FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2)

# Estados de execucao, do mais ao menos infosso. `desconhecido` e o estado
# honesto para "o horario planejado ja passou e o Intervals nao confirma a
# realizacao": pode ser que o atleta esteja treinando com a sincronizacao
# pendente, e tratar isso como "nao iniciado" seria reescrever uma sessao em
# andamento.
SESSAO_CONCLUIDA = "concluida"
SESSAO_PUBLICADA = "publicada"
SESSAO_NAO_PUBLICADA = "nao_publicada"
SESSAO_SEM_IDENTIDADE = "sem_identidade"
SESSAO_DESCONHECIDA = "estado_desconhecido"


def session_execution_state(workout, events):
    """O que o Intervals diz sobre a execucao desta sessao. Nada alem disso.

    Reusa o criterio de `_done_and_extra`: um treino do plano so conta como
    realizado quando o evento traz `paired_activity_id` (ou `activity_id`) E o
    `external_id` e nosso. Sem isso, a ausencia de evento nao prova que o atleta
    nao treinou — prova apenas que ainda nao sincronizou.
    """
    eid = (workout or {}).get("external_id")
    if not eid:
        return SESSAO_SEM_IDENTIDADE
    achados = [e for e in (events or []) if _field(e, "external_id") == eid]
    if any(_is_completed(e) for e in achados):
        return SESSAO_CONCLUIDA
    if achados:
        return SESSAO_PUBLICADA
    return SESSAO_NAO_PUBLICADA


def _planned_start(day_iso):
    """Instante planejado da sessao: `START_TIME` na data do treino.

    `START_TIME` ja e a hora que o `push` publica (via `event_payload`), entao
    este e o horario real da sessao, nao uma suposicao nova.
    """
    return datetime.fromisoformat(f"{day_iso}T{START_TIME}")


@dataclasses.dataclass(frozen=True)
class ReadinessEligibility:
    """Resposta as tres perguntas, para a CLI decidir o que fazer."""

    workout: dict | None
    state: str
    eligible: bool
    reason: str

    @property
    def day(self):
        return self.workout["day"] if self.workout else None


def readiness_eligibility(plan, events, today=None, now=None):
    """A sessao de hoje aceita uma intervencao de prontidao?

    Sequencia de filtros, na ordem em que cada um pode barrar:

    - sem treino hoje            -> nada a adaptar;
    - foco nao qualitativo       -> REDUCE/REPLACE so existe para qualidade;
    - sem `external_id`          -> sem identidade, nada a confirmar depois;
    - concluida                  -> preservada sempre (evidencia de que aconteceu);
    - horario planejado ja passou e sem realizacao confirmada -> ESTADO
      DESCONHECIDO: propoe, nao aplica (pode estar em andamento);
    - caso contrario             -> nao iniciada, elegivel.

    A data e a do sistema local (`date.today()`), que e o que o resto do projeto
    usa: nao existe configuracao de fuso suportada, e criar uma seria uma
    refatoracao global de datas fora do escopo deste passo. Ver a SPEC.
    """
    today = today or date.today()
    now = now or datetime.now()
    alvo = today.isoformat()
    treino = next((w for w in (plan or []) if w["day"] == alvo), None)
    if treino is None:
        return ReadinessEligibility(None, "sem_sessao", False,
                                    "hoje nao tem treino no plano")
    if treino.get("focus") not in QUALITY_FOCUSES:
        return ReadinessEligibility(treino, SESSAO_NAO_PUBLICADA, False,
                                    f"o treino de hoje e {treino.get('focus')}, "
                                    "nao uma sessao de qualidade")
    estado = session_execution_state(treino, events)
    if estado == SESSAO_CONCLUIDA:
        return ReadinessEligibility(treino, estado, False,
                                    "o treino de hoje ja foi realizado; "
                                    "preservado")
    if estado == SESSAO_SEM_IDENTIDADE:
        return ReadinessEligibility(treino, estado, False,
                                    "o treino de hoje nao tem external_id; "
                                    "nao da para confirmar o estado")
    inicio = _planned_start(alvo)
    if now >= inicio:
        return ReadinessEligibility(
            treino, SESSAO_DESCONHECIDA, False,
            f"o horario planejado ({inicio.strftime('%H:%M')}) ja passou e o "
            "Intervals nao confirma a realizacao; pode haver treino em "
            "andamento com sincronizacao pendente")
    return ReadinessEligibility(treino, estado, True,
                               "sessao de hoje ainda nao iniciada")


def rebuild_workout(workout, params, ftp=DEFAULT_FTP):
    """Reconstroi o registro do plano a partir de `params`, preservando identidade.

    `planned_duration`, `name`, `tss` e `focus` sao DERIVADOS de `params`, entao
    recalcula-los aqui e nao no CLI: um segundo lugar que recontaisses volume
    seria um segundo motor de adaptacao, que e o que a SPEC proibe.
    """
    focus = params.focus
    duration = sum((params.warmup_sec,
                    params.repeats * (params.on_sec + params.off_sec),
                    params.cooldown_sec))
    novo = PlannedWorkout(
        day=workout["day"], focus=focus, planned_duration=duration,
        name=workout_name(workout["day"], focus),
        params=_params_dict(params), tss=float(estimate_tss(params, ftp)),
        external_id=workout["external_id"], ftp_watts=int(ftp))
    saida = _as_dict(novo)
    # `hr_mode` nao vem de `params`: e uma marca de prescricao do registro
    # original e precisa sobreviver a reconstrucao (ver `reconcile`).
    if workout.get("hr_mode"):
        saida["hr_mode"] = True
    return saida


def _readiness_dirige(state, day):
    """A prontidao dirigiu a adaptacao deste dia, ou so o TSB agiu?

    Distingue os dois casos porque o livro-razao do orcamento so deve preservar
    o TSS pre-intervencao quando a PRONTIDAO foi a fonte da mudanca. Marcar
    `readiness_agiu` pela simples presenca de `state.readiness` fazia uma decisao
    `NONE` (que nao adapta nada) alterar o plano assim que o TSB agisse: o
    registro usava `tss_pre` e a reducao por TSB devolvia menos teto do que
    devolvia antes. Medido com TSB -30 e decisao NONE: carga total 173 -> 166.

    Portanto: a prontidao dirigiu se e uma `ReadinessDecision`, se a acao e
    adaptativa, se a leitura vale para este dia, e se o TSB nao forçou REPLACE.

    A ultima condicao importa: com TSB abaixo do limite a acao ja e REPLACE por
    TSB, e a prontidao nao dirigiu nada. Sem ela, uma decisao REDUCE inflava o
    razao com o `tss_pre` do treino que o proprio TSB tinha substituido por Z2,
    e cortava um dia seguinte que o plano de referencia nao cortava
    (medido: 18/09 de 39 para 32), alem de reportar "aplicada" indevidamente.
    """
    if state.tsb < TSB_ADAPT_LIMIT:
        return False
    decisao = state.readiness
    if not isinstance(decisao, ReadinessDecision):
        return False
    if not decisao.is_adaptive:
        return False
    return day is None or _readiness_applies_on(decisao, day)


def _adapt_session(params, state, day=None):
    """Adapta a sessao quando o estado diario pede. Duas fontes, uma so saida.

    Fontes: TSB (regra historica, preservada como estava) e a decisao de
    prontidao (issue #58 Passo A). **Precedencia: a regra mais restritiva
    vence e nenhuma desfaz a outra.**

    - TSB < -15            -> REPLACE (comportamento historico, inalterado)
    - prontidao REPLACE    -> REPLACE, so no dia que o sinal descreve
    - prontidao REDUCE     -> REDUCE, so no dia que o sinal descreve
    - prontidao NONE       -> nao mexe

    Nao existe "dupla reducao": a escalao e unica e ordenada, e REDUCE nunca
    e aplicado sobre um REPLACE. `NONE` por prontidao nao impede a adaptacao
    por TSB, porque as duas fontes sao avaliadas antes de escolher a acao.

    O escopo por dia (`_readiness_applies_on`) vale **apenas para prontidao**.
    `day` e o dia do plano em montagem, em ISO. Sem `day` (chamadores antigos),
    a prontidao continua sem escopo e o comportamento e o de sempre.

    `state.readiness` carrega um `ReadinessDecision` (ver
    `readiness.readiness_decision`); `None` significa "sem avaliacao", e e o
    que os chamadores antigos continuam passando.
    """
    quality = (FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2)
    tsb_forca_replace = state.tsb < TSB_ADAPT_LIMIT
    decisao = state.readiness
    acao_readiness = (decisao.action if isinstance(decisao, ReadinessDecision)
                      else ReadinessAction.NONE)

    if tsb_forca_replace:
        acao = ReadinessAction.REPLACE
    else:
        # Escapa por dia: fora do dia que a leitura descreve, a prontidao nao
        # vota. TSB acima ja estava descartado aqui.
        acao = acao_readiness if (day is None or not isinstance(decisao, ReadinessDecision)
                                  or _readiness_applies_on(decisao, day)) \
            else ReadinessAction.NONE

    if acao is ReadinessAction.NONE or params.focus not in quality:
        return params
    if acao is ReadinessAction.REPLACE:
        return readiness_mod.legacy_recovery_params()
    return _reduce_for_readiness(params)


def _reduce_for_readiness(params):
    """REDUCE: um degrau da escada de volume-antes-potencia.

    Reusa `_reduce_one_step` — a mesma escada e os mesmos fatores de
    `_fit_budget` — para que reduzir por prontidao e reduzir por orcamento nao
    possam divergir. Um degrau porque a magnitude nao esta calibrada: e uma
    escolha de projeto, marcada como tal, e nao um percentual com lastro
    cientifico (ver `docs/SPEC-passo-A-readiness.md`).

    Garantias: preserva `focus`, tipo e ordem dos segmentos, nunca aumenta
    intensidade nem duracao, e nunca baixa `on_power` abaixo do piso da zona.
    Devolve o MESMO objeto quando nao ha o que reduzir, para o chamador
    distinguir "adaptou" de "nao-adaptou" por identidade.
    """
    piso = zone_floor(params.focus)
    repeats, on_sec, off_sec, on_power, mudou = _reduce_one_step(
        params, piso, params.repeats, params.on_sec, params.off_sec, params.on_power)
    if not mudou:
        return params
    return _apply_state(params, repeats, on_sec, off_sec, on_power)


# Janela (dias) usada para derivar a carga media e, portanto, o teto semanal.
# Fonte unica: build_plan e o reconcile DEVEM usar a mesma, senao derivam tetos
# diferentes da mesma carga e o reconcile absorve por cima/por baixo do plano.
BUDGET_WINDOW_DAYS = 60


def avg_load(events, window_days=BUDGET_WINDOW_DAYS, realized_only=True):
    """Carga media por DIA DE TREINO na janela, para derivar o cap diario.

    `realized_only` ignora eventos de treino nunca executados (planned sem
    `paired_activity_id`): carga prescrita nao e evidencia de tolerancia. Sem
    sessao realizada na janela, cai no fallback conservador de 40 TSS/dia.
    """
    loads = []
    cutoff = date.today() - timedelta(days=window_days)
    for item in events:
        if realized_only and not _is_completed(item):
            continue
        day = _day(item)
        load = _num(_field(item, "training_load"))
        if day and load and load > 0 and day >= cutoff:
            loads.append(load)
    return sum(loads) / len(loads) if loads else 40.0


def daily_tss_cap(avg):
    return max(35, min(200, int(avg * 0.95)))


def weekly_budget(avg, training_days=DEFAULT_TRAINING_DAYS, scale=1.0):
    """Orcamento de TSS para a janela de 7 dias.

    `avg_load` e media por DIA DE TREINO, nao por dia-calendario: multiplicar
    por 7 concedia 7 sessoes numa semana que so tem `len(training_days)`
    treinos, inflando o teto em 7/n (1,4x com 5 dias). O teto e o cap diario
    vezes os dias de treino da semana.
    """
    cap = max(1, int(daily_tss_cap(avg) * scale))
    return cap * max(1, len(training_days))


def _recovery_budget(recovery_ramp, day_index, default):
    """Teto semanal da rampa de retorno a forma (#19) para o dia `day_index`
    (0-base a partir do inicio do plano). Semana = dia//7; alem do fim da
    rampa, mantem o ultimo teto (nao deixa de capar)."""
    if not recovery_ramp:
        return default
    return recovery_ramp[min(day_index // 7, len(recovery_ramp) - 1)]


def _validate_zone_intent(focus, params):
    """Resolve a familia semantica declarada pelo foco, sem prescrever nada.

    Focos fora das familias atuais (como VO2max) seguem pelo fluxo existente.
    """
    if params.focus != focus:
        raise ValueError("focus e params.focus precisam declarar a mesma intencao")
    try:
        return zone_intent.describe(focus)
    except KeyError:
        return None


_PHASE_ENGINE = training_phase_mod.TrainingPhaseEngine()


def _focus_stimulus(focus):
    """Familia de estimulo canonica de um foco prescrito (para o alinhamento
    advisory). `None` quando o foco nao e mapeavel — o alinhamento fica de fora
    em vez de emitir observacao falsa."""
    return {
        FOCUS_ZONE2: "zone2",
        ENDURANCE: "zone2",
        FOCUS_SWEETSPOT: "sweetspot",
        FOCUS_THRESHOLD: "threshold",
        FOCUS_VO2: "vo2max",
    }.get(focus)


def derive_plan_phase(goal, race_date, day):
    """Fase semantica advisory do dia — observacional, no padrao de zone_intent.

    Deriva a fase apenas de GOAL + calendario (race_date/start). Nao usa TSB,
    CTL, readiness, wellness, FTP, VO2 nem Pw:HR; nao alimenta prescricao (o
    valor nunca entra no PlannedWorkout) e nao toca a fase legada
    (`state.phase`/`phase_weekly_template`).

    Regras v1:
    - GOAL_START_PHASE define a fase inicial (tabela explicita por GOAL);
    - `race` com race_date valida rotula PEAK na janela de taper
      (0 <= (prova - dia) < TAPER_DAYS), incluindo o dia da prova;
    - fora do taper nao ha PEAK; TEST/RECOVERY nunca sao inferidos
      automaticamente (exigem contexto explicito, fora desta integracao);
    - race sem data valida usa o fallback da tabela (BUILD), sem PEAK.
    """
    if goal == "race" and race_date:
        try:
            days_to_race = (date.fromisoformat(race_date) - day).days
        except (TypeError, ValueError):
            days_to_race = None
        if days_to_race is not None and 0 <= days_to_race < TAPER_DAYS:
            return TrainingPhase.PEAK
    return GOAL_START_PHASE.get(goal, TrainingPhase.BUILD)


def _record_phase_report(phase_report, goal, race_date, day, focus):
    """Preenche a entrada advisory do dia. Nunca altera prescricao.

    `phase_report` e dict preenchido in-place (seam opcional, mesmo contrato de
    `readiness_report`); `None` desliga o seam por completo. O alinhamento e
    neutro: "match"/"mismatch" entre a familia do foco final e os estimulos da
    fase, sem diagnostico fisiologico.
    """
    if phase_report is None:
        return
    phase = derive_plan_phase(goal, race_date, day)
    entry = {"phase": phase.value}
    stimulus = _focus_stimulus(focus)
    if stimulus is not None:
        definition = _PHASE_ENGINE.definition(phase)
        alinhado = (stimulus in definition.priority_stimuli or
                    stimulus in definition.secondary_stimuli)
        entry["template_alignment"] = "match" if alinhado else "mismatch"
    phase_report[day.isoformat()] = entry


def build_plan(events, tsb, ftp=DEFAULT_FTP, days=14, start=None, existing=None,
               training_days=DEFAULT_TRAINING_DAYS, goal=None, race_date=None,
               ftp_test_date=None, weekly_hours=None, long_day=None,
               hr_mode=False, recovery_ramp=None, periodization=None,
               readiness=None, readiness_report=None, phase_report=None,
               min_regular_duration_sec=None, active_recovery_days=()):
    # `readiness_report` e preenchido in-place para o CLI relatar o desfecho da
    # avaliacao sem alterar o retorno (que e a lista de treinos, contrato).
    readiness_report = {} if readiness_report is None else readiness_report
    active_recovery_days = tuple(sorted(set(active_recovery_days)))
    if not set(active_recovery_days).issubset(training_days):
        raise ValueError("active_recovery_days deve estar contido em training_days")
    today = date.today()
    if isinstance(existing, dict) and "workouts" in existing:
        existing = existing["workouts"]
    if start is None:
        start = today + timedelta(days=1)
        if existing and today.weekday() in training_days:
            kept = [w for w in existing if w["day"] == today.isoformat()]
            if kept:
                # A sessao de hoje vem do plano anterior, verbatim. Se a leitura
                # de prontidao for sobre hoje, ela nao pode ser aplicada aqui:
                # "preservar o treino de hoje" e contrato, e reescrever o treino
                # de hoje seria contradize-lo. Registrado para o CLI explicar.
                if isinstance(readiness, ReadinessDecision) and \
                        readiness.applies_to_day == today.isoformat():
                    readiness_report.setdefault("situacao",
                                                "sessao_do_dia_preservada")
                sessao = dict(kept[0])
                # Esta e a UNICA saida de `build_plan` que nao constroi a
                # sessao, entao e por aqui que uma entrada gravada antes da
                # introducao de `ftp_watts` escapa sem o campo. O relatorio
                # recusa o perfil (contrato: nao inferir watts do `.env`), e a
                # sessao de HOJE -- o dia que o painel descreve -- ficava sem
                # grafico. Carimba a MESMA referencia FTP usada para estimar o
                # TSS das demais sessoes desta chamada.
                sessao.setdefault("ftp_watts", int(ftp))
                _record_phase_report(phase_report, goal, race_date, today,
                                     sessao.get("focus", FOCUS_ZONE2))
                plan = [sessao]
                recent = [(today, sessao["tss"])]
                return plan + build_plan(events, tsb, ftp=ftp, days=days,
                                         start=start,
                                         training_days=training_days,
                                         goal=goal, race_date=race_date,
                                          ftp_test_date=ftp_test_date,
                                          weekly_hours=weekly_hours,
                                          long_day=long_day, hr_mode=hr_mode,
                                          recovery_ramp=recovery_ramp,
                                          periodization=periodization,
                                          readiness=readiness,
                                          readiness_report=readiness_report,
                                          phase_report=phase_report,
                                          min_regular_duration_sec=min_regular_duration_sec,
                                          active_recovery_days=active_recovery_days)
    slots = sorted(training_days)
    scale = GOAL_BUDGET_SCALE.get(goal, 1.0)
    avg = avg_load(events)
    cap = max(1, int(daily_tss_cap(avg) * scale))
    budget = weekly_budget(avg, training_days, scale)
    state = training_plan_state(goal, race_date, start, budget,
                                avg * len(training_days), tsb, readiness)
    weekly = phase_weekly_template(state, periodization)
    weekly = _place_long_day(weekly, long_day, slots)
    volume_scale = _volume_scale(weekly, weekly_hours, slots)
    plan = []
    recent = []  # (day, tss) dos ultimos 7 dias
    adapted = False
    notas = []
    dias_do_plano = set()
    dias_qualidade = set()
    for i in range(days):
        day = start + timedelta(days=i)
        if day.weekday() not in training_days:
            continue
        budget = _recovery_budget(recovery_ramp, i, budget)
        focus = weekly[slots.index(day.weekday()) % len(weekly)]
        taper = _taper_focus(goal, day, race_date)
        if taper is not None:
            focus, params, phase = taper
            day_name = f"{day.isoformat()} - {RACE_PHASE_LABELS[phase]}"
        elif day.weekday() in active_recovery_days:
            focus = FOCUS_ZONE2
            params = _active_recovery_params()
            day_name = f"{day.isoformat()} - Recuperacao ativa (Z2)"
        else:
            params = WorkoutParams(focus=focus, **_block_for(focus, i, goal))
            params = _scale_duration(params, volume_scale)
            day_name = workout_name(day.isoformat(), focus)
        # Issue #58 Passo A revisao 2: uma intervencao de prontidao nao pode
        # devolver orcamento para os dias seguintes. `tss_pre` e a carga que a
        # sessao teria sem a intervencao, e e ela que entra no livro-razon.
        # O teto e um GUARDA-CHUVA, nao uma meta: ficar abaixo dele e correto,
        # e "o atleta reduziu hoje, logo aguenta mais amanha" e exatamente a
        # inferencia que nao se pode fazer a partir de um sinal de um dia so.
        tss_pre = estimate_tss(params, ftp)
        readiness_agiu = False
        dias_do_plano.add(day.isoformat())
        if params.focus in (FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2):
            dias_qualidade.add(day.isoformat())
        if day.weekday() not in active_recovery_days and not adapted:
            adjusted = _adapt_session(params, state, day.isoformat())
            if adjusted is not params:
                params = adjusted
                focus = params.focus
                day_name = workout_name(day.isoformat(), focus)
                adapted = True
                readiness_agiu = _readiness_dirige(state, day.isoformat())
                notas.append((day.isoformat(), readiness_agiu))
        # A intencao e derivada do foco final. O perfil nao entra no workout,
        # preservando `focus` como a unica fonte de verdade publicada.
        _validate_zone_intent(focus, params)
        _record_phase_report(phase_report, goal, race_date, day, focus)
        tss = estimate_tss(params, ftp)
        if tss > cap:
            factor = max(0.4, cap / tss)
            params = WorkoutParams(**{**params.__dict__,
                                      "on_sec": max(120, int(params.on_sec * factor))})
            tss = estimate_tss(params, ftp)
        params, tss = _fit_budget(params, tss, recent, budget, ftp)
        if taper is None:
            params, tss = _enforce_min_regular_duration(
                params, tss, recent, budget, cap, ftp,
                min_duration_sec=min_regular_duration_sec,
                budget_or_readiness_protected=readiness_agiu)
        duration = sum((params.warmup_sec,
                        params.repeats * (params.on_sec + params.off_sec),
                        params.cooldown_sec))
        plan.append(PlannedWorkout(
            day=day.isoformat(), focus=focus,
            planned_duration=duration,
            name=day_name,
            params=_params_dict(params), tss=float(tss),
            external_id=f"{EXTERNAL_ID_PREFIX}-{day.isoformat()}",
            ftp_watts=int(ftp),
        ))
        recent.append((day, tss_pre if readiness_agiu else tss))
        while recent and day - recent[0][0] >= timedelta(days=7):
            recent.pop(0)
    plan = [_as_dict(w) for w in plan]
    # Relatorio de aplicacao da prontidao. `build_plan` devolve a lista de
    # treinos (contrato preservado), entao o desfecho vai por `readiness_report`,
    # um dict que o chamador pode passar e que o motor preenche in-place. Sem
    # ele, o CLI nao tem como dizer "a leitura nao foi aplicada porque..." em
    # vez de ficar em silencio.
    aplicada = [d for d, por_readiness in notas if por_readiness]
    readiness_report.update({
        "aplicada_em": aplicada,
        "adaptacoes": len(notas),
        "situacao": _readiness_situacao(
            readiness, aplicada,
            readiness_report.get("situacao") == "sessao_do_dia_preservada",
            dias_do_plano, dias_qualidade),
    })
    # Preparacao do teste de FTP: o ciclo do dia manda no teste, nao no
    # template. Protege as 48h antes (D-2 facil, D-1 spin), cria o evento do
    # teste (D0) e a recuperacao pos-teste (D+1).
    plan = _protect_ftp_test(plan, ftp_test_date, training_days,
                             start, days, ftp)
    # Dia da prova (GOAL=race): garante o evento na data, mesmo fora da agenda.
    plan = _protect_race(plan, race_date, training_days, start, days, ftp)
    # Modo FC (#3): prescricao sem medidor de potencia (%FTHR + RPE). Todos os
    # workouts do plano carregam a marca para o push escolher HR.
    if hr_mode:
        for w in plan:
            w["hr_mode"] = True
    return plan


def _readiness_situacao(readiness, aplicada, preservada, dias_do_plano,
                        dias_qualidade):
    """Por que a leitura de prontidao foi ou nao aplicada. Sem isto, o CLI
    ficaria em silencio quando um sinal ruim nao chega a tocar em nada, e o
    atleta nao distinguiria "prontidao ok" de "prontidao ruim mas nada foi
    adaptationado".

    `situacao` e um rotulo estavel; o texto vem em `SITUACOES_READINESS`.
    """
    if not isinstance(readiness, ReadinessDecision):
        return "sem_avaliacao"
    if not readiness.is_adaptive:
        return "nenhuma_adaptacao_necessaria"
    if preservada:
        return "sessao_do_dia_preservada"
    alvo = readiness.applies_to_day
    if alvo is None:
        return "aplicada" if aplicada else "sem_ancora_de_dia"
    if alvo in aplicada:
        return "aplicada"
    if alvo not in dias_do_plano:
        return "dia_alvo_fora_do_plano"
    if alvo in dias_qualidade:
        return "outra_adaptacao_ocorreu_antes"
    return "sem_sessao_de_qualidade_no_dia"


SITUACOES_READINESS = {
    "aplicada": "aplicada",
    "sem_avaliacao": "sem avaliacao de recuperacao",
    "nenhuma_adaptacao_necessaria": "nenhuma adaptacao necessaria",
    "sem_ancora_de_dia": "aplicada (decisao sem ancora de dia)",
    "dia_alvo_fora_do_plano": "leitura e de um dia fora do plano; "
                              "nao foi transferida para outra sessao",
    "sem_sessao_de_qualidade_no_dia": "o dia da leitura nao tem sessao de "
                                       "qualidade; nada foi adaptado",
    "outra_adaptacao_ocorreu_antes": "outra adaptacao ja tinha ocorrido antes "
                                     "no mesmo plano",
    "sessao_do_dia_preservada": "sessao do dia preservada do plano anterior; "
                                "preservacao tem precedencia",
}


def _block_for(focus, slot, goal):
    """Bloco do foco. Com GOAL ativo, rotaciona as variantes de formato para o
    plano nao ficar monotonico; sem GOAL, usa o template atual."""
    if goal is None:
        return templates()[focus]
    variants = BLOCK_VARIANTS.get(focus, [templates()[focus]])
    return variants[slot % len(variants)]


def _taper_focus(goal, day, race_date):
    """GOAL=race com prova proxima: ultima semana antes de RACE_DATE vira
    preparacao progressiva (periodizacao de Joe Friel):

    - D-6        -> `sharpening`: ultimo estimulo de qualidade curto
                    (Limiar ~2x6') — "abrir a perna" antes de descarregar;
    - D-5..D-3   -> `recovery`: Z2 curto (descarregar fatigue);
    - D-2/D-1    -> `spin`: muito leve (<60% FTP) — o dia antes importa mais
                    que o estimulo (o CTL decai devagar, a fatigue cai rapido).

    Retorna (focus, params, fase) ou None. O dia da prova (D0) e tratado por
    `_protect_race` (evento usando, fora da agenda)."""
    if goal != "race" or not race_date:
        return None
    try:
        race = date.fromisoformat(race_date)
    except (TypeError, ValueError):
        return None
    delta = (race - day).days
    if delta < 0:
        return None  # prova ja passou: volta ao template normal
    if delta >= TAPER_DAYS:
        return None
    if delta == RACE_SHARPENING_DELTA:
        # Ultimo estimulo: Limiar curto (2x6' ~rFTP), tipo-prova.
        return (FOCUS_THRESHOLD,
                WorkoutParams(focus=FOCUS_THRESHOLD, repeats=2, on_sec=360,
                              off_sec=180, on_power=0.97, off_power=0.55,
                              cadence=90, cadence_rest=90),
                "sharpening")
    if delta in (1, 2):
        # Spin: muito leve, so para nao zerar o dia por completo.
        return (FOCUS_ZONE2,
                WorkoutParams(focus=FOCUS_ZONE2, repeats=1, on_sec=1080,
                              off_sec=0, on_power=0.50, off_power=0.50,
                              cadence=90, cadence_rest=90),
                "spin")
    # D-5..D-3: recuperacao Z2 curta.
    return (FOCUS_ZONE2,
            WorkoutParams(focus=FOCUS_ZONE2, repeats=1, on_sec=1200,
                          off_sec=0, on_power=0.60, off_power=0.55,
                          cadence=90, cadence_rest=90),
            "recovery")


def _prep_workout(day, kind, ftp):
    """Workout leve ao redor do teste de FTP (consenso dos treinadores):
    - d-2: recuperacao facil (sem treino duro nas 48h antes do teste)
    - d-1: spin muito facil (<65% FTP) — o dia antes importa mais que o teste
    - d0 : evento do proprio Ramp Test (app Zwift), so warmup/instrucao
    - d+1: recuperacao pos-teste
    Retorna um PlannedWorkout do dia."""
    zones = {
        "d-2": ("Recuperacao (pre-teste FTP)", 2400, 0.55),
        "d-1": ("Spin facil (pre-teste FTP)", 1800, 0.50),
        "d0": ("Ramp Test (FTP)", 1800, 0.55),
        "d+1": ("Recuperacao (pos-teste FTP)", 1800, 0.55),
    }
    name, on_sec, on_power = zones[kind]
    params = WorkoutParams(focus=FOCUS_ZONE2, repeats=1, on_sec=on_sec,
                           off_sec=0, on_power=on_power, off_power=on_power,
                           cadence=90, cadence_rest=90)
    tss = estimate_tss(params, ftp)
    duration = (params.warmup_sec
                + params.repeats * (params.on_sec + params.off_sec)
                + params.cooldown_sec)
    return PlannedWorkout(
        day=day.isoformat(), focus=FOCUS_ZONE2,
        planned_duration=duration,
        name=f"{day.isoformat()} - {name}",
        params=_params_dict(params), tss=float(tss),
        external_id=f"{EXTERNAL_ID_PREFIX}-{day.isoformat()}",
        ftp_watts=int(ftp),
    )


def _protect_ftp_test(plan, ftp_test_date, training_days, start, days, ftp):
    """Protege os dias ao redor de um teste de FTP agendado: D-2 e D-1 viram
    treino facil (nada de VO2/Limiar nas 48h antes), D0 recebe o evento do
    teste (sempre, mesmo fora da agenda — e um lembrete) e D+1 recuperacao.
    Dias de descanso natural (fora da agenda) ficam como estao."""
    test = parse_ftp_test_date(ftp_test_date)
    if test is None:
        return plan
    horizon_start = start
    horizon_end = start + timedelta(days=days)
    if test < horizon_start or test >= horizon_end:
        return plan  # teste fora do horizonte do plano: nada a fazer
    preps = {test - timedelta(days=2): "d-2",
             test - timedelta(days=1): "d-1",
             test: "d0",
             test + timedelta(days=1): "d+1"}
    kept = [w for w in plan if date.fromisoformat(w["day"]) not in preps]
    for d, kind in sorted(preps.items()):
        if d < horizon_start or d >= horizon_end:
            continue
        if d != test and d.weekday() not in training_days:
            continue  # descanso natural do dia fora da agenda: nada a criar
        kept.append(_as_dict(_prep_workout(d, kind, ftp)))
    kept.sort(key=lambda w: w["day"])
    return kept


def _race_workout(day, ftp):
    """Evento do dia da prova (GOAL=race): marcador no calendario com TSS 0 —
    a carga real da prova entra pela API depois. O TSB projetado nesse dia
    reflete o estado de chegada (descansado), como quer a periodizacao."""
    params = WorkoutParams(focus=FOCUS_ZONE2, repeats=0, on_sec=0, off_sec=0,
                           on_power=0.60, off_power=0.55, cadence=90,
                           cadence_rest=90)
    duration = sum((params.warmup_sec,
                    params.repeats * (params.on_sec + params.off_sec),
                    params.cooldown_sec))
    return PlannedWorkout(
        day=day.isoformat(), focus=FOCUS_ZONE2,
        planned_duration=duration,
        name=f"{day.isoformat()} - Prova: dia de prova",
        params=_params_dict(params), tss=0.0,
        external_id=f"{EXTERNAL_ID_PREFIX}-race-{day.isoformat()}",
        ftp_watts=int(ftp),
    )


def _race_recovery(day, ftp):
    """Recuperacao pos-prova (D+1): spin leve para o corpo voltar ao normal
    depois do esforco de prova."""
    params = WorkoutParams(focus=FOCUS_ZONE2, repeats=1, on_sec=1080,
                           off_sec=0, on_power=0.50, off_power=0.50,
                           cadence=90, cadence_rest=90)
    tss = estimate_tss(params, ftp)
    return PlannedWorkout(
        day=day.isoformat(), focus=FOCUS_ZONE2,
        planned_duration=sum((params.warmup_sec,
                              params.repeats * (params.on_sec + params.off_sec),
                              params.cooldown_sec)),
        name=f"{day.isoformat()} - Recuperacao (pos-prova)",
        params=_params_dict(params), tss=float(tss),
        external_id=f"{EXTERNAL_ID_PREFIX}-{day.isoformat()}",
        ftp_watts=int(ftp),
    )


def _protect_race(plan, race_date, training_days, start, days, ftp):
    """Garante o dia da prova no plano (GOAL=race): o evento 'Prova' entra
    SEMPRE na data, mesmo fora da agenda de treino (o atleta corre em qualquer
    dia); D+1 vira recuperacao leve quando for dia de treino."""
    if not race_date:
        return plan
    try:
        race = date.fromisoformat(race_date)
    except (TypeError, ValueError):
        return plan
    horizon_start = start
    horizon_end = start + timedelta(days=days)
    if race < horizon_start or race >= horizon_end:
        return plan  # prova fora do horizonte do plano: nada a fazer
    preps = {race: "race", race + timedelta(days=1): "after"}
    kept = [w for w in plan if date.fromisoformat(w["day"]) not in preps]
    for d, kind in sorted(preps.items()):
        if d < horizon_start or d >= horizon_end:
            continue
        if kind == "after" and d.weekday() not in training_days:
            continue  # descanso natural: nada a criar
        w = _race_workout(d, ftp) if kind == "race" else _race_recovery(d, ftp)
        kept.append(_as_dict(w))
    kept.sort(key=lambda w: w["day"])
    return kept


def _reduce_one_step(params, piso, repeats, on_sec, off_sec, on_power):
    """Aplica UM degrau da escada de reducao e devolve o novo estado.

    Escada de reducao (documentada em `_fit_budget`): volume antes de
    intensidade, e `on_power` nunca abaixo do piso da zona. Extrair o degrau
    permite que a reducao por prontidao use exatamente a mesma politica e os
    mesmos fatores do ajuste por orcamento, sem duplicar numeros.

    Devolve `(repeats, on_sec, off_sec, on_power, mudou)`.
    """
    if repeats > 1:
        return repeats - 1, on_sec, off_sec, on_power, True
    if on_sec > 120:
        return repeats, max(120, int(on_sec * 0.8)), off_sec, on_power, True
    if off_sec > 0:
        return repeats, on_sec, max(0, int(off_sec * 0.8)), on_power, True
    if piso is not None and on_power > piso:
        return repeats, on_sec, off_sec, max(piso, round(on_power - 0.05, 2)), True
    return repeats, on_sec, off_sec, on_power, False


def _apply_state(params, repeats, on_sec, off_sec, on_power):
    return WorkoutParams(**{**params.__dict__, "repeats": repeats,
                            "on_sec": on_sec, "off_sec": off_sec,
                            "on_power": on_power})


def _fit_budget(params, tss, recent, budget, ftp):
    """Reduz a carga deste dia para que a soma rolante de 7 dias nao estoure o
    orcamento semanal, SEM quebrar a zona que o treino declara.

    Ordem de reducao. As tres primeiras sao reducoes de VOLUME: preservam
    integralmente a intensidade e, portanto, a zona e o nome do treino.
      1. `repeats` - cortar um intervalo inteiro (3x15min -> 2x15min) e o corte de
         volume mais honesto: nao altera o estímulo-alvo, so a quantidade.
      2. `on_sec` - encurta o trabalho dentro do intervalo.
      3. `off_sec` - encurta a recuperacao entre intervalos (corte de sessao).
      4. `on_power` - ULTIMO recurso, e so ate o PISO de %FTP da zona
         (`ZONE_BANDS`). Ex.: Sweet Spot 0.88 -> 0.84 ainda e Sweet Spot.

    Regra inviolavel: `on_power` nunca fica abaixo do piso da zona. A versao
    anterior descia ate 0.55 fixo, o que rebaixava um treino de `sweetspot`
    (piso 0.84) para um estimulo de recuperacao - mantendo o nome "Treino de
    Sweet Spot" e o `focus` intactos. Isso e pior que estourar o teto: produz
    um treino nomeado que nao entrega a zona prometida, e ainda quebra a
    deteccao de active recovery (que se baseia em `on_power`).

    A escada esta extraida em `_reduce_one_step` e e compartilhada com a
    reducao por prontidao (`_adapt_session`), para que os dois caminhos
    usem os mesmos fatores e o mesmo piso de zona.
    """
    used = sum(t for _, t in recent)
    if used + tss <= budget:
        return params, tss
    piso = zone_floor(params.focus)
    repeats, on_sec, off_sec, on_power = (params.repeats, params.on_sec,
                                          params.off_sec, params.on_power)
    for _ in range(30):
        if used + tss <= budget:
            break
        repeats, on_sec, off_sec, on_power, mudou = _reduce_one_step(
            params, piso, repeats, on_sec, off_sec, on_power)
        if not mudou:
            # 5) nao cabe sem sair da zona. O limite de zona vale mais que o
            #    teto: nao rebaixamos o estimulo para forcar a conta.
            break
        params = _apply_state(params, repeats, on_sec, off_sec, on_power)
        tss = estimate_tss(params, ftp)
    return params, tss


def _enforce_min_regular_duration(params, tss, recent, budget, cap, ftp,
                                  min_duration_sec,
                                  budget_or_readiness_protected):
    """Leva sessao regular a 60min quando ha margem de carga.

    O minimo do atleta e uma preferencia de disponibilidade, nao permissao para
    ultrapassar protecoes. Por isso readiness, cap diario e teto semanal vencem
    o minimo. A extensao divide volume facil entre aquecimento e desaquecimento,
    preservando integralmente blocos de trabalho, foco e zona declarada.
    """
    if min_duration_sec is None:
        return params, tss
    duration = (params.warmup_sec + params.repeats *
                (params.on_sec + params.off_sec) + params.cooldown_sec)
    if duration >= min_duration_sec or budget_or_readiness_protected:
        return params, tss
    extra = min_duration_sec - duration
    candidate = WorkoutParams(**{
        **params.__dict__,
        "warmup_sec": params.warmup_sec + extra // 2,
        "cooldown_sec": params.cooldown_sec + extra - extra // 2,
    })
    candidate_tss = estimate_tss(candidate, ftp)
    used = sum(load for _, load in recent)
    if candidate_tss > cap or used + candidate_tss > budget:
        return params, tss
    return candidate, candidate_tss


def _params_dict(params):
    return {
        "focus": params.focus,
        "warmup_sec": params.warmup_sec, "warmup_cadence": params.warmup_cadence,
        "warmup_power_low": params.warmup_power_low,
        "warmup_power_high": params.warmup_power_high,
        "repeats": params.repeats, "on_sec": params.on_sec,
        "off_sec": params.off_sec, "on_power": params.on_power,
        "off_power": params.off_power, "cadence": params.cadence,
        "cadence_rest": params.cadence_rest, "cooldown_sec": params.cooldown_sec,
        "cooldown_cadence": params.cooldown_cadence,
        "cooldown_power_low": params.cooldown_power_low,
        "cooldown_power_high": params.cooldown_power_high,
    }


def planned_workout_profile(workout):
    """Projeta os ``params`` canônicos em blocos serializáveis para leitura.

    Esta é uma projeção do formato persistido em ``plan.json`` — não faz parsing
    de ``name``/``description`` nem estima blocos a partir de TSS ou duração.
    Watts são calculados com ``ftp_watts`` salvo na própria sessão; um plano
    legado sem essa referência não ganha um gráfico em watts inferido do `.env`.
    Quando os parâmetros estruturados não existem ou estão incompletos, mantém
    apenas os metadados canônicos disponíveis e declara ``has_structured_blocks``
    falso. Assim um consumidor visual pode mostrar um estado vazio honesto.

    A duração de um perfil estruturado é a soma exata dos blocos canônicos. Ela
    prevalece sobre um ``planned_duration`` legado eventualmente divergente para
    impedir que gráfico e metadados apresentem tempos diferentes.
    """
    workout = workout if isinstance(workout, dict) else {}
    params = workout.get("params")
    focus = workout.get("focus")
    if not focus and isinstance(params, dict):
        focus = params.get("focus")
    focus = str(focus or "")
    duration = _profile_int(workout.get("planned_duration"))
    tss = _profile_float(workout.get("tss"))
    intensity = _profile_float(workout.get("intensity_factor"))
    ftp = _profile_int(workout.get("ftp_watts"))
    profile = {
        "date": workout.get("day"),
        "title": workout.get("name") or FOCUS_LABELS_PT.get(focus, focus),
        "focus": focus or None,
        "focus_label": FOCUS_LABELS_PT.get(focus, focus or "Treino"),
        "duration_seconds": duration,
        "planned_tss": tss,
        "intensity_factor": intensity,
        "ftp_watts": ftp,
        "has_structured_blocks": False,
        "blocks": [],
    }
    if not isinstance(params, dict):
        return profile

    required = ("warmup_sec", "warmup_power_low", "warmup_power_high",
                "repeats", "on_sec", "on_power", "off_sec", "off_power",
                "cooldown_sec", "cooldown_power_low", "cooldown_power_high")
    if ftp is None or ftp <= 0 or any(key not in params for key in required):
        return profile

    warmup_sec = _profile_int(params["warmup_sec"])
    repeats = _profile_int(params["repeats"])
    on_sec = _profile_int(params["on_sec"])
    off_sec = _profile_int(params["off_sec"])
    cooldown_sec = _profile_int(params["cooldown_sec"])
    powers = [_profile_float(params[key]) for key in (
        "warmup_power_low", "warmup_power_high", "on_power", "off_power",
        "cooldown_power_low", "cooldown_power_high")]
    if (None in (warmup_sec, repeats, on_sec, off_sec, cooldown_sec)
            or any(power is None for power in powers)
            or warmup_sec < 0 or cooldown_sec < 0 or off_sec < 0
            or repeats < 1 or on_sec < 1):
        return profile

    warmup_low, warmup_high, on_power, off_power, cooldown_low, cooldown_high = powers
    blocks = []
    elapsed = 0

    def add(kind, seconds, start_pct, end_pct, label):
        nonlocal elapsed
        if seconds <= 0:
            return
        start = elapsed
        elapsed += seconds
        blocks.append({
            "kind": kind,
            "duration_seconds": seconds,
            "start_seconds": start,
            "end_seconds": elapsed,
            "start_pct_ftp": start_pct,
            "end_pct_ftp": end_pct,
            "start_watts": round(start_pct * ftp, 1),
            "end_watts": round(end_pct * ftp, 1),
            "label": label,
        })

    add("warmup", warmup_sec, warmup_low, warmup_high, "Aquecimento")
    focus_label = FOCUS_LABELS_PT.get(focus, focus or "Trabalho")
    for repeat in range(repeats):
        add("work", on_sec, on_power, on_power,
            f"{focus_label} · série {repeat + 1}")
        add("recovery", off_sec, off_power, off_power,
            f"Recuperação · série {repeat + 1}")
    add("cooldown", cooldown_sec, cooldown_low, cooldown_high, "Desaquecimento")

    if not blocks:
        return profile
    profile.update({
        "duration_seconds": elapsed,
        "ftp_watts": ftp,
        "has_structured_blocks": True,
        "blocks": blocks,
    })
    return profile


def _profile_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, float) and not value.is_integer():
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _profile_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _as_dict(w):
    return dataclasses.asdict(w)


def _day(item):
    raw = _field(item, "start_date")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw)[:19]).date()
    except ValueError:
        return None


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


CUE_LANGS = ("pt", "en")


def _normalize_lang(lang: str) -> str:
    """Defesa em profundidade: idioma invalido cai para 'pt' (ver nota
    defensiva de `workout_text`/`event_payload` no KNOWN_ISSUES). O argparse
    da CLI ja normaliza; aqui garantimos que nenhum chamador externo quebre
    com `KeyError: 'zz'`."""
    return lang if lang in CUE_LANGS else "pt"

# Roteiro explicativo da zona do dia (cue text no aquecimento). IMPORTANTE: o
# parser do Intervals.icu trunca o texto explicativo do passo no primeiro "%"
# (o resto e interpretado como target) e ignora texto apos a duracao. Por isso
# as mensagens escrevem "por cento"/"percent" por extenso e vem antes da
# duracao. Maiusculas/minusculas seguem o jeitao da frase.
FOCUS_ZONE_HINT = {
    FOCUS_ZONE2: {
        "pt": "a zona 2 fica entre 55 e 75 por cento do FTP",
        "en": "the zone 2 band sits between 55 and 75 percent of FTP",
    },
    FOCUS_SWEETSPOT: {
        "pt": "a zona de sweet spot fica entre 84 e 97 por cento do FTP",
        "en": "the sweet spot training zone sits between 84 and 97 percent of FTP",
    },
    FOCUS_THRESHOLD: {
        "pt": "a zona de limiar fica entre 95 e 105 por cento do FTP",
        "en": "the threshold zone sits between 95 and 105 percent of FTP",
    },
    FOCUS_VO2: {
        "pt": "a zona de VO2 Max fica acima de 105 por cento do FTP",
        "en": "the VO2 Max zone sits above 105 percent of FTP",
    },
    ENDURANCE: {
        "pt": "a endurance (resistencia longa) fica entre 65 e 85 por cento do FTP",
        "en": "the endurance band sits between 65 and 85 percent of FTP",
    },
}

FOCUS_LABELS_EN = {
    FOCUS_ZONE2: "zone 2",
    FOCUS_SWEETSPOT: "sweet spot",
    FOCUS_THRESHOLD: "threshold",
    FOCUS_VO2: "VO2 Max",
    ENDURANCE: "endurance",
}

# Prescricao sem medidor de potencia (#3): alvo em %FTHR por foco, com RPE
# como ancora quando o atleta nao tem medidor. A carga do dia continua sendo
# estimada pelo Intervals (icu_training_load), inclusive via FC (has_heartrate).
# Valores calibrados contra zonas de FC comuns (fração do FTHR/LTHR):
#   Z2 ~ 70-80%, Sweet Spot ~ 85-90%, Limiar ~ 95-100%, VO2 ~ 105%+.
FOCUS_HR_PCT = {
    FOCUS_ZONE2: 0.75,
    FOCUS_SWEETSPOT: 0.88,
    FOCUS_THRESHOLD: 0.98,
    FOCUS_VO2: 1.05,
    ENDURANCE: 0.75,
}

FOCUS_RPE = {
    FOCUS_ZONE2: "3-4",
    "endurance": "3-5",
    FOCUS_SWEETSPOT: "5-6",
    FOCUS_THRESHOLD: "7-8",
    FOCUS_VO2: "9-10",
}

# Roteiro explicativo da zona em %FTHR (modo FC / sem medidor de potencia).
# Mesma regra do parser: mensagens escrevem "por cento"/"percent" por extenso.
FOCUS_HR_HINT = {
    FOCUS_ZONE2: {
        "pt": "a zona 2 fica entre 65 e 80 por cento do FTHR",
        "en": "the zone 2 band sits between 65 and 80 percent of your HR threshold",
    },
    FOCUS_SWEETSPOT: {
        "pt": "a zona de sweet spot fica entre 84 e 93 por cento do FTHR",
        "en": "the sweet spot zone sits between 84 and 93 percent of your HR threshold",
    },
    FOCUS_THRESHOLD: {
        "pt": "a zona de limiar fica entre 95 e 100 por cento do FTHR",
        "en": "the threshold zone sits between 95 and 100 percent of your HR threshold",
    },
    FOCUS_VO2: {
        "pt": "a zona de VO2 Max fica acima de 100 por cento do FTHR",
        "en": "the VO2 Max zone sits above 100 percent of your HR threshold",
    },
    ENDURANCE: {
        "pt": "a endurance (resistencia longa) fica entre 65 e 80 por cento do FTHR",
        "en": "the endurance band sits between 65 and 80 percent of your HR threshold",
    },
}


def hr_target_bpm(focus, fthr):
    """FC alvo (bpm) do esforco do foco, a partir do FTHR (#3)."""
    return round(fthr * FOCUS_HR_PCT[focus])


def rpe_for_focus(focus):
    """Faixa RPE (escala 1-10) como ancora do esforco sem medidor de potencia."""
    return FOCUS_RPE.get(focus, "5-6")


def event_payload(workout, ftp=DEFAULT_FTP, desc=None, lang="pt", prev=None,
                  fthr=None):
    """Evento do calendario. Com `fthr` e o workout marcado `hr_mode` (#3), o
    target vira HR e o texto usa %FTHR + RPE; senao, POWER (%FTP). Nota: o
    Intervals usa o enum `HR` (nao `HEART_RATE`) no campo `target`."""
    hr = bool(workout.get("hr_mode")) and bool(fthr)
    lang = _normalize_lang(lang)
    return {
        "start_date_local": f"{workout['day']}T{START_TIME}",
        "category": "WORKOUT", "type": "Ride",
        "name": workout["name"],
        "description": desc or workout_text(workout, ftp, lang=lang, prev=prev,
                                            fthr=fthr),
        "planned_duration": workout["planned_duration"],
        "target": "HR" if hr else "POWER",
        "external_id": workout["external_id"],
    }


def workout_text(workout, ftp=DEFAULT_FTP, lang="pt", prev=None, fthr=None):
    """Descricao nativa do Intervals (workout builder): a primeira linha e o
    titulo do treino e cada passo e `texto duracao percentual%`. Os watts (ex:
    `83% (151w)`) sao calculados pelo Intervals a partir do FTP.

    Cada intervalo vira um passo proprio com uma mensagem explicativa antes da
    duracao (cue text -> textevent no .zwo). As repeticoes sao achatadas em
    passos individuais porque o parser do Intervals ignora o grupo `Nx` quando
    os passos internos trazem texto. O texto do cue nao pode conter "%".

    Com `fthr` e `hr_mode` no workout: prescricao por FC (#3) — os alvos usam
    %FTHR e cada serie traz o RPE como ancora (sem medidor de potencia)."""
    lang = _normalize_lang(lang)
    if workout.get("hr_mode") and fthr:
        return _workout_text_hr(workout, fthr, lang=lang, prev=prev)
    params = workout["params"]
    lines = [workout["name"], ""]
    lines.append(f"- {_warmup_msg(workout, lang, prev)} "
                 f"{_hm(params['warmup_sec'])} "
                 f"{_pct(params['warmup_power_low'])}-{_pct(params['warmup_power_high'])}%")
    for _ in range(max(1, params["repeats"])):
        lines.append(f"- {_interval_msg(params, lang)} "
                     f"{_hm(params['on_sec'])} {_pct(params['on_power'])}%")
        if params["off_sec"]:
            lines.append(f"- {_recovery_msg(params, lang)} "
                         f"{_hm(params['off_sec'])} {_pct(params['off_power'])}%")
    lines += ["",
              f"- {_cooldown_msg(params, lang)} "
              f"{_hm(params['cooldown_sec'])} "
              f"{_pct(params['cooldown_power_low'])}-{_pct(params['cooldown_power_high'])}%"]
    return "\n".join(lines)


def _workout_text_hr(workout, fthr, lang="pt", prev=None):
    """Texto em %FTHR + RPE para treino sem medidor de potencia (#3)."""
    params = workout["params"]
    focus = workout["focus"]
    lines = [workout["name"], ""]
    lines.append(f"- {_warmup_msg_hr(workout, lang, fthr, prev)} "
                 f"{_hm(params['warmup_sec'])} "
                 f"{_pct(params['warmup_power_low'])}-{_pct(params['warmup_power_high'])}%")
    for _ in range(max(1, params["repeats"])):
        lines.append(f"- {_interval_msg_hr(focus, params, lang, fthr)} "
                     f"{_hm(params['on_sec'])} {_pct(FOCUS_HR_PCT[focus])}%")
        if params["off_sec"]:
            lines.append(f"- {_recovery_msg_hr(params, lang)} "
                         f"{_hm(params['off_sec'])} {_pct(params['off_power'])}%")
    lines += ["",
              f"- {_cooldown_msg_hr(params, lang)} "
              f"{_hm(params['cooldown_sec'])} "
              f"{_pct(params['cooldown_power_low'])}-{_pct(params['cooldown_power_high'])}%"]
    return "\n".join(lines)


def _warmup_msg_hr(workout, lang, fthr, prev):
    focus = workout["focus"]
    rpe = rpe_for_focus(focus)
    bpm = hr_target_bpm(focus, fthr)
    hint = FOCUS_HR_HINT[focus][lang]
    pct = _pct(FOCUS_HR_PCT[focus])
    if lang == "en":
        head = (f"Warm-up: {hint}. Today we aim at {pct} percent of your HR "
                f"threshold (about {bpm} bpm, RPE {rpe}).")
        body = " After the warm-up, " + _structure_msg_hr(workout, lang, fthr) + "."
        pep = " Listen to your body!"
    else:
        head = (f"Aquecimento: {hint}. Hoje miramos {pct} por cento do seu FTHR "
                f"(cerca de {bpm} bpm, RPE {rpe}).")
        body = " Apos o aquecimento, " + _structure_msg_hr(workout, lang, fthr) + "."
        pep = " Vai com tudo!"
    return head + body + _progress_msg(workout, prev, lang) + pep


def _structure_msg_hr(workout, lang, fthr):
    params = workout["params"]
    focus = workout["focus"]
    dur = _dur_text(params["on_sec"], lang)
    pct = _pct(FOCUS_HR_PCT[focus])
    bpm = hr_target_bpm(focus, fthr)
    if lang == "en":
        if params["off_sec"]:
            return (f"we'll do {params['repeats']} sets of {dur} at {pct} percent "
                    f"of your HR threshold (about {bpm} bpm), with "
                    f"{_dur_text(params['off_sec'], lang)} of recovery between them, "
                    "then cool down")
        return (f"we'll do a continuous {dur} block at {pct} percent of your HR "
                f"threshold (about {bpm} bpm), then cool down")
    if params["off_sec"]:
        return (f"faremos {params['repeats']} series de {dur} a {pct} por cento do "
                f"FTHR (cerca de {bpm} bpm), com "
                f"{_dur_text(params['off_sec'], lang)} de recuperacao entre elas, "
                "e depois o desaquecimento")
    return (f"faremos um bloco continuo de {dur} a {pct} por cento do FTHR "
            f"(cerca de {bpm} bpm), e depois o desaquecimento")


def _interval_msg_hr(focus, params, lang, fthr):
    dur = _dur_text(params["on_sec"], lang)
    pct = _pct(FOCUS_HR_PCT[focus])
    bpm = hr_target_bpm(focus, fthr)
    rpe = rpe_for_focus(focus)
    if lang == "en":
        return (f"Now you'll ride {dur} at {pct} percent of your HR threshold "
                f"(about {bpm} bpm, RPE {rpe})")
    return (f"Agora voce vai entrar em {dur} a {pct} por cento do FTHR "
            f"(cerca de {bpm} bpm, RPE {rpe})")


def _recovery_msg_hr(params, lang):
    dur = _dur_text(params["off_sec"], lang)
    pct = _pct(params["off_power"])
    if lang == "en":
        return f"Recovery: {dur} at {pct} percent of HR threshold"
    return f"Recuperacao de {dur} a {pct} por cento do FTHR"


def _cooldown_msg_hr(params, lang):
    low = _pct(params["cooldown_power_low"])
    high = _pct(params["cooldown_power_high"])
    if lang == "en":
        return f"Cooldown: ease down from {low} to {high} percent of HR threshold"
    return f"Desaquecimento: reduza de {low} a {high} por cento do FTHR"


def _warmup_msg(workout, lang, prev):
    params = workout["params"]
    focus = workout["focus"]
    pct = _pct(params["on_power"])
    hint = FOCUS_ZONE_HINT[focus][lang]
    if lang == "en":
        head = f"Warm-up: {hint}. Today we'll thread the needle at {pct} percent of FTP."
        body = " After the warm-up, " + _structure_msg(params, lang) + "."
        prog = _progress_msg(workout, prev, lang)
        pep = " Look at you go!"
    else:
        head = f"Aquecimento: {hint}. Hoje miramos {pct} por cento do FTP."
        body = " Apos o aquecimento, " + _structure_msg(params, lang) + "."
        prog = _progress_msg(workout, prev, lang)
        pep = " Vai com tudo!"
    return head + body + prog + pep


def _structure_msg(params, lang):
    dur = _dur_text(params["on_sec"], lang)
    pct = _pct(params["on_power"])
    if lang == "en":
        if params["off_sec"]:
            return (f"we'll do {params['repeats']} sets of {dur} at {pct} percent of FTP, "
                    f"with {_dur_text(params['off_sec'], lang)} of recovery between them, then cool down")
        return f"we'll do a continuous {dur} block at {pct} percent of FTP, then cool down"
    if params["off_sec"]:
        return (f"faremos {params['repeats']} series de {dur} a {pct} por cento do FTP, "
                f"com {_dur_text(params['off_sec'], lang)} de recuperacao entre elas, e depois o desaquecimento")
    return (f"faremos um bloco continuo de {dur} a {pct} por cento do FTP, "
            "e depois o desaquecimento")


def _progress_msg(workout, prev, lang):
    """`prev` e o treino anterior do mesmo foco (dict do plano). Fala de
    progressao de volume so quando ha comparacao possivel."""
    if not prev:
        return ""
    prev_total = int(prev["params"]["repeats"]) * int(prev["params"]["on_sec"])
    cur_total = int(workout["params"]["repeats"]) * int(workout["params"]["on_sec"])
    delta_min = round((cur_total - prev_total) / 60)
    if lang == "en":
        label = FOCUS_LABELS_EN.get(workout["focus"], workout["focus"])
        if delta_min > 0:
            return f" That's {delta_min} minutes more than the last {label} workout."
        if delta_min < 0:
            return f" That's {-delta_min} minutes less than the last {label} workout."
        return f" Same load as the last {label} workout."
    label = FOCUS_LABELS_PT.get(workout["focus"], workout["focus"])
    if delta_min > 0:
        return f" Isso sao {delta_min} minutos a mais que o ultimo treino de {label}."
    if delta_min < 0:
        return f" Isso sao {-delta_min} minutos a menos que o ultimo treino de {label}."
    return f" Mesma carga do ultimo treino de {label}."


def _interval_msg(params, lang):
    dur = _dur_text(params["on_sec"], lang)
    pct = _pct(params["on_power"])
    if lang == "en":
        return f"Now you'll ride {dur} at {pct} percent of your FTP"
    return f"Agora voce vai entrar em {dur} a {pct} por cento do seu FTP"


def _recovery_msg(params, lang):
    dur = _dur_text(params["off_sec"], lang)
    pct = _pct(params["off_power"])
    if lang == "en":
        return f"Recovery: {dur} at {pct} percent of FTP"
    return f"Recuperacao de {dur} a {pct} por cento do FTP"


def _cooldown_msg(params, lang):
    low = _pct(params["cooldown_power_low"])
    high = _pct(params["cooldown_power_high"])
    if lang == "en":
        return f"Cooldown: ease down from {low} to {high} percent of FTP"
    return f"Desaquecimento: reduza de {low} a {high} por cento do FTP"


def _dur_text(seconds, lang="pt"):
    """'8 minutos'/'8 minutes' (sempre por extenso: o parser do Intervals
    trunca o texto explicativo no primeiro padrao de duracao abreviado,
    '6m'/'30s'/'1h', assim como no primeiro '%')."""
    minutes = max(1, round(seconds / 60))
    if lang == "en":
        return f"{minutes} minute" + ("" if minutes == 1 else "s")
    return f"{minutes} minuto" + ("" if minutes == 1 else "s")


def _pct(frac):
    return str(int(round(frac * 100)))


def _hm(seconds):
    h, rem = divmod(seconds, 3600)
    m = round(rem / 60)
    if m == 60:
        h, m = h + 1, 0
    if h:
        return f"{h}h{m:02d}" if m else f"{h}h"
    return f"{m}m"


def _zone(frac):
    if frac >= 1.05:
        return "Z4"
    if frac >= 0.84:
        return "Z3"
    if frac >= 0.55:
        return "Z2"
    return "Z1"


def reconcile(plan, events, ftp=DEFAULT_FTP, training_days=DEFAULT_TRAINING_DAYS,
              budget=None, absorbed_ids=None):
    """Reconcilia o plano com o historico real.

    `budget` e o teto semanal de TSS. Deve ser calculado pelo caller com a MESMA
    base do build_plan (mesma janela de `avg_load` e mesma `GOAL_BUDGET_SCALE` do
    goal); se omitido, cai no legado basedo em `events`, que pode subestimar o
    teto quando `events` cobre uma janela menor que a do build.
    """
    today = date.today()
    hr_mode = any(w.get("hr_mode") for w in plan)
    done_ids, extras = _done_and_extra(events)
    reduced_ids = set()
    absorbed_ids = set(absorbed_ids or ())
    missed = [w for w in plan
              if w["day"] < today.isoformat() and w["external_id"] not in done_ids]
    already_absorbed = [w for w in missed
                        if w["external_id"] in absorbed_ids]
    absorbed_tss = 0.0
    absorbable = 0.0
    if missed:
        # Um treino perdido e absorvido pelo ORCAMENTO semanal: distribui-se a
        # carga nao feita nos treinos Z2/SweetSpot posteriores que ainda tem
        # folga dentro do teto (weekly_budget). Nao se insere "recuperacao"
        # nem se reduz -5% no proximo Limiar: a compensacao e limitada pelo
        # teto, nao por um fator arbitrario (ver _absorb_missed_into_budget).
        # A carga absorvivel depende da INTENSIDADE do treino perdido
        # (_absorbable_tss): active recovery nao se compensa; alta intensidade
        # (Limiar/VO2) nao se substitui com mais volume - fica para o build
        # seguinte repriorizar conforme o TSB real.
        new_missed = [w for w in missed
                      if w["external_id"] not in absorbed_ids]
        absorbable = _absorbable_tss(new_missed)
        plan, absorbed_tss = _absorb_missed_into_budget(
            plan, absorbable, ftp, events, training_days, budget=budget)
        if absorbed_tss > 0:
            # A identidade persistida e a do treino PERDIDO, nao a do treino
            # que recebeu volume. Assim a mesma falta nao pode ser compensada
            # outra vez por outro receptor numa nova execucao do reconcile.
            absorbed_ids.update(
                w["external_id"] for w in new_missed
                if _absorbable_tss([w]) > 0
            )
    plan = _adjust_for_extra_workouts(plan, extras, ftp, training_days,
                                      cap=daily_tss_cap(avg_load(events)),
                                      reduced_ids=reduced_ids)
    # Modo FC (#3): treinos reescritos (recuperacao, limiar reduzido) perdem a
    # marca `hr_mode` ao serem reconstruidos; restaura em todos para o plano
    # nao misturar prescricao por FC e por potencia.
    if hr_mode:
        for w in plan:
            w["hr_mode"] = True
    info = {"absorbed_tss": absorbed_tss, "missed_tss":
            sum(float(w["tss"]) for w in missed) if missed else 0.0,
            "absorbable_tss": absorbable,
            "already_absorbed_tss": _absorbable_tss(already_absorbed),
            "absorbed_ids": sorted(absorbed_ids)}
    return plan, missed, info


def _done_and_extra(events):
    """Separa eventos hermes concluidos (done) de treinos feitos fora do plano
    (extra): evento com paired_activity_id cujo external_id nao e hermes-plan."""
    done_ids = set()
    extras = []
    for item in events:
        eid = _field(item, "external_id")
        if not _is_completed(item):
            continue
        if eid and eid.startswith(EXTERNAL_ID_PREFIX):
            done_ids.add(eid)
        else:
            day = _day(item)
            load = _num(_field(item, "tss") or _field(item, "training_load"))
            if day and load:
                extras.append({"day": day, "load": float(load)})
    return done_ids, extras


def _week_start(day):
    """Segunda-feira da semana ISO da data (o plano treina seg-sex)."""
    return day - timedelta(days=day.weekday())


def adherence_report(plan, events, today=None):
    """Relatorio de cumprimento do plano (Expected Plan Adherence) por semana.

    Cada treino planejado e classificado como `feito` (evento hermes concluido
    com external_id), `pendente` (dia de hoje ou futuro) ou `perdido` (dia
    passado sem conclusao), usando o mesmo criterio do reconcile
    (`_done_and_extra`): so o que ja venceu conta como perdido.
    Agrega por semana ISO com % de cumprimento sobre os treinos ja ocorridos.

    Retorna {"today", "weeks": [{week, week_start, done, missed, pending,
    total, pct}], "summary": {done, missed, pending, pct}}.
    """
    today = today or date.today()
    done_ids, _ = _done_and_extra(events)
    weeks = {}
    for w in plan:
        day = date.fromisoformat(str(w["day"])[:10])
        key = day.isocalendar()[:2]
        bucket = weeks.setdefault(
            key, {"week_start": _week_start(day),
                  "done": 0, "missed": 0, "pending": 0})
        # UI-2: a classificacao passa pelo lifecycle explicito (planned /
        # completed / missed), em vez de inferir "feito" de `external_id` aqui.
        state = lifecycle.derive(
            day=str(w["day"]), today=today,
            is_done=w.get("external_id") in done_ids,
            declared=w.get("lifecycle"))
        if state == lifecycle.LIFECYCLE_PLANNED:
            bucket["pending"] += 1
        elif state == lifecycle.LIFECYCLE_COMPLETED:
            bucket["done"] += 1
        else:
            bucket["missed"] += 1
    weeks_out = []
    for (year, iso_week), bucket in sorted(weeks.items()):
        occurred = bucket["done"] + bucket["missed"]
        weeks_out.append({
            "week": f"{year}-W{iso_week:02d}",
            "week_start": bucket["week_start"].isoformat(),
            "done": bucket["done"], "missed": bucket["missed"],
            "pending": bucket["pending"],
            "total": occurred + bucket["pending"],
            "pct": (bucket["done"] / occurred * 100) if occurred else None,
        })
    summary = {"done": sum(b["done"] for _, b in weeks.items()),
               "missed": sum(b["missed"] for _, b in weeks.items()),
               "pending": sum(b["pending"] for _, b in weeks.items())}
    occurred = summary["done"] + summary["missed"]
    summary["pct"] = (summary["done"] / occurred * 100) if occurred else None
    return {"today": today.isoformat(), "weeks": weeks_out,
            "summary": summary}


def _adjust_for_extra_workouts(plan, extras, ftp,
                               training_days=DEFAULT_TRAINING_DAYS,
                               extra_window_days=7, cap=None,
                               reduced_ids=None):
    """Treino feito fora do plano soma carga no atleta. Se a carga extra nos
    ultimos `extra_window_days` dias chegar a um treino cheio (>= cap diario),
    insere recuperacao no proximo dia de treino e reduz o proximo Limiar.
    Trabalho leve (abaixo do cap) nao mexe no plano."""
    if not extras:
        return plan
    today = date.today()
    cutoff = today - timedelta(days=extra_window_days)
    window = [e for e in extras if cutoff <= e["day"] <= today]
    if not window:
        return plan
    extra_load = sum(e["load"] for e in window)
    cap = cap if cap is not None else daily_tss_cap(avg_load([]))
    if extra_load < cap:
        return plan
    anchor = max(e["day"] for e in window)
    # recuperacao nunca em dia passado: proximo dia de treino a partir do
    # extra, mas no minimo hoje/tomorrow conforme o dia de hoje ser treino.
    target = _next_training_day(anchor.isoformat(), training_days)
    while target < today.isoformat():
        target = _next_training_day(target, training_days)
    if any(w["day"] == target and "Recuperacao" in w["name"] for w in plan):
        return plan  # recuperacao ja programada (ex.: treino perdido)
    plan = _insert_recovery(plan, target, ftp, training_days, on=target)
    plan = _reduce_next_hard(plan, target, ftp, reduced_ids)
    return plan


def _insert_recovery(plan, day, ftp, training_days=DEFAULT_TRAINING_DAYS, on=None):
    next_day = on or _next_training_day(day, training_days)
    base = templates()[FOCUS_ZONE2]
    params = WorkoutParams(focus=FOCUS_ZONE2, **dict(base, on_sec=1200, on_power=0.60))
    duration = sum((params.warmup_sec, params.repeats * (params.on_sec + params.off_sec),
                    params.cooldown_sec))
    recovery = PlannedWorkout(
        day=next_day, focus=FOCUS_ZONE2, planned_duration=duration,
        name=f"{next_day} - Recuperacao (plano ajustado)",
        params=_params_dict(params), tss=float(estimate_tss(params, ftp)),
        external_id=f"{EXTERNAL_ID_PREFIX}-{next_day}",
        ftp_watts=int(ftp),
    )
    return [w for w in plan if w["day"] != next_day] + [_as_dict(recovery)]


def _reduce_next_hard(plan, day, ftp, reduced_ids=None):
    out = []
    reduced_ids = reduced_ids if reduced_ids is not None else set()
    reduced_this_call = False
    for w in sorted(plan, key=lambda x: x["day"]):
        if (not reduced_this_call and w["external_id"] not in reduced_ids
                and w["day"] > day and w["focus"] == FOCUS_THRESHOLD):
            params = dict(w["params"])
            params["on_power"] = round(params["on_power"] * 0.95, 3)
            tss = estimate_tss(WorkoutParams(**params), ftp)
            w = PlannedWorkout(day=w["day"], focus=w["focus"],
                               planned_duration=w["planned_duration"],
                               name=w["name"], params=params,
                                tss=float(tss), external_id=w["external_id"],
                                ftp_watts=int(ftp))
            w = _as_dict(w)
            reduced_ids.add(w["external_id"])
            reduced_this_call = True
        out.append(w)
    return out


# --- Absorcao de treino perdido pelo orcamento semanal -----------------------
# Embasamento cientifico (docs/EMBASAMENTO-CIENTIFICO.md secao 5, "Treino
# perdido: absorver pelo orcamento, nao substituir por recuperacao"): um treino
# perdido nao se repara com uma sessao binaria de "recuperacao" nem com uma
# reducao fixa de -5% no proximo Limiar. A literatura de periodizacao (Banister;
# Seiler, Periodization Theory, 3a ed.; Friel, Periodization Bible) trata a
# falta de adesao como ruido esperado e manda ABSORVER o deficit elevando a
# carga das sessoes restantes DENTRO do orcamento semanal ja calculado pelo
# _fit_budget. O limite da compensacao e o proprio teto (guardrail), nao um
# -5% arbitrario.
#
# O QUE E (e nao e) absorvivel depende da INTENSIDADE do treino perdido, nao
# do seu TSS bruto - o stimulus fisiologico e o que determina o custo real de
# uma falta (Seiler; Friel):
#   - ACTIVE RECOVERY (Z2 ~0.55-0.60, ~14 TSS): o proprio objetivo do treino e
#     NAO gerar carga. Perder e praticamente sem custo -> nao se compensa
#     (compensar exiquria carga, contradizendo o proposito do treino);
#   - BASE Z2 (~0.70) / SWEETSPOT (~0.88): volume puro; perder esse workload e
#     absorvivel com mais volume da mesma natureza -> redistribui-se dentro do
#     teto semanal;
#   - LIMIAR (~0.98) / VO2MAX (~1.15): o estímulo e de ALTA INTENSIDADE. VO2max
#     nao se constroi com mais Z2 (Seiler: a adaptacao aerobica vem da
#     intensidade acima do LT1). Nao se compensa com volume - deixa-se o
#     treino de intensidade como "debito" e deixa o proprio build seguinte
#     repriorizar a intensidade conforme o TSB real.
#
# Limites (conservadores, para nao estourar o teto nem criar picos):
#   - so sessoes ZONA2/SWEETSPOT recebem a elevacao: sessoes VO2/Limiar nao
#     sao "enchidas" por causa de uma falta;
#   - cada treino cresce no maximo ABSORB_MAX_GAIN (20%) de on_sec por chamada
#     (evita inflar um unico treino e criar um pico apos a falta);
#   - so absorve enquanto a soma rolante de 7 dias couber no teto
#     (weekly_budget). Sem folga, a falta e grande demais para compensar: o
#     plano fica intacto e a carga nao feita sobe o TSB, o proprio motor de
#     autorregulacao reduz a proxima semana no build seguinte.
ABSORB_MAX_GAIN = 1.20
ABSORB_FOCUSES = (FOCUS_ZONE2, FOCUS_SWEETSPOT)
# Focos que NAO se compensam com volume: o estímulo nao e substituido por Z2.
ABSORB_SKIP_FOCUSES = (FOCUS_THRESHOLD, FOCUS_VO2)
# Abaixo desta potencia, um Z2 e active recovery (nao compensa).
ACTIVE_RECOVERY_MAX_POWER = 0.65
_ABSORB_STEP_SEC = 30  # granularidade do ajuste de on_sec


def _is_active_recovery(w):
    """Active recovery = Z2 muito leve (on_power <= ~0.65). Perder e sem custo
    fisiologico relevante, logo nao se compensa com volume."""
    return (w.get("focus") == FOCUS_ZONE2
            and float((w.get("params") or {}).get("on_power", 1.0))
            <= ACTIVE_RECOVERY_MAX_POWER)


def _absorbable_tss(missed):
    """Carga realmente absorvivel de uma lista de treinos perdidos: soma
    apenas os de BASE (Z2 >=~0.70 / SweetSpot). Active recovery (nao compensa)
    e alta intensidade (nao se substitui com volume) ficam de fora."""
    total = 0.0
    for m in missed:
        if m.get("focus") in ABSORB_SKIP_FOCUSES:
            continue
        if _is_active_recovery(m):
            continue
        total += float(m["tss"])
    return total


def _absorb_missed_into_budget(plan, missed_tss, ftp, events, training_days,
                               budget=None):
    """Eleva a duracao (on_sec) dos treinos Z2/SweetSpot posteriores para
    reabsorver `missed_tss`, sem estourar o teto semanal (weekly_budget).

    Devolve (plan, ganho_tss), sendo ganho_tss a parcela da falta
    efetivamente redistribuida. Sem folga no teto, devolve o plano intacto.
    """
    if missed_tss <= 0:
        return plan, 0.0
    # O teto deve vir do mesmo calculo do build_plan (mesma janela de eventos e
    # mesma escala do goal). Se o caller nao informar, cai no comportamento
    # legado basedo nos `events` recebidos - que pode ser mais estreito que a
    # janela do build e, por isso, subestimar a media e o teto.
    budget = (budget if budget is not None
              else weekly_budget(avg_load(events), training_days))
    plan = [dict(w) for w in plan]
    dias = [date.fromisoformat(x["day"]) for x in plan]
    # Se o plano JA esta acima do teto que o reconcile calculou, nao absorve:
    # isso significa que o plano veio de um build com um teto diferente (o
    # reconcile ve uma janela de eventos mais estreita que o build) e elevar
    # aqui so agravaria. defensive: nao piora o que ja estourou.
    ja_estourado = max(
        sum(x["tss"] for x in plan
            if 0 <= (d - date.fromisoformat(x["day"])).days < 7)
        for d in dias) > budget
    if ja_estourado:
        return plan, 0.0
    gained = 0.0
    remaining = missed_tss
    for w in sorted((w for w in plan
                      if w["focus"] in ABSORB_FOCUSES
                      and not _is_active_recovery(w)),
                    key=lambda x: x["day"]):
        if remaining <= 0:
            break
        day = date.fromisoformat(w["day"])
        params = dict(w["params"])
        on = int(params.get("on_sec", 0))
        if on <= 0:
            continue
        base_tss = float(estimate_tss(WorkoutParams(**params), ftp))
        # Elevar este treino cresce a soma de TODA janela rolante de 7 dias que
        # o contem. A forma correta de respeitar o teto e checar, para cada
        # dia D >= `day` em que o treino entra na janela, se
        # soma(D) + ganho <= budget. `folga` e a menor folga entre esses dias.
        folga = min(
            (budget - sum(x["tss"] for x in plan
                          if 0 <= (d - date.fromisoformat(x["day"])).days < 7))
            for d in dias if d >= day)
        if folga <= 0:
            continue
        # procura o maior on_sec que cabe na folga, ate ABSORB_MAX_GAIN
        best = None
        for target_on in range(on + _ABSORB_STEP_SEC,
                               int(on * ABSORB_MAX_GAIN) + 1,
                               _ABSORB_STEP_SEC):
            cand = dict(params, on_sec=target_on)
            cand_tss = float(estimate_tss(WorkoutParams(**cand), ftp))
            ganho = cand_tss - base_tss
            if ganho <= 0 or ganho > folga:
                break
            best = (cand, cand_tss, ganho)
        if not best:
            continue
        cand, cand_tss, ganho = best
        # grava o treino elevado
        off = int(params.get("off_sec", 0))
        warm = int(params.get("warmup_sec", 600))
        cool = int(params.get("cooldown_sec", 600))
        duration = warm + int(params["repeats"]) * (cand["on_sec"] + off) + cool
        w["params"] = cand
        w["tss"] = cand_tss
        w["planned_duration"] = duration
        gained += ganho
        remaining -= ganho
    return plan, gained


def _next_training_day(day, training_days=DEFAULT_TRAINING_DAYS):
    d = date.fromisoformat(day) + timedelta(days=1)
    while d.weekday() not in training_days:
        d += timedelta(days=1)
    return d.isoformat()


def orphan_external_ids(plan, events, start=None):
    """external_ids hermes-plan presentes em `events` que nao pertencem ao
    plano atual (ou que ficam fora da janela iniciada em `start`)."""
    keep = {w["external_id"] for w in plan
            if not start or w["day"] >= start}
    return [e["external_id"] for e in events
            if (e.get("external_id") or "").startswith(EXTERNAL_ID_PREFIX)
            and e["external_id"] not in keep]


def manual_duplicate_ids(plan, events, start=None):
    """IDs numericos de eventos MANUAIS (sem `external_id`) que duplicam um
    dia do plano -- isto e, existe um `hermes-plan-*` no mesmo dia.

    O `bulk-delete` so apaga por `external_id`, entao essas duplicatas (criadas
    direto no app do Intervals) exigem `delete_event(id)`. Um evento manual
    em dia SEM treino do plano nao e duplicata e e preservado.
    """
    plan_days = {w["day"] for w in plan if not start or w["day"] >= start}
    return [e["id"] for e in events
            if not e.get("external_id") and e["start_date_local"][:10] in plan_days]


_BLOCK_CONTEXT_UNSET = object()


def save_plan(plan, path="plan.json", goal=None, race_date=None,
              ftp_test_date=None, ftp_candidates=None, absorbed_ids=None,
              block_context=_BLOCK_CONTEXT_UNSET):
    """Salva o plano. Com GOAL configurado, guarda a meta junto
    (plan.json passa a ser {'goal', 'race_date', 'ftp_test_date',
    'ftp_candidates', 'absorbed_ids', 'block_context', 'workouts'}); sem meta
    nem estado de reconciliacao, mantem o formato antigo (lista pura) para
    compatibilidade."""
    if block_context is _BLOCK_CONTEXT_UNSET:
        block_context = load_plan_meta(path)["block_context"]
    data = plan
    if goal is not None or absorbed_ids or block_context is not None:
        data = {"goal": goal, "race_date": race_date,
                "ftp_test_date": ftp_test_date,
                "ftp_candidates": ftp_candidates or {},
                "absorbed_ids": sorted(set(absorbed_ids or ())),
                "block_context": (block_context.to_dict()
                                  if block_context is not None else None),
                "workouts": plan}
    out = pathlib.Path(path)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return out


def load_plan(path="plan.json"):
    """Retorna a lista de workouts do plan.json (tolera o formato novo com
    meta e o antigo de lista pura)."""
    with open(pathlib.Path(path), "r", encoding="utf-8") as fh:
        data = json.load(fh)
    if isinstance(data, dict) and "workouts" in data:
        return data["workouts"]
    return data


def load_plan_meta(path="plan.json"):
    """Meta salva junto com o plano, ou defaults seguros quando ausente."""
    try:
        with open(pathlib.Path(path), "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"goal": None, "race_date": None, "ftp_test_date": None,
                "ftp_candidates": {}, "absorbed_ids": [], "block_context": None}
    if isinstance(data, dict) and "workouts" in data:
        if __package__:
            from .training_block import BlockContext  # type: ignore
        else:  # plan carregado top-level pela CLI executada como script direto
            from training_block import BlockContext
        block = data.get("block_context")
        return {"goal": data.get("goal"), "race_date": data.get("race_date"),
                "ftp_test_date": data.get("ftp_test_date"),
                "ftp_candidates": data.get("ftp_candidates") or {},
                "absorbed_ids": data.get("absorbed_ids") or [],
                "block_context": BlockContext.from_dict(block) if block is not None else None}
    return {"goal": None, "race_date": None, "ftp_test_date": None,
            "ftp_candidates": {}, "absorbed_ids": [], "block_context": None}
