"""Testes da exportacao do resumo (report.py): HTML com SVG e PDF via
chromium. Sem rede; o chromium e mockado (so verificamos o comando).
"""

import os
import subprocess
import unittest
import tempfile
import html as html_lib
import json
import re
from datetime import date
from unittest import mock

from src import report, brand
from src.activity_summary import summarize


def _rows():
    return [{"name": "Treino de Limiar", "day": "2026-09-23",
             "_day": date(2026, 9, 23), "type": "VirtualRide", "time_s": 3225,
             "distance_m": 24732.67, "elevation_m": 175.0, "load": 58.0,
             "avg_power": 133.0, "np": 147.0, "avg_hr": 153.0},
            {"name": "Z2", "day": "2026-09-21", "_day": date(2026, 9, 21),
             "type": "VirtualRide", "time_s": 3315, "distance_m": 25800.0,
             "elevation_m": 0.0, "load": 41.0, "avg_power": 120.0,
             "np": 128.0, "avg_hr": 145.0}]


def _pmc_rows():
    from datetime import timedelta
    ctl = atl = 0.0
    rows = []
    for i in range(10):
        tss = 40.0 if i % 4 == 0 else 0.0
        ctl += (tss - ctl) * (1 - __import__("math").exp(-1 / 42))
        atl += (tss - atl) * (1 - __import__("math").exp(-1 / 7))
        rows.append((date(2026, 9, 14) + timedelta(days=i), ctl, atl, ctl - atl))
    return rows


def _weeks():
    return [(date(2026, 9, 14), 83.0), (date(2026, 9, 21), 156.0)]


class RenderHtmlTest(unittest.TestCase):
    def test_emite_pagina_com_resumo_e_dois_svg(self):
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="Resumo semana - 2026-09-17 a 2026-09-23",
            start=date(2026, 9, 17), end=date(2026, 9, 23), agg=agg,
            rows=_rows(), pmc_rows=_pmc_rows(), weeks=_weeks())
        self.assertIn("<!doctype html>", html)
        self.assertIn("Resumo semana", html)
        self.assertIn("Treino de Limiar", html)
        self.assertIn("fitness / fadiga / forma", html)
        self.assertIn("Carga semanal (TSS)", html)
        self.assertEqual(html.count(' role="img"'), 2)  # PMC + carga semanal
        self.assertIn("1h49", html)     # 3225 + 3315 segs = 6540
        self.assertIn("50.5 km", html)  # 24732.67 + 25800 m

    def test_embute_menu_de_temas_e_tokens(self):
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="Resumo", start=date(2026, 9, 17), end=date(2026, 9, 23),
            agg=agg, rows=_rows(), pmc_rows=_pmc_rows(), weeks=_weeks())
        self.assertIn('data-theme="tokyo-night"', html)
        self.assertIn('id="themeBtn"', html)
        self.assertIn("Temas", html)
        self.assertIn("Tokyo Night", html)
        self.assertIn("Matte Black", html)
        self.assertIn("Vantablack", html)
        self.assertEqual(
            html.count('class="theme-opt" data-theme="'),
            len(brand.THEMES))
        self.assertIn(":root {", html)
        self.assertIn("[data-theme=\"catppuccin\"] {", html)
        # as series do grafico usam as variaveis do tema (trocam sem regenerar)
        self.assertIn("var(--ctl)", html)
        self.assertIn("var(--atl)", html)

    def test_tema_escolhido_vira_data_theme(self):
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="R", start=date(2026, 9, 17), end=date(2026, 9, 23),
            agg=agg, rows=_rows(), pmc_rows=_pmc_rows(), weeks=_weeks(),
            theme="matte-black")
        self.assertIn('data-theme="matte-black"', html)

    def test_tema_invalido_cai_no_padrao(self):
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="R", start=date(2026, 9, 17), end=date(2026, 9, 23),
            agg=agg, rows=_rows(), pmc_rows=_pmc_rows(), weeks=_weeks(),
            theme="nao-existe")
        self.assertIn('data-theme="tokyo-night"', html)

    def test_css_padrao_nao_sobrescreve_os_temas(self):
        """O bloco :root (tema padrao) vem ANTES de todos os [data-theme].

        `:root` e `[data-theme]` tem a mesma especificidade e atuam no mesmo
        elemento (html); a regra mais recente vence. Se o padrao for emitido
        na posicao alfabetica do tokyo-night, ele sobrescreve todos os temas
        anteriores (catppuccin..solitude) e esses param de funcionar.
        """
        css = report._theme_css()
        self.assertLess(css.index(":root"), css.index("[data-theme="))
        for slug in brand.THEMES:
            self.assertIn(f'[data-theme="{slug}"]', css)
        # tokens das zonas da forma em todos os temas (+ 1 do :root)
        self.assertEqual(css.count("--fresh"), len(brand.THEMES) + 1)
        self.assertEqual(css.count("--risk"), len(brand.THEMES) + 1)

    def test_tsb_muda_de_cor_por_zona(self):
        # atravessa risco (TSB -20 -> -15), ideal (0) e fresco (+15)
        pmc = [(date(2026, 9, 20), 100.0, 120.0, -20.0),
               (date(2026, 9, 21), 100.0, 115.0, -15.0),
               (date(2026, 9, 22), 100.0, 100.0, 0.0),
               (date(2026, 9, 23), 100.0, 85.0, 15.0)]
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="R", start=date(2026, 9, 20), end=date(2026, 9, 23),
            agg=agg, rows=_rows(), pmc_rows=pmc, weeks=[])
        self.assertIn('class="sr"', html)   # trecho de risco (vermelho)
        self.assertIn('class="ss"', html)   # trecho ideal (verde)
        self.assertIn('class="sf"', html)   # trecho fresco (azul)
        # estado atual do atleta (fresco, TSB +15) -- copy neutra + heuristica
        self.assertIn("Estado: forma acima da carga recente", html)
        self.assertIn("Heurística Hermes", html)
        # desc com explicacao + referencias
        self.assertIn("Science2Sport", html)
        self.assertIn("Joe Friel", html)

    def test_estado_reflete_zona_de_risco(self):
        pmc = [(date(2026, 9, 23), 100.0, 120.0, -20.0)]
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="R", start=date(2026, 9, 23), end=date(2026, 9, 23),
            agg=agg, rows=_rows(), pmc_rows=pmc, weeks=[])
        self.assertIn("Estado: carga recente acima da forma", html)
        self.assertNotIn("alto risco - descanse", html)
        self.assertNotIn('class="sr"', html)  # ponto unico: sem segmentos

    def test_escapa_conteudo_proveniente_da_api(self):
        rows = [{"name": "<script>alert(1)</script>", "day": "2026-09-23",
                 "_day": date(2026, 9, 23), "type": "VirtualRide",
                 "time_s": 1, "distance_m": 0, "elevation_m": 0, "load": 0.0}]
        agg = summarize(rows)
        html = report.render_summary_html(
            title="<b>x</b>", start=date(2026, 9, 23), end=date(2026, 9, 23),
            agg=agg, rows=rows, pmc_rows=[], weeks=[])
        self.assertNotIn("<script>alert", html)
        self.assertIn("&lt;script&gt;alert", html)
        self.assertNotIn("<b>x</b>", html)
        self.assertIn("Sem histórico de carga", html)

    def test_sem_treinos_nao_quebra(self):
        agg = summarize([])
        html = report.render_summary_html(
            title="Resumo dia", start=date(2026, 9, 23), end=date(2026, 9, 23),
            agg=agg, rows=[], pmc_rows=[], weeks=[])
        self.assertIn("0", html)
        # sem plan_status nao ha anel de consistencia; pmc/carga caem em nota
        self.assertEqual(html.count(' role="img"'), 0)

    def test_graficos_embutem_tooltip_tematico(self):
        """Os cards de hover usam os tokens do tema (var(--surface)/--ctl/...)
        e o JS vem embutido -- popup acompanha o tema, sem <title> nativo."""
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="R", start=date(2026, 9, 17), end=date(2026, 9, 23),
            agg=agg, rows=_rows(), pmc_rows=_pmc_rows(), weeks=_weeks())
        self.assertIn("tt-card", html)
        self.assertIn("pmc-hit", html)
        self.assertIn("load-hit", html)
        self.assertIn("attachPmc", html)
        self.assertIn("attachLoad", html)
        self.assertIn("data-pmc=", html)
        self.assertIn("data-load=", html)
        self.assertIn("var(--surface)", html)  # card segue o tema
        # so o <title> do documento; os SVGs nao tem <title> nativo do browser
        self.assertEqual(html.count("<title>"), 1)


def _planned_profile(*, structured=True):
    from src.plan import planned_workout_profile
    workout = {
        "day": "2026-10-06",
        "focus": "zone2",
        "planned_duration": 3840,
        "name": "2026-10-06 - Treino de Zona 2",
        "tss": 51.0,
        "intensity_factor": 0.69,
        "ftp_watts": 183,
        "params": {
            "warmup_sec": 600, "warmup_power_low": 0.55,
            "warmup_power_high": 0.75, "repeats": 2,
            "on_sec": 1140, "on_power": 0.75,
            "off_sec": 180, "off_power": 0.55,
            "cooldown_sec": 600, "cooldown_power_low": 0.70,
            "cooldown_power_high": 0.45,
        } if structured else {},
    }
    return planned_workout_profile(workout)


class PlannedProfileReportTest(unittest.TestCase):
    def _html(self, profile):
        return report.render_summary_html(
            title="Resumo", start=date(2026, 9, 1), end=date(2026, 10, 5),
            agg=summarize(_rows()), rows=_rows(), pmc_rows=_pmc_rows(),
            weeks=_weeks(), planned_workout=profile,
            readiness={"available": True, "reference_day": "2026-10-06",
                       "heuristic_level": "GREEN", "heuristic_score": .8,
                       "heuristic_confidence": .43})

    def test_geometria_respeita_tempo_cumulativo_exato(self):
        profile = _planned_profile()
        geometry = report._profile_geometry(profile)
        segments = geometry["segments"]
        self.assertEqual([(s["block"]["start_seconds"], s["block"]["end_seconds"])
                          for s in segments],
                         [(0, 600), (600, 1740), (1740, 1920),
                          (1920, 3060), (3060, 3240), (3240, 3840)])
        self.assertAlmostEqual(segments[0]["x0"], geometry["left"])
        self.assertAlmostEqual(segments[0]["x1"], 156.75)
        self.assertAlmostEqual(segments[1]["x0"], segments[0]["x1"])
        self.assertAlmostEqual(segments[-1]["x1"], geometry["right"])

    def test_svg_carrega_o_perfil_canonico_e_desenha_rampas_patamares(self):
        profile = _planned_profile()
        svg = report._planned_profile_svg(profile)
        match = re.search(r'data-workout-profile="([^"]+)"', svg)
        self.assertIsNotNone(match)
        payload = json.loads(html_lib.unescape(match.group(1)))
        self.assertEqual(payload, profile)
        self.assertEqual(svg.count('class="profile-segment '), 6)
        self.assertIn('class="profile-line warmup"', svg)
        self.assertIn('class="profile-line work"', svg)
        self.assertIn('class="profile-line recovery"', svg)
        self.assertIn('class="profile-line cooldown"', svg)
        self.assertIn('>10m</text>', svg)  # primeiro limite: 600 s
        self.assertIn('75% FTP (137 W)', svg)

    def test_html_usa_mesmos_metadados_e_perfil_planejados(self):
        html = self._html(_planned_profile())
        # HOJE agora separa prontidao e treino (PROMPT 37, secao 11)
        self.assertIn("Prontidão de hoje", html)
        self.assertIn("Treino do dia", html)
        self.assertIn("Perfil planejado do treino", html)
        self.assertIn("potência-alvo", html)
        self.assertIn("1h04", html)
        self.assertIn("51 TSS", html)
        self.assertIn("69%", html)
        self.assertIn("Treino de Zona 2", html)
        self.assertIn('class="planned-profile"', html)

    def test_sessao_sem_blocos_nao_desenha_faixa_generica(self):
        html = self._html(_planned_profile(structured=False))
        self.assertIn("Perfil detalhado indisponível para esta sessão", html)
        self.assertNotIn('class="planned-profile"', html)
        self.assertNotIn("data-workout-profile", html)
        self.assertIn("1h04", html)
        self.assertIn("51 TSS", html)


class ReadinessReportTest(unittest.TestCase):
    def _html(self, *, available, implemented=3, model=7, level=None,
              score=None, illness_alert=False, composite_low=False):
        names = (
            ("hrv_score", "HRV"),
            ("rhr_score", "Frequência cardíaca de repouso"),
            ("sleep_score", "Sono"),
            ("subjective_fatigue_score", "Fadiga subjetiva"),
            ("recent_load_score", "Carga recente"),
            ("performance_score", "Desempenho"),
            ("consistency_score", "Consistência"),
        )
        axes = [{"axis": axis, "label": label, "implemented": index < implemented,
                 "available": index < available,
                 "score": .8 if index < available else None}
                for index, (axis, label) in enumerate(names[:model])]
        readiness = {
            "available": score is not None,
            "heuristic_level": level,
            "heuristic_score": score,
            "model_axis_count": model,
            "implemented_axis_count": implemented,
            "available_axis_count": available,
            "axis_states": axes,
            "illness_alert": illness_alert,
            "composite_low": composite_low,
        }
        plan_status = {"today": {"lifecycle_effective": "planned"},
                       "summary": {"done": 1, "missed": 2, "pending": 3},
                       "weeks": [{"week": "2026-W41", "done": 1,
                                  "missed": 2, "pending": 3, "pct": 100 / 3}]}
        return report.render_summary_html(
            title="Resumo", start=date(2026, 10, 6), end=date(2026, 10, 6),
            agg=summarize(_rows()), rows=_rows(), pmc_rows=_pmc_rows(),
            weeks=[], readiness=readiness, plan_status=plan_status)

    def test_readiness_data_coverage_is_separate_from_model_coverage(self):
        cases = ((0, "Sem dados suficientes", "0 de 3 eixos avaliáveis"),
                 (1, "Leitura parcial", "1 de 3 eixos avaliáveis"),
                 (2, "Leitura parcial", "2 de 3 eixos avaliáveis"),
                 (3, "Leitura completa", "3 de 3 eixos avaliáveis"))
        for available, state, coverage in cases:
            with self.subTest(available=available):
                html = self._html(available=available, level="green",
                                  score=.8 if available else None)
                self.assertIn(state, html)
                self.assertIn(coverage, html)
                self.assertIn("Cobertura do modelo: 3 de", html)
                self.assertIn("7 eixos possuem avaliação implementada", html)

    def test_readiness_renderer_supports_all_seven_implemented_axes(self):
        html = self._html(available=7, implemented=7, model=7,
                          level="green", score=.8)
        self.assertIn("7 de 7 eixos avaliáveis", html)
        self.assertIn("Cobertura do modelo: 7 de", html)
        self.assertIn("Consistência", html)

    def test_green_partial_reading_and_external_alert_are_distinct(self):
        html = self._html(available=1, level="green", score=.8,
                          illness_alert=True)
        self.assertIn("Leitura parcial", html)
        self.assertIn("Verde · sem alerta nos eixos avaliados", html)
        self.assertIn("Há um alerta separado de possível doença", html)

    def test_readiness_copy_does_not_claim_renderer_changes_the_plan(self):
        html = self._html(available=3, level="yellow", score=.6)
        self.assertIn("Nenhuma alteração foi feita no plano de treinos.", html)
        self.assertNotIn("Nenhuma alteração automática foi aplicada por este relatório", html)
        self.assertNotIn("A renderização não decide adaptação", html)
        self.assertIn("Sinais sem dados ficam fora da média", html)
        self.assertIn("sem avaliação implementada", html)

    def test_eixos_nao_implementados_usam_copy_neutra_sem_genero(self):
        html = self._html(available=0, implemented=3, model=7)
        self.assertNotIn("ainda não implementado", html)
        for axis in ("Fadiga subjetiva", "Carga recente", "Desempenho",
                     "Consistência"):
            self.assertIn(f"<dt>{axis}</dt><dd>sem avaliação "
                          f"implementada</dd>", html)
        self.assertEqual(html.count("sem avaliação implementada"), 4)


class CanonicalReportTest(unittest.TestCase):
    """Ordem, determinismo e estados do relatório canônico (PROMPT 37).

    Os marcadores `data-report-section`/`data-report-group` são o contrato
    de teste da ordem: RESUMO -> HOJE -> EVOLUÇÃO -> PLANO -> DETALHES.
    """

    ORDER = ["summary", "readiness", "planned-workout", "pmc", "weekly-load",
             "vo2", "ftp", "adherence", "activities"]
    GROUPS = ["resumo", "hoje", "evolucao", "plano", "detalhes"]

    def _html(self, **overrides):
        kwargs = dict(
            title="Resumo da semana", start=date(2026, 9, 17),
            end=date(2026, 9, 23), agg=summarize(_rows()), rows=_rows(),
            pmc_rows=_pmc_rows(), weeks=_weeks(),
            readiness={"available": True, "target_day": "2026-10-06",
                       "heuristic_level": "GREEN", "heuristic_score": .8},
            plan_status={"today": {"lifecycle_effective": "planned"},
                         "summary": {"done": 2, "missed": 1, "pending": 4},
                         "weeks": [{"week": "2026-W38", "done": 2,
                                    "missed": 1, "pending": 4,
                                    "pct": 200 / 3}]},
            vo2=None,
            ftp={"value": 182, "unit": "W", "source": ".env FTP",
                 "date": None, "series": []},
        )
        kwargs.update(overrides)
        return report.render_summary_html(**kwargs)

    @staticmethod
    def _attr(html, name):
        return re.findall(rf'{name}="([^"]+)"', html)

    @staticmethod
    def _block(html, key):
        return html.split(f'data-report-section="{key}"', 1)[1] \
                   .split("</section>", 1)[0]

    # -- ordem ---------------------------------------------------------
    def test_ordem_das_secoes_e_a_canonica(self):
        self.assertEqual(self._attr(self._html(), "data-report-section"),
                         self.ORDER)

    def test_ordem_dos_grupos_e_resumo_hoje_evolucao_plano_detalhes(self):
        self.assertEqual(self._attr(self._html(), "data-report-group"),
                         self.GROUPS)

    def test_secoes_ausentes_nao_reordenam_as_presentes(self):
        html = self._html(readiness=None, plan_status=None, vo2=None,
                          ftp=None, pmc_rows=[], weeks=[], rows=[])
        sections = self._attr(html, "data-report-section")
        # adherence some: sem estado do plano nao ha o que medir
        self.assertNotIn("adherence", sections)
        self.assertEqual(sections, [key for key in self.ORDER
                                    if key in sections])
        self.assertEqual(sections, ["summary", "readiness", "planned-workout",
                                    "pmc", "weekly-load", "vo2", "ftp",
                                    "activities"])
        self.assertEqual(self._attr(html, "data-report-group"),
                         ["resumo", "hoje", "evolucao", "detalhes"])

    def test_todos_os_periodos_usam_o_mesmo_template(self):
        for period in ("day", "week", "month", "45d", "semester"):
            with self.subTest(period=period):
                html = self._html(title=report.summary_heading(period))
                self.assertEqual(self._attr(html, "data-report-section"),
                                 self.ORDER)
                self.assertEqual(self._attr(html, "data-report-group"),
                                 self.GROUPS)

    def test_titulos_de_resumo_por_periodo(self):
        self.assertEqual(report.summary_heading("day"), "Resumo do dia")
        self.assertEqual(report.summary_heading("week"), "Resumo da semana")
        self.assertEqual(report.summary_heading("month"), "Resumo do mês")
        self.assertEqual(report.summary_heading("45d"), "Resumo de 45 dias")
        self.assertEqual(report.summary_heading("semester"),
                         "Resumo do semestre")
        self.assertEqual(report.summary_heading("custom"),
                         "Resumo personalizado")
        self.assertNotEqual(report.summary_heading("custom"),
                            "Resumo do personalizado")

    def test_custom_titulo_sem_artigo_no_hero(self):
        html = self._html(title=report.summary_heading("custom"))
        hero = html.split('<header class="hero">', 1)[1].split("</header>", 1)[0]
        self.assertIn("Resumo personalizado", hero)
        self.assertNotIn("Resumo do personalizado", html)

    def test_todas_as_secoes_declaram_data_report_section(self):
        html = self._html()
        for key in self.ORDER:
            with self.subTest(section=key):
                self.assertIn(f'data-report-section="{key}"', html)

    # -- determinismo --------------------------------------------------
    def test_mesmo_input_produz_mesmo_html(self):
        def normalize(html):
            return re.sub(r"Gerado em [^<]+", "Gerado em <dia>", html)
        first, second = self._html(), self._html()
        self.assertEqual(normalize(first), normalize(second))
        # a unica diferenca aceita e a data de geracao
        self.assertEqual(len(re.findall(r"Gerado em ", first)), 1)

    def test_atividades_tem_ordem_fixa_e_nao_vem_do_provider(self):
        block = self._block(self._html(), "activities")
        self.assertLess(block.index("2026-09-23"), block.index("2026-09-21"))

    # -- hero / resumo -------------------------------------------------
    def test_hero_nao_repete_kpis(self):
        html = self._html()
        hero = html.split('<header class="hero">', 1)[1].split("</header>", 1)[0]
        self.assertNotIn("hero-chip", html)
        self.assertNotIn("TSS", hero)
        self.assertIn("Relatório do atleta", hero)
        self.assertIn("Resumo da semana", hero)
        self.assertIn("17 set – 23 set 2026", hero)
        # o KPI existe uma unica vez: no RESUMO
        summary = self._block(html, "summary")
        self.assertIn("1h49", summary)
        self.assertIn("99 TSS", summary)

    def test_resumo_ordena_os_kpis_conforme_a_spec(self):
        summary = self._block(self._html(), "summary")
        labels = re.findall(r"<span>([^<]+)</span>", summary)
        self.assertEqual(labels, ["treinos", "tempo", "carga", "distância",
                                  "potência (média / NP)", "FC média",
                                  "elevação"])

    def test_kpi_ausente_vira_traco_e_nao_zero(self):
        agg = summarize([{"name": "x", "day": "2026-09-23", "type": "Ride",
                          "time_s": 600, "distance_m": 0, "elevation_m": 0,
                          "load": 0.0}])
        summary = self._block(self._html(agg=agg, rows=[]), "summary")
        self.assertIn("<b>—</b><span>potência (média / NP)</span>", summary)
        self.assertIn("<b>—</b><span>FC média</span>", summary)

    def test_kpi_de_treinos_pluraliza_por_contagem(self):
        row = {"name": "x", "day": "2026-09-23", "type": "Ride",
               "time_s": 600, "distance_m": 0, "elevation_m": 0,
               "load": 0.0}
        casos = ((0, "treinos"), (1, "treino"), (2, "treinos"))
        for n, rotulo in casos:
            with self.subTest(n=n):
                rows = [dict(row) for _ in range(n)]
                summary = self._block(self._html(agg=summarize(rows),
                                                 rows=rows), "summary")
                self.assertIn(f'<div class="card"><b>{n}</b>'
                              f'<span>{rotulo}</span></div>', summary)

    def test_legenda_da_media_semanal_esta_acentuada(self):
        block = self._block(self._html(), "weekly-load")
        self.assertRegex(block, r">média \d+/sem</text>")
        self.assertNotIn(">media ", block)

    def test_menu_de_temas_nao_desborda_em_320px(self):
        css = self._html().split("<style>", 1)[1].split("</style>", 1)[0]
        self.assertIn("min-width: 340px", css)
        self.assertIn("min-width: 0; max-width: calc(100vw - 32px); "
                      "grid-template-columns: 1fr", css)

    # -- período humano ------------------------------------------------
    def test_periodo_humano_no_hero(self):
        def hero(**overrides):
            html = self._html(**overrides)
            return html.split('<header class="hero">', 1)[1] \
                       .split("</header>", 1)[0]
        self.assertIn("10 abr – 06 out 2026",
                      hero(start=date(2026, 4, 10), end=date(2026, 10, 6)))
        self.assertIn("07 out 2026",
                      hero(start=date(2026, 10, 7), end=date(2026, 10, 7)))
        self.assertIn("30 dez 2025 – 02 jan 2026",
                      hero(start=date(2025, 12, 30), end=date(2026, 1, 2)))
        self.assertNotIn("2026-04-10", hero(start=date(2026, 4, 10),
                                            end=date(2026, 10, 6)))

    # -- TSB / heurística ----------------------------------------------
    def test_estado_do_tsb_identifica_a_heuristica(self):
        html = self._html(pmc_rows=[(date(2026, 9, 23), 100.0, 120.0, -20.0)])
        chips = html.split('class="chips"', 1)[1].split("</div>", 1)[0]
        self.assertIn("Estado: carga recente acima da forma", chips)
        self.assertIn("Heurística Hermes", chips)
        for banned in ("alto risco - descanse", "zona de treino ideal",
                       "fresco - pronto para competir"):
            self.assertNotIn(banned, html)

    # -- HTML válido ----------------------------------------------------
    def test_tabela_nao_aninha_td(self):
        html = self._html()
        self.assertNotIn("<td><td", html)
        self.assertNotIn("</td></td>", html)
        block = self._block(html, "activities")
        self.assertEqual(block.count('<td class="num">'), 6)  # 2 linhas x 3

    # -- VO₂ / FTP ------------------------------------------------------
    def test_vo2_sem_fonte_fica_indisponivel_sem_grafico(self):
        block = self._block(self._html(vo2=None), "vo2")
        self.assertIn("Indisponível", block)
        self.assertIn("Ainda não há dado confiável para exibir este "
                      "indicador.", block)
        self.assertNotIn("<svg", block)

    def test_vo2_com_serie_real_renderiza_o_grafico(self):
        vo2 = {"value": 52.4, "unit": "ml/kg/min", "source": "estimado",
               "date": "2026-05-01",
               "series": [("2025-11-01", 50.1), ("2026-05-01", 52.4)]}
        block = self._block(self._html(vo2=vo2), "vo2")
        self.assertIn("52.4 ml/kg/min", block)
        self.assertIn('role="img"', block)
        self.assertIn("sem interpolação", block)

    def test_ftp_sem_serie_mostra_atual_e_historico_insuficiente(self):
        block = self._block(self._html(), "ftp")
        self.assertIn("182 W", block)
        self.assertIn("Histórico insuficiente para mostrar evolução.", block)
        self.assertNotIn("<svg", block)

    def test_ftp_sem_mediacao_fica_indisponivel(self):
        block = self._block(self._html(ftp=None), "ftp")
        self.assertIn("Indisponível", block)
        self.assertIn("Não há medição de FTP registrada para este atleta.",
                      block)
        self.assertNotIn("<svg", block)

    def test_ftp_com_serie_real_mostra_tendencia_sem_interpolar(self):
        ftp = {"value": 184, "unit": "W", "source": ".env FTP",
               "date": "2026-06-01",
               "series": [("2025-11-01", 176.0), ("2026-02-01", 180.0),
                          ("2026-06-01", 184.0)]}
        block = self._block(self._html(ftp=ftp), "ftp")
        self.assertIn("184 W", block)
        self.assertIn("TENDÊNCIA", block)
        self.assertIn("+8 W desde 2025-11-01 até 2026-06-01", block)
        self.assertIn("Série de 3 medições reais; sem interpolação", block)
        self.assertEqual(block.count("role=\"img\""), 1)
        # as tres mediacoes viram pontos reais, nao curva suavizada
        self.assertEqual(block.count("<circle"), 3)
        d = re.search(r'<path class="sc" d="([^"]+)"', block).group(1)
        self.assertEqual({t for t in d.split() if t.isalpha()}, {"M", "L"})

    # -- escaping -------------------------------------------------------
    def test_escapa_script_nos_indicadores_e_na_serie(self):
        ftp = {"value": 182, "unit": "W",
               "source": "<script>alert(1)</script>",
               "date": "<script>alert(2)</script>",
               "series": [("<script>x</script>", 180.0),
                          ("2026-01-01", 182.0)]}
        vo2 = {"value": 50.0, "unit": "ml/kg/min",
               "source": "<img src=x onerror=alert(3)>", "date": None,
               "series": []}
        html = self._html(ftp=ftp, vo2=vo2)
        self.assertNotIn("<script>alert", html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;script&gt;alert(1)", html)
        self.assertIn("&lt;script&gt;alert(2)", html)
        self.assertIn("&lt;img src=x", html)

    # -- readiness (Prompt 39 preservado) -------------------------------
    def test_readiness_ausente_nao_vira_score_verde(self):
        block = self._block(self._html(readiness=None), "readiness")
        self.assertIn("Sem dados suficientes", block)
        self.assertIn("— <span>/ 1,00</span>", block)
        self.assertNotIn("Verde", block)

    # -- consistência (PLANO) -------------------------------------------
    def test_adherence_com_ocorrencias(self):
        block = self._block(self._html(), "adherence")
        self.assertIn("<strong>2 de 3</strong> sessões concluídas.", block)
        self.assertIn("<b>67%</b>", block)

    def test_adherence_sem_ocorrencias_mostra_branch_proprio(self):
        status = {"today": {"lifecycle_effective": "planned"},
                  "summary": {"done": 0, "missed": 0, "pending": 3},
                  "weeks": [{"week": "2026-W38", "done": 0, "missed": 0,
                             "pending": 3, "pct": None}]}
        block = self._block(self._html(plan_status=status), "adherence")
        self.assertIn("Ainda não há sessões concluídas ou perdidas neste "
                      "período.", block)
        self.assertIn("<b>—</b>", block)
        self.assertIn("A iniciar", block)
        self.assertNotIn("treinos ocorridos foi cumprido", block)
        self.assertNotIn("0 de 0", block)


class WriteTest(unittest.TestCase):
    def test_html_escreve_direto(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resumo.html")
            out = report.write(path, "<h1>oi</h1>")
            self.assertEqual(out, path)
            with open(path, encoding="utf-8") as f:
                self.assertEqual(f.read(), "<h1>oi</h1>")

    def test_pdf_chama_chromium_com_print_to_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resumo.pdf")
            with mock.patch("subprocess.run") as run:
                out = report.write(path, "<h1>oi</h1>")
            self.assertEqual(out, path)
            run.assert_called_once()
            cmd = run.call_args.args[0]
            self.assertEqual(cmd[0], "chromium")
            self.assertIn("--headless", cmd)
            self.assertTrue(any(c.startswith("--print-to-pdf=") and
                                c.endswith("resumo.pdf") for c in cmd))
            self.assertTrue(any(c.startswith("file://") for c in cmd))

    def test_pdf_relanca_erro_do_chromium(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resumo.pdf")
            run = mock.Mock(side_effect=subprocess.CalledProcessError(1, cmd=[]))
            with mock.patch("subprocess.run", run):
                with self.assertRaises(subprocess.CalledProcessError):
                    report.write(path, "<h1>oi</h1>")


class PmcSvgHoverTest(unittest.TestCase):
    """Tooltip tematico do PMC: o SVG embute os dados (`data-pmc`), a
    linha-guia com os pontos por serie (`pmc-guide`), o alvo de mouse
    (`pmc-hit`) e o card (`.tt-card`) que o JS preenche com o tema."""

    ROWS = [
        ("2026-09-01", 10.0, 20.0, -10.0),
        ("2026-09-08", 12.5, 25.0, -12.5),
        ("2026-09-15", 15.0, 30.0, -15.0),
        ("2026-09-22", 17.5, 35.0, -17.5),
    ]

    def _payload(self, svg):
        import json as _json
        import re
        m = re.search(r"data-pmc='([^']*)'", svg)
        self.assertIsNotNone(m, "svg deve embutir data-pmc")
        return _json.loads(m.group(1))

    def test_svg_embute_dados_e_alvo_de_hover(self):
        from src.report import _pmc_svg
        svg = _pmc_svg(self.ROWS)
        self.assertIn('class="pmc-hit"', svg)
        self.assertIn('pointer-events="all"', svg)
        self.assertIn('class="pmc-guide"', svg)
        self.assertIn('class="tt-card"', svg)
        self.assertNotIn("<title>", svg)  # tooltip nativo removido

    def test_payload_cobre_todas_as_series(self):
        from src.report import _pmc_svg
        d = self._payload(_pmc_svg(self.ROWS))
        self.assertEqual(len(d["days"]), 4)
        self.assertEqual(d["days"][-1], "2026-09-22")
        self.assertEqual(d["ctl"], [10.0, 12.5, 15.0, 17.5])
        self.assertEqual(d["atl"], [20.0, 25.0, 30.0, 35.0])
        self.assertEqual(d["tsb"], [-10.0, -12.5, -15.0, -17.5])

    def test_guia_tem_uma_linha_e_tres_pontos(self):
        from src.report import _pmc_svg
        svg = _pmc_svg(self.ROWS)
        guide = svg.split('class="pmc-guide"')[1].split("</g>")[0]
        self.assertEqual(guide.count("<line"), 1)
        self.assertEqual(guide.count("<circle"), 3)
        # um ponto por serie, nas cores do tema
        self.assertIn('class="pmc-dot sc"', guide)
        self.assertIn('class="pmc-dot sa"', guide)
        self.assertIn('class="pmc-dot ss"', guide)

    def test_serie_unica_embute_dados(self):
        from src.report import _pmc_svg
        svg = _pmc_svg([("2026-09-01", 10.0, 20.0, -10.0)])
        d = self._payload(svg)
        self.assertEqual(len(d["days"]), 1)


if __name__ == "__main__":
    unittest.main()
