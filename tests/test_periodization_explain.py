import unittest

from src import periodization
from src.periodization import (PERIODIZATION_INFO, GOAL_AFFINITY,
                               describe, list_models, quote, suggest_for_goal,
                               explain_current)


class QuoteTest(unittest.TestCase):
    def test_valido(self):
        self.assertEqual(quote("polarized"), "polarized")
        self.assertEqual(quote("POLARIZED"), "polarized")

    def test_invalido(self):
        self.assertIsNone(quote(""))
        self.assertIsNone(quote(None))
        self.assertIsNone(quote("nao-existe"))
        self.assertIsNone(quote("_polarized_"))  # underscore nas bordas


class DescribeTest(unittest.TestCase):
    def test_descricao_contem_dados(self):
        desc = describe("pyramidal")
        self.assertIn("pyramidal", desc)
        self.assertIn("Na pratica", desc)
        self.assertIn("Melhor para", desc)

    def test_invalido_none(self):
        self.assertIsNone(describe("xyz"))


class ListModelsTest(unittest.TestCase):
    def test_cinco_modelos(self):
        models = list_models()
        self.assertEqual(len(models), 5)
        for m in models:
            self.assertIn("—", m)


class SuggestForGoalTest(unittest.TestCase):
    def test_ftp_builder_sem_tsb(self):
        top, avoid = suggest_for_goal("ftp-builder")
        self.assertIn("pyramidal", top)
        self.assertIn("block", avoid)

    def test_tsb_baixo_favorece_undulating(self):
        top, _ = suggest_for_goal("ftp-builder", tsb=-28.4)
        self.assertIn("undulating", top)
        self.assertNotIn("linear", top)

    def test_tsb_alto_permite_qualidade(self):
        top, _ = suggest_for_goal("ftp-builder", tsb=15)
        self.assertIn("linear", top)
        self.assertNotIn("undulating", top)

    def test_sem_goal_padrao_sensato(self):
        top, _ = suggest_for_goal(None)
        self.assertTrue(top)

    def test_todos_os_goals_tem_afinidade(self):
        self.assertIn("race", GOAL_AFFINITY)
        for goal, (top, avoid) in GOAL_AFFINITY.items():
            self.assertTrue(top)
            for m in top + avoid:
                self.assertIn(m, PERIODIZATION_INFO)


class ExplainCurrentTest(unittest.TestCase):
    def test_sem_periodization_diz_tsb_governa(self):
        out = explain_current(goal="ftp-builder")
        self.assertIn("TSB governa", out)

    def test_com_periodization_diz_configurado(self):
        out = explain_current(goal="ftp-builder", periodization="undulating")
        self.assertIn("Configurado agora", out)
        self.assertIn("undulating", out)

    def test_sugestao_com_tsb(self):
        out = explain_current(goal="ftp-builder", tsb=-28.4)
        self.assertIn("fadiga", out)


if __name__ == "__main__":
    unittest.main()