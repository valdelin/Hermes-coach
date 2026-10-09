import random
import unittest

from src.readiness_assessment import ReadinessAssessment, ReadinessLevel


AXES = (
    "hrv_score",
    "rhr_score",
    "sleep_score",
    "subjective_fatigue_score",
    "recent_load_score",
    "performance_score",
    "consistency_score",
)


def assessment(hrv=None, rhr=None, sleep=None, fatigue=None, load=None,
               performance=None, consistency=None):
    """Constroi uma avaliacao sintetica com os sete eixos reais."""
    return ReadinessAssessment(
        hrv_score=hrv,
        rhr_score=rhr,
        sleep_score=sleep,
        subjective_fatigue_score=fatigue,
        recent_load_score=load,
        performance_score=performance,
        consistency_score=consistency,
    )


def expected_average(values):
    """Oracle independente: None e ausencia, zero e valor observado."""
    present = [value for value in values if value is not None]
    return sum(present) / len(present) if present else None


def expected_level(values):
    """Oracle de regressao do contrato atual, nao uma nova regra de readiness."""
    average = expected_average(values)
    if average is None:
        return ReadinessLevel.YELLOW
    poor_signals = sum(value < .4 for value in values if value is not None)
    if poor_signals >= 3 and average < .5:
        return ReadinessLevel.RED
    if poor_signals or average < .7:
        return ReadinessLevel.YELLOW
    return ReadinessLevel.GREEN


def from_values(values):
    return ReadinessAssessment(**dict(zip(AXES, values)))


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

    def test_green_with_all_seven_available(self):
        avaliacao = assessment(.8, .8, .8, .8, .8, .8, .8)
        self.assertAlmostEqual(avaliacao.overall_readiness, .8)
        self.assertEqual(avaliacao.level(), ReadinessLevel.GREEN)

    def test_green_with_different_favorable_values(self):
        values = (.90, .75, .80, .85, .70, .78, .82)
        avaliacao = from_values(values)
        self.assertAlmostEqual(avaliacao.overall_readiness,
                               expected_average(values))
        self.assertEqual(avaliacao.level(), ReadinessLevel.GREEN)

    def test_single_low_axis_yields_yellow(self):
        values = (.2, .8, .8, .8, .8, .8, .8)
        avaliacao = from_values(values)
        self.assertAlmostEqual(avaliacao.overall_readiness,
                               expected_average(values))
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)
        self.assertNotEqual(avaliacao.level(), ReadinessLevel.RED)

    def test_average_below_point_seven_yields_yellow_without_poor_axis(self):
        values = (.69,) * 7
        avaliacao = from_values(values)
        self.assertLess(avaliacao.overall_readiness, .7)
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)

    def test_three_low_axes_and_low_mean_yield_red(self):
        values = (.2, .2, .2, .6, .6, .6, .6)
        avaliacao = from_values(values)
        self.assertLess(avaliacao.overall_readiness, .5)
        self.assertEqual(avaliacao.level(), ReadinessLevel.RED)

    def test_three_low_axes_with_mean_at_least_point_five_yield_yellow(self):
        values = (.3, .3, .3, .9, .9, .4, .4)
        avaliacao = from_values(values)
        self.assertAlmostEqual(avaliacao.overall_readiness, .5)
        self.assertGreaterEqual(avaliacao.overall_readiness, .5)
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)

    def test_level_boundaries_are_strict(self):
        with self.subTest(boundary="poor signal at 0.4"):
            values = (.4, .75, .75, .75, .75, .75, .75)
            avaliacao = from_values(values)
            self.assertAlmostEqual(avaliacao.overall_readiness, .7)
            self.assertEqual(avaliacao.level(), ReadinessLevel.GREEN)

        with self.subTest(boundary="red mean at 0.5"):
            values = (.3, .3, .3, .9, .9, .4, .4)
            avaliacao = from_values(values)
            self.assertAlmostEqual(avaliacao.overall_readiness, .5)
            self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)

        with self.subTest(boundary="yellow mean at 0.7"):
            values = (.7,) * 7
            avaliacao = from_values(values)
            self.assertAlmostEqual(avaliacao.overall_readiness, .7)
            self.assertEqual(avaliacao.level(), ReadinessLevel.GREEN)

    def test_none_axes_are_excluded_from_average(self):
        cases = (
            ((.8, .6, .4, None, None, None, None), .6),
            ((None, None, None, None, None, .8, None), .8),
            ((.8, .7, .6, .5, .4, .3, None), .55),
        )
        for values, expected in cases:
            with self.subTest(values=values):
                avaliacao = from_values(values)
                self.assertAlmostEqual(avaliacao.overall_readiness, expected)
                self.assertEqual(avaliacao.level(), expected_level(values))

    def test_all_none_has_no_average_and_is_yellow(self):
        avaliacao = assessment()
        self.assertIsNone(avaliacao.overall_readiness)
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)

    def test_zero_is_observed_not_missing(self):
        values = (0.0, .8, .8, .8, .8, .8, .8)
        avaliacao = from_values(values)
        self.assertAlmostEqual(avaliacao.overall_readiness,
                               expected_average(values))
        self.assertAlmostEqual(avaliacao.confidence, 1.0)
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)

    def test_all_seven_axes_participate_in_average(self):
        baseline = from_values((.8,) * 7)
        for axis in AXES[3:]:
            with self.subTest(axis=axis):
                values = dict.fromkeys(AXES, .8)
                values[axis] = .2
                changed = ReadinessAssessment(**values)
                self.assertNotEqual(changed.overall_readiness,
                                    baseline.overall_readiness)
                self.assertAlmostEqual(changed.overall_readiness,
                                       (6 * .8 + .2) / 7)

    def test_seeded_seven_axis_scenarios_match_contract(self):
        seed = 20261006
        rng = random.Random(seed)
        boundary_values = (.0, .2, .39, .4, .41, .49, .5, .51,
                           .69, .7, .71, .8, 1.0)
        counts = {level: 0 for level in ReadinessLevel}

        for index in range(1_000):
            values = tuple(
                rng.choice(boundary_values) if rng.randrange(4) == 0
                else rng.random()
                for _ in AXES
            )
            self._assert_matches_contract(values, seed, index)
            counts[expected_level(values)] += 1

        for level in ReadinessLevel:
            self.assertGreater(counts[level], 0,
                               f"seed={seed} nao gerou {level.value}")

    def test_seeded_missing_axis_scenarios_match_contract(self):
        seed = 20261007
        rng = random.Random(seed)
        boundary_values = (.0, .2, .39, .4, .41, .49, .5, .51,
                           .69, .7, .71, .8, 1.0)
        counts = {level: 0 for level in ReadinessLevel}

        for index in range(500):
            values = tuple(
                None if rng.randrange(4) == 0
                else rng.choice(boundary_values)
                for _ in AXES
            )
            self._assert_matches_contract(values, seed, index)
            counts[expected_level(values)] += 1

        for level in ReadinessLevel:
            self.assertGreater(counts[level], 0,
                               f"seed={seed} nao gerou {level.value}")

    def _assert_matches_contract(self, values, seed, index):
        avaliacao = from_values(values)
        expected_avg = expected_average(values)
        expected = expected_level(values)
        diagnostic = (f"seed={seed}; index={index}; values={values}; "
                      f"expected_average={expected_avg}; "
                      f"actual_average={avaliacao.overall_readiness}; "
                      f"expected_level={expected.value}; "
                      f"actual_level={avaliacao.level().value}")
        if expected_avg is None:
            self.assertIsNone(avaliacao.overall_readiness, diagnostic)
        else:
            self.assertAlmostEqual(avaliacao.overall_readiness, expected_avg,
                                   msg=diagnostic)
        self.assertEqual(avaliacao.level(), expected, diagnostic)


if __name__ == "__main__":
    unittest.main()
