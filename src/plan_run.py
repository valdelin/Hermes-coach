"""Prototipo #18: treinos de corrida (esporte #2).

Prescricao SEM medidor de potencia (padrao de mercado — quase ninguem tem
power meter de corrida): alvos em **%LTHR** (FC no limiar da corrida) + **RPE**
como ancora, com **dica opcional de ritmo** (rFTP, config `RFTP_PACE`).

Foco (TSB) -> sessao de corrida:
  zone2      -> rodada facil continua
  endurance  -> rodada longa (dia do longo)
  sweetspot  -> tempo run (intervalos)
  threshold  -> intervalos no limiar
  vo2max     -> intervalos VO2 (ou tiros em subida)

Estrutura identica ao ciclismo (aquecimento -> blocos -> desaquecimento); o
`params` ganha `sport: "run"`. A carga (TSS) NAO e calculada aqui: no fluxo
real ela vem do Intervals por FC (`icu_training_load`, como o modo FC do
ciclismo #3) — zero matematica nova.
"""
import re

# Unidade de intensidade -> %LTHR e RPE por foco (consenso da literatura de
# corrida: Daniel's/LPF zonas de FC). `hr_high > 100` indica esforco acima do
# limiar de FC (VO2 na pratica nao segura 100% LTHR tanto tempo).
RUN_FOCUS = {
    "zone2": dict(repeats=1, on_sec=2700, off_sec=0, hr_low=60, hr_high=75, rpe=2),
    "endurance": dict(repeats=1, on_sec=4500, off_sec=0, hr_low=65, hr_high=75, rpe=4),
    "sweetspot": dict(repeats=3, on_sec=600, off_sec=180, hr_low=75, hr_high=85, rpe=7),
    "threshold": dict(repeats=4, on_sec=480, off_sec=180, hr_low=85, hr_high=95, rpe=9),
    "vo2max": dict(repeats=6, on_sec=180, off_sec=180, hr_low=95, hr_high=102, rpe=10),
    # Fartlek: 10x (1' forte + 1' trote). NAO se controla por FC — a FC atrasa
    # e nunca alcança a zona num surto de 1': alvo = RPE + ritmo relativo.
    "fartlek": dict(repeats=10, on_sec=60, off_sec=60, hr_low=0, hr_high=0, rpe=9),
}

# RPE da recuperacao (trote) e aquecimento/desaquecimento.
_RECOVERY_RPE = 3
WARMUP_SEC = 600
COOLDOWN_SEC = 600
START_TIME = "07:00"

RUN_FOCUS_LABELS = {
    "zone2": "Rodada facil",
    "endurance": "Rodada longa",
    "sweetspot": "Tempo run",
    "threshold": "Intervalos Limiar",
    "vo2max": "Intervalos VO2",
    "fartlek": "Fartlek",
}

# Fator para transformar o ritmo-limiar (rFTP, s/km) em ritmo-alvo da serie.
# > 1 = mais lento que o rFTP; < 1 = mais rapido.
_PACE_FACTOR = {
    "zone2": 1.25,
    "endurance": 1.25,
    "sweetspot": 1.08,
    "threshold": 1.00,
    "vo2max": 0.94,
}

# Linguagem de alvo por template (decidir com treinador no #18) — a variavel
# de controle NAO e do foco, e de cada formato de exercicio:
# - PACE: mais facil de controlar nos treinos de qualidade (corredor segura
#   ritmo, nao FC); FC vira ancora nas repeticoes longas;
# - HR: estados estaveis (endurance/recovery) onde a FC alcança e segura a zona;
# - RPE: fartlek/VO2 curto — a FC atrasa 20-40s e nunca alcança a zona num
#   surto < 2'; prescreve-se esforco, nao bpm. HR e so validacao posterior.
# O atleta pode trocar ao montar o plano (target explicito vence); sem
# `rftp_pace` no build, alvos "pace" caem para "hr".
RUN_TARGET_DEFAULT = {
    "zone2": "hr",
    "endurance": "hr",
    "sweetspot": "pace",
    "threshold": "pace",
    "vo2max": "pace",
    "fartlek": "rpe",
}


def _hm(sec):
    """Duracao em minutos arredondada, formato '12' ('xx')."""
    return f"{round(sec / 60)}"


def _pct(value):
    return f"{int(round(value))}%"


def _pace_str(seconds_km):
    """'mm:ss/km' a partir de s/km."""
    sec = int(round(seconds_km))
    return f"{sec // 60}:{sec % 60:02d}/km"


def _parse_pace(rftp_pace):
    """'4:30/km' ou '4:30' -> segundos por km (None se invalido)."""
    if not rftp_pace:
        return None
    m = re.match(r"(\d+):(\d{2})", str(rftp_pace).strip())
    if not m:
        return None
    minutes, seconds = int(m.group(1)), int(m.group(2))
    if seconds >= 60:
        return None
    sec = minutes * 60 + seconds
    return sec if sec > 0 else None


def run_workout(focus, *, r_lthr=170, target=None, day=None, name=None):
    """Workout de corrida (dict pronto para o plan.json) para um foco.

    `params` herda os campos do ciclismo (foco/repeats/on_sec/off_sec) e soma
    `sport: "run"` + `hr_mode: True`; o push correspondente vai com
    `target: HEART_RATE` e `type: Run`.

    `target` escolhe a linguagem da serie: "pace" (ritmo-alvo do rFTP, mais
    facil de controlar), "hr" (zona LTHR + RPE) ou "rpe" (fartlek — esforco,
    nao bpm). Default em RUN_TARGET_DEFAULT (a validar com treinador); sem
    `rftp_pace` disponivel no build, alvos "pace" caem para "hr".
    """
    preset = RUN_FOCUS[focus]
    target = target or RUN_TARGET_DEFAULT.get(focus, "hr")
    params = {
        "sport": "run",
        "hr_mode": True,
        "focus": focus,
        "repeats": preset["repeats"],
        "on_sec": preset["on_sec"],
        "off_sec": preset["off_sec"],
        "hr_low": preset["hr_low"],
        "hr_high": preset["hr_high"],
        "rpe": preset["rpe"],
        "r_lthr": int(r_lthr),
        "target": target,  # "pace" | "hr" | "rpe" — decisao do treinador
    }
    return {
        "day": day or "2026-09-23",
        "focus": focus,
        "name": name or RUN_FOCUS_LABELS[focus],
        "planned_duration": (WARMUP_SEC
                             + preset["repeats"] * (preset["on_sec"] + preset["off_sec"])
                             + COOLDOWN_SEC),
        "params": params,
        "tss": 0.0,  # carga real via Intervals (FC) — preenchido no fluxo
        "external_id": f"hermes-run-{day or '2026-09-23'}",
    }


def run_text(workout, *, r_lthr=None, rftp_pace=None, lang="pt"):
    """Texto prescritivo. A variavel de controle vem de `params["target"]`:

    - "hr"   -> zona de FC (%LTHR + bpm) com RPE como ancora;
    - "pace" -> ritmo-alvo do rFTP como alvo primario, FC (zona+bpm) como
      ancora da serie (ritmo responde a subida/calor);
    - "rpe"  -> fartlek/VO2 curto: a FC nao alcança a zona em surto < 2',
      prescreve-se esforco ("ritmo 5K", RPE) — bpm e so validacao posterior.

    Sem `rftp_pace` disponivel, alvos "pace" caem para "hr".
    """
    params = workout["params"]
    focus = workout["focus"]
    lthr = int(r_lthr or params.get("r_lthr", 170))
    preset = RUN_FOCUS[focus]
    low, high, rpe = preset["hr_low"], preset["hr_high"], preset["rpe"]
    pace_sec = _parse_pace(rftp_pace)
    target = params.get("target", RUN_TARGET_DEFAULT.get(focus, "hr"))
    if target == "pace" and not pace_sec:
        target = "hr"  # sem rFTP configurado, nada de ritmo-alvo

    title = RUN_FOCUS_LABELS[focus]
    lines = [workout["name"] or title, ""]
    bpm_lo = round(lthr * low / 100)
    bpm_hi = round(lthr * high / 100)
    if focus in ("zone2", "endurance"):
        # Estados estaveis: FC e a variavel certa (ritmo varia com terreno).
        pace_hint = _pace_hint(pace_sec, focus) if pace_sec else ""
        lines.append(
            f"- {title}: {_hm(preset['on_sec'])}' continuo a "
            f"{_pct(low)}-{_pct(high)} LTHR ({bpm_lo}-{bpm_hi} bpm)"
            f"{pace_hint}; RPE {preset['rpe']}")
        return "\n".join(lines)

    lines.append(f"- Aquecimento {_hm(WARMUP_SEC)}' a 60-75% LTHR, RPE 2")
    for _ in range(preset["repeats"]):
        if target == "rpe":
            # Fartlek: 1' forte a "ritmo 5K" nao tem zona de FC possivel.
            lines.append(
                f"- {title}: {_hm(preset['on_sec'])}' forte a ritmo 5-10K "
                f"(RPE {rpe})")
        elif target == "pace" and pace_sec:
            lines.append(
                f"- {title}: {_hm(preset['on_sec'])}' a "
                f"ritmo ~{_pace_str(pace_sec * _PACE_FACTOR[focus])} "
                f"({_pct(low)}-{_pct(high)} LTHR, {bpm_lo}-{bpm_hi} bpm); "
                f"RPE {rpe}")
        else:
            lines.append(
                f"- {title}: {_hm(preset['on_sec'])}' a "
                f"{_pct(low)}-{_pct(high)} LTHR ({bpm_lo}-{bpm_hi} bpm); "
                f"RPE {rpe}")
        if preset["off_sec"]:
            lines.append(
                f"- Trote leve {_hm(preset['off_sec'])}' "
                f"a 55-65% LTHR; RPE {_RECOVERY_RPE}")
    lines.append(f"- Desaquecimento {_hm(COOLDOWN_SEC)}' a 60-70% LTHR, RPE 2")
    return "\n".join(lines)


def _pace_hint(pace_sec, focus):
    return f" | ritmo ~{_pace_str(pace_sec * _PACE_FACTOR[focus])}"


def event_payload_run(workout, desc=None):
    """Evento de corrida no calendario: `type: Run`, `target: HR`.

    O Garmin (935 suporta) executa a sessao por zona de FC diretamente no
    relogio; `rftp_pace` so aparece como dica no texto. `.zwo` (ERG) nao se
    aplica a corrida. Nota: o Intervals usa o enum `HR` (nao `HEART_RATE`).
    """
    return {
        "start_date_local": f"{workout['day']}T{START_TIME}",
        "category": "WORKOUT",
        "type": "Run",
        "name": workout["name"],
        "description": desc or run_text(workout),
        "planned_duration": workout["planned_duration"],
        # corrida sem power meter: alvo por FC
        "target": "HR",
        "external_id": workout["external_id"],
    }
