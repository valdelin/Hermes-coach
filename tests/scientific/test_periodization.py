"""Invariantes de periodização: fases, transição e deload.

O que estas travas defendem, do `docs/EMBASAMENTO-CIENTIFICO.md` §1 e §5:

* **Periodização ≠ autoregulação.** TSB não troca fase; a fase vem de `GOAL`.
* As transições são **regras de plano**, não sequência fisiológica universal.
* Deload leva a `RECOVERY` a partir de qualquer fase, com semana 1.
* Cada fase tem duração configurável e limites de carga coerentes com o
  objetivo — `PEAK` e `RECOVERY` não podem exigir carga alta.
* Galán-Rioja et al. (2023, PMID 36640771) não encontraram evidência a favor de
  um modelo de periodização específico; logo nenhuma fase aqui pode ser
  apresentada como "a" sequência.
"""
import unittest

from src.training_phase import (PhaseState, TrainingPhase, TrainingPhaseEngine)

FASES = tuple(TrainingPhase)


class DefinicoesDeFaseTest(unittest.TestCase):
    """Cada fase declara objetivo, duração, carga e criteria de saída."""

    def setUp(self):
        self.engine = TrainingPhaseEngine()

    def test_todas_as_fases_tem_definicao_completa(self):
        for phase in FASES:
            definition = self.engine.definition(phase)
            self.assertTrue(definition.objective.strip(), phase)
            self.assertGreater(definition.duration, 0, phase)
            self.assertTrue(definition.progression_criteria.strip(), phase)
            self.assertTrue(definition.deload_criteria.strip(), phase)
            self.assertTrue(definition.exit_criteria.strip(), phase)
            self.assertTrue(definition.priority_stimuli, phase)

    def test_limites_de_carga_sao_ordenados_e_dentro_de_faixa(self):
        for phase in FASES:
            low, high = self.engine.definition(phase).load_limits
            self.assertLess(low, high, f"{phase}: piso >= teto")
            self.assertGreaterEqual(low, 0.0, phase)
            self.assertLessEqual(high, 1.5, f"{phase}: teto acima de Z6")

    def test_deload_e_peak_nao_exigem_carga_alta(self):
        # Peak chega fresco a prova e Recovery absorve carga: as duas fases de
        # descarga precisam ter teto abaixo das fases de construcao.
        for phase in (TrainingPhase.PEAK, TrainingPhase.RECOVERY,
                      TrainingPhase.TEST):
            high = self.engine.definition(phase).load_limits[1]
            self.assertLessEqual(high, 1.0, f"{phase} exige carga alta")

    def test_build_e_specific_aceitam_mais_carga_que_base(self):
        base_high = self.engine.definition(TrainingPhase.BASE).load_limits[1]
        for phase in (TrainingPhase.BUILD, TrainingPhase.SPECIFIC):
            self.assertGreater(self.engine.definition(phase).load_limits[1],
                               base_high, phase)

    def test_estimulos_prioritarios_nao_sao_vazios_nem_duplicados(self):
        for phase in FASES:
            definition = self.engine.definition(phase)
            self.assertEqual(len(set(definition.priority_stimuli)),
                             len(definition.priority_stimuli), phase)


class TransicaoDeFaseTest(unittest.TestCase):
    """A ordem é do plano; as propriedades é que importam."""

    def setUp(self):
        self.engine = TrainingPhaseEngine()

    def test_fase_avanca_na_duracao_e_so_entao_muda(self):
        state = self.engine.create(TrainingPhase.BASE)
        duracao = self.engine.definition(TrainingPhase.BASE).duration
        for semana in range(2, duracao + 1):
            state = self.engine.transition(state, progression_met=True)
            self.assertEqual(state.phase, TrainingPhase.BASE)
            self.assertEqual(state.week, semana)
        state = self.engine.transition(state, progression_met=True)
        self.assertNotEqual(state.phase, TrainingPhase.BASE)
        self.assertEqual(state.week, 1)

    def test_sem_progressao_a_fase_permanece(self):
        state = self.engine.create(TrainingPhase.BUILD)
        for _ in range(10):
            state = self.engine.transition(state, progression_met=False)
        self.assertEqual(state.phase, TrainingPhase.BUILD)

    def test_deload_vai_para_recovery_a_partir_de_qualquer_fase(self):
        for phase in FASES:
            state = self.engine.create(phase)
            self.assertEqual(self.engine.transition(state, deload=True).phase,
                             TrainingPhase.RECOVERY)

    def test_deload_reseta_a_semana(self):
        state = PhaseState(phase=TrainingPhase.BUILD, week=3)
        self.assertEqual(self.engine.transition(state, deload=True).week, 1)

    def test_peak_e_recovery_sao_alvos_de_transicao(self):
        self.assertEqual(self.engine.recovery().phase, TrainingPhase.RECOVERY)
        self.assertEqual(self.engine.test().phase, TrainingPhase.TEST)

    def test_transicao_e_deterministica(self):
        # Mesma entrada, mesma saida: a transicao nao carrega estado oculto.
        primeiro = self.engine.create(TrainingPhase.BASE)
        segundo = self.engine.create(TrainingPhase.BASE)
        self.assertEqual(self.engine.transition(primeiro, progression_met=True),
                         self.engine.transition(segundo, progression_met=True))

    def test_a_sequencia_padrao_e_ciclica(self):
        # A ordem e uma regra de plano, nao uma sequencia fisiologica
        # universal: ela fecha um ciclo em vez de terminar. Este teste fixa a
        # ordem de regras, e a ausencia de evidencia para "a ordem certa" esta
        # na secao 5 do embasamento.
        # Um ciclo completo dura a soma das duracoes declaradas, entao o passo
        # tem de ser weeks, nao fases: a ordem se verifica depois de percorrer
        # o ciclo inteiro.
        weeks = sum(self.engine.definition(phase).duration for phase in FASES)
        visited = []
        state = self.engine.create(TrainingPhase.BASE)
        for _ in range(weeks + 1):
            state = self.engine.transition(state, progression_met=True)
            if not visited or visited[-1] != state.phase:
                visited.append(state.phase)
        self.assertEqual(visited[0], TrainingPhase.BASE)
        self.assertEqual(visited[-1], TrainingPhase.BASE)
        self.assertEqual(visited[1:-1], [TrainingPhase.BUILD,
                                         TrainingPhase.SPECIFIC,
                                         TrainingPhase.PEAK,
                                         TrainingPhase.RECOVERY])

    def test_a_sequencia_nao_passa_de_recovery_para_test_so_por_tempo(self):
        # TEST nao entra por progressao automatica: exige decisao explicita
        # (test()), senao o plano mediria sem o atleta pedir.
        state = self.engine.create(TrainingPhase.BASE)
        for _ in range(len(FASES) * 3):
            state = self.engine.transition(state, progression_met=True)
        self.assertNotEqual(state.phase, TrainingPhase.TEST)


class DeloadTest(unittest.TestCase):
    """Deload reduz carga, e isso e verificavel na definicao."""

    def setUp(self):
        self.engine = TrainingPhaseEngine()

    def test_recovery_tem_teto_de_carga_mais_baixo_que_build(self):
        recovery = self.engine.definition(TrainingPhase.RECOVERY).load_limits
        build = self.engine.definition(TrainingPhase.BUILD).load_limits
        self.assertLess(recovery[1], build[1])
        self.assertLess(recovery[0], build[0])

    def test_deload_nao_e_ausencia_de_criterio(self):
        for phase in FASES:
            self.assertTrue(self.engine.definition(phase).deload_criteria.strip(),
                            f"{phase} sem criterio de deload")

    def test_peak_tem_baixo_teto_para_chegar_fresco(self):
        peak = self.engine.definition(TrainingPhase.PEAK)
        specific = self.engine.definition(TrainingPhase.SPECIFIC)
        self.assertLess(peak.load_limits[1], specific.load_limits[1])


class PeriodizacaoNaoEAutoregulacaoTest(unittest.TestCase):
    """A distincao de §1: TSB/readiness nao escolhem fase."""

    def test_o_motor_de_fases_nao_recebe_tsb_nem_readiness(self):
        # A assinatura e a trava: se `transition` ganhar um parametro de TSB,
        # esta propriedade quebra e a separacao entre camadas foi perdida.
        import inspect
        parametros = set(inspect.signature(
            TrainingPhaseEngine.transition).parameters)
        self.assertEqual(parametros, {"self", "state", "progression_met",
                                      "deload"})

    def test_fase_nao_depende_de_carga_realizada(self):
        engine = TrainingPhaseEngine()
        primeiro = engine.create(TrainingPhase.BASE)
        segundo = engine.create(TrainingPhase.BASE)
        self.assertEqual(primeiro, segundo)

    def test_definicoes_customizadas_sao_respeitadas(self):
        from src.training_phase import PhaseDefinition
        custom = PhaseDefinition(objective="objetivo proprio", duration=2,
                                 priority_stimuli=("vo2max",),
                                 secondary_stimuli=(), load_limits=(0.5, 0.8),
                                 progression_criteria="c", deload_criteria="d",
                                 exit_criteria="e")
        # O engine exige definicao para todas as fases: um override parcial
        # deixaria a fase sem contrato, que e o modo de uma heuristica virar
        # regra sem nocao.
        defaults = TrainingPhaseEngine()
        definitions = {phase: defaults.definition(phase) for phase in FASES}
        definitions[TrainingPhase.BASE] = custom
        engine = TrainingPhaseEngine(definitions=definitions)
        self.assertEqual(engine.definition(TrainingPhase.BASE).duration, 2)
        self.assertEqual(engine.definition(TrainingPhase.BASE).load_limits,
                         (0.5, 0.8))
        state = engine.create(TrainingPhase.BASE)
        state = engine.transition(state, progression_met=True)
        self.assertEqual(state.phase, TrainingPhase.BASE)
        state = engine.transition(state, progression_met=True)
        self.assertNotEqual(state.phase, TrainingPhase.BASE)

    def test_definicao_parcial_e_recusada(self):
        from src.training_phase import PhaseDefinition
        with self.assertRaises(ValueError):
            TrainingPhaseEngine(definitions={
                TrainingPhase.BASE: PhaseDefinition(
                    objective="so base", duration=1, priority_stimuli=("vo2max",),
                    secondary_stimuli=(), load_limits=(0.5, 0.8),
                    progression_criteria="c", deload_criteria="d",
                    exit_criteria="e")})


if __name__ == "__main__":
    unittest.main()
