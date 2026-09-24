"""Graficos em texto (stdlib-only) para o CLI.

Estilo inspirado no "Advanced Progress Tracking" e no PMC fitness/fatigue/form
de apps como Pillar/TrainingPeaks, mas renderizado no terminal: sparklines
unicode por serie (PMC CTL/ATL/TSB) e barras de carga semanal.
"""

from datetime import date, timedelta

BLOCKS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"  # 8 graus
BAR = "\u2588"  # bloco cheio


def sparkline(values, width=None, vmin=None, vmax=None):
    """Uma serie vira uma linha de blocos unicode na escala [vmin, vmax].

    Sem `vmin`/`vmax`, usa o proprio min/max da serie (formato do shape).
    Com escala global, varias series ficam comparaveis entre si.
    """
    if not values:
        return ""
    if width is not None:
        values = _resample(values, width)
    lo = min(values) if vmin is None else vmin
    hi = max(values) if vmax is None else vmax
    span = hi - lo
    if span <= 0:
        return BLOCKS[-1] * len(values)
    return "".join(BLOCKS[round((v - lo) / span * (len(BLOCKS) - 1))]
                   for v in values)


def _resample(values, width):
    if len(values) <= width:
        return values
    step = (len(values) - 1) / (width - 1)
    return [values[round(i * step)] for i in range(width)]


def _resample_rows(rows, width):
    if len(rows) <= width:
        return rows
    step = (len(rows) - 1) / (width - 1)
    return [rows[round(i * step)] for i in range(width)]


def pmc_chart(rows, width=64):
    """Linhas CTL/ATL/TSB do PMC compartilhando a MESMA escala (comparaveis).

    `rows`: lista de (day, ctl, atl, tsb) de recovery.pmc_series.
    """
    if not rows:
        return []
    rows = _resample_rows(rows, width)
    ctl = [r[1] for r in rows]
    atl = [r[2] for r in rows]
    tsb = [r[3] for r in rows]
    lo = min(min(ctl), min(atl), min(tsb))
    hi = max(max(ctl), max(atl), max(tsb))
    return [
        f"CTL {rows[-1][1]:6.1f}  {sparkline(ctl, vmin=lo, vmax=hi)}",
        f"ATL {rows[-1][2]:6.1f}  {sparkline(atl, vmin=lo, vmax=hi)}",
        f"TSB {rows[-1][3]:+6.1f}  {sparkline(tsb, vmin=lo, vmax=hi)}",
        f"escala {lo:.0f}..{hi:.0f} | {rows[0][0]} a {rows[-1][0]}",
    ]


def weekly_load(rows):
    """Agrega treinos feitos por semana ISO -> [(segunda, tss)].

    `rows`: linhas de activity_summary.done_activities (com `day` e `load`).
    Semana ISO comeca na segunda-feira.
    """
    weeks = {}
    for r in rows:
        d = r.get("_day") or date.fromisoformat(r.get("day", ""))
        iso = d.isocalendar()
        key = (iso.year, iso.week)
        weeks[key] = weeks.get(key, 0.0) + (r.get("load", 0.0) or 0.0)
    out = []
    for (year, week), tss in sorted(weeks.items()):
        out.append((date.fromisocalendar(year, week, 1), tss))
    return out


def load_chart(weeks, height=6):
    """Barras verticais de carga semanal (TSS) por semana."""
    if not weeks:
        return []
    values = [tss for _, tss in weeks]
    vmax = max(values) or 1.0
    heights = [round(v / vmax * height) for v in values]
    lines = []
    for level in range(height, 0, -1):
        lines.append("".join(BAR if h >= level else " " for h in heights))
    lines.append("".join(BAR if h else " " for h in heights))
    lines.append(" ".join(f"{v:.0f}" for v in values))
    lines.append(f"TSS/semana | {weeks[0][0]} a {weeks[-1][0]} | "
                 f"peak {vmax:.0f} | media {sum(values)/len(values):.0f}/sem")
    return lines