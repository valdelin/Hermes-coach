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
    return [tss for _, tss in sorted(by_day.items())]


def _day(item):
    return item.get("start_date_local") or item.get("start_time_local") \
        or item.get("day")


def _num(value):
    return float(value) if value is not None else None