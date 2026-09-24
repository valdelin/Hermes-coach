"""Resumo de treinos realizados por periodo (dia / semana / mes).

Usa apenas atividades PAREDAS (treinos feitos) no Intervals; o planejado-
nao-feito fica fora. O periodo e uma janela que termina no dia-ancla (por
padrao, ontem): dia = 1 dia, semana = 7 dias, mes = 30 dias.
"""

from datetime import date, timedelta

PERIODS = ("day", "week", "month")
PERIOD_LABELS = {"day": "dia", "week": "semana", "month": "mes"}


def period_range(anchor, period):
    """Janela (start, end) inclusive do periodo terminando em `anchor`."""
    if period == "day":
        return anchor, anchor
    if period == "week":
        return anchor - timedelta(days=6), anchor
    if period == "month":
        return anchor - timedelta(days=29), anchor
    raise ValueError(f"periodo invalido: {period!r}")


def done_activities(client, start, end):
    """Treinos FEITOS entre `start` e `end` (inclusive): lista de linhas
    resumidas. Evento conta apenas se tiver atividade pareada."""
    events = client.events(oldest=start.isoformat(), newest=end.isoformat())
    rows = []
    for e in events:
        aid = e.get("activity_id") or e.get("paired_activity_id")
        if not aid:
            continue
        a = client.activity(aid)
        if not isinstance(a, dict):
            continue
        day = (e.get("start_date_local") or "").split("T")[0] or str(start)
        rows.append({
            "name": (a.get("name") or e.get("name") or "Treino").strip(),
            "day": day,
            "type": a.get("type") or "",
            "time_s": int(a.get("moving_time") or a.get("elapsed_time") or 0),
            "distance_m": float(a.get("distance") or 0),
            "elevation_m": float(a.get("total_elevation_gain") or 0),
            "load": float(a.get("icu_training_load") or a.get("tss") or 0),
            "avg_power": a.get("icu_average_watts") or a.get("average_power"),
            "np": a.get("icu_weighted_avg_watts"),
            "avg_hr": a.get("average_heartrate"),
        })
    return rows


def summarize(rows):
    """Totais agregados da lista de treinos feitos."""
    n = len(rows)
    agg = {
        "sessions": n,
        "time_s": sum(r["time_s"] for r in rows),
        "distance_m": sum(r["distance_m"] for r in rows),
        "elevation_m": sum(r["elevation_m"] for r in rows),
        "load": sum(r["load"] for r in rows),
    }
    if n:
        agg["avg_power"] = _weighted_avg(rows, "avg_power")
        agg["np"] = _weighted_avg(rows, "np")
        agg["avg_hr"] = _weighted_avg(rows, "avg_hr")
    return agg


def fmt_time(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}"
    if m:
        return f"{m}m{str(s).rjust(2, '0')}"
    return f"{s}s"


def fmt_dist(meters):
    km = meters / 1000
    if km >= 1:
        return f"{km:.1f} km"
    return f"{meters:.0f} m"


def _weighted_avg(rows, key):
    total_w = 0.0
    acc = 0.0
    for r in rows:
        value = r.get(key)
        if value is None:
            continue
        w = r["time_s"] or 1
        acc += value * w
        total_w += w
    if not total_w:
        return None
    return acc / total_w