import unittest

from src.adaptation import AdaptationState


class AdaptationStateTest(unittest.TestCase):
    def test_atualiza_por_estimulo(self):
        state = AdaptationState().apply("threshold")
        self.assertEqual(state.threshold, .10)
        self.assertEqual(state.muscular_endurance, .04)

    def test_decaimento_e_saturacao(self):
        state = AdaptationState(threshold=.95)
        self.assertEqual(state.apply("threshold").threshold, 1.0)
        self.assertLess(state.decay(10).threshold, state.threshold)

    def test_sessao_neutra_e_combinacao(self):
        state = AdaptationState()
        self.assertEqual(state.apply("rest"), state)
        combined = state.apply("zone2").apply("vo2max")
        self.assertGreater(combined.aerobic_base, 0)
        self.assertGreater(combined.vo2max, 0)


if __name__ == "__main__":
    unittest.main()
