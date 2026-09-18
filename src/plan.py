import dataclasses
import json
import pathlib
from datetime import date, datetime, timedelta

try:
    from coach import (WorkoutParams, estimate_tss,
                       FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2)
except ImportError:
    from .coach import (WorkoutParams, estimate_tss,
                        FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2)

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


@dataclasses.dataclass(frozen=True)
class PlannedWorkout:
    day: str
    focus: str
    planned_duration: int
    name: str
    params: dict
    tss: float
    external_id: str


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


# Indice = posicao do dia dentro da agenda de treino (build_plan). O template
# de 5 focos e cortado/cirado ao tamanho da agenda configurada (TRAINING_DAYS,
# default seg-sex). A carga e aplicada apos (ver build_plan / weekly_budget).
WEEKLY_BY_TSB = [
    (-15, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT]),
    (0, [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_VO2]),
    (5, [FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
    (10**9, [FOCUS_THRESHOLD, FOCUS_VO2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2]),
]

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


def weekly_template(tsb):
    for threshold, template in WEEKLY_BY_TSB:
        if tsb < threshold:
            return template
    return WEEKLY_BY_TSB[-1][1]


def avg_load(events, window_days=60):
    loads = []
    cutoff = date.today() - timedelta(days=window_days)
    for item in events:
        day = _day(item)
        load = _num(item.get("icu_training_load"))
        if day and load and load > 0 and day >= cutoff:
            loads.append(load)
    return sum(loads) / len(loads) if loads else 40.0


def daily_tss_cap(avg):
    return max(35, min(200, int(avg * 0.95)))


def weekly_budget(avg):
    """Orcamento de TSS para um janela de 7 dias (7x o cap diario)."""
    return daily_tss_cap(avg) * 7


def build_plan(events, tsb, ftp=DEFAULT_FTP, days=14, start=None, existing=None,
               training_days=DEFAULT_TRAINING_DAYS):
    today = date.today()
    if start is None:
        start = today + timedelta(days=1)
        if existing and today.weekday() in training_days:
            kept = [w for w in existing if w["day"] == today.isoformat()]
            if kept:
                plan = [kept[0]]
                recent = [(today, kept[0]["tss"])]
                return plan + build_plan(events, tsb, ftp=ftp, days=days,
                                         start=start, training_days=training_days)
    base = templates()
    weekly = weekly_template(tsb)
    slots = sorted(training_days)
    cap = daily_tss_cap(avg_load(events))
    budget = weekly_budget(avg_load(events))
    plan = []
    recent = []  # (day, tss) dos ultimos 7 dias
    for i in range(days):
        day = start + timedelta(days=i)
        if day.weekday() not in training_days:
            continue
        focus = weekly[slots.index(day.weekday()) % len(weekly)]
        params = WorkoutParams(focus=focus, **base[focus])
        tss = estimate_tss(params, ftp)
        if tss > cap:
            factor = max(0.4, cap / tss)
            params = WorkoutParams(**{**params.__dict__,
                                      "on_sec": max(120, int(params.on_sec * factor))})
            tss = estimate_tss(params, ftp)
        params, tss = _fit_budget(params, tss, recent, budget, ftp)
        duration = sum((params.warmup_sec,
                        params.repeats * (params.on_sec + params.off_sec),
                        params.cooldown_sec))
        plan.append(PlannedWorkout(
            day=day.isoformat(), focus=focus,
            planned_duration=duration,
            name=workout_name(day.isoformat(), focus),
            params=_params_dict(params), tss=float(tss),
            external_id=f"{EXTERNAL_ID_PREFIX}-{day.isoformat()}",
        ))
        recent.append((day, tss))
        while recent and day - recent[0][0] >= timedelta(days=7):
            recent.pop(0)
    return [_as_dict(w) for w in plan]


def _fit_budget(params, tss, recent, budget, ftp):
    """Reduz a carga deste dia (e por consequencia os subsequentes) para que a
    soma rolante de 7 dias nao estoure o orcamento semanal."""
    used = sum(t for _, t in recent)
    if used + tss <= budget:
        return params, tss
    on_sec, on_power = params.on_sec, params.on_power
    for _ in range(20):
        if used + tss <= budget:
            break
        if on_sec > 120:
            on_sec = max(120, int(on_sec * 0.8))
        elif on_power > 0.55:
            on_power = max(0.55, round(on_power - 0.05, 2))
        else:
            break
        params = WorkoutParams(**{**params.__dict__,
                                  "on_sec": on_sec, "on_power": on_power})
        tss = estimate_tss(params, ftp)
    return params, tss


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


def _as_dict(w):
    return dataclasses.asdict(w)


def _day(item):
    raw = item.get("start_date_local") or item.get("start_time_local")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw[:19]).date()
    except ValueError:
        return None


def _num(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


CUE_LANGS = ("pt", "en")

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
}

FOCUS_LABELS_EN = {
    FOCUS_ZONE2: "zone 2",
    FOCUS_SWEETSPOT: "sweet spot",
    FOCUS_THRESHOLD: "threshold",
    FOCUS_VO2: "VO2 Max",
}


def event_payload(workout, ftp=DEFAULT_FTP, desc=None, lang="pt", prev=None):
    return {
        "start_date_local": f"{workout['day']}T{START_TIME}",
        "category": "WORKOUT", "type": "Ride",
        "name": workout["name"],
        "description": desc or workout_text(workout, ftp, lang=lang, prev=prev),
        "planned_duration": workout["planned_duration"],
        "target": "POWER", "external_id": workout["external_id"],
    }


def workout_text(workout, ftp=DEFAULT_FTP, lang="pt", prev=None):
    """Descricao nativa do Intervals (workout builder): a primeira linha e o
    titulo do treino e cada passo e `texto duracao percentual%`. Os watts (ex:
    `83% (151w)`) sao calculados pelo Intervals a partir do FTP.

    Cada intervalo vira um passo proprio com uma mensagem explicativa antes da
    duracao (cue text -> textevent no .zwo). As repeticoes sao achatadas em
    passos individuais porque o parser do Intervals ignora o grupo `Nx` quando
    os passos internos trazem texto. O texto do cue nao pode conter "%".
    """
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


def reconcile(plan, events, ftp=DEFAULT_FTP, training_days=DEFAULT_TRAINING_DAYS):
    today = date.today()
    done_ids, extras = _done_and_extra(events)
    reduced_ids = set()
    missed = [w for w in plan
              if w["day"] < today.isoformat() and w["external_id"] not in done_ids]
    if missed:
        for m in missed:
            plan = _insert_recovery(plan, m["day"], ftp, training_days)
            plan = _reduce_next_hard(plan, m["day"], ftp, reduced_ids)
    plan = _adjust_for_extra_workouts(plan, extras, ftp, training_days,
                                      cap=daily_tss_cap(avg_load(events)),
                                      reduced_ids=reduced_ids)
    return plan, missed


def _done_and_extra(events):
    """Separa eventos hermes concluidos (done) de treinos feitos fora do plano
    (extra): evento com paired_activity_id cujo external_id nao e hermes-plan."""
    done_ids = set()
    extras = []
    for item in events:
        eid = item.get("external_id")
        paired = item.get("paired_activity_id")
        if not paired:
            continue
        if eid and eid.startswith(EXTERNAL_ID_PREFIX):
            done_ids.add(eid)
        else:
            day = _day(item)
            load = _num(item.get("tss") or item.get("icu_training_load"))
            if day and load:
                extras.append({"day": day, "load": float(load)})
    return done_ids, extras


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
                               tss=float(tss), external_id=w["external_id"])
            w = _as_dict(w)
            reduced_ids.add(w["external_id"])
            reduced_this_call = True
        out.append(w)
    return out


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


def save_plan(plan, path="plan.json"):
    out = pathlib.Path(path)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(plan, fh, ensure_ascii=False, indent=2)
    return out


def load_plan(path="plan.json"):
    with open(pathlib.Path(path), "r", encoding="utf-8") as fh:
        return json.load(fh)