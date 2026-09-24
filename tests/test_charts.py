"""Testes dos graficos em texto do CLI (charts.py).

Regras: stdlib-only, sem rede, deterministico. Cobrem os 4 helpers publicos:
sparkline, pmc_chart, weekly_load e load_chart.
"""

import unittest
from datetime import date

from src import charts


class SparklineTest(unittest.TestCase):
    def test_vazio_retorna_vazio(self):
        self.assertEqual(charts.sparkline([]), "")

    def test_serie_constante_usa_bloco_cheio(self):
        out = charts.sparkline([5, 5, 5])
        self.assertEqual(out, charts.BLOCKS[-1] * 3)

    def test_ascendente_usa_toda_a_escala(self):
        out = charts.sparkline([0, 100])
        self.assertEqual(len(out), 2)
        self.assertEqual(out[0], charts.BLOCKS[0])
        self.assertEqual(out[-1], charts.BLOCKS[-1])

    def test_escala_global_comparada(self):
        # zero..10: 5 fica no meio (indice 4 de 8), 10 no topo
        out = charts.sparkline([5, 10], vmin=0, vmax=10)
        self.assertEqual(out[0], charts.BLOCKS[4])
        self.assertEqual(out[1], charts.BLOCKS[-1])


class PmcChartTest(unittest.TestCase):
    DAYS = [date(2026, 9, 1) + __import__("datetime").timedelta(days=i)
            for i in range(5)]
    ROWS = [(d, float(i + 1), float(i * 2), float(i + 1 - i * 2))
            for i, d in enumerate(DAYS)]

    def test_vazio_retorna_vazio(self):
        self.assertEqual(charts.pmc_chart([]), [])

    def test_emite_series_e_escala(self):
        out = charts.pmc_chart(self.ROWS)
        self.assertEqual(len(out), 4)
        self.assertTrue(out[0].startswith("CTL"))
        self.assertTrue(out[1].startswith("ATL"))
        self.assertTrue(out[2].startswith("TSB"))
        self.assertIn("escala", out[3])
        self.assertIn("2026-09-01 a 2026-09-05", out[3])
        self.assertIn(f"CTL {self.ROWS[-1][1]:6.1f}", out[0])
        self.assertIn(f"TSB {self.ROWS[-1][3]:+6.1f}", out[2])

    def test_resample_para_largura(self):
        out = charts.pmc_chart(self.ROWS, width=4)
        self.assertEqual(len(out[0].split("  ")[-1]), 4)
        self.assertEqual(len(out[1].split("  ")[-1]), 4)
        self.assertEqual(len(out[2].split("  ")[-1]), 4)

    def test_tsb_abaixo_do_ctl_compartilha_escala(self):
        # tsb nunca deve passar de ctl (decaimento lento), mas a escala
        # conjunta garante que as 3 linhas sejam comparaveis entre si.
        out = charts.pmc_chart(self.ROWS)
        lo = min(min(r[1] for r in self.ROWS), min(r[2] for r in self.ROWS),
                 min(r[3] for r in self.ROWS))
        hi = max(max(r[1] for r in self.ROWS), max(r[2] for r in self.ROWS),
                 max(r[3] for r in self.ROWS))
        self.assertIn(f"escala {lo:.0f}..{hi:.0f}", out[3])


class WeeklyLoadTest(unittest.TestCase):
    def _row(self, day, load):
        return {"day": day.isoformat(), "_day": day, "load": load}

    def test_agrupa_por_semana_iso_e_ordena(self):
        # 16/09/2026 quarta (W38); 21/09 segunda e 22/09 terca (ambas W39).
        rows = [
            self._row(date(2026, 9, 16), 40),
            self._row(date(2026, 9, 22), 50),
            self._row(date(2026, 9, 21), 30),
        ]
        weeks = charts.weekly_load(rows)
        self.assertEqual([(w, tss) for w, tss in weeks],
                         [(date(2026, 9, 14), 40.0),   # W38 comeca seg 14/09
                          (date(2026, 9, 21), 80.0)])  # W39: 30 + 50

    def test_fallback_para_chave_day_sem_underline(self):
        rows = [{"day": "2026-09-22", "load": 10}]
        self.assertEqual(charts.weekly_load(rows), [(date(2026, 9, 21), 10.0)])

    def test_sem_treinos_retorna_vazio(self):
        self.assertEqual(charts.weekly_load([]), [])


class LoadChartTest(unittest.TestCase):
    def test_vazio_retorna_vazio(self):
        self.assertEqual(charts.load_chart([]), [])

    def test_barras_e_legenda(self):
        out = charts.load_chart([(date(2026, 9, 14), 30.0),
                                 (date(2026, 9, 21), 90.0)])
        # altura 6: 30 -> 2 blocos, 90 -> 6 blocos
        self.assertEqual(out[0], " " + charts.BAR)             # nivel 6 (so o 90)
        self.assertEqual(out[4], charts.BAR * 2)             # nivel 2 (30 + 90)
        row_labels = out[-2]
        self.assertEqual(row_labels, "30 90")
        self.assertIn("TSS/semana", out[-1])
        self.assertIn("peak 90", out[-1])
        self.assertIn("media 60/sem", out[-1])

    def test_zero_ou_um_item_vai_sempre_para_o_topo(self):
        out = charts.load_chart([(date(2026, 9, 21), 0.0)])
        self.assertEqual(out[-2], "0")
        self.assertIn("TSS/semana", out[-1])
        self.assertIn("media 0/sem", out[-1])


if __name__ == "__main__":
    unittest.main()