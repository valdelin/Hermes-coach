from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Metrics:
    tsb: float
    ctl: float | None = None
    atl: float | None = None
    tss: float | None = None
    ftp: float | None = None
    day: str | None = None


@dataclass(frozen=True)
class WorkoutParams:
    focus: str
    warmup_sec: int = 600
    warmup_cadence: int = 90
    warmup_power_low: float = 0.45
    warmup_power_high: float = 0.75
    repeats: int = 3
    on_sec: int = 480
    off_sec: int = 240
    on_power: float = 0.98
    off_power: float = 0.55
    cadence: int = 90
    cadence_rest: int = 85
    cooldown_sec: int = 600
    cooldown_cadence: int = 85
    cooldown_power_low: float = 0.70
    cooldown_power_high: float = 0.45


FOCUS_ZONE2 = "zone2"
FOCUS_SWEETSPOT = "sweetspot"
FOCUS_THRESHOLD = "threshold"
FOCUS_VO2 = "vo2max"

FOCUS_LABELS = {
    FOCUS_ZONE2: "Zona 2 (recuperacao ativa)",
    FOCUS_SWEETSPOT: "Sweet Spot",
    FOCUS_THRESHOLD: "Limiar FTP",
    FOCUS_VO2: "VO2 Max",
}


def latest_metrics(events):
    latest = None
    for item in events:
        marker = _raw_metrics(item)
        if marker is None:
            continue
        if latest is None or ((marker.day or "") >= (latest.day or "")):
            latest = marker
    return latest


def _raw_metrics(item):
    summary = item.get("summary") or {}
    tsb = item.get("tsb", summary.get("tsb"))
    ctl = item.get("ctl", summary.get("ctl"))
    atl = item.get("atl", summary.get("atl"))
    if ctl is None:
        ctl = item.get("icu_ctl", summary.get("icu_ctl"))
    if atl is None:
        atl = item.get("icu_atl", summary.get("icu_atl"))
    if ctl is not None:
        ctl = _num(ctl)
    if atl is not None:
        atl = _num(atl)
    if tsb is not None:
        tsb = _num(tsb)
    if tsb is None and ctl is not None and atl is not None:
        tsb = ctl - atl
    if tsb is None:
        return None
    tss = item.get("tss", summary.get("tss"))
    if tss is None:
        tss = item.get("icu_training_load")
    return Metrics(
        tsb=float(tsb),
        ctl=_num(ctl),
        atl=_num(atl),
        tss=_num(tss),
        ftp=_num(item.get("icu_ftp", summary.get("icu_ftp"))),
        day=item.get("start_time_local") or item.get("start_date_local"),
    )


def _num(value):
    return float(value) if value is not None else None


def decide_focus(tsb):
    if tsb < -15:
        return FOCUS_ZONE2
    if tsb < -5:
        return FOCUS_SWEETSPOT
    if tsb >= 5:
        return FOCUS_VO2
    return FOCUS_THRESHOLD


def build_workout(tsb, ftp, **overrides):
    focus = decide_focus(tsb)
    plan = _BLOCKS[focus]
    params = WorkoutParams(focus=focus, **plan)
    return params.__class__(**{**params.__dict__, **overrides})


_BLOCKS = {
    FOCUS_ZONE2: {
        "repeats": 3,
        "on_sec": 900,
        "off_sec": 180,
        "on_power": 0.75,
        "off_power": 0.55,
        "cadence": 90,
        "cadence_rest": 90,
    },
    FOCUS_SWEETSPOT: {
        "repeats": 3,
        "on_sec": 480,
        "off_sec": 240,
        "on_power": 0.88,
        "off_power": 0.55,
        "cadence": 90,
        "cadence_rest": 85,
    },
    FOCUS_THRESHOLD: {
        "repeats": 3,
        "on_sec": 480,
        "off_sec": 240,
        "on_power": 0.98,
        "off_power": 0.55,
        "cadence": 90,
        "cadence_rest": 85,
    },
    FOCUS_VO2: {
        "repeats": 4,
        "on_sec": 180,
        "off_sec": 180,
        "on_power": 1.15,
        "off_power": 0.55,
        "cadence": 90,
        "cadence_rest": 90,
    },
}


def estimate_tss(params, ftp):
    acc = 0.0
    mid = lambda a, b: (a + b) / 2
    acc += params.warmup_sec * mid(params.warmup_power_low, params.warmup_power_high) ** 3
    acc += params.repeats * (params.on_sec * params.on_power ** 3
                             + params.off_sec * params.off_power ** 3)
    acc += params.cooldown_sec * mid(params.cooldown_power_low, params.cooldown_power_high) ** 3
    return round(acc / 36)


FTP_TEST_KEYWORDS = ("ramp", "ftp", "teste", "test", "prova")
DEFAULT_FTP_TEST_WEEKS = 8

# Janela de reteste do FTP conforme o tipo de plano (GOAL): faz mais sentido
# testar ao final de cada bloco (FTP Builder = blocos de 6 semanas) ou com
# intensidade alta (TT/Climbing = 4 semanas); manutencao/off-season pode
# esperar mais.
FTP_TEST_WEEKS_BY_GOAL = {
    None: 8,
    "back-to-fitness": 8,
    "ftp-builder": 6,
    "gran-fondo": 6,
    "time-trial": 4,
    "climbing": 4,
    "active-off-season": 8,
    "race": 4,
}

FTP_TEST_WEEKS_NOTE = {
    None: "",
    "back-to-fitness": " (progressao lenta pos-pausa)",
    "ftp-builder": " — ao final do bloco do FTP Builder",
    "gran-fondo": " — ao final do bloco de volume",
    "time-trial": " — intensidade alta (TT)",
    "climbing": " — intensidade alta (subidas)",
    "active-off-season": " — manutencao leve",
    "race": " — fase de especializacao para a prova",
}


@dataclass(frozen=True)
class FtpTestSuggestion:
    due: bool
    last_test: str | None = None
    days_since: int | None = None
    reason: str = ""


def last_ftp_test(events):
    """Data (ISO, YYYY-MM-DD) do teste de FTP mais recente detectado nos
    eventos, ou None. Procura pelo nome do treino (Ramp Test do Zwift, etc)."""
    best = None
    for item in events:
        name = (item.get("name") or "").lower()
        if not any(k in name for k in FTP_TEST_KEYWORDS):
            continue
        day = item.get("start_date_local") or item.get("start_time_local") or item.get("day")
        if day:
            day = str(day)[:10]
            if best is None or day > best:
                best = day
    return best


def suggest_ftp_test(events, ftp, weeks=DEFAULT_FTP_TEST_WEEKS, today=None, goal=None):
    """Indica se esta na hora de (re)fazer um teste de FTP (Ramp Test do app
    Zwift). A janela segue o tipo de plano ativo (`FTP_TEST_WEEKS_BY_GOAL`):
    FTP Builder testa ao final de cada bloco (~6 semanas), TT/Climbing a cada
    4 semanas, off-season pode esperar; sem plano, 8 semanas."""
    if goal is not None:
        weeks = FTP_TEST_WEEKS_BY_GOAL.get(goal, DEFAULT_FTP_TEST_WEEKS)
    note = FTP_TEST_WEEKS_NOTE.get(goal, "")
    today = today or date.today()

    def _reason(msg):
        return f"{msg}{note}"

    last = last_ftp_test(events)
    days_since = None
    if last:
        days_since = (today - date.fromisoformat(last)).days

    if days_since is None:
        days = [str(item.get("start_date_local") or item.get("start_time_local")
                    or item.get("day") or "")[:10] for item in events]
        days = [d for d in days if d]
        if len(days) < 2 or not days:
            return FtpTestSuggestion(False, None, None,
                                     _reason("historico curto demais para calibrar o FTP"))
        first = date.fromisoformat(min(days))
        if (today - first).days < weeks * 7:
            return FtpTestSuggestion(False, None, None,
                                     _reason(f"sem teste registrado, mas ainda com menos de {weeks} "
                                             "semanas de historico; sem pressa"))
        return FtpTestSuggestion(True, None, None,
                                 _reason(f"nenhum teste de FTP registrado em {weeks}+ semanas de treino"))
    if days_since >= weeks * 7:
        return FtpTestSuggestion(True, last, days_since,
                                 f"ultimo teste ha {days_since} dias (janela de {weeks} semanas){note}")
    return FtpTestSuggestion(False, last, days_since,
                             f"ultimo teste ha {days_since} dias; dentro da janela de {weeks} semanas{note}")