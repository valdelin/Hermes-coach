"""Prontidao diaria (wellness -> sugestao de treino).

Features 1 e 3 da comparacao competitiva com o IntervalCoach (26/09):

- **Sugestao por recuperacao (nao obrigatoria):** le os sinais de wellness
  (RHR, HRV, sono, readiness) e *sugere* trocar o treino de hoje por uma
  recuperacao leve. O atleta decide: o `check` so reporta, e aplicar a troca
  exige `check --apply` explicito.
- **Alerta de inicio de doenca:** RHR subindo 2+ noites seguidas com HRV
  caindo -> aviso de "algo se aproximando" (nao treinar sobre doenca). Se
  `COACH_WEBHOOK` estiver no .env, o aviso e enviado ao treinador tambem.

Tudo e opcional e nunca altera o plano sozinho (regra do projeto: o motor e
deterministico e o atleta sempre tem a palavra final).
"""
from dataclasses import dataclass

try:
    from coach import WorkoutParams, estimate_tss, FOCUS_ZONE2
except ImportError:
    from .coach import WorkoutParams, estimate_tss, FOCUS_ZONE2


# Limiares dos sinais (ajustaveis por constante, documentados aqui):
# - RHR subindo: ultimo registro acima da media dos anteriores + 3 bpm;
# - HRV caindo: ultimo abaixo de 80% da media (sinal de estresse acumulado);
# - Sono curto: ultima noite < 6h (ou 2h abaixo da media);
# - Readiness baixo: < 60 (escala do Intervals/Garmin).
RHR_RISE_BPM = 3.0
HRV_LOW_RATIO = 0.80
SLEEP_SHORT_HOURS = 6.0
SLEEP_BELOW_AVG_HOURS = 2.0
READINESS_LOW = 60


@dataclass(frozen=True)
class Readiness:
    """Estado de prontidao do atleta no dia."""

    signals: dict          # {'rhr_rising': bool, 'hrv_low': bool, ...}
    illness: bool          # possivel inicio de doenca (RHR 2 noites + HRV caindo)
    reason: str            # texto explicativo do porquê
    has_data: bool         # False quando nao ha wellness sincronizado


def _rows(records):
    """Linhas (dia, registro) ordenadas, tolerando id ou day como chave."""
    rows = []
    for rec in records or []:
        day = str(rec.get("id") or rec.get("day") or "")[:10]
        if day:
            rows.append((day, rec))
    rows.sort(key=lambda r: r[0])
    return rows


def _last(key, rows):
    for _, rec in reversed(rows):
        v = rec.get(key)
        if isinstance(v, (int, float)):
            return float(v)
    return None


def _avg(key, rows, days=7):
    vals = [float(rec[key]) for _, rec in rows[-days:]
            if isinstance(rec.get(key), (int, float))]
    return (sum(vals) / len(vals)) if vals else None


def _rising_rhr(rows, days=7):
    """RHR subindo: ultimo registro acima da media dos `days` + RHR_RISE_BPM.
    Usa a media dos dias anteriores ao ultimo para nao contaminar a base."""
    if len(rows) < 2:
        return False
    last_rhr = _last("restingHR", rows)
    base = _avg("restingHR", rows[:-1], days=days)
    if last_rhr is None or base is None:
        return False
    return last_rhr > base + RHR_RISE_BPM


def _low_hrv(rows, days=7):
    """HRV caindo: ultimo abaixo de HRV_LOW_RATIO x a media."""
    last_hrv = _last("hrv", rows) or _last("hrvSDNN", rows)
    base = _avg("hrv", rows, days=days) or _avg("hrvSDNN", rows, days=days)
    if last_hrv is None or base is None or base <= 0:
        return False
    return last_hrv < base * HRV_LOW_RATIO


def _short_sleep(rows, days=7):
    last = _last("sleepSecs", rows)
    base = _avg("sleepSecs", rows, days=days)
    if last is None:
        return False
    hours = last / 3600
    if hours < SLEEP_SHORT_HOURS:
        return True
    if base:
        return last < base - SLEEP_BELOW_AVG_HOURS * 3600
    return False


def _low_readiness(rows):
    last = _last("readiness", rows)
    return last is not None and last < READINESS_LOW


def _illness(rows):
    """Possivel inicio de doenca: RHR subindo 2+ noites seguidas E HRV caindo
    (mesmo heuristico do IntervalCoach: 'Resting heart rate up two nights
    running while HRV falls')."""
    if len(rows) < 3:
        return False
    rhrs = [rec.get("restingHR") for _, rec in rows[-3:]
            if isinstance(rec.get("restingHR"), (int, float))]
    if len(rhrs) < 3:
        return False
    rising_two = rhrs[-1] > rhrs[-2] > rhrs[-3]
    hrv_last = _last("hrv", rows) or _last("hrvSDNN", rows)
    hrv_prev = None
    for _, rec in reversed(rows[:-1]):
        v = rec.get("hrv")
        if v is None:
            v = rec.get("hrvSDNN")
        if isinstance(v, (int, float)):
            hrv_prev = float(v)
            break
    dropping = hrv_last is not None and hrv_prev is not None and \
        hrv_last < hrv_prev
    return rising_two and dropping


def assess_readiness(records, days=7):
    """Analisa os registros de wellness e devolve o estado de prontidao."""
    rows = _rows(records)
    if not rows:
        return Readiness({}, False,
                         "sem dados de wellness (sync Garmin -> Intervals "
                         "pendente)", has_data=False)
    signals = {
        "rhr_rising": _rising_rhr(rows, days),
        "hrv_low": _low_hrv(rows, days),
        "sleep_short": _short_sleep(rows, days),
        "readiness_low": _low_readiness(rows),
    }
    illness = _illness(rows)
    why = _reason(signals, illness)
    return Readiness(signals, illness, why, has_data=True)


def _reason(signals, illness):
    parts = []
    if illness:
        parts.append("RHR subindo 2+ noites com HRV caindo: possivel inicio "
                     "de doenca")
    if signals.get("rhr_rising") and not illness:
        parts.append("RHR acima da media")
    if signals.get("hrv_low") and not illness:
        parts.append("HRV abaixo de 80% da media")
    if signals.get("sleep_short"):
        parts.append("sono curto (< 6h ou bem abaixo da media)")
    if signals.get("readiness_low"):
        parts.append("readiness baixo (< 60)")
    return "; ".join(parts) if parts else "sinais de recuperacao dentro do normal"


def suggest_swap(readiness, planned_today=None):
    """Sugestao de (nao) trocar o treino por recuperacao leve.

    Retorna (swap, texto): `swap` True quando vale considerar reduzir, com o
    motivo. Nunca aplica nada — o atleta decide (o CLI exige `--apply`)."""
    if not readiness.has_data:
        return False, "sem dados de wellness para sugerir ajuste."
    if not any(readiness.signals.values()):
        return False, readiness.reason
    if readiness.illness:
        return True, ("alerta de doenca: considere trocar o treino de hoje "
                      "por recuperacao leve ou descanso.")
    if planned_today and planned_today.get("focus") in ("threshold", "vo2max"):
        return True, (f"treino exigente hoje ({planned_today.get('focus')}) "
                      f"com {readiness.reason}: considere uma recuperacao "
                      "leve no lugar.")
    if readiness.signals.get("rhr_rising") or readiness.signals.get("hrv_low"):
        return True, (f"{readiness.reason}: vale conversar antes de manter "
                      "o treino de qualidade.")
    return False, readiness.reason


def recovery_workout(day, ftp, lang="pt"):
    """Workout de recuperacao leve (Z2 curto) para o `check --apply` trocar o
    treino do dia. Retorna dict no formato do plan.json."""
    params = WorkoutParams(
        focus=FOCUS_ZONE2, repeats=1, on_sec=900, off_sec=0,
        on_power=0.70, off_power=0.70, cadence=90, cadence_rest=90,
    )
    tss = estimate_tss(params, ftp)
    duration = params.warmup_sec + params.repeats * (params.on_sec + params.off_sec) \
        + params.cooldown_sec
    name = f"{day} - Treino de Zona 2 (recuperacao ativa)"
    return {
        "day": day,
        "focus": FOCUS_ZONE2,
        "planned_duration": duration,
        "name": name,
        "params": {
            "focus": params.focus,
            "warmup_sec": params.warmup_sec,
            "warmup_cadence": params.warmup_cadence,
            "warmup_power_low": params.warmup_power_low,
            "warmup_power_high": params.warmup_power_high,
            "repeats": params.repeats,
            "on_sec": params.on_sec,
            "off_sec": params.off_sec,
            "on_power": params.on_power,
            "off_power": params.off_power,
            "cadence": params.cadence,
            "cadence_rest": params.cadence_rest,
            "cooldown_sec": params.cooldown_sec,
            "cooldown_cadence": params.cooldown_cadence,
            "cooldown_power_low": params.cooldown_power_low,
            "cooldown_power_high": params.cooldown_power_high,
        },
        "tss": float(tss),
        "external_id": f"hermes-plan-{day}",
    }


def coach_alert_payload(atleta_id, readiness, today):
    """Payload JSON para avisar o treinador (COACH_WEBHOOK) de um alerta de
    inicio de doenca. Chamado apenas quando `readiness.illness`."""
    return {
        "atleta": atleta_id,
        "dia": today,
        "tipo": "alerta-doenca",
        "mensagem": readiness.reason,
        "sinais": readiness.signals,
    }