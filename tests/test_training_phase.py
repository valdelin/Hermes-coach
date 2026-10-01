import unittest

from src.training_phase import (DEFAULT_PHASES, PhaseDefinition, PhaseState,
                                TrainingPhase, TrainingPhaseEngine)


class TrainingPhaseEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = TrainingPhaseEngine()

    def test_cria_todas_as_fases_com_contrato_completo(self):
        self.assertEqual(set(DEFAULT_PHASES), set(TrainingPhase))
        for phase in TrainingPhase:
            definition = self.engine.definition(phase)
            self.assertIsInstance(definition, PhaseDefinition)
            self.assertGreater(definition.duration, 0)
            self.assertTrue(definition.objective)
            self.assertTrue(definition.priority_stimuli)
            self.assertTrue(definition.progression_criteria)
            self.assertTrue(definition.deload_criteria)
            self.assertTrue(definition.exit_criteria)

    def test_permanece_sem_criterio_de_progressao(self):
        state = self.engine.create(TrainingPhase.BUILD)
        self.assertEqual(self.engine.transition(state), PhaseState(TrainingPhase.BUILD, 2))

    def test_transiciona_ao_concluir_duracao_e_criterio(self):
        state = PhaseState(TrainingPhase.BASE, self.engine.definition(TrainingPhase.BASE).duration)
        self.assertEqual(self.engine.transition(state, progression_met=True),
                         PhaseState(TrainingPhase.BUILD))

    def test_deload_vai_para_recovery(self):
        self.assertEqual(self.engine.transition(self.engine.create(TrainingPhase.SPECIFIC),
                                                deload=True),
                         PhaseState(TrainingPhase.RECOVERY))

    def test_recovery_retorna_a_base_ao_concluir(self):
        state = PhaseState(TrainingPhase.RECOVERY,
                           self.engine.definition(TrainingPhase.RECOVERY).duration)
        self.assertEqual(self.engine.transition(state, progression_met=True),
                         PhaseState(TrainingPhase.BASE))

    def test_test_retorna_a_recovery_ao_concluir(self):
        state = PhaseState(TrainingPhase.TEST,
                           self.engine.definition(TrainingPhase.TEST).duration)
        self.assertEqual(self.engine.transition(state, progression_met=True),
                         PhaseState(TrainingPhase.RECOVERY))

    def test_duracoes_sao_configuraveis(self):
        definitions = dict(DEFAULT_PHASES)
        definitions[TrainingPhase.BASE] = PhaseDefinition(
            "base", 2, ("zone2",), (), (0.5, 0.8), "ok", "fadiga", "fim")
        engine = TrainingPhaseEngine(definitions)
        self.assertEqual(engine.definition(TrainingPhase.BASE).duration, 2)


if __name__ == "__main__":
    unittest.main()
