"""Retorno a forma: reconstrucao do PMC real (historico do Intervals) e
estimativa segura de prazo para voltar a um CTL-alvo.

Fluxo (CLI `recovery`):
1. `fetch_full_history` puxa todo o historico de eventos (janelas paginadas,
   sem parar em hiatos).
2. `actual_daily_load` monta a serie diaria de carga de TSS **somente dos
   treinos feitos** (com atividade pareada) — planejado-nao-feito nao entra.
3. `pmc_series` reconstroi CTL/ATL/TSB (EWMA 42/7) por dia, zerando os dias
   sem carga (importante para o decaimento durante hiatos).
4. `state` resume onde o atleta esteve (pico de CTL, pico de TSB, melhor
   janela de 30 dias) e onde esta agora.
5. `estimate_return` projeta o prazo (semanas) para recuperar X% do CTL de
   pico sob uma rampa de volume semanal, com deload a cada 4 semanas.
6. `ramp_schedule` prescreve o volume semanal alvo (TSS) para o retorno.

A prescricao de rampa segue as mesmas regras de seguranca do plano: orcamento
semanal via teto (nunca ultrapassa a carga que sustenta o CTL-alvo) e deload
periodico em vez de progressao infinita.
"""
import math
from collections import defaultdict
from datetime import date, timedelta

TC_CTL = 42
TC_ATL = 7
MAX_WEEKS = 160
DELOAD_EVERY = 4
DELOAD_FACTOR = 0.6

TRAIN_DAYS_PER_WEEK = 5


def fetch_full_history(client, start_year=2011, chunk_days=180):
    """Todo o historico de eventos do atleta, paginado para tras.

    A API de `/events` aceita janelas `oldest`/`newest`; caminhamos em
    blocos de `chunk_days` ate `start_year`. NAO paramos em janela vazia
    (hiatos de treino), so quando chega ao limite. Dedupe por `id`/`uid`.
    """
    out = {}
    oldest = date.today() - timedelta(days=chunk_days)
    while oldest >= date(start_year, 1, 1):
        batch = client.events(oldest=oldest.isoformat(),
                              newest=(oldest + timedelta(days=chunk_days - 1)).isoformat())
        for e in batch:
            key = e.get("id") or e.get("uid")
            if key is not None:
                out[key] = e
        oldest = oldest - timedelta(days=chunk_days)
    return list(out.values())


def actual_daily_load(events):
    """{date: TSS somado} apenas dos treinos feitos (atividade pareada).

    Evento "feito" = tem `paired_activity_id` ou `activity_id` (treino
    planejado nao-feito nao tem pareamento e fica de fora). Carga vem de
    `icu_training_load` (fallback `tss`); ignora valores invalidos/<=0.
    """
    by = defaultdict(float)
    for e in events:
        if not (e.get("paired_activity_id") or e.get("activity_id")):
            continue
        day = str(e.get("start_date_local") or e.get("start_time_local") or "")[:10]
        raw = e.get("icu_training_load")
        if raw is None:
            raw = e.get("tss")
        try:
            load = float(raw)
        except (TypeError, ValueError):
            continue
        if day and load > 0:
            by[date.fromisoformat(day)] = by.get(date.fromisoformat(day), 0.0) + load
    return dict(by)


def pmc_series(daily, tc_ctl=TC_CTL, tc_atl=TC_ATL):
    """Series [(day, ctl, atl, tsb)] do primeiro dia com carga ate hoje.

    Dias sem carga (incluindo hiatos) entram com TSS 0 para o decaimento
    exponencial NAO comprimir o tempo. `daily` usa chaves `date`.
    """
    if not daily:
        return []
    kc = 1 - math.exp(-1 / tc_ctl)
    ka = 1 - math.exp(-1 / tc_atl)
    ctl = atl = 0.0
    rows = []
    d = min(daily)
    end = date.today()
    while d <= end:
        tss = daily.get(d, 0.0)
        ctl = ctl + (tss - ctl) * kc
        atl = atl + (tss - atl) * ka
        rows.append((d, ctl, atl, ctl - atl))
        d += timedelta(days=1)
    return rows


def pmc_series_anchored(real_by_day, start, end, tc_ctl=TC_CTL, tc_atl=TC_ATL):
    """Serie [(day, ctl, atl, tsb)] ancorada nos valores REAIS do Intervals.

    Dias com valor real (`real_by_day`: {date: (ctl, atl)} do Intervals) usam
    o CTL/ATL da propria API; os demais dias decaem EWMA com TSS 0 a partir do
    ultimo valor real (mesmo decaimento do Intervals entre treinos). Assim a
    serie parte do estado real mais antigo disponivel, sem cold-start de zero.

    Se nao houver nenhum valor real na janela, retorna [] e o chamador decide
    o fallback (ex.: `pmc_series` sobre `actual_daily_load`).
    """
    if not real_by_day:
        return []
    kc = 1 - math.exp(-1 / tc_ctl)
    ka = 1 - math.exp(-1 / tc_atl)
    first = min(real_by_day)
    ctl, atl = real_by_day[first]
    rows = []
    d = max(start, first)
    while d <= end:
        if d in real_by_day:
            ctl, atl = real_by_day[d]
        else:
            ctl *= 1 - kc
            atl *= 1 - ka
        rows.append((d, ctl, atl, ctl - atl))
        d += timedelta(days=1)
    return rows


def state(rows, window_days=30):
    """Resumo do historico reconstruido.

    Retorna dict com: estado atual (ctl/atl/tsb), pico de CTL (valor/data/tsb),
    melhor janela de `window_days` dias (CTL medio), pico de TSB
    (valor/data/ctl) e o periodo coberto.
    """
    if not rows:
        return None
    cur = rows[-1]
    peak_ctl = max(rows, key=lambda r: r[1])
    peak_tsb = max(rows, key=lambda r: r[3])

    best_window = None
    for i in range(len(rows) - window_days + 1):
        avg = sum(r[1] for r in rows[i:i + window_days]) / window_days
        if best_window is None or avg > best_window[0]:
            best_window = (avg, rows[i][0], rows[i + window_days - 1][0])

    return {
        "current_ctl": cur[1],
        "current_atl": cur[2],
        "current_tsb": cur[3],
        "peak_ctl": peak_ctl[1],
        "peak_ctl_day": peak_ctl[0],
        "peak_ctl_tsb": peak_ctl[3],
        "window_avg": best_window[0],
        "window_start": best_window[1],
        "window_end": best_window[2],
        "peak_tsb": peak_tsb[3],
        "peak_tsb_day": peak_tsb[0],
        "peak_tsb_ctl": peak_tsb[1],
        "first_day": rows[0][0],
        "last_day": cur[0],
    }


def weekly_volume(daily, days=28):
    """Volume semanal recente (TSS): soma dos ultimos `days` dias / semanas."""
    end = date.today()
    total = sum(daily.get(end - timedelta(days=i), 0.0) for i in range(days))
    return round(total / max(1, days / 7), 1)


def estimate_return(current_ctl, current_atl, target_ctl, weekly_now,
                    ramp_pts, tc_ctl=TC_CTL, tc_atl=TC_ATL,
                    max_weeks=MAX_WEEKS, deload_every=DELOAD_EVERY,
                    deload_factor=DELOAD_FACTOR):
    """Semanas para recuperar 90% e 99% do `target_ctl`.

    Simula uma rampa de volume semanal: parte de `weekly_now` TSS/semana e
    cresce `ramp_pts` por semana ate o teto que sustenta o CTL-alvo
    (`target_ctl * 7`), com deload a cada `deload_every` semanas (`deload_factor`).
    Retorna {"weeks_90": n|None, "weeks_99": n|None, "target_weekly": n}.
    None = nao atingiu no horizonte de `max_weeks` semanas.
    """
    kc = 1 - math.exp(-1 / tc_ctl)
    ka = 1 - math.exp(-1 / tc_atl)
    ctl, atl = current_ctl, current_atl
    target_weekly = target_ctl * 7
    weekly = max(weekly_now, 1.0)
    weeks_90 = weeks_99 = None
    for week in range(max_weeks + 1):
        base = weekly * deload_factor if (week and week % deload_every == 0) else weekly
        load = min(base, target_weekly)
        per = load / TRAIN_DAYS_PER_WEEK
        for i in range(7):
            tss = per if i < TRAIN_DAYS_PER_WEEK else 0.0
            ctl = ctl + (tss - ctl) * kc
            atl = atl + (tss - atl) * ka
            if weeks_90 is None and ctl >= 0.90 * target_ctl:
                weeks_90 = week
            if weeks_99 is None and ctl >= 0.99 * target_ctl:
                weeks_99 = week
                return {"weeks_90": weeks_90, "weeks_99": weeks_99,
                        "target_weekly": target_weekly}
        weekly = weekly + ramp_pts
    return {"weeks_90": weeks_90, "weeks_99": weeks_99,
            "target_weekly": target_weekly}


def ramp_schedule(target_ctl, weekly_now, ramp_pts, weeks=12,
                  deload_every=DELOAD_EVERY, deload_factor=DELOAD_FACTOR):
    """Prescricao segura: TSS semanal alvo para as proximas `weeks` semanas.

    Cresce de `weekly_now` em `ramp_pts`/semana ate o teto do CTL-alvo
    (`target_ctl * 7`) e aplica deload a cada `deload_every` semanas. Retorna
    lista de floats (uma por semana).
    """
    target_weekly = target_ctl * 7
    weekly = max(weekly_now, 1.0)
    out = []
    for week in range(1, weeks + 1):
        base = weekly * deload_factor if week % deload_every == 0 else weekly
        load = min(base, target_weekly)
        out.append(round(load, 1))
        weekly = min(weekly + ramp_pts, target_weekly)
    return out