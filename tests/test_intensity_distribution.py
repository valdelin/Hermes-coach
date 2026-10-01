import unittest

from src.intensity_distribution import (IntensityDistributionEngine,
                                        IntensityDistributionModel,
                                        IntensityMinutes)


class IntensityDistributionTest(unittest.TestCase):
    def test_soma_minutos_e_percentuais(self):
        report = IntensityDistributionEngine().weekly_report(
            [IntensityMinutes(120, 30, 10), IntensityMinutes(60, 0, 20)])
        self.assertEqual(report.minutes, IntensityMinutes(180, 30, 30))
        self.assertAlmostEqual(sum(report.percentages.values()), 100)

    def test_sessoes_mistas_e_volumes_diferentes(self):
        report = IntensityDistributionEngine().weekly_report(
            [IntensityMinutes(10, 10, 10), IntensityMinutes(200, 0, 0)])
        self.assertGreater(report.percentages["low"], 80)
        self.assertEqual(report.minutes.total, 230)

    def test_modelos_incluem_custom_sem_assumir_8020(self):
        engine = IntensityDistributionEngine(IntensityDistributionModel.CUSTOM,
                                             custom={"low": 50, "moderate": 30, "high": 20})
        self.assertEqual(engine.model, IntensityDistributionModel.CUSTOM)
        self.assertEqual(engine.custom["low"], 50)


if __name__ == "__main__":
    unittest.main()
