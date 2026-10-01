import unittest

from src.progression import Completion, CompletionScore, ProgressionEngine, StimulusFamily


class ProgressionEngineTest(unittest.TestCase):
    def score(self, **kwargs):
        values = dict(target_power=200, completed_power=200, planned_sec=1800,
                      completed_sec=1800, rpe=6, heart_rate=160)
        values.update(kwargs)
        return CompletionScore(**values)

    def test_sequencias_exemplificadas(self):
        engine = ProgressionEngine()
        self.assertEqual(engine.step(StimulusFamily.SWEET_SPOT, 0).work_sec, 8 * 60)
        self.assertEqual(engine.step(StimulusFamily.THRESHOLD, 3).repeats, 2)
        self.assertEqual(engine.step(StimulusFamily.VO2MAX, 2).work_sec, 4 * 60)

    def test_classifica_completion_score(self):
        self.assertEqual(self.score().classify(), Completion.COMPLETED)
        self.assertEqual(self.score(rpe=3).classify(), Completion.EASY)
        self.assertEqual(self.score(completed_sec=1200).classify(), Completion.PARTIAL)
        self.assertEqual(self.score(interruptions=1).classify(), Completion.FAILED)

    def test_so_progride_apos_sucesso(self):
        engine = ProgressionEngine()
        family = StimulusFamily.SWEET_SPOT
        self.assertEqual(engine.next(family, 1, self.score()), ("advance", 2))
        self.assertEqual(engine.next(family, 1, self.score(completed_sec=1200)), ("repeat", 1))
        self.assertEqual(engine.next(family, 1, self.score(interruptions=1)), ("reduce", 0))


if __name__ == "__main__":
    unittest.main()
