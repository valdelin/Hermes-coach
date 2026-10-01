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


# --- Focos de prescricao -------------------------------------------------
# O VALOR string de cada foco e persistido em plan.json e publicado no
# Intervals.icu. Renomear um valor quebra plano salvo e o calendario: por isso
# as mudancas de nomenclatura Happens nas CONSTANTES, nunca nos valores.
# As constantes seguem a nomenclatura da "Tabela Cientifica Z1-Z7" do
# documento; os valores preservam a compatibilidade historica.
FOCUS_ZONE2 = "zone2"                       # alias legado -> FOCUS_ZONE2_ENDURANCE
FOCUS_SWEETSPOT = "sweetspot"
FOCUS_THRESHOLD = "threshold"                # alias legado -> FOCUS_ZONE4_LIMIAR
FOCUS_VO2 = "vo2max"                         # alias legado -> FOCUS_ZONE5_VO2MAX
FOCUS_ENDURANCE = "endurance"                # alias legado -> FOCUS_ZONE2_ENDURANCE

# Zonas canonicas (nomenclatura do documento). Z1, Z3, Z6 e Z7 ainda nao tem
# foco prescrito no algortimo; as bandas existem para tornar a tabela do
# documento integralmente verificavel em codigo.
FOCUS_ZONE1_RECOVERY = "z1_recovery"
FOCUS_ZONE2_ENDURANCE = "zone2"
FOCUS_ZONE3_TEMPO = "z3_tempo"
FOCUS_ZONE4_LIMIAR = "threshold"
FOCUS_ZONE5_VO2MAX = "vo2max"
FOCUS_ZONE6_ANAEROBICA = "z6_anaerobica"
# Z7 Neuromuscular fica de fora: e potencia maxima, nao uma faixa de %FTP, e
# por isso nao cabe em ZONE_BANDS (ver commentario nessa tabela).
ZONE_SWEETSPOT = "sweetspot"

FOCUS_LABELS = {
    FOCUS_ZONE2: "Zona 2 (recuperacao ativa)",
    FOCUS_SWEETSPOT: "Sweet Spot",
    FOCUS_THRESHOLD: "Limiar FTP",
    FOCUS_VO2: "VO2 Max",
}


def metrics_history(events):
    """Metricas (Metrics) por item na ordem dos eventos, mantendo o citério de
    `_raw_metrics` (TSB obrigatorio; CTL/ATL/props via fallbacks da API).
    Itens sem metricas validas ficam de fora. Usado por `latest_metrics`
    (estado atual) e pelo bootstrap do `cmd_model` (estado passado)."""
    history = []
    for item in events:
        marker = _raw_metrics(item)
        if marker is not None:
            history.append(marker)
    return history


def latest_metrics(events):
    latest = None
    for marker in metrics_history(events):
        if latest is None or ((marker.day or "") >= (latest.day or "")):
            latest = marker
    return latest


def real_pmc_by_day(events):
    """{(date): (ctl, atl)} reais do Intervals por dia de treino.

    Usa os valores `icu_ctl`/`icu_atl` que a API devolve em cada atividade
    pareada (pipeline interna do Intervals — o mesmo numero que o site dele
    plota). Dias sem treino ficam de fora; a serie continua e feita pelo
    `pmc_series_anchored`. Chave `date` vem do `day` do `Metrics`.
    """
    by = {}
    for marker in metrics_history(events):
        if marker.ctl is None or marker.atl is None or not marker.day:
            continue
        try:
            day = date.fromisoformat(marker.day[:10])
        except ValueError:
            continue
        by[day] = (marker.ctl, marker.atl)
    return by


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

# Faixas de prescricao por zona, espelhando a "Tabela Cientifica Z1-Z7" do
# documento canonico no vault (ver docs/EMBASAMENTO-CIENTIFICO.md, secao 6, que
# aponta para o vault). Sao FAIXAS DE REFERENCIA, nao limites
# fisiologicos universais: nao existe conversao universal entre %FTP, %FCmax,
# %FC de limiar e RPE.
#
# Uso: piso da zona. O algoritmo NUNCA rebaixa a potencia de um treino abaixo do
# piso da zona que ele declara - cortar duracao (on_sec) e a forma de reduzir
# carga; rebaixar a potencia transformaria um "Treino de Sweet Spot" em
#eless stimulus de recuperacao sem renomear, quebrando a coerencia nome<->zona.
#
# Z1 (recuperacao, <55%) nao entra aqui: e uma intencao de sessao executada
# DENTRO da banda Z2 (active recovery ~0.60), nao uma zona de prescricao
# independente.
ZONE_BANDS = {
    FOCUS_ZONE1_RECOVERY: (0.00, 0.55),   # Z1 Recuperacao     <55%
    FOCUS_ZONE2_ENDURANCE: (0.56, 0.75),  # Z2 Endurance     56-75%
    FOCUS_ZONE3_TEMPO: (0.76, 0.90),      # Z3 Tempo         76-90%
    ZONE_SWEETSPOT: (0.84, 0.97),         # Sweet Spot       84-97%
    FOCUS_ZONE4_LIMIAR: (0.91, 1.05),     # Z4 Limiar        91-105%
    FOCUS_ZONE5_VO2MAX: (1.06, 1.20),     # Z5 VO2max       106-120%
    FOCUS_ZONE6_ANAEROBICA: (1.21, 1.50), # Z6 Anaerobica   121-150%
    # Z7 Neuromuscular NAO entra: e potencia maxima (all-out), nao uma faixa de
    # %FTP, e nao cabe neste modelo. Esta aqui apenas para deixar o motivo
    # explicito em codigo.
}

# Bandas por FOCO DE PRESCRICAO -> zona canonica. Um foco pode ser servido por
# mais de uma zona do documento: 'zone2' e 'endurance' sao ambos Z2, e
# 'sweetspot' e a categoria de prescricao (nao um numero de zona).
FOCUS_ZONE = {
    FOCUS_ZONE2: FOCUS_ZONE2_ENDURANCE,
    FOCUS_ENDURANCE: FOCUS_ZONE2_ENDURANCE,
    FOCUS_SWEETSPOT: ZONE_SWEETSPOT,
    FOCUS_THRESHOLD: FOCUS_ZONE4_LIMIAR,
    FOCUS_VO2: FOCUS_ZONE5_VO2MAX,
}

# Rotulos do documento, para mensagens e documentacao.
ZONE_LABELS_PT = {
    FOCUS_ZONE1_RECOVERY: "Z1 Recuperacao",
    FOCUS_ZONE2_ENDURANCE: "Z2 Endurance",
    FOCUS_ZONE3_TEMPO: "Z3 Tempo",
    ZONE_SWEETSPOT: "Sweet Spot",
    FOCUS_ZONE4_LIMIAR: "Z4 Limiar",
    FOCUS_ZONE5_VO2MAX: "Z5 VO2max",
    FOCUS_ZONE6_ANAEROBICA: "Z6 Anaerobica",
}


def focus_zone(focus):
    """Zona canonica do documento que sustenta este foco de prescricao."""
    return FOCUS_ZONE.get(focus)


def zone_band(focus):
    """Faixa (piso, teto) de %FTP do foco, resolvendo pela zona do documento.

    Aceita tanto o foco de prescricao ('sweetspot') quanto a zona canonica
    ('Z4 Limiar'). Devolve None se a zona nao tem faixa em %FTP.
    """
    zone = focus if focus in ZONE_BANDS else focus_zone(focus)
    return ZONE_BANDS.get(zone)


def zone_floor(focus):
    """Piso de %FTP da zona. Foco/zona sem faixa conhecida -> None (sem guardrail)."""
    band = zone_band(focus)
    return band[0] if band else None


def zone_ceiling(focus):
    """Teto de %FTP da zona. Foco/zona sem faixa conhecida -> None."""
    band = zone_band(focus)
    return band[1] if band else None


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


def wellness_summary(records, days=7):
    """Resumo de wellness (issue #4) a partir dos registros do
    `/wellness` do Intervals.icu. Campos sincronizados do Garmin:
    `restingHR`, `sleepSecs`, `steps`, `hrv`/`hrvSDNN`, `stress`,
    `sleepScore`, `readiness`. Retorna dict com o ultimo valor e a media
    dos ultimos `days` registros (chave `id` = data), ou None sem dados."""
    if not records:
        return None
    rows = []
    for rec in records:
        day = str(rec.get("id") or rec.get("day") or "")[:10]
        rows.append((day, rec))
    rows = [r for r in rows if r[0]]
    rows.sort()
    if not rows:
        return None
    recent = rows[-days:]

    def _avg(key):
        vals = [r.get(key) for _, r in recent
                if isinstance(r.get(key), (int, float))]
        return (sum(vals) / len(vals)) if vals else None

    def _last(key):
        for _, r in reversed(rows):
            v = r.get(key)
            if isinstance(v, (int, float)):
                return v
        return None

    def _hours(secs):
        return round(secs / 3600, 1) if secs is not None else None

    sleep_last = _last("sleepSecs")
    sleep_avg = _avg("sleepSecs")
    return {
        "days": len(recent),
        "resting_hr_last": _last("restingHR"),
        "resting_hr_avg": _avg("restingHR"),
        "sleep_hours_last": _hours(sleep_last),
        "sleep_hours_avg": _hours(sleep_avg),
        "hrv_last": _last("hrv"),
        "hrv_sdnn_last": _last("hrvSDNN"),
        "stress_last": _last("stress"),
        "sleep_score_last": _last("sleepScore"),
        "readiness_last": _last("readiness"),
        "steps_last": _last("steps"),
    }


def format_wellness(summary, lang="pt"):
    """Texto curto do resumo de wellness para o `info`/relatorio diario."""
    if not summary:
        return "sem dados (sync Garmin -> Intervals pendente)"
    parts = []
    if summary["resting_hr_last"] is not None:
        text = f"RHR {summary['resting_hr_last']:.0f} bpm"
        if summary["resting_hr_avg"] is not None:
            text += f" (media {summary['resting_hr_avg']:.1f})"
        parts.append(text)
    if summary["sleep_hours_last"] is not None:
        text = f"sono {summary['sleep_hours_last']:.1f}h"
        if summary["sleep_hours_avg"] is not None:
            text += f" (media {summary['sleep_hours_avg']:.1f}h)"
        parts.append(text)
    if summary["hrv_last"] is not None:
        parts.append(f"HRV {summary['hrv_last']:.0f}ms")
    if summary["sleep_score_last"] is not None:
        parts.append(f"score sono {summary['sleep_score_last']:.0f}")
    if summary["stress_last"] is not None:
        parts.append(f"stress {summary['stress_last']:.0f}")
    if summary["steps_last"] is not None:
        parts.append(f"passos {summary['steps_last']:.0f}")
    if summary["hrv_last"] is None and summary["days"]:
        parts.append("HRV sem dados (FR935)")
    return " | ".join(parts) if parts else "sem dados (sync pendente)"


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