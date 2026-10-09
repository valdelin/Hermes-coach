"""Exporta o resumo do atleta para HTML (graficos em SVG inline) e PDF.

Sem dependencias: o HTML e gerado so com a stdlib; o PDF e produzido
renderizado esse mesmo HTML no chromium headless (`--print-to-pdf`), que ja
existe na maquina. Os graficos sao desenhos de verdade (curvas/areas/barras em
SVG) a partir dos MESMOS dados do terminal (`recovery.pmc_series` para o PMC e
`charts.weekly_load` para a carga semanal).

Toda cor vem dos design tokens em `brand.py` (22 temas inspirados no Omarchy).
O HTML embute um menu de tema (tecla T, igual no site do Omarchy) e guarda a
escolha no navegador via localStorage; o PDF usa o tema padrao (ou o passado
via parametro `theme`).
"""

import json
import math
import subprocess
import tempfile
from html import escape

try:
    from activity_summary import fmt_time, fmt_dist, period_label
    from brand import THEMES, DEFAULT_THEME
except ImportError:
    from .activity_summary import fmt_time, fmt_dist, period_label
    from .brand import THEMES, DEFAULT_THEME

DESC_PMC = ("<b>Leitura:</b> CTL, ATL e TSB mostram o contexto de carga e forma "
            "ao longo do período. Os rótulos de cor são heurísticas operacionais "
            "do Hermes, não diagnóstico fisiológico. <i>Referências de contexto: "
            "Science2Sport; Joe Friel.</i>")
DESC_LOAD = ("<b>Leitura:</b> cada barra mostra o TSS somado na semana ISO; "
             "a linha indica a média semanal do período.")

_HEADLESS_BIN = "chromium"

# Zonas da forma (TSB), como no Intervals.icu / Joe Friel:
TSB_RISK = -10      # <= -10: alto risco (recuperar)
TSB_FRESH = 10      # >= +10: fresco, pronto para competir


def _tsb_zone(v):
    """Zona do TSB: "risk" (<= -10), "ideal" (-10..+10) ou "fresh" (>= +10)."""
    if v <= TSB_RISK:
        return "risk"
    if v >= TSB_FRESH:
        return "fresh"
    return "ideal"


_ZONE_CLASS = {"risk": "sr", "ideal": "ss", "fresh": "sf"}
# Rotulos de copy (PROMPT 37 §26): neutros, descritivos do que o numero
# DIZ — sem prescricao medica ("descanse") nem promessa ("pronto para
# competir"). Os THRESHOLDS em `TSB_RISK`/`TSB_FRESH` nao mudam; o chip
# `Heuristica Hermes` identifica que se trata de heuristica operacional.
_ZONE_LABEL = {"risk": "carga recente acima da forma",
               "ideal": "carga e forma equilibradas",
               "fresh": "forma acima da carga recente"}

_MESES = ("jan", "fev", "mar", "abr", "mai", "jun",
          "jul", "ago", "set", "out", "nov", "dez")
_LABEL_ACCENTS = {"mes": "mês"}


def summary_heading(period):
    """Título canônico do resumo: `Resumo do dia`, `Resumo da semana`, ...

    O artigo acompanha o gênero do rótulo do período (`period_label`), e
    durações livres entram com "de" (`Resumo de 45 dias`).
    """
    label = period_label(period)
    label = _LABEL_ACCENTS.get(label, label)
    if label == "semana":
        return f"Resumo da {label}"
    if label == "personalizado":
        return f"Resumo {label}"
    if label[:1].isdigit():
        return f"Resumo de {label}"
    return f"Resumo do {label}"


def period_human(start, end):
    """Período legível do hero: `10 abr – 06 out 2026` (sem locale)."""
    def one(day):
        return f"{day.day:02d} {_MESES[day.month - 1]}"

    if start == end:
        return f"{one(start)} {start.year}"
    if start.year == end.year:
        return f"{one(start)} – {one(end)} {end.year}"
    return f"{one(start)} {start.year} – {one(end)} {end.year}"


def render_summary_html(*, title, start, end, agg, rows, pmc_rows, weeks,
                        planned_workout=None, readiness=None, plan_status=None,
                        vo2=None, ftp=None, theme=None):
    """Pagina HTML autossuficiente com o resumo e os graficos SVG.

    Ordem canonica e imutavel (PROMPT 37 §4):

        RESUMO -> HOJE -> EVOLUCAO -> PLANO -> DETALHES

    A lista abaixo E a fonte da ordem: nunca `set`, dict externo, ordem
    alfabetica ou ordem vinda do provider (§5). Alem disso, cada grupo tem
    `data-report-group` e cada bloco tem `data-report-section`, que sao os
    marcadores usados pelos testes de ordem.

    Regra de ausencia (§6/§72): uma secao so e omitida quando nao existe
    fallback semantico util — hoje apenas `adherence`, que precisa de um
    estado do plano. Todo o resto tem nota propria de estado vazio, para a
    estrutura do relatorio ficar estavel entre periodos (§67).
    """
    slug = theme if theme in THEMES else DEFAULT_THEME
    groups = (
        ("resumo", "RESUMO", (_summary_section(agg),)),
        ("hoje", "HOJE", (_readiness_section(readiness, plan_status),
                          _planned_section(planned_workout))),
        ("evolucao", "EVOLUÇÃO", (_pmc_section(pmc_rows),
                                  _load_section(weeks),
                                  _vo2_section(vo2),
                                  _ftp_section(ftp))),
        ("plano", "PLANO", (_adherence_section(plan_status),)),
        ("detalhes", "DETALHES", (_activities_section(rows),)),
    )
    body = f"""
<main>
  {_topbar()}

  {_hero(title, start, end)}

  {_render_groups(groups)}

  <footer>
    <span>Hermes Coach &mdash; plano adaptativo de ciclismo indoor.</span>
    <span>Gerado em {_e(str(_today()))}</span>
  </footer>
</main>
"""
    return _page(f"{title} · {period_human(start, end)}", body, slug)


def _render_groups(groups):
    out = []
    for slug, label, items in groups:
        present = [item for item in items if item]
        if not present:
            continue
        out.append(
            f'<section class="group" data-report-group="{slug}" '
            f'aria-labelledby="g-{slug}">'
            f'<h2 class="group-title" id="g-{slug}">{_e(label)}</h2>'
            f'{"".join(present)}</section>')
    return "\n  ".join(out)


def _summary_section(agg):
    return (f'<section class="stats" data-report-section="summary" '
            f'aria-label="Resumo do período">{_stats_cards(agg)}</section>')


def _pmc_section(pmc_rows):
    if pmc_rows:
        chart = _pmc_svg(pmc_rows)
        chips = _pmc_chips(pmc_rows)
        desc = f'<p class="chart-desc">{DESC_PMC}</p>'
    else:
        chart = _empty_note("Sem histórico de carga no período.")
        chips, desc = "", ""
    return f"""
  <section class="block" data-report-section="pmc" aria-labelledby="s-pmc">
    <div class="block-head">
      <h3 id="s-pmc">Evolução da carga</h3>
      <span class="pill">PMC · fitness / fadiga / forma</span>
    </div>
    {chips}
    {desc}
    {chart}
  </section>"""


def _load_section(weeks):
    if weeks:
        chart = _load_svg(weeks)
        desc = f'<p class="chart-desc">{DESC_LOAD}</p>'
    else:
        chart = _empty_note(
            "Sem treinos feitos no período (carga semanal indisponível).")
        desc = ""
    count = len(weeks)
    return f"""
  <section class="block" data-report-section="weekly-load" aria-labelledby="s-load">
    <div class="block-head">
      <h3 id="s-load">Carga semanal (TSS)</h3>
      <span class="pill">{count} {"semana" if count == 1 else "semanas"}</span>
    </div>
    {desc}
    {chart}
  </section>"""


def _vo2_section(vo2):
    """VO₂máx: hoje sem fonte real (auditoria §29), então `None` -> indisponível."""
    return _indicator_section(
        vo2, key="vo2", heading="VO₂máx", value_label="VO₂MÁX",
        unit="ml/kg/min", digits=1,
        unavailable="Ainda não há dado confiável para exibir este indicador.")


def _ftp_section(ftp):
    return _indicator_section(
        ftp, key="ftp", heading="FTP", value_label="FTP ATUAL",
        unit="W", digits=0,
        unavailable="Não há medição de FTP registrada para este atleta.")


def _indicator_section(data, *, key, heading, value_label, unit, digits,
                       unavailable):
    """Bloco canônico de indicador fisiológico — um único helper para VO₂ e FTP.

    Contrato do `data` (§32): `{value, source, date, series}`. `series` é uma
    lista de `(dia, valor)`; só vira gráfico com pontos reais (>= 2), ligados
    por retas — sem interpolação, suavização ou pontos inventados (§40).
    """
    data = data if isinstance(data, dict) else {}
    value = data.get("value")
    series = []
    for entry in (data.get("series") or ()):
        if not isinstance(entry, (list, tuple)) or len(entry) != 2:
            continue
        day, raw = entry
        if not day or raw is None:
            continue
        try:
            series.append((str(day)[:10], float(raw)))
        except (TypeError, ValueError):
            continue
    series.sort(key=lambda point: point[0])
    source = data.get("source")
    measured = data.get("date")

    trend = None
    chart = ""
    if value is None:
        value_text, origin, day_text = "Indisponível", None, None
        note = unavailable
    else:
        value_text = f"{float(value):.{digits}f} {unit}"
        origin, day_text = source, measured
        if len(series) >= 2:
            delta = series[-1][1] - series[0][1]
            trend = (f"{delta:+.{digits}f} {unit} desde {series[0][0]}"
                     f" até {series[-1][0]}")
            chart = _series_svg(series, unit=unit, label=heading)
            note = (f"Série de {len(series)} medições reais; sem interpolação "
                    "e sem pontos inventados.")
        else:
            note = "Histórico insuficiente para mostrar evolução."

    meta_items = [(value_label, value_text), ("ORIGEM", origin or "—"),
                  ("DATA", day_text or "—")]
    if trend:
        meta_items.append(("TENDÊNCIA", trend))
    meta = "".join(f"<div><b>{_e(text)}</b><span>{_e(label)}</span></div>"
                   for label, text in meta_items)
    return f"""
  <section class="block" data-report-section="{key}" aria-labelledby="s-{key}">
    <div class="block-head"><h3 id="s-{key}">{_e(heading)}</h3></div>
    <div class="plan-meta">{meta}</div>
    {chart}
    <p class="chart-footnote">{_e(note)}</p>
  </section>"""


def _series_svg(points, *, unit, label, width=760, height=190):
    """Série temporal real: retas entre medições, sem suavização."""
    ml, mr, mt, mb = 60, 16, 18, 34
    pw, ph = width - ml - mr, height - mt - mb
    values = [value for _, value in points]
    lo, hi = min(values), max(values)
    if hi - lo < 1:
        lo, hi = lo - 1, hi + 1

    def x(index):
        return ml + pw * index / max(len(points) - 1, 1)

    def y(value):
        return mt + ph * (hi - value) / (hi - lo)

    grid = []
    for step in range(4):
        level = lo + (hi - lo) * step / 3
        gy = mt + ph * step / 3
        grid.append(
            f'<line class="gl" x1="{ml}" y1="{gy:.1f}" x2="{width - mr}" '
            f'y2="{gy:.1f}" stroke-width="1" stroke-dasharray="3 4"/>')
        grid.append(
            f'<text class="tc" x="{ml - 8}" y="{gy + 3.5:.1f}" font-size="11" '
            f'text-anchor="end">{level:.0f}</text>')
    for index in sorted({0, len(points) - 1}):
        grid.append(
            f'<text class="tc" x="{x(index):.1f}" y="{height - 9}" '
            f'font-size="11" text-anchor="middle">{_e(points[index][0])}</text>')

    path = " ".join(
        ("M" if i == 0 else "L") + f" {x(i):.1f} {y(values[i]):.1f}"
        for i in range(len(points)))
    dots = "".join(
        f'<circle class="dk sc" cx="{x(i):.1f}" cy="{y(value):.1f}" r="4" '
        f'stroke-width="2.5"/>' for i, value in enumerate(values))
    desc = (f"{label}: {len(points)} medições entre {points[0][0]} e "
            f"{points[-1][0]}, em {unit}.")
    return (f'<svg viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{_e(desc)}"><desc>{_e(desc)}</desc>'
            f'{"".join(grid)}'
            f'<path class="sc" d="{path}" fill="none" stroke-width="2.5" '
            f'stroke-linecap="round" stroke-linejoin="round"/>{dots}</svg>')


def _activities_section(rows):
    ordered = sorted(rows, key=lambda r: (str(r.get("day") or ""),
                                          str(r.get("name") or "")),
                     reverse=True)
    if ordered:
        table_rows = "".join(_workout_row(r) for r in ordered)
        content = f"""<div class="table-wrap">
      <table>
        <thead><tr>
          <th>Dia</th><th>Treino</th><th>Tipo</th><th>Tempo</th>
          <th class="num">Distância</th><th class="num">Elevação</th>
          <th class="num">Carga</th>
        </tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>"""
    else:
        content = _empty_note("Nenhum treino foi realizado neste período.")
    return f"""
  <section class="block" data-report-section="activities" aria-labelledby="s-activities">
    <div class="block-head"><h3 id="s-activities">Treinos realizados</h3></div>
    {content}
  </section>"""



def write(path, html, chromium=_HEADLESS_BIN):
    """Escreve `html` no `path`; `.pdf` roda o chromium headless.

    Extensao decide: `.pdf` -> PDF via chromium; qualquer outra ->
    HTML direto. Retorna o caminho final.
    """
    if str(path).lower().endswith(".pdf"):
        return export_pdf(str(path), html, chromium=chromium)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    return str(path)


def export_pdf(path, html, chromium=_HEADLESS_BIN):
    """Gera um PDF imprimindo o HTML no chromium headless."""
    with tempfile.NamedTemporaryFile(
            "w", suffix=".html", encoding="utf-8", delete=False) as f:
        f.write(html)
        html_tmp = f.name
    cmd = [
        chromium, "--headless", "--disable-gpu", "--no-sandbox",
        "--no-pdf-header-footer",
        f"--print-to-pdf={path}",
        f"file://{html_tmp}",
    ]
    try:
        subprocess.run(cmd, check=True, timeout=120,
                       capture_output=True, text=True)
    finally:
        import os
        os.unlink(html_tmp)
    return path


def _topbar():
    opts = "".join(
        f'<button type="button" class="theme-opt" data-theme="{slug}">'
        f'<span class="sw">'
        f'<i style="background:{t["accent"]}"></i>'
        f'<i style="background:{t["ctl"]}"></i>'
        f'<i style="background:{t["atl"]}"></i>'
        f'<i style="background:{t["tsb"]}"></i></span>'
        f'<span class="opt-name">{_e(t["nome"])}</span>'
        f'<span class="opt-mode">{"claro" if t["claro"] else "escuro"}</span>'
        f'</button>'
        for slug, t in THEMES.items())
    return f"""
  <div class="topbar">
    <span class="brand">Hermes Coach</span>
    <div class="theme-wrap">
      <button type="button" class="theme-btn" id="themeBtn"
              aria-haspopup="true" aria-expanded="false" title="Escolher tema (tecla T)">
        <svg viewBox="0 0 24 24" width="15" height="15" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round"
             stroke-linejoin="round" aria-hidden="true">
          <circle cx="13.5" cy="6.5" r=".5" fill="currentColor"/>
          <circle cx="17.5" cy="10.5" r=".5" fill="currentColor"/>
          <circle cx="8.5" cy="7.5" r=".5" fill="currentColor"/>
          <circle cx="6.5" cy="12.5" r=".5" fill="currentColor"/>
          <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c.9 0 1.5-.7 1.5-1.5
                   0-.4-.2-.8-.4-1.1-.3-.4-.5-.8-.5-1.3 0-1.1.9-2 2-2h2
                   a5 5 0 0 0 5-5c0-4.4-4-6.6-8-6.6z"/>
        </svg>
        Temas
      </button>
      <div class="theme-menu" id="themeMenu" role="listbox" hidden>{opts}</div>
    </div>
  </div>
"""


def _theme_js():
    slugs = list(THEMES)
    return f"""
<script>
  (function () {{
    var SLUGS = {json.dumps(slugs)};
    var DEF = {json.dumps(DEFAULT_THEME)};
    var root = document.documentElement;
    var btn = document.getElementById("themeBtn");
    var menu = document.getElementById("themeMenu");
    var saved = null;
    try {{ saved = localStorage.getItem("hc-theme"); }} catch (e) {{}}
    var current = SLUGS.indexOf(saved) !== -1 ? saved : DEF;
    root.dataset.theme = current;

    function markActive() {{
      var opts = menu.querySelectorAll(".theme-opt");
      for (var i = 0; i < opts.length; i++) {{
        opts[i].classList.toggle("on",
          opts[i].getAttribute("data-theme") === root.dataset.theme);
      }}
    }}

    function apply(slug) {{
      root.dataset.theme = slug;
      try {{ localStorage.setItem("hc-theme", slug); }} catch (e) {{}}
      markActive();
    }}

    btn.addEventListener("click", function (ev) {{
      ev.stopPropagation();
      menu.hidden = !menu.hidden;
      btn.setAttribute("aria-expanded", String(!menu.hidden));
    }});

    menu.addEventListener("click", function (ev) {{
      var opt = ev.target.closest(".theme-opt");
      if (!opt) return;
      apply(opt.getAttribute("data-theme"));
      menu.hidden = true;
      btn.setAttribute("aria-expanded", "false");
    }});

    document.addEventListener("click", function (ev) {{
      if (!menu.hidden && !btn.contains(ev.target) && !menu.contains(ev.target)) {{
        menu.hidden = true;
        btn.setAttribute("aria-expanded", "false");
      }}
    }});

    document.addEventListener("keydown", function (ev) {{
      if (ev.key === "Escape") {{
        menu.hidden = true;
        btn.setAttribute("aria-expanded", "false");
        return;
      }}
      if ((ev.key !== "t" && ev.key !== "T")) return;
      var tag = ev.target && ev.target.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      var i = SLUGS.indexOf(root.dataset.theme);
      apply(SLUGS[(i + 1) % SLUGS.length]);
    }});

    markActive();
  }})();
</script>
"""


def _chart_js():
    """Tooltip tematico dos graficos (PMC + carga semanal).

    Usa os design tokens da pagina (--surface/--ctl/--atl/--tsb/...), entao o
    card segue o tema do relatorio e troca junto com ele (tecla T). Sem
    dependencias: so DOM/SVG puro.
    """
    return """
<script>
  (function () {
    function row(label, value, tok) {
      return '<div class="tt-row"><span class="tt-dot" style="background:var('
        + tok + ')"></span><span class="tt-muted">' + label + '</span>'
        + '<span class="v">' + value + '</span></div>';
    }
    function place(card, ev, host) {
      var r = host.getBoundingClientRect();
      var x = ev.clientX - r.left + 14;
      var y = ev.clientY - r.top - 14;
      if (x + card.offsetWidth > r.width - 6) {
        x = ev.clientX - r.left - card.offsetWidth - 14;
      }
      if (y + card.offsetHeight > r.height - 6) {
        y = ev.clientY - r.top - card.offsetHeight - 14;
      }
      card.style.left = Math.max(4, x) + "px";
      card.style.top = Math.max(4, y) + "px";
    }
    function fmtTsb(v) {
      return (v > 0 ? "+" : "") + v.toFixed(1);
    }
    function attachPmc(svg) {
      var host = svg.parentElement;
      var card = host.querySelector(".tt-card");
      var guide = svg.querySelector(".pmc-guide");
      var line = guide.querySelector("line");
      var dots = guide.querySelectorAll("circle");
      var d = JSON.parse(svg.getAttribute("data-pmc"));
      var n = d.days.length;
      var denom = Math.max(n - 1, 1);
      svg.addEventListener("mousemove", function (ev) {
        var r = svg.getBoundingClientRect();
        var vbX = (ev.clientX - r.left) / r.width * d.w;
        var i = Math.round((vbX - d.ml) / d.pw * denom);
        i = Math.max(0, Math.min(n - 1, i));
        var x = d.ml + d.pw * i / denom;
        var yOf = function (v) {
          return d.mt + d.ph * (d.hi - v) / (d.hi - d.lo);
        };
        var vals = [d.ctl[i], d.atl[i], d.tsb[i]];
        line.setAttribute("x1", x);
        line.setAttribute("x2", x);
        for (var k = 0; k < 3; k++) {
          dots[k].setAttribute("cx", x);
          dots[k].setAttribute("cy", yOf(vals[k]));
        }
        guide.setAttribute("visibility", "visible");
        card.innerHTML = '<div class="tt-date">' + d.days[i] + '</div>'
          + row("CTL", d.ctl[i].toFixed(1), "--ctl")
          + row("ATL", d.atl[i].toFixed(1), "--atl")
          + row("TSB", fmtTsb(d.tsb[i]), "--tsb");
        card.classList.add("on");
        place(card, ev, host);
      });
      svg.addEventListener("mouseleave", function () {
        guide.setAttribute("visibility", "hidden");
        card.classList.remove("on");
      });
    }
    function attachLoad(svg) {
      var host = svg.parentElement;
      var card = host.querySelector(".tt-card");
      var d = JSON.parse(svg.getAttribute("data-load"));
      var n = d.days.length;
      var ml = d.ml;
      var slot = d.pw / Math.max(n, 1);
      svg.addEventListener("mousemove", function (ev) {
        var r = svg.getBoundingClientRect();
        var vbX = (ev.clientX - r.left) / r.width * d.w;
        var i = Math.floor((vbX - ml) / slot);
        i = Math.max(0, Math.min(n - 1, i));
        card.innerHTML = '<div class="tt-date">' + d.days[i] + '</div>'
          + row("Carga", d.tss[i].toFixed(0) + " TSS", "--accent");
        card.classList.add("on");
        place(card, ev, host);
      });
      svg.addEventListener("mouseleave", function () {
        card.classList.remove("on");
      });
    }
    function init() {
      var p = document.querySelectorAll("svg[data-pmc]");
      for (var i = 0; i < p.length; i++) attachPmc(p[i]);
      var l = document.querySelectorAll("svg[data-load]");
      for (var j = 0; j < l.length; j++) attachLoad(l[j]);
    }
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init);
    } else {
      init();
    }
  })();
</script>
"""


def _page(title, body, slug):
    return f"""<!doctype html>
<html lang="pt-BR" data-theme="{slug}"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(title)}</title>
<style>
  :root {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto,
              sans-serif; line-height: 1.5; }}

  {_theme_css()}

  * {{ box-sizing: border-box; }}
  html {{ background: var(--bg3); }}
  body {{ margin: 0; padding: 26px 16px; color: var(--text); background:
           linear-gradient(180deg, var(--bg) 0%, var(--bg2) 320px,
           var(--bg3) 100%); color-adjust: exact;
           -webkit-print-color-adjust: exact; }}
  main {{ max-width: 880px; margin: 0 auto; }}

  .topbar {{ display: flex; align-items: center; justify-content:
             space-between; margin-bottom: 14px; }}
  .brand {{ font-size: .8rem; font-weight: 700; letter-spacing: .14em;
            text-transform: uppercase; color: var(--muted); }}
  .theme-wrap {{ position: relative; }}
  .theme-btn {{ display: inline-flex; align-items: center; gap: 7px;
                background: var(--surface); color: var(--text);
                border: 1px solid var(--border); border-radius: 999px;
                padding: 7px 14px; font-size: .82rem; font-weight: 600;
                cursor: pointer; box-shadow: 0 1px 2px var(--shadow);
                transition: background .12s, transform .05s; }}
  .theme-btn:hover {{ background: var(--hover); }}
  .theme-btn:active {{ transform: translateY(1px); }}
  .theme-menu {{ position: absolute; right: 0; top: calc(100% + 6px);
                 z-index: 50; background: var(--surface); border: 1px solid
                 var(--border); border-radius: 14px; padding: 6px;
                 box-shadow: 0 16px 40px -12px var(--shadow);
                 display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
                 min-width: 340px; }}
  .theme-menu[hidden] {{ display: none; }}
  .theme-opt {{ display: grid; grid-template-columns: 42px 1fr auto;
                align-items: center; gap: 8px; background: transparent;
                border: 1px solid transparent; border-radius: 9px; color:
                var(--text); font-size: .8rem; text-align: left; padding:
                7px 8px; cursor: pointer; }}
  .theme-opt:hover {{ background: var(--hover); }}
  .theme-opt.on {{ border-color: var(--accent); }}
  .sw {{ display: inline-flex; gap: 3px; }}
  .sw i {{ width: 9px; height: 9px; border-radius: 50%; border: 1px solid
            rgba(255, 255, 255, .35); }}
  .opt-name {{ font-weight: 650; }}
  .opt-mode {{ font-size: .68rem; color: var(--muted); text-transform:
               uppercase; letter-spacing: .05em; }}

  .hero {{ position: relative; overflow: hidden; color: #fff; padding:
           26px 28px; border-radius: 20px; box-shadow: 0 10px 30px -12px
           var(--shadow); background: linear-gradient(135deg, var(--accent)
           0%, var(--accent-2) 60%, var(--accent-3) 100%); }}
  .hero::before {{ content: ""; position: absolute; inset: 0; z-index: 0;
                   pointer-events: none; border-radius: inherit; background:
                   linear-gradient(180deg, rgba(10, 10, 20, .34) 0%,
                   rgba(10, 10, 20, 0) 70%); }}
  .hero > * {{ position: relative; z-index: 1; }}
  .hero .kicker {{ font-size: .72rem; letter-spacing: .16em; font-weight: 700;
                   text-transform: uppercase; opacity: .85; }}
  .hero h1 {{ margin: 4px 0 6px; font-size: 1.5rem; font-weight: 700; }}
  .hero .meta {{ margin: 0; font-size: .85rem; opacity: .9; }}

  .group {{ margin-top: 26px; }}
  .hero + .group {{ margin-top: 16px; }}
  .group-title {{ margin: 0 0 10px; font-size: .7rem; font-weight: 700;
                  letter-spacing: .16em; text-transform: uppercase;
                  color: var(--muted); page-break-after: avoid; }}
  .group-title + .block, .group-title + .stats {{ margin-top: 4px; }}

  .stats {{ display: grid; grid-template-columns: repeat(auto-fit,
            minmax(132px, 1fr)); gap: 10px; margin: 16px 0 4px; }}
  .card {{ background: var(--surface); border: 1px solid var(--border);
           border-radius: 14px; padding: 12px 14px; box-shadow: 0 1px 2px
           var(--shadow); }}
  .card b {{ display: block; font-size: 1.15rem; font-weight: 700;
             font-variant-numeric: tabular-nums; }}
  .card span {{ font-size: .72rem; color: var(--muted); text-transform:
                uppercase; letter-spacing: .05em; }}

  .block {{ background: var(--surface); border: 1px solid var(--border);
            border-radius: 16px; padding: 18px 20px 10px; margin-top: 16px;
            box-shadow: 0 1px 3px var(--shadow); page-break-inside: avoid; }}
  .block-head {{ display: flex; align-items: baseline; gap: 10px; }}
  h2 {{ margin: 0; font-size: 1.05rem; font-weight: 700; }}
  h3 {{ margin: 0; font-size: 1rem; font-weight: 700; }}
  .pill {{ background: var(--subtle); color: var(--subtle-text);
           border-radius: 999px; font-size: .72rem; padding: 2px 10px;
           font-weight: 600; }}
   .chart-desc {{ margin: 4px 0 10px; font-size: .82rem; color: var(--muted); }}
   .chart-desc b {{ color: var(--text); }}

   .readiness-copy {{ margin: 6px 0 12px; color: var(--muted); font-size: .84rem; }}
   .plan-meta {{ display: grid; grid-template-columns: repeat(auto-fit,
                minmax(112px, 1fr)); gap: 8px; margin: 10px 0 12px; }}
   .plan-meta div {{ background: var(--subtle); border: 1px solid var(--border);
                    border-radius: 10px; padding: 8px 10px; }}
   .plan-meta b {{ display: block; font-size: .86rem; font-variant-numeric: tabular-nums; }}
   .plan-meta span {{ display: block; color: var(--muted); font-size: .69rem;
                     text-transform: uppercase; letter-spacing: .05em; }}
   .profile-caption {{ margin: 4px 0 10px; color: var(--muted); font-size: .8rem; }}
   .profile-legend {{ display: flex; flex-wrap: wrap; gap: 9px; margin: 8px 0 2px;
                      color: var(--muted); font-size: .76rem; }}
   .profile-legend span {{ display: inline-flex; align-items: center; gap: 4px; }}
   .profile-legend i {{ width: 10px; height: 10px; border-radius: 3px; }}
   .profile-legend .warmup {{ background: var(--accent); }}
   .profile-legend .work {{ background: var(--ctl); }}
    .profile-legend .recovery {{ background: var(--accent-3); }}
    .profile-legend .cooldown {{ background: var(--atl); }}
    .adherence-panel {{ padding-bottom: 18px; }}
    .adherence-panel .block-head {{ justify-content: space-between; flex-wrap: wrap; }}
    .eyebrow {{ font-size: .65rem; letter-spacing: .13em; color: var(--subtle-text); font-weight: 700; }}
    .session-title {{ font-size: 1.4rem; margin: 5px 0; }}
    .panel-copy {{ font-size: .82rem; color: var(--subtle-text); margin: 6px 0 16px; }}
    .session-metrics {{ display: flex; gap: 28px; margin: 20px 0; }}
    .session-metrics b {{ display: block; font-size: 1.5rem; font-variant-numeric: tabular-nums; }}
    .session-metrics small, .session-metrics span {{ font-size: .7rem; color: var(--subtle-text); }}
    .workout-figure {{ margin: 0; background: var(--bg2); border: 1px solid var(--border); border-radius: 12px; padding: 14px; }}
    .workout-figure figcaption {{ display: flex; justify-content: space-between; gap: 10px; flex-wrap: wrap; font-size: .75rem; margin-bottom: 12px; }}
    .workout-figure figcaption span, .chart-footnote {{ color: var(--subtle-text); font-size: .71rem; line-height: 1.6; }}
    .readiness-summary {{ padding: 18px; border: 1px solid var(--border); border-radius: 12px; background: var(--bg2); }}
    .status-line {{ display: flex; align-items: center; gap: 7px; font-size: .75rem; }}
    .status-line > span:last-child {{ margin-left: auto; color: var(--subtle-text); }}
    .status-dot {{ width: 8px; height: 8px; border-radius: 50%; background: var(--accent); }}
    .status-line.green strong {{ color: var(--tsb); }} .status-line.green .status-dot {{ background: var(--tsb); }}
    .status-line.yellow strong {{ color: var(--atl); }} .status-line.yellow .status-dot {{ background: var(--atl); }}
    .status-line.red strong {{ color: var(--risk); }} .status-line.red .status-dot {{ background: var(--risk); }}
    .readiness-score {{ font-size: 2.5rem; font-weight: 750; line-height: 1.2; margin-top: 18px; font-variant-numeric: tabular-nums; }}
    .readiness-score span {{ font-size: .8rem; color: var(--subtle-text); font-weight: 400; }}
    .coverage-label {{ display: flex; justify-content: space-between; font-size: .72rem; margin-top: 20px; gap: 8px; }}
    .coverage-track {{ height: 5px; border-radius: 4px; background: var(--grid); margin-top: 8px; overflow: hidden; }}
    .coverage-track span {{ display: block; height: 100%; background: var(--accent); }}
    .readiness-list {{ margin: 20px 0; }}
    .readiness-list div {{ display: flex; justify-content: space-between; gap: 10px; padding: 6px 0; border-bottom: 1px solid var(--border); font-size: .78rem; }}
    .readiness-list dt {{ color: var(--subtle-text); }} .readiness-list dd {{ margin: 0; font-weight: 700; }}
    .decision-note {{ border-left: 3px solid var(--accent); padding: 0 0 0 10px; font-size: .75rem; }}
    .decision-note strong, .decision-note span {{ display: block; }} .decision-note span {{ color: var(--subtle-text); margin-top: 4px; }}
    .data-details {{ border-top: 1px solid var(--border); margin-top: 20px; padding-top: 12px; font-size: .73rem; color: var(--subtle-text); }}
    .data-details summary {{ cursor: pointer; min-height: 28px; }} .data-details p {{ margin-bottom: 0; }}
    .adherence-layout {{ display: grid; grid-template-columns: 160px minmax(0, 1fr); gap: 30px; margin-top: 24px; align-items: center; }}
    .adherence-overview {{ text-align: center; }} .adherence-overview p {{ font-size: .8rem; margin: 14px 0 3px; }}
    .adherence-ring {{ width: 128px; height: 128px; margin: auto; border-radius: 50%; padding: 10px; }}
    .adherence-ring > div {{ width: 100%; height: 100%; border-radius: 50%; background: var(--surface); display: flex; flex-direction: column; justify-content: center; align-items: center; }}
    .adherence-ring b {{ font-size: 2rem; line-height: 1.25; }} .adherence-ring b span {{ font-size: .9rem; }}
    .adherence-ring small {{ font-size: .57rem; letter-spacing: .1em; color: var(--subtle-text); }}
    .consistency-legend {{ display: flex; flex-wrap: wrap; gap: 16px; font-size: .7rem; margin-bottom: 20px; }}
    .consistency-legend > span {{ display: flex; align-items: center; gap: 6px; }} .consistency-legend i {{ width: 8px; height: 8px; border-radius: 2px; }}
    .done {{ background: var(--accent-3); color: var(--bg3); }} .missed {{ background: var(--risk); color: var(--bg3); }}
    .pending {{ background: repeating-linear-gradient(135deg, var(--grid), var(--grid) 5px, var(--surface) 5px, var(--surface) 7px); color: var(--text); }}
    .week-row {{ display: grid; grid-template-columns: 110px minmax(0, 1fr) 55px; align-items: center; gap: 12px; margin: 16px 0; }}
    .week-label strong, .week-label span {{ display: block; }} .week-label strong {{ font-size: .78rem; }} .week-label span, .week-rate small {{ font-size: .65rem; color: var(--subtle-text); margin-top: 2px; }}
    .week-bar {{ display: flex; gap: 3px; height: 28px; overflow: hidden; border-radius: 5px; }} .week-bar span {{ display: flex; align-items: center; justify-content: center; font-size: .75rem; font-weight: 750; min-width: 0; }}
    .week-rate {{ text-align: right; }} .week-rate b, .week-rate small {{ display: block; }} .week-rate b {{ font-size: .87rem; }}

  .chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
  .chip {{ display: inline-flex; align-items: center; gap: 5px;
           background: var(--subtle); border: 1px solid var(--border);
           border-radius: 999px; font-size: .76rem; font-weight: 700;
           padding: 2px 10px; font-variant-numeric: tabular-nums; }}
  .chip .dot {{ width: 8px; height: 8px; border-radius: 50%; }}

  svg {{ display: block; width: 100%; height: auto; }}
  .gl {{ stroke: var(--grid); }}
  .tc {{ fill: var(--muted); }}
  .tb {{ fill: var(--text); }}
  .ml {{ stroke: var(--atl); }}
  .tl {{ fill: var(--atl); }}
  .sc {{ stroke: var(--ctl); }}
  .sa {{ stroke: var(--atl); }}
  .ss {{ stroke: var(--tsb); }}
  .sf {{ stroke: var(--fresh); }}
  .sr {{ stroke: var(--risk); }}
  .dk {{ fill: var(--surface); }}
  .gp-ctl-a {{ stop-color: var(--ctl); stop-opacity: .28; }}
  .gp-ctl-b {{ stop-color: var(--ctl); stop-opacity: 0; }}
  .gp-atl-a {{ stop-color: var(--atl); stop-opacity: .20; }}
  .gp-atl-b {{ stop-color: var(--atl); stop-opacity: 0; }}
   .gp-bara {{ stop-color: var(--accent); }}
   .gp-barb {{ stop-color: var(--accent-2); }}
   .profile-fill.warmup {{ fill: var(--accent); fill-opacity: .24; }}
   .profile-line.warmup {{ stroke: var(--accent); }}
   .profile-fill.work {{ fill: var(--ctl); fill-opacity: .25; }}
   .profile-line.work {{ stroke: var(--ctl); }}
   .profile-fill.recovery {{ fill: var(--accent-3); fill-opacity: .24; }}
   .profile-line.recovery {{ stroke: var(--accent-3); }}
   .profile-fill.cooldown {{ fill: var(--atl); fill-opacity: .23; }}
   .profile-line.cooldown {{ stroke: var(--atl); }}
   .profile-line {{ fill: none; stroke-width: 3; stroke-linecap: round;
                    stroke-linejoin: round; }}
   .profile-boundary {{ stroke: var(--grid); stroke-width: 1; stroke-dasharray: 2 3; }}

  .pmc-chart, .load-chart {{ position: relative; }}
  .pmc-hit, .load-hit {{ cursor: crosshair; }}
  .pmc-guide line {{ stroke: var(--grid); stroke-width: 1; }}
  .pmc-dot {{ fill: var(--surface); stroke: var(--surface); stroke-width: 2; }}
  .pmc-dot.sc {{ fill: var(--ctl); }}
  .pmc-dot.sa {{ fill: var(--atl); }}
  .pmc-dot.ss {{ fill: var(--tsb); }}
  .tt-card {{ position: absolute; z-index: 20; pointer-events: none;
              opacity: 0; min-width: 132px; background: var(--surface);
              color: var(--text); border: 1px solid var(--border);
              border-radius: 10px; padding: 7px 11px; font-size: .78rem;
              line-height: 1.5; box-shadow: 0 10px 28px -10px var(--shadow);
              transition: opacity .08s; }}
  .tt-card.on {{ opacity: 1; }}
  .tt-date {{ font-weight: 700; margin-bottom: 3px; font-size: .8rem; }}
  .tt-row {{ display: flex; align-items: center; gap: 6px;
             font-variant-numeric: tabular-nums; }}
  .tt-dot {{ width: 8px; height: 8px; border-radius: 50%; flex: none; }}
  .tt-row .v {{ margin-left: auto; padding-left: 14px; font-weight: 700; }}
  .tt-muted {{ color: var(--muted); }}

  .table-wrap {{ overflow-x: auto; }}
  table {{ border-collapse: collapse; width: 100%; font-size: .86rem; }}
  th, td {{ padding: 8px 10px; text-align: left; white-space: nowrap;
            border-bottom: 1px solid var(--grid); }}
  th {{ color: var(--muted); font-weight: 600; font-size: .74rem;
        text-transform: uppercase; letter-spacing: .05em; }}
  td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tbody tr {{ transition: background .12s; }}
  tbody tr:hover {{ background: var(--hover); }}
  .note {{ color: var(--muted); font-size: .85rem; padding: 10px 0 6px; }}
  footer {{ display: flex; justify-content: space-between; color: var(--muted);
            font-size: .75rem; padding: 16px 4px 0; }}

   @media print {{
    body {{ padding: 0; }}
    .topbar {{ display: none; }}
    .block {{ box-shadow: none; }}
     footer {{ page-break-inside: avoid; }}
     .data-details {{ display: none; }}
   }}
   @media(max-width:650px) {{ .adherence-layout {{ grid-template-columns: 1fr; gap: 20px; }} .adherence-overview {{ display: flex; flex-direction: column; align-items: center; }} .session-metrics {{ gap: 24px; }} .block {{ padding-left: 14px; padding-right: 14px; }} .session-title {{ font-size: 1.25rem; }} .theme-menu {{ min-width: 0; max-width: calc(100vw - 32px); grid-template-columns: 1fr; }} }}
</style>
</head><body>{body}{_theme_js()}{_chart_js()}</body></html>
"""


def _theme_css():
    keeps = {"nome", "claro", "shadow_px"}

    def _block(selector, theme):
        vars_ = "".join(
            f"    --{k}: {v};\n" for k, v in theme.items() if k not in keeps)
        return f"{selector} {{\n{vars_}}}"

    # o padrao como `:root` PRIMEIRO: mesmo elemento do `[data-theme=...]`
    # e mesma especificidade, entao cada bloco de tema (que vem depois) sempre
    # vence o fallback. Se o padrao fosse emitido depois, sobrescreveria todos
    # os temas listados antes dele no CSS.
    blocks = [_block(":root", THEMES[DEFAULT_THEME])]
    blocks += [_block(f'[data-theme="{slug}"]', t)
               for slug, t in THEMES.items()]
    return "\n".join(blocks)


def _hero(title, start, end):
    """Hero só com identidade do relatório (§7): kicker, título e período.

    Os KPIs vivem apenas no RESUMO (§9) — nada de `hero-chip`.
    """
    return f"""
  <header class="hero">
    <div class="kicker">Relatório do atleta</div>
    <h1>{_e(title)}</h1>
    <p class="meta">{_e(period_human(start, end))}</p>
  </header>
"""


def _stats_cards(agg):
    """KPIs do RESUMO, na ordem fixa do §8: treinos, tempo, carga, distância,
    potência, FC média e elevação. Ausência vira `—`, nunca zero (§10)."""
    def card(value, label):
        return f'<div class="card"><b>{_e(value)}</b><span>{_e(label)}</span></div>'

    power = _fmt_power(agg) or "—"
    hr = f"{agg['avg_hr']:.0f} bpm" if agg.get("avg_hr") is not None else "—"
    elev = f"+{agg['elevation_m']:.0f} m" if agg.get("elevation_m") else "—"
    sessions = agg.get("sessions") or 0
    return "".join([
        card(str(sessions), "treino" if sessions == 1 else "treinos"),
        card(fmt_time(agg["time_s"]), "tempo"),
        card(f"{agg['load']:.0f} TSS", "carga"),
        card(fmt_dist(agg["distance_m"]), "distância"),
        card(power, "potência (média / NP)"),
        card(hr, "FC média"),
        card(elev, "elevação"),
    ])


def _fmt_power(agg):
    parts = []
    if agg.get("avg_power") is not None:
        parts.append(f"{agg['avg_power']:.0f} W")
    if agg.get("np") is not None:
        parts.append(f"NP {agg['np']:.0f} W")
    return " / ".join(parts)


def _workout_row(r):
    # `_num` já devolve a célula completa; embrulhar de novo gerava
    # `<td><td class="num">…</td></td>` (HTML inválido, PROMPT 37 §49).
    cells = [
        f"<td>{_e(r['day'])}</td>",
        f"<td>{_e(r['name'])}</td>",
        f"<td>{_e(r['type'] or '—')}</td>",
        f"<td>{fmt_time(r['time_s'])}</td>",
        _num(fmt_dist(r["distance_m"]) if r["distance_m"] else "—"),
        _num(f"+{r['elevation_m']:.0f} m" if r["elevation_m"] else "—"),
        _num(f"{r['load']:.0f} TSS" if r["load"] else "—"),
    ]
    return "<tr>" + "".join(cells) + "</tr>"


def _num(text):
    return f'<td class="num">{text}</td>'


def _pmc_chips(pmc_rows):
    if not pmc_rows:
        return ""
    last = pmc_rows[-1]
    lo = _scale_lo(pmc_rows)
    hi = _scale_hi(pmc_rows)
    zone = _tsb_zone(last[3])
    estado = (
        f'<span class="chip"><span class="dot" '
        f'style="background:var(--{_zone_var(zone)})"></span>'
        f'Estado: {_ZONE_LABEL[zone]}</span>')
    return f"""
    <div class="chips">
      <span class="chip"><span class="dot" style="background:var(--ctl)"></span>CTL {last[1]:.1f}</span>
      <span class="chip"><span class="dot" style="background:var(--atl)"></span>ATL {last[2]:.1f}</span>
      <span class="chip"><span class="dot" style="background:var(--tsb)"></span>TSB {last[3]:+.1f}</span>
      {estado}
      <span class="chip">Heurística Hermes</span>
      <span class="chip">escala {lo:.0f}..{hi:.0f}</span>
      <span class="chip">{pmc_rows[0][0]} a {pmc_rows[-1][0]}</span>
    </div>"""


def _zone_var(zone):
    return {"risk": "risk", "ideal": "tsb", "fresh": "fresh"}[zone]


def _scale_lo(pmc_rows):
    return min(min(r[1], r[2], r[3]) for r in pmc_rows)


def _scale_hi(pmc_rows):
    return max(max(r[1], r[2], r[3]) for r in pmc_rows)


def _empty_note(text):
    return f'<p class="note">{_e(text)}</p>'


def _readiness_section(readiness, plan_status):
    """HOJE/1 — prontidão do dia, separada do treino (PROMPT 37 §11).

    Preserva o contrato do Prompt 39: entrada `None` vira "Sem dados
    suficientes" — nunca score verde por ausência.
    """
    day = None
    if isinstance(readiness, dict):
        day = readiness.get("target_day") or readiness.get("reference_day")
    return f"""
  <section class="block" data-report-section="readiness" aria-labelledby="s-readiness">
    <div class="block-head">
      <h3 id="s-readiness">Prontidão de hoje</h3>
      <span class="pill">{_e(day or "hoje")}</span>
    </div>
    {_readiness_summary(readiness, plan_status)}
  </section>"""


def _planned_section(profile):
    """HOJE/2 — sessão planejada, separada da prontidão (PROMPT 37 §11).

    A estrutura vem sempre de `planned_workout_profile(...)`; sem blocos
    suficientes o próprio fallback explica a ausência (§24).
    """
    day = profile.get("date") if isinstance(profile, dict) else None
    return f"""
  <section class="block" data-report-section="planned-workout" aria-labelledby="s-planned">
    <div class="block-head">
      <h3 id="s-planned">Treino do dia</h3>
      <span class="pill">{_e(day or "hoje")}</span>
    </div>
    {_planned_workout_html(profile)}
  </section>"""


def _readiness_summary(readiness, plan_status):
    readiness = readiness if isinstance(readiness, dict) else {}
    axes = readiness.get("axis_states") or ()
    model_count = int(readiness.get("model_axis_count") or len(axes))
    implemented_count = int(readiness.get("implemented_axis_count") or 0)
    available_count = int(readiness.get("available_axis_count") or 0)
    score = readiness.get("heuristic_score")
    level = str(readiness.get("heuristic_level") or "").lower()
    if implemented_count == 0:
        data_state = "Sem dados suficientes"
    elif available_count == 0:
        data_state = "Sem dados suficientes"
    elif available_count == implemented_count:
        data_state = "Leitura completa"
    else:
        data_state = "Leitura parcial"
    level_copy = {
        "green": "Verde · sem alerta nos eixos avaliados",
        "yellow": "Atenção · pelo menos um sinal merece atenção",
        "red": "Alerta · múltiplos sinais indicam atenção",
    }.get(level, "Sem classificação")
    score_text = (f"{float(score):.2f}".replace(".", ",")
                  if score is not None else "—")
    coverage = (available_count / implemented_count * 100
                if implemented_count else 0)
    axis_rows = "".join(
        '<div><dt>{}</dt><dd>{}</dd></div>'.format(
            _e(str(axis.get("label") or axis.get("axis") or "Sinal")),
            "avaliado" if axis.get("available") else
            ("sem dados hoje" if axis.get("implemented")
             else "sem avaliação implementada"),
        )
        for axis in axes
    )
    if not axis_rows:
        axis_rows = '<div><dt>Sinais de prontidão</dt><dd>sem dados hoje</dd></div>'
    alerts = []
    if readiness.get("illness_alert"):
        alerts.append("Há um alerta separado de possível doença.")
    if readiness.get("composite_low"):
        alerts.append("O indicador composto do provider está baixo.")
    alert_html = "".join(f'<p class="chart-footnote">{_e(text)}</p>'
                         for text in alerts)
    return f"""
      <aside aria-label="Indicadores de prontidão" class="readiness-summary">
        <div class="status-line { _e(level) }"><span class="status-dot"></span>
          <strong>{_e(data_state)}</strong><span>Prontidão</span></div>
        <div class="readiness-score">{score_text} <span>/ 1,00</span></div>
        <p class="panel-copy">{_e(level_copy)}</p>
        <div class="coverage-label"><span>Dados disponíveis hoje</span>
          <b>{available_count} de {implemented_count} eixos avaliáveis</b></div>
        <div aria-label="Cobertura de dados dos eixos avaliáveis" aria-valuemin="0"
          aria-valuemax="100" aria-valuenow="{coverage:.0f}" class="coverage-track"
          role="meter"><span style="width:{coverage:.2f}%"></span></div>
        <p class="chart-footnote">Cobertura do modelo: {implemented_count} de
          {model_count} eixos possuem avaliação implementada.</p>
        <dl class="readiness-list">{axis_rows}</dl>
        {_plan_status_copy(plan_status)}
        {alert_html}
        <details class="data-details"><summary>Como esta leitura é calculada</summary>
          <p>A pontuação é uma média simples dos sinais avaliados. Sinais sem dados ficam fora da média. As regras atuais são heurísticas operacionais
          do Hermes e não uma escala fisiológica calibrada.</p></details>
      </aside>"""


def _plan_status_copy(plan_status):
    status = plan_status if isinstance(plan_status, dict) else {}
    today = status.get("today") if isinstance(status.get("today"), dict) else {}
    lifecycle = today.get("lifecycle_effective")
    if lifecycle == "planned":
        lines = ("Nenhuma alteração foi feita no plano de treinos.",
                 "A sessão de hoje continua como planejada.")
    elif lifecycle:
        lines = (f"A sessão de hoje está marcada como {_e(str(lifecycle))}.",)
    else:
        lines = ("Não há estado registrado para a sessão de hoje.",)
    return '<div class="decision-note"><strong>Estado do plano</strong>{}</div>'.format(
        "".join(f"<span>{line}</span>" for line in lines))


def _planned_workout_html(profile):
    if not isinstance(profile, dict):
        return ('<div><div class="eyebrow">SESSÃO PLANEJADA</div>'
                '<h3 class="session-title">Nenhuma sessão planejada</h3>'
                '<p class="panel-copy">Não há treino planejado para hoje.</p></div>')
    title = _e(profile.get("title") or "Treino planejado")
    intensity = profile.get("intensity_factor")
    intensity_text = (f"{float(intensity) * 100:.0f}%"
                      if intensity is not None else "—")
    metrics = "".join(
        f'<div><b>{value}</b><span>{_e(label)}</span></div>'
        for label, value in (
            ("Duração", _fmt_profile_duration(profile.get("duration_seconds"))),
            ("Carga planejada", _fmt_profile_tss(profile.get("planned_tss"))),
            ("Intensidade", intensity_text),
        )
    )
    if not profile.get("has_structured_blocks"):
        chart = _empty_note("Perfil detalhado indisponível para esta sessão.")
    else:
        chart = f"""
        <figure class="workout-figure">
          <figcaption><strong>Perfil do treino</strong><span>potência-alvo planejada</span></figcaption>
          {_planned_profile_svg(profile)}
          {_profile_legend()}
          <p class="chart-footnote">O gráfico representa a prescrição do plano,
          não a execução observada.</p>
        </figure>"""
    return f"""
    <div class="planned-workout">
      <div class="eyebrow">SESSÃO PLANEJADA</div>
      <h3 class="session-title">{title}</h3>
      <p class="panel-copy">Esta é a sessão planejada para hoje.</p>
      <div class="session-metrics">{metrics}</div>
      {chart}
    </div>"""


def _adherence_section(plan_status):
    """PLANO — consistência. Sem estado do plano não há o que medir, então a
    seção (e o grupo PLANO) some; com estado vazio válido, mostre o branch
    próprio em vez de concatenação quebrada (§43–§46)."""
    if not isinstance(plan_status, dict):
        return None
    summary = plan_status.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    done = int(summary.get("done") or 0)
    missed = int(summary.get("missed") or 0)
    pending = int(summary.get("pending") or 0)
    occurred = done + missed
    pct = (done / occurred * 100) if occurred else None
    ring_pct = pct if pct is not None else 0
    ring = ("background:conic-gradient(var(--accent-3) 0 "
            f"{ring_pct:.2f}%,var(--grid) {ring_pct:.2f}% 100%)")
    weeks = plan_status.get("weeks") if isinstance(plan_status.get("weeks"), list) else []
    week_rows = "".join(_adherence_week_html(week) for week in weeks)
    if not week_rows:
        week_rows = _empty_note("Sem sessões do plano para mostrar neste período.")

    rate = f"{pct:.0f}%" if pct is not None else "—"
    pending_word = "sessão" if pending == 1 else "sessões"
    if occurred:
        occurred_word = "sessão" if occurred == 1 else "sessões"
        headline = (f"<strong>{done} de {occurred}</strong> {occurred_word} "
                    f"concluída{'s' if occurred != 1 else ''}.")
        footnote = (f"{pending} {pending_word} pendente"
                    f"{'s' if pending != 1 else ''} não entra"
                    f"{'m' if pending != 1 else ''} no percentual.")
    else:
        headline = "Ainda não há sessões concluídas ou perdidas neste período."
        footnote = "O percentual aparece depois da primeira sessão concluída ou perdida."
    return f"""
  <section class="block adherence-panel" data-report-section="adherence" aria-labelledby="s-adherence">
    <div class="block-head"><h3 id="s-adherence">Consistência no plano</h3>
      <span class="pill">Estado atual</span></div>
    <p class="panel-copy">Sessões futuras permanecem pendentes e não entram no percentual.</p>
    <div class="adherence-layout">
      <div class="adherence-overview">
        <div aria-label="Cumprimento do plano: {_e(rate)}" class="adherence-ring" role="img" style="{ring}">
          <div><b>{rate}</b><small>CUMPRIMENTO</small></div>
        </div>
        <p>{headline}</p>
        <span class="chart-footnote">{_e(footnote)}</span>
      </div>
      <div class="weekly-consistency">
        <div class="consistency-legend"><span><i class="done"></i>Feito <b>{done}</b></span>
          <span><i class="missed"></i>Perdido <b>{missed}</b></span>
          <span><i class="pending"></i>Pendente <b>{pending}</b></span></div>
        {week_rows}
      </div>
    </div>
    <details class="data-details"><summary>Como este indicador é calculado</summary>
      <p>Cumprimento = feitos ÷ (feitos + perdidos). O indicador mede sessões
      cumpridas, não a correspondência exata de potência, duração ou TSS.</p></details>
  </section>"""


def _adherence_week_html(week):
    if not isinstance(week, dict):
        return ""
    done = int(week.get("done") or 0)
    missed = int(week.get("missed") or 0)
    pending = int(week.get("pending") or 0)
    occurred = done + missed
    pct = week.get("pct")
    rate = f"{float(pct):.0f}%" if pct is not None else "—"
    bars = "".join(
        f'<span class="{kind}" style="flex:{count}">{count}</span>'
        for kind, count in (("done", done), ("missed", missed), ("pending", pending))
        if count
    ) or '<span class="pending" style="flex:1">—</span>'
    label = _e(str(week.get("week") or "Semana"))
    rate_caption = f"{done} de {occurred}" if occurred else "A iniciar"
    return f"""<div class="week-row"><div class="week-label"><strong>{label}</strong>
      <span>{occurred + pending} sessões</span></div><div aria-label="{label}: {done} feito, {missed} perdido, {pending} pendente" class="week-bar" role="img">{bars}</div>
      <div class="week-rate"><b>{rate}</b><small>{rate_caption}</small></div></div>"""


def _fmt_profile_duration(value):
    try:
        return fmt_time(int(value)) if value is not None else "—"
    except (TypeError, ValueError):
        return "—"


def _fmt_profile_tss(value):
    try:
        return f"{float(value):.0f} TSS" if value is not None else "—"
    except (TypeError, ValueError):
        return "—"


def _profile_legend():
    entries = (("warmup", "Aquecimento"), ("work", "Trabalho"),
               ("recovery", "Recuperação"), ("cooldown", "Desaquecimento"))
    return ('<div class="profile-legend" aria-label="Legenda do perfil">' +
            "".join(f'<span><i class="{kind}"></i>{label}</span>'
                    for kind, label in entries) + "</div>")


def _profile_geometry(profile, width=760, height=270):
    """Geometria determinística do perfil em watts a partir dos blocos.

    O eixo X usa os segundos cumulativos de cada bloco. Não há suavização nem
    reamostragem: patamares ficam horizontais, rampas ficam inclinadas e cada
    transição é desenhada na mesma coordenada temporal.
    """
    ml, mr, mt, mb = 48, 16, 20, 38
    pw, ph = width - ml - mr, height - mt - mb
    total = int(profile["duration_seconds"])
    targets = [float(value) for block in profile["blocks"]
               for value in (block["start_watts"], block["end_watts"])]
    maximum = max(targets)
    y_max = max(25, int(math.ceil(maximum / 25.0) * 25))

    def x(seconds):
        return ml + pw * seconds / total

    def y(watts):
        return mt + ph * (1 - watts / y_max)

    segments = []
    for block in profile["blocks"]:
        segments.append({
            "block": block,
            "x0": x(block["start_seconds"]),
            "x1": x(block["end_seconds"]),
            "y0": y(block["start_watts"]),
            "y1": y(block["end_watts"]),
        })
    return {"width": width, "height": height, "left": ml, "right": width - mr,
            "top": mt, "bottom": mt + ph, "y_max": y_max, "segments": segments}


def _planned_profile_svg(profile):
    """SVG acessível do perfil canônico, sem inferência a partir de texto."""
    geometry = _profile_geometry(profile)
    width, height = geometry["width"], geometry["height"]
    left, right = geometry["left"], geometry["right"]
    top, bottom = geometry["top"], geometry["bottom"]

    grid = []
    for value in (0, geometry["y_max"] / 2, geometry["y_max"]):
        y = bottom - (bottom - top) * value / geometry["y_max"]
        grid.append(
            f'<line class="gl" x1="{left}" y1="{y:.1f}" x2="{right}" '
            f'y2="{y:.1f}" stroke-width="1" stroke-dasharray="3 4"/>')
        grid.append(
            f'<text class="tc" x="{left - 8}" y="{y + 3.5:.1f}" font-size="11" '
            f'text-anchor="end">{value:.0f} W</text>')

    segments = []
    boundaries = {0, int(profile["duration_seconds"])}
    for segment in geometry["segments"]:
        block = segment["block"]
        x0, x1, y0, y1 = (segment["x0"], segment["x1"],
                          segment["y0"], segment["y1"])
        boundaries.add(block["end_seconds"])
        label = _profile_block_label(block)
        segments.append(
            f'<g class="profile-segment {block["kind"]}" tabindex="0" role="img" '
            f'aria-label="{_e(label)}">'
            f'<title>{_e(label)}</title>'
            f'<path class="profile-fill {block["kind"]}" '
            f'd="M {x0:.1f} {bottom:.1f} L {x0:.1f} {y0:.1f} '
            f'L {x1:.1f} {y1:.1f} L {x1:.1f} {bottom:.1f} Z"/>'
            f'<path class="profile-line {block["kind"]}" '
            f'd="M {x0:.1f} {y0:.1f} L {x1:.1f} {y1:.1f}"/>'
            f'</g>')

    markers = []
    total = int(profile["duration_seconds"])
    for seconds in sorted(boundaries):
        x = left + (right - left) * seconds / total
        markers.append(
            f'<line class="profile-boundary" x1="{x:.1f}" y1="{top}" '
            f'x2="{x:.1f}" y2="{bottom}"/>'
            f'<text class="tc" x="{x:.1f}" y="{height - 10}" font-size="10" '
            f'text-anchor="middle">{_fmt_elapsed(seconds)}</text>')

    payload = _e(json.dumps(profile, ensure_ascii=False, separators=(",", ":")))
    aria = _e(f"Perfil planejado do treino {profile.get('title') or ''}")
    return (f'<svg class="planned-profile" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{aria}" '
            f'data-workout-profile="{payload}">'
            f'{"".join(grid)}{"".join(segments)}{"".join(markers)}</svg>')


def _profile_block_label(block):
    start = float(block["start_pct_ftp"]) * 100
    end = float(block["end_pct_ftp"]) * 100
    watts = (f"{block['start_watts']:.0f} W" if start == end else
             f"{block['start_watts']:.0f}–{block['end_watts']:.0f} W")
    percent = (f"{start:.0f}% FTP" if start == end else
               f"{start:.0f}–{end:.0f}% FTP")
    return (f"{block['label']}: {_fmt_elapsed(block['duration_seconds'])}, "
            f"{percent} ({watts})")


def _fmt_elapsed(seconds):
    seconds = int(seconds)
    hours, remaining = divmod(seconds, 3600)
    minutes, secs = divmod(remaining, 60)
    if hours:
        return f"{hours}h{minutes:02d}" if not secs else f"{hours}h{minutes:02d}m"
    return f"{minutes}m" if not secs else f"{minutes}m{secs:02d}s"


def _pmc_svg(pmc_rows, width=760, height=320):
    """Curvas suaves CTL/ATL/TSB com area em gradiente sob CTL/ATL.

    As cores vêm dos tokens da página (classes `sc`/`sa`/`ss` + `--ctl`/...),
    então o SVG troca de tema junto com a página sem regerar nada.

    Cada serie carrega o tooltip tematico via JS (`_chart_js`): o SVG embute
    os dados (`data-pmc`), uma linha-guia vertical com um ponto por serie
    (`pmc-guide`) e um retangulo invisivel que captura o mouse (`pmc-hit`);
    o card (`.tt-card`) usa os tokens da pagina e acompanha o tema.
    """
    ml, mr, mt, mb = 46, 14, 16, 30
    pw, ph = width - ml - mr, height - mt - mb
    lo, hi = _scale_lo(pmc_rows), _scale_hi(pmc_rows)
    if hi - lo < 1:
        lo, hi = lo - 1, hi + 1

    def x(i):
        n = max(len(pmc_rows) - 1, 1)
        return ml + pw * i / n

    def y(v):
        return mt + ph * (hi - v) / (hi - lo)

    grid = []
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        gy = mt + ph * k / 4
        grid.append(
            f'<line class="gl" x1="{ml}" y1="{gy:.1f}" x2="{width - mr}" '
            f'y2="{gy:.1f}" stroke-width="1" stroke-dasharray="3 4"/>')
        grid.append(
            f'<text class="tc" x="{ml - 8}" y="{gy + 3.5:.1f}" font-size="11" '
            f'text-anchor="end">{v:.0f}</text>')
    days = [r[0] for r in pmc_rows]
    shown = {0, len(days) - 1}
    if len(days) > 2:
        shown.add(len(days) // 2)
    for i in sorted(shown):
        grid.append(
            f'<text class="tc" x="{x(i):.1f}" y="{height - 9}" font-size="11" '
            f'text-anchor="middle">{days[i]}</text>')
    base_y = mt + ph

    def line_points(series):
        return [(x(i), y(v)) for i, v in enumerate(series)]

    def area_path(series):
        pts = line_points(series)
        d = _smooth_d(pts)
        return f"{d} L {pts[-1][0]:.1f} {base_y:.1f} L {pts[0][0]:.1f} {base_y:.1f} Z"

    def line_path(series):
        return _smooth_d(line_points(series))

    ctl = [r[1] for r in pmc_rows]
    atl = [r[2] for r in pmc_rows]
    tsb = [r[3] for r in pmc_rows]
    ctl_pts = line_points(ctl)
    atl_pts = line_points(atl)
    tsb_pts = line_points(tsb)

    def last_dot(pts, cls):
        lx, ly = pts[-1]
        return (f'<circle class="dk {cls}" cx="{lx:.1f}" cy="{ly:.2f}" r="4" '
                f'stroke-width="2.5"/>')

    tsb_zone_cls = _ZONE_CLASS[_tsb_zone(tsb[-1])]
    defs = f"""
    <defs>
      <linearGradient id="fillCtl" x1="0" y1="0" x2="0" y2="1">
        <stop class="gp-ctl-a" offset="0%"/>
        <stop class="gp-ctl-b" offset="100%"/>
      </linearGradient>
      <linearGradient id="fillAtl" x1="0" y1="0" x2="0" y2="1">
        <stop class="gp-atl-a" offset="0%"/>
        <stop class="gp-atl-b" offset="100%"/>
      </linearGradient>
      <linearGradient id="loadBar" x1="0" y1="0" x2="0" y2="1">
        <stop class="gp-bara" offset="0%"/>
        <stop class="gp-barb" offset="100%"/>
      </linearGradient>
    </defs>"""

    body_svg = (
        f'<path d="{area_path(ctl)}" fill="url(#fillCtl)"/>'
        f'<path d="{area_path(atl)}" fill="url(#fillAtl)"/>'
        f'<path class="sc" d="{line_path(ctl)}" fill="none" '
        f'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<path class="sa" d="{line_path(atl)}" fill="none" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>'
        + _tsb_paths(tsb_pts, tsb)
        + "".join([
            last_dot(ctl_pts, "sc"), last_dot(atl_pts, "sa"),
            last_dot(tsb_pts, tsb_zone_cls),
        ]))
    guide = (
        f'<g class="pmc-guide" visibility="hidden">'
        f'<line x1="0" y1="{mt}" x2="0" y2="{mt + ph}" class="gl"/>'
        f'<circle class="pmc-dot sc" r="4.5"/>'
        f'<circle class="pmc-dot sa" r="4.5"/>'
        f'<circle class="pmc-dot ss" r="4.5"/>'
        f'</g>')
    hit = (f'<rect class="pmc-hit" x="{ml}" y="{mt}" width="{pw}" '
           f'height="{ph}" fill="transparent" pointer-events="all"/>')
    payload = json.dumps({
        "days": [str(r[0]) for r in pmc_rows],
        "ctl": ctl, "atl": atl, "tsb": tsb,
        "w": width, "ml": ml, "mt": mt, "pw": pw, "ph": ph,
        "lo": lo, "hi": hi,
    })
    svg = (f'<svg viewBox="0 0 {width} {height}" '
           f'xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="PMC CTL ATL TSB" data-pmc=\'{payload}\'>'
           f'{defs}{"".join(grid)}{body_svg}{guide}{hit}</svg>')
    return (f'<div class="pmc-chart">{svg}'
            f'<div class="tt-card" role="status" aria-live="polite"></div>'
            f'</div>')


def _tsb_paths(pts, values):
    """Forma (TSB) colorida por zona: Bezier segmento a segmento.

    Cada trecho da curva fica na cor da zona (`risk`/`ideal`/`fresh`) do dia
    de chegada — o corte acontece exatamente no dia em que o atleta muda de
    estado. A geometria é a mesma Catmull-Rom da linha completa (o tracinho
    pontilhado continua), só o `stroke` muda.
    """
    if len(pts) < 2:
        return ""
    out = []
    for i in range(len(pts) - 1):
        zone = _tsb_zone(values[i + 1])
        out.append(
            f'<path class="{_ZONE_CLASS[zone]}" d="{_bezier_segment(pts, i)}" '
            f'fill="none" stroke-width="2.5" stroke-dasharray="1 6" '
            f'stroke-linecap="round" stroke-linejoin="round"/>')
    return "".join(out)


def _bezier_segment(p, i):
    """Bezier de p[i] para p[i+1] com os controles Catmull-Rom de `_smooth_d`."""
    x0, y0 = p[i]
    x1, y1 = p[i + 1]
    px, py = p[i - 1] if i else p[i]
    if i + 2 < len(p):
        nx, ny = p[i + 2]
    else:
        nx, ny = p[i + 1]
    c1x, c1y = x0 + (x1 - px) / 6, y0 + (y1 - py) / 6
    c2x, c2y = x1 - (nx - x0) / 6, y1 - (ny - y0) / 6
    return (f"M {x0:.1f} {y0:.2f} C {c1x:.1f} {c1y:.2f} {c2x:.1f} {c2y:.2f} "
            f"{x1:.1f} {y1:.2f}")


def _smooth_d(pts):
    """Curva de Catmull-Rom -> Bezier cubica atraves de `pts`."""
    p = pts
    if len(p) == 1:
        return f"M {p[0][0]:.1f} {p[0][1]:.1f}"
    parts = [f"M {p[0][0]:.1f} {p[0][1]:.1f}"]
    for i in range(len(p) - 1):
        c1x = p[i][0] + (p[i + 1][0] - p[i - 1][0]) / 6 if i else p[i][0]
        c1y = p[i][1] + (p[i + 1][1] - p[i - 1][1]) / 6 if i else p[i][1]
        c2x = (p[i + 1][0] - (p[i + 2][0] - p[i][0]) / 6
               if i + 2 < len(p) else p[i + 1][0])
        c2y = (p[i + 1][1] - (p[i + 2][1] - p[i][1]) / 6
               if i + 2 < len(p) else p[i + 1][1])
        parts.append(
            f"C {c1x:.1f} {c1y:.2f} {c2x:.1f} {c2y:.2f} "
            f"{p[i + 1][0]:.1f} {p[i + 1][1]:.2f}")
    return " ".join(parts)


def _load_svg(weeks, width=760, height=240):
    """Barras verticais com gradiente, rotulos e tooltip tematico.

    Mesma logica do `_pmc_svg`: cor vem das classes/tokens, o tema troca na
    hora sem regenerar o SVG; o card do tooltip (`.tt-card`) e o JS de
    `_chart_js` (`data-load` + `load-hit`).
    """
    ml, mr, mt, mb = 46, 14, 20, 34
    pw, ph = width - ml - mr, height - mt - mb
    vmax = max((t for _, t in weeks), default=1.0) or 1.0
    n = len(weeks)
    slot = pw / n
    bw = max(min(slot * 0.56, 56.0), 4.0)

    grid = []
    for k in range(4):
        v = vmax * k / 3
        gy = mt + ph * (1 - k / 3)
        grid.append(
            f'<line class="gl" x1="{ml}" y1="{gy:.1f}" x2="{width - mr}" '
            f'y2="{gy:.1f}" stroke-width="1" stroke-dasharray="3 4"/>')
        grid.append(
            f'<text class="tc" x="{ml - 8}" y="{gy + 3.5:.1f}" font-size="11" '
            f'text-anchor="end">{v:.0f}</text>')

    mean = sum(t for _, t in weeks) / n
    mean_y = mt + ph * (1 - mean / vmax)
    grid.append(
        f'<line class="ml" x1="{ml}" y1="{mean_y:.1f}" x2="{width - mr}" '
        f'y2="{mean_y:.1f}" stroke-width="1.4" stroke-dasharray="5 4"/>')
    grid.append(
        f'<text class="tl" x="{width - mr}" y="{mean_y - 5:.1f}" font-size="10" '
        f'text-anchor="end">média {mean:.0f}/sem</text>')

    bars = []
    for i, (monday, tss) in enumerate(weeks):
        cx = ml + slot * i + slot / 2
        bh = ph * tss / vmax
        by = mt + ph - bh
        bars.append(
            f'<rect x="{cx - bw / 2:.1f}" y="{by:.1f}" width="{bw:.1f}" '
            f'height="{max(bh, 2):.1f}" rx="5" fill="url(#loadBar)"/>')
        bars.append(
            f'<text class="tb" x="{cx:.1f}" y="{by - 6:.1f}" font-size="11" '
            f'font-weight="700" text-anchor="middle">{tss:.0f}</text>')
        bars.append(
            f'<text class="tc" x="{cx:.1f}" y="{height - 9}" font-size="11" '
            f'text-anchor="middle">{monday.day:02d}/{monday.month:02d}</text>')

    hit = (f'<rect class="load-hit" x="{ml}" y="{mt}" width="{pw}" '
           f'height="{ph}" fill="transparent" pointer-events="all"/>')
    payload = json.dumps({
        "days": [f"{monday:%d/%m/%Y} (W{monday.isocalendar().week:02d})"
                 for monday, _ in weeks],
        "tss": [tss for _, tss in weeks],
        "w": width, "ml": ml, "pw": pw,
    })
    svg = (f'<svg viewBox="0 0 {width} {height}" '
           f'xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Carga semanal" data-load=\'{payload}\'>'
           f'{"".join(grid)}{"".join(bars)}{hit}</svg>')
    return (f'<div class="load-chart">{svg}'
            f'<div class="tt-card" role="status" aria-live="polite"></div>'
            f'</div>')


def _today():
    from datetime import date
    return date.today()


def _e(text):
    return escape(str(text))
