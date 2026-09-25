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
import subprocess
import tempfile
from html import escape

try:
    from activity_summary import fmt_time, fmt_dist
    from brand import THEMES, DEFAULT_THEME
except ImportError:
    from .activity_summary import fmt_time, fmt_dist
    from .brand import THEMES, DEFAULT_THEME

DESC_PMC = (
    "<b>Leitura:</b> a linha <b style=\"color:var(--ctl)\">de aptidão (CTL)</b> "
    "mostra a média exponencialmente ponderada da carga dos últimos 42 dias. "
    "A linha <b style=\"color:var(--atl)\">do cansaço (ATL)</b> é a mesma "
    "média, mas de 7 dias. Para ficar mais apto é preciso criar stress "
    "mantendo o cansaço acima da aptidão. A <b>forma</b> é aptidão − fadiga e "
    "muda de cor pelo estado do atleta: <b style=\"color:var(--risk)\">zona de "
    "alto risco</b> (TSB ≤ −10 — risco de lesão/desgaste), "
    "<b style=\"color:var(--tsb)\">zona de treino ideal</b> (ganhando "
    "aptidão) e <b style=\"color:var(--fresh)\">fresco e em forma</b> "
    "(pronto para competir). Evite ficar muito tempo em alto risco e inclua "
    "semanas de descanso periódicas. <i>Refs: Monitoring your training load "
    "(Science2Sport); Managing Training Using TSB (Joe Friel).</i>")
DESC_LOAD = ("<b>Leitura:</b> TSS somado por semana ISO (começa na segunda). "
             "Semanas acima da média sustentam o fitness; abaixo, liberam "
             "espaço para descansar e regenerar.")

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
_ZONE_LABEL = {"risk": "alto risco - descanse", "ideal": "zona de treino ideal",
               "fresh": "fresco - pronto para competir"}


def render_summary_html(*, title, start, end, agg, rows, pmc_rows, weeks,
                        theme=None):
    """Pagina HTML autossuficiente com o resumo e os graficos SVG."""
    slug = theme if theme in THEMES else DEFAULT_THEME
    hero = _hero(agg, start, end)
    stats = _stats_cards(agg)
    table_rows = "".join(_workout_row(r) for r in rows)
    pmc_svg = _pmc_svg(pmc_rows) if pmc_rows else _empty_note(
        "Sem historico de carga no periodo.")
    load_svg = _load_svg(weeks) if weeks else _empty_note(
        "Sem treinos feitos no periodo (carga semanal indisponivel).")

    body = f"""
<main>
  {_topbar()}

  {hero}

  <section class="stats">{stats}</section>

  <section class="block">
    <div class="block-head">
      <h2>PMC &middot; fitness / fadiga / forma</h2>
      {_pmc_chips(pmc_rows)}
    </div>
    <p class="chart-desc">{DESC_PMC}</p>
    {pmc_svg}
  </section>

  <section class="block">
    <div class="block-head">
      <h2>Carga semanal (TSS)</h2>
      <span class="pill">{len(weeks)} semanas</span>
    </div>
    <p class="chart-desc">{DESC_LOAD}</p>
    {load_svg}
  </section>

  <section class="block">
    <div class="block-head"><h2>Treinos feitos</h2></div>
    <div class="table-wrap">
      <table>
        <thead><tr>
          <th>Dia</th><th>Treino</th><th>Tipo</th><th>Tempo</th>
          <th class="num">Distancia</th><th class="num">Elevacao</th>
          <th class="num">Carga</th>
        </tr></thead>
        <tbody>{table_rows}</tbody>
      </table>
    </div>
  </section>

  <footer>
    <span>Hermes Coach &mdash; plano adaptativo de ciclismo indoor.</span>
    <span>Gerado em {_e(str(_today()))}</span>
  </footer>
</main>
"""
    return _page(title, body, slug)


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
  .hero .hero-stats {{ display: flex; flex-wrap: wrap; gap: 10px;
                       margin-top: 16px; }}
  .hero-chip {{ background: rgba(255, 255, 255, .16); border:
                 1px solid rgba(255, 255, 255, .3); backdrop-filter: blur(4px);
                 border-radius: 12px; padding: 8px 14px; min-width: 108px; }}
  .hero-chip b {{ display: block; font-size: 1.1rem; }}
  .hero-chip span {{ font-size: .72rem; opacity: .85; }}

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
  .pill {{ background: var(--subtle); color: var(--subtle-text);
           border-radius: 999px; font-size: .72rem; padding: 2px 10px;
           font-weight: 600; }}
  .chart-desc {{ margin: 4px 0 10px; font-size: .82rem; color: var(--muted); }}
  .chart-desc b {{ color: var(--text); }}

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
  }}
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


def _hero(agg, start, end):
    return f"""
  <header class="hero">
    <div class="kicker">Relatorio do atleta</div>
    <h1>{_e(_hero_title(agg))}</h1>
    <p class="meta">{_e(str(start))} ate {_e(str(end))} &middot; treinos
      feitos no periodo</p>
    <div class="hero-stats">
      <div class="hero-chip"><b>{agg['sessions']}</b><span>treinos</span></div>
      <div class="hero-chip"><b>{agg['load']:.0f} TSS</b><span>carga total</span></div>
      <div class="hero-chip"><b>{fmt_time(agg['time_s'])}</b><span>tempo</span></div>
    </div>
  </header>
"""


def _hero_title(agg):
    n = agg["sessions"]
    if n == 0:
        return "Nenhum treino no periodo"
    if n == 1:
        return "Seu treino mais recente"
    return f"{n} treinos realizados"


def _stats_cards(agg):
    def card(value, label):
        return f'<div class="card"><b>{_e(value)}</b><span>{_e(label)}</span></div>'

    power = _fmt_power(agg) or "—"
    hr = f"{agg['avg_hr']:.0f} bpm" if agg.get("avg_hr") is not None else "—"
    elev = f"+{agg['elevation_m']:.0f} m" if agg.get("elevation_m") else "—"
    return "".join([
        card(fmt_dist(agg["distance_m"]), "distancia"),
        card(power, "potencia (media / NP)"),
        card(fmt_time(agg["time_s"]), "tempo"),
        card(hr, "FC media"),
        card(elev, "elevacao"),
    ])


def _fmt_power(agg):
    parts = []
    if agg.get("avg_power") is not None:
        parts.append(f"{agg['avg_power']:.0f} W")
    if agg.get("np") is not None:
        parts.append(f"NP {agg['np']:.0f} W")
    return " / ".join(parts)


def _workout_row(r):
    cells = [
        _e(r["day"]), _e(r["name"]), _e(r["type"] or "—"),
        fmt_time(r["time_s"]),
        _num(fmt_dist(r["distance_m"]) if r["distance_m"] else "—"),
        _num(f"+{r['elevation_m']:.0f} m" if r["elevation_m"] else "—"),
        _num(f"{r['load']:.0f} TSS" if r["load"] else "—"),
    ]
    return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"


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
        f'text-anchor="end">media {mean:.0f}/sem</text>')

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