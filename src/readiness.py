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
from enum import Enum

try:
    from coach import WorkoutParams, estimate_tss, FOCUS_ZONE2
except ImportError:
    from .coach import WorkoutParams, estimate_tss, FOCUS_ZONE2

try:
    from .readiness_assessment import ReadinessAssessment, ReadinessLevel
except ImportError:  # pragma: no cover - execucao como script solto
    from readiness_assessment import ReadinessAssessment, ReadinessLevel


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

# ---------------------------------------------------------------------------
# Produtor + politica de decisao (issue #58, Passo A)
# ---------------------------------------------------------------------------
#
# O modelo de 7 eixos (`readiness_assessment.ReadinessAssessment`) classifica a
# prontidao em GREEN/YELLOW/RED. Faltava a ponte entre o wellness bruto do
# Intervals e esse modelo, e faltava a politica que traduz a classe ordinal em
# uma decisao de adaptacao. As duas ficam aqui porque este modulo ja e o dono
# da leitura do wellness bruto e dos limiares(exercicios 1-4 acima).
#
# ## Escopo do que e medida
#
# O Intervals expoe **quatro** metricas de wellness em `/wellness`
# (`intervals_client.wellness`): `restingHR`, `hrv`/`hrvSDNN`, `sleepSecs` e o
# `readiness` do proprio Intervals. Sao as unicas fontes usadas aqui.
#
# Dos sete eixos do modelo, **tres** tem fonte real e sao preenchidos. Os
# outros quatro ficam `None` de proposito:
#
# - `recent_load_score`    — a carga recente nao existe no ponto da decisao: o
#   `build` ainda nao tem a serie de treino resolvida quando o dia e montado.
# - `subjective_fatigue_score` — RPE e digitado no treino realizado, nao chega
#   em `/wellness`.
# - `performance_score`    — sem fonte.
# - `consistency_score`    — sem fonte que nao seja derivada (ver abaixo).
#
# Preencher eixo ausente com um valor neutro (0,5) seria pior que deixar
# `None`: a media de `overall_readiness` cairia para todo mundo e um atleta
# saudavel leria YELLOW, reduzindo treino sem sinal nenhum. Ausencia de
# dado nao e evidencia de nada, em direcao nenhuma.
#
# ## Por que o `readiness` do Intervals nao vira eixo
#
# O campo `readiness` do Intervals e um **composto** derivado de HRV, sono e
# RHR — as mesmas entradas que ja viraram eixo. mapea-lo para um sétimo eixo
# contaria o mesmo dado duas vezes e inflaria a cobertura sem acrescentar
# observacao. Ele nao entra em `ReadinessAssessment`; entra como sinal
# separado (`composite_low`), preservando o limiar `READINESS_LOW` e a
# semantica do sinal `readiness_low` que ja existia.
#
# ## Escala dos escores
#
# `saudavel -> 0.8`, `sinal ligado -> 0.2`. Sao **heuristica do sistema**, nao
# escala calibrada: nao ha literatura que fixe 0.8 e 0.2, e o limiar poor
# do modelo (<0.4) fica exatamente no meio do intervalo entre eles, o que
# torna qualquer outro par pelo menos tao arbitrario. O que importa e que os
# tres limiares do modelo (<0.4 poor, media<0.5, media<0.7) mantem o mesmo
# significado que tinham antes desta ponte.


class ReadinessAction(str, Enum):
    """Decisao de adaptacao decorrente da prontidao."""

    NONE = "none"          # nao adapta por prontidao
    REDUCE = "reduce"      # reduz volume (e so depois intensidade), preserva a sessao
    REPLACE = "replace"    # politica conservadora legada: troca a sessao por leve


@dataclass(frozen=True)
class ReadinessObservation:
    """Um eixo realmente observado, com a fonte que o produziu."""

    axis: str              # nome do campo em ReadinessAssessment
    score: float
    source: str            # chave de /wellness e limiar que disparou, ou "-"
    flagged: bool          # o sinal existente disparou?


@dataclass(frozen=True)
class ReadinessTrace:
    """Rastreabilidade do produtor: o que foi medido e o que nao foi."""

    observations: tuple    # tuple[ReadinessObservation, ...]
    missing: tuple         # eixos sem dado -> None (nunca zero, nunca neutro)
    signals: dict          # sinais de assess_readiness, para auditoria
    illness_alert: bool    # conjuncao RHR 2+ noites E HRV caindo
    composite_low: bool    # readiness do Intervals < READINESS_LOW
    stale_days: int | None  # dias desde o ultimo registro, None se nao ha dado
    reference_day: str | None  # dia que o sinal descreve (ultimo registro)

    @property
    def coverage(self) -> float:
        return len(self.observations) / 7.0


@dataclass(frozen=True)
class ReadinessDecision:
    """Decisao efetiva + o que a produziu. `level` e a classificacao original,
    preservada mesmo quando o alerta separado a ultrapassa.

    `applies_to_day` e o dia que o sinal DESCREVE (o dia do ultimo registro de
    wellness), nao o dia em que a decisao foi tomada. E a ancora de validade:
    ver `_adapt_session` em `plan.py`. `None` significa "sem ancora" e mantem o
    comportamento legado — o produtor sempre preenche, entao `None` so aparece
    em decisoes montadas a mao.
    """

    action: ReadinessAction
    reason: str
    level: ReadinessLevel | None
    coverage: float
    illness_alert: bool
    composite_low: bool
    observations: tuple
    applies_to_day: str | None = None

    @property
    def is_adaptive(self) -> bool:
        return self.action is not ReadinessAction.NONE


HEALTHY_SCORE = 0.8    # heuristica do sistema, nao escala calibrada
FLAGGED_SCORE = 0.2   # idem


def assess_readiness_assessment(records, days=7):
    """Wellness bruto -> (ReadinessAssessment | None, ReadinessTrace).

    Devolve `None` quando nao ha wellness utilizavel: um atleta sem dispositivo
    de sono/HRV precisa gerar plano normalmente, entao ausencia de dado aqui
    significa "nada a dizer", nunca "prontidao ruim".
    """
    legacy = assess_readiness(records, days=days)
    trace_missing = ("hrv_score", "rhr_score", "sleep_score",
                     "recent_load_score", "subjective_fatigue_score",
                     "performance_score", "consistency_score")
    if not legacy.has_data:
        return None, ReadinessTrace(observations=(), missing=trace_missing,
                                    signals={}, illness_alert=False,
                                    composite_low=False, stale_days=None,
                                    reference_day=None)

    rows = _rows(records)
    obs = []

    def eixo(nome, fonte, sinal):
        obs.append(ReadinessObservation(
            axis=nome,
            score=FLAGGED_SCORE if sinal else HEALTHY_SCORE,
            source=fonte, flagged=bool(sinal)))

    eixo("hrv_score", f"hrv/hrvSDNN (< {HRV_LOW_RATIO:.2f} x media)", _low_hrv(rows, days))
    eixo("rhr_score", f"restingHR (> media + {RHR_RISE_BPM} bpm)", _rising_rhr(rows, days))
    eixo("sleep_score", f"sleepSecs (< {SLEEP_SHORT_HOURS}h ou < media - {SLEEP_BELOW_AVG_HOURS}h)", _short_sleep(rows, days))

    # `illness` e conjuncao (RHR 2+ noites E HRV caindo) e nao cabe em um eixo
    # escalar. Fica como sinal separado, avaliado por `readiness_decision`, e
    # NAO rebaixa rhr/hrv score: rebaixar os dois eixos seria contar o mesmo
    # dado duas vezes e criaria um RED que o detector de doenca nunca pediu.
    legacy_comp = legacy.signals.get("readiness_low", False)
    avaliacao = ReadinessAssessment(
        hrv_score=obs[0].score,
        rhr_score=obs[1].score,
        sleep_score=obs[2].score,
        recent_load_score=None,
        subjective_fatigue_score=None,
        performance_score=None,
        consistency_score=None,
    )
    missing = tuple(nome for nome in trace_missing
                    if nome not in ("hrv_score", "rhr_score", "sleep_score"))
    stale = _days_since_last(rows)
    return avaliacao, ReadinessTrace(
        observations=tuple(obs), missing=missing, signals=dict(legacy.signals),
        illness_alert=bool(legacy.illness), composite_low=bool(legacy_comp),
        stale_days=stale, reference_day=rows[-1][0] if rows else None)


def _days_since_last(rows):
    """Dias desde o ultimo registro, ou None se a data nao e parseavel."""
    from datetime import date
    if not rows:
        return None
    try:
        ultimo = date.fromisoformat(rows[-1][0])
    except (TypeError, ValueError):
        return None
    return max(0, (date.today() - ultimo).days)


def readiness_decision(assessment, illness_alert=False, composite_low=False,
                       coverage=None, observations=(), reference_day=None):
    """Classificacao ordinal -> decisao de adaptacao. Politica explicita.

    Precedencia (a mais restritiva vence, e nenhuma regra desfaz a anterior):

    1. `illness_alert` — alerta de possivel doenca/recuperacao comprometida.
       Vence sempre, inclusive com `level()` GREEN e cobertura baixa, porque e
       uma conjuncao observada (RHR 2+ noites E HRV caindo), nao uma media.
       Nao e diagnostico: e um alerta de que treinar forte hoje e questionavel.
    2. `level() == RED` — tres eixos abaixo de 0.4 E media abaixo de 0.5.
    3. `level() == YELLOW` — um eixo ruim, ou media abaixo de 0.7.
    4. `composite_low` — readiness do Intervals abaixo de READINESS_LOW. Fora
       dos eixos (deriva das mesmas entradas), mas e um sinal real: isolado,
       ele segura REDUCE, nunca RED.
    5. `NONE`.

    Sem nenhuma observacao e sem alerta: `NONE` por prontidao, com o motivo
    explicito de dados insuficientes. Isso nao e "prontidao boa" e a
    adaptacao por TSB continua valendo normalmente.
    """
    if assessment is None:
        # Caminho mais frequente do sistema: atleta sem leitura de sono/HRV
        # continua gerando plano normalmente. Precisa vir antes de qualquer
        # leitura de atributo, porque `assessment` nao existe aqui.
        return ReadinessDecision(
            ReadinessAction.NONE,
            "dados de recuperacao indisponiveis: nenhuma observacao de "
            "sono/HRV/RHR para avaliar (ausencia de dado nao e sinal ruim)",
            None, 0.0 if coverage is None else coverage, False, composite_low,
            tuple(observations), reference_day)

    cov = assessment.confidence if coverage is None else coverage
    if illness_alert:
        return ReadinessDecision(
            ReadinessAction.REPLACE,
            "alerta de possivel doenca/recuperacao comprometida (RHR em "
            "2+ noites e HRV em queda): aplica-se a politica conservadora",
            assessment.level(), cov, True, composite_low, tuple(observations),
            reference_day)

    nivel = assessment.level()
    if nivel is ReadinessLevel.RED:
        return ReadinessDecision(
            ReadinessAction.REPLACE,
            f"prontidao RED (>=3 eixos abaixo de 0.4 e media {assessment.overall_readiness:.2f} "
            "< 0.5): aplica-se a politica conservadora",
            nivel, cov, False, composite_low, tuple(observations))

    if nivel is ReadinessLevel.YELLOW:
        return ReadinessDecision(
            ReadinessAction.REDUCE,
            f"prontidao YELLOW (media {assessment.overall_readiness:.2f}): reduz volume, "
            "preserva a sessao e a intensidade da zona",
            nivel, cov, False, composite_low, tuple(observations),
            reference_day)

    if composite_low:
        return ReadinessDecision(
            ReadinessAction.REDUCE,
            f"readiness do Intervals abaixo de {READINESS_LOW} (sinal derivado, "
            "fora dos eixos): reduz volume, preserva a sessao",
            nivel, cov, False, composite_low, tuple(observations))

    return ReadinessDecision(
        ReadinessAction.NONE,
        f"prontidao GREEN (media {assessment.overall_readiness:.2f}, cobertura "
        f"{cov:.0%} dos 7 eixos): sem alteracao por prontidao",
        nivel, cov, False, composite_low, tuple(observations), reference_day)


def legacy_recovery_params():
    """A prescricao de Z2 usada historicamente pelo alerta de doenca.

    **Politica legada, nao garantia de segurança.** Trocar o treino por 15 min
    de Z2 quando ha alerta e o que o motor ja fazia; e um recurso conservador
    de convencao, nao uma resposta validada para possivel doenca e nao
    prescricao clinica. Treino leve nao e obrigatoriamente adequado para
    ninguem: continua sendo uma *proposta*, com o aviso visivel.
    """
    return WorkoutParams(focus=FOCUS_ZONE2, repeats=1, on_sec=900, off_sec=0,
                         on_power=0.70, off_power=0.70, cadence=90,
                         cadence_rest=90)
