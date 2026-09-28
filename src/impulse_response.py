"""Motor de carga fisiologica (Banister Impulse-Response).

Implementa o modelo descrito no doc de arquitetura do projeto
(docs/ARQUITETURA.md, secao 1): calculo de TSS padrao (IF^2 x horas x 100) e
atualizacao continua de Fitness (CTL), Fadiga (ATL) e Forma (TSB) por
suavizacao exponencial com constantes de tempo de 42 e 7 dias.

Uso:
    engine = ImpulseResponseEngine()
    tss = engine.calculate_tss(duration_sec=3600, avg_intensity=0.95, threshold=1.0)
    m = engine.compute_metrics([45, 60, 0, 80, ...])

O fluxo principal (build/reconcile/push) usa as metricas do Intervals.icu
(src/coach.py::latest_metrics); este motor serve para analise local e
projecao (CLI `model`).
"""
import math
from datetime import date, timedelta


class ImpulseResponseEngine:
    """Motor Impulse-Response do modelo de Banister (CTL/ATL/TSB)."""

    def __init__(self, ctl_time_constant: int = 42, atl_time_constant: int = 7):
        self.tc_ctl = ctl_time_constant
        self.tc_atl = atl_time_constant

    def calculate_tss(self, duration_sec: int, avg_intensity: float,
                      threshold: float) -> float:
        """Training Stress Score (TSS) padrao de um treino.

        `avg_intensity / threshold` representa o Intensity Factor (IF).
        Formula: TSS = IF^2 * horas * 100 (equivalente a
        `(dur * avg_intensity * IF) / (threshold * 3600) * 100`).
        Retorna 0.0 para threshold invalido (<= 0).
        """
        if threshold <= 0:
            return 0.0
        intensity_factor = avg_intensity / threshold
        tss = (duration_sec * (avg_intensity * intensity_factor)) / (threshold * 3600) * 100
        return round(tss, 2)

    def compute_metrics(self, daily_tss_history, initial_ctl: float = 0.0,
                        initial_atl: float = 0.0) -> dict:
        """Aplica o modelo Impulse-Response sobre o historico diario de TSS.

        Cada dia atualiza CTL e ATL por suavizacao exponencial (`tc` em dias).
        Retorna {"ctl_fitness", "atl_fatigue", "tsb_form"} (tsb = ctl - atl).
        `initial_ctl`/`initial_atl` permitem projetar a partir de um estado
        atual (ex.: metricas do Intervals.icu) em vez de partir de zero.
        """
        ctl = initial_ctl
        atl = initial_atl
        for tss in daily_tss_history:
            ctl = ctl + (tss - ctl) * (1 - math.exp(-1 / self.tc_ctl))
            atl = atl + (tss - atl) * (1 - math.exp(-1 / self.tc_atl))
        tsb = ctl - atl
        return {
            "ctl_fitness": round(ctl, 1),
            "atl_fatigue": round(atl, 1),
            "tsb_form": round(tsb, 1),
        }


def daily_tss_series(events, window_days: int = 60, today=None) -> list:
    """Serie diaria de TSS ordenada por dia (cronologica).

    Soma por dia o TSS dos eventos (campo `tss` ou fallback
    `icu_training_load`) dentro da janela `window_days` encerrada em `today`.
    Eventos sem carga (None/0) sao ignorados. Mesmo criterio de carga usado
    no reconcile (src/plan.py::_done_and_extra).
    """
    by_day = daily_load_by_date(events, window_days=window_days, today=today)
    return [tss for _, tss in sorted(by_day.items())]


def daily_load_by_date(events, window_days: int = 60, today=None) -> dict:
    """Mapa `{date: carga}` dos eventos dentro da janela (dias com carga 0
    ficam de fora — o preenchimento com zeros e responsabilidade do consumo).

    Mesmo criterio de carga da `daily_tss_series`: campo `tss`, fallback
    `icu_training_load`, ignorando dias sem carga.
    """
    today = today or date.today()
    cutoff = today - timedelta(days=window_days)
    by_day = {}
    for item in events:
        day = _day(item)
        load = _num(item.get("tss") or item.get("icu_training_load"))
        if not day or not load or load <= 0:
            continue
        day = date.fromisoformat(str(day)[:10])
        if day < cutoff or day > today:
            continue
        by_day[day] = by_day.get(day, 0.0) + float(load)
    return by_day


def fill_daily_series(by_day, start, end):
    """Expande {date: carga} em lista cronologica com dias de descanso = 0.

    Necessario para o decaimento exponencial (EWMA 42/7) do modelo
    Impulse-Response nao sofrer compressao de tempo quando ha hiatos sem
    treino (ver `forecast_pmc`). Retorna uma carga por dia de `start` a `end`,
    ambos inclusivos; dias sem carga entram como 0.0.
    """
    one = timedelta(days=1)
    day = start
    series = []
    while day <= end:
        series.append(float(by_day.get(day, 0.0)))
        day += one
    return series


PMC_ALERT_TSB = -10.0
PMC_ZONE_HIGH_RISK = -30.0
PMC_ZONE_TRANSITION = 25.0

_ALERT_THRESHOLD = PMC_ALERT_TSB


def _tsb_zone(tsb):
    """Rótulo da zona de TSB conforme Joe Friel ("Managing Training Using TSB").

    - `high-risk`: `< -30` (overreaching; ficar poucos dias, R&R depois).
    - `optimal`:   `-30..-10` (maior estímulo de treino).
    - `grey`:      `-10..+5` (planalto: recuperação/taper/volta).
    - `freshness`: `+5..+25` (pronto p/ prova / qualidade).
    - `transition`: `> +25` (fim de temporada; pouco/nenhum treino).
    """
    if tsb < PMC_ZONE_HIGH_RISK:
        return "high-risk"
    if tsb < PMC_ALERT_TSB:
        return "optimal"
    if tsb < 5.0:
        return "grey"
    if tsb <= PMC_ZONE_TRANSITION:
        return "freshness"
    return "transition"


def forecast_pmc(events, plan, initial_ctl: float = None,
                 initial_atl: float = None, today=None, horizon=None,
                 window_days: int = 60) -> dict:
    """Expected PMC: projeta CTL/ATL/TSB misturando o real com o planejado.

    - Fase real: os eventos (carga real) ate `today`, incluindo dias com
      carga 0 para o decaimento exponencial nao sofrer compressao de tempo.
      Se `initial_ctl`/`initial_atl` vierem da API (estado atual autoritativo),
      essa fase e pulada e a simulacao parte desse estado em `today`;
      caso contrario o proprio historico real estabelece o ponto de partida.
    - Fase planejada: treinos do plano (campo `tss`, TSS somado por dia) de
      `today + 1` ate o fim do plano (ou `horizon`, se menor que o fim).

    Retorna {"series": [{"day", "ctl", "atl", "tsb", "zone"} por dia de hoje ao
    fim], "alerts": [{"day", "tsb"} nos dias onde TSB <= PMC_ALERT_TSB],
    "high_risk": [{"day", "tsb"} nos dias onde TSB < PMC_ZONE_HIGH_RISK],
    "transition": [{"day", "tsb"} nos dias onde TSB > PMC_ZONE_TRANSITION],
    "end": {"ctl_fitness", "atl_fatigue", "tsb_form"}}.
    Sem plano futuro retorna series vazia e end None.
    """
    today = today or date.today()
    planned = {}
    for w in plan:
        day = date.fromisoformat(str(w["day"])[:10])
        if day <= today:
            continue
        load = _num(w.get("tss"))
        if load and load > 0:
            planned[day] = planned.get(day, 0.0) + float(load)
    if not planned:
        return {"series": [], "alerts": [], "high_risk": [],
                "transition": [], "end": None}

    end_day = today + timedelta(days=1)
    for day in planned:
        if day > end_day:
            end_day = day
    if horizon is not None and date.fromisoformat(str(horizon)[:10]) < end_day:
        end_day = date.fromisoformat(str(horizon)[:10])

    engine = ImpulseResponseEngine()
    ctl = initial_ctl if initial_ctl is not None else 0.0
    atl = initial_atl if initial_atl is not None else 0.0

    if initial_ctl is None:
        # fase real (sem estado inicial): simula o historico incluindo zeros
        real = daily_load_by_date(events, window_days=window_days, today=today)
        if real:
            start = min(real)
            day_list = [real.get(start + timedelta(days=i), 0.0)
                        for i in range((today - start).days + 1)]
        else:
            day_list = []
        m = engine.compute_metrics(day_list, initial_ctl=ctl, initial_atl=atl)
        ctl, atl = m["ctl_fitness"], m["atl_fatigue"]

    k_ctl = 1 - math.exp(-1 / engine.tc_ctl)
    k_atl = 1 - math.exp(-1 / engine.tc_atl)
    series = [{"day": today.isoformat(),
               "ctl": round(ctl, 1), "atl": round(atl, 1),
               "tsb": round(ctl - atl, 1),
               "zone": _tsb_zone(round(ctl - atl, 1))}]
    d = today + timedelta(days=1)
    while d <= end_day:
        tss = planned.get(d, 0.0)
        ctl = ctl + (tss - ctl) * k_ctl
        atl = atl + (tss - atl) * k_atl
        tsb = round(ctl - atl, 1)
        series.append({"day": d.isoformat(),
                       "ctl": round(ctl, 1), "atl": round(atl, 1),
                       "tsb": tsb, "zone": _tsb_zone(tsb)})
        d += timedelta(days=1)

    alerts = [{"day": row["day"], "tsb": row["tsb"]}
              for row in series if row["tsb"] <= _ALERT_THRESHOLD]
    high_risk = [{"day": row["day"], "tsb": row["tsb"]}
                 for row in series if row["tsb"] < PMC_ZONE_HIGH_RISK]
    transition = [{"day": row["day"], "tsb": row["tsb"]}
                  for row in series if row["tsb"] > PMC_ZONE_TRANSITION]
    last = series[-1]
    return {
        "series": series,
        "alerts": alerts,
        "high_risk": high_risk,
        "transition": transition,
        "end": {"ctl_fitness": last["ctl"], "atl_fatigue": last["atl"],
                "tsb_form": last["tsb"]},
    }


def _day(item):
    return item.get("start_date_local") or item.get("start_time_local") \
        or item.get("day")


def _num(value):
    return float(value) if value is not None else None