import unittest

from src.training_decision import TrainingDecisionEngine


class TrainingDecisionTest(unittest.TestCase):
    def setUp(self):
        self.engine = TrainingDecisionEngine()
        self.base = dict(goal="ftp-builder", phase="build",
                         adaptations={"aerobic_base": .4, "threshold": .1},
                         recent_load=100, readiness=None, family="threshold",
                         progression_step=2, duration=1800, planned_load=120)

    def test_decisao_expoe_fluxo_e_racional(self):
        decision = self.engine.decide(**self.base)
        self.assertEqual(decision.primary_adaptation, "threshold")
        self.assertEqual(decision.selected_zone, "threshold")
        self.assertIn("prioriza", decision.rationale)

    def test_seguranca_reduz_dose_por_carga(self):
        decision = self.engine.decide(**{**self.base, "recent_load": 200})
        self.assertEqual(decision.readiness_modifier, "recovery")
        self.assertEqual(decision.selected_zone, "zone2")


if __name__ == "__main__":
    unittest.main()
