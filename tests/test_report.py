"""Testes da exportacao do resumo (report.py): HTML com SVG e PDF via
chromium. Sem rede; o chromium e mockado (so verificamos o comando).
"""

import os
import subprocess
import unittest
import tempfile
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
        self.assertEqual(html.count(' role="img"'), 2)  # PMC + carga (o icone do menu nao conta)
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
        # estado atual do atleta (fresco, TSB +15)
        self.assertIn("Estado: fresco - pronto para competir", html)
        # desc com explicacao + referencias
        self.assertIn("Science2Sport", html)
        self.assertIn("Joe Friel", html)

    def test_estado_reflete_zona_de_risco(self):
        pmc = [(date(2026, 9, 23), 100.0, 120.0, -20.0)]
        agg = summarize(_rows())
        html = report.render_summary_html(
            title="R", start=date(2026, 9, 23), end=date(2026, 9, 23),
            agg=agg, rows=_rows(), pmc_rows=pmc, weeks=[])
        self.assertIn("Estado: alto risco - descanse", html)
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
        self.assertIn("Sem historico de carga", html)

    def test_sem_treinos_nao_quebra(self):
        agg = summarize([])
        html = report.render_summary_html(
            title="Resumo dia", start=date(2026, 9, 23), end=date(2026, 9, 23),
            agg=agg, rows=[], pmc_rows=[], weeks=[])
        self.assertIn("0", html)
        self.assertEqual(html.count(' role="img"'), 0)


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


if __name__ == "__main__":
    unittest.main()