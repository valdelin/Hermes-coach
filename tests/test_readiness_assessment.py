import unittest

from src.readiness_assessment import ReadinessAssessment, ReadinessLevel


class ReadinessAssessmentTest(unittest.TestCase):
    def test_verde_e_confidence(self):
        assessment = ReadinessAssessment(.9, .8, .9, .8, .8, None, .9)
        self.assertEqual(assessment.level(), ReadinessLevel.GREEN)
        self.assertLess(assessment.confidence, 1)

    def test_sinal_isolado_nao_cancela_sessao(self):
        assessment = ReadinessAssessment(.3, .9, .9, .9, .9, .9, .9)
        self.assertEqual(assessment.level(), ReadinessLevel.YELLOW)
        self.assertNotIn("recovery", assessment.adjustments())

    def test_multiplos_sinais_ruins_ajustam_recuperacao(self):
        assessment = ReadinessAssessment(.2, .2, .2, .6, .6, None, .6)
        self.assertEqual(assessment.level(), ReadinessLevel.RED)
        self.assertIn("recovery", assessment.adjustments())


if __name__ == "__main__":
    unittest.main()
