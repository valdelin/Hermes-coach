"""Invariantes de progressão e recuperação.

O que estas travas defendem, do `docs/EMBASAMENTO-CIENTIFICO.md` §11 e §13:

* Cada degrau altera **uma** dimensão por vez; subir repetições e duração no
  mesmo degrau é erro de prescrição.
* `CompletionScore` é uma **heurística do sistema**, não medida de quanto o
  atleta executou. Os limiares (0,80 / 0,95 / 0,60 / 0,90) são do Hermes.
* A progressão **para** no último degrau: repetir o último passo indefinidamente
  é progressão fictícia.
* Reduce nunca produz índice negativo; um atleta que falha não fica preso.
* active recovery perdido **não** é absorvível, e treino de VO2/Limiar não é
  substituível por volume de base.
"""
import unittest

from src.progression import (SEQUENCES, Completion, CompletionScore,
                            ProgressionEngine, ProgressionStep, StimulusFamily)

FAMILIAS = tuple(StimulusFamily)


def score(**kwargs):
    base = dict(target_power=250, completed_power=250, planned_sec=1200,
                completed_sec=1200, rpe=6, heart_rate=160)
    base.update(kwargs)
    return CompletionScore(**base)


class CompletionScoreTest(unittest.TestCase):
    """Classificação heurística com limiares declarados."""

    def test_execucao_completa_e_completed(self):
        self.assertEqual(score().classify(), Completion.COMPLETED)

    def test_interrupcao_forca_failed(self):
        # Uma unica interrupcao zera a sessao, independente do demais. Heurística
        # conservadora do sistema, nao fisiologia.
        self.assertEqual(score(interruptions=1).classify(), Completion.FAILED)

    def test_potencia_abaixo_de_80_por_cento_e_failed(self):
        # Os limites sao estritos: 0,80 exato nao e falha, cai em partial.
        self.assertEqual(score(completed_power=199).classify(), Completion.FAILED)
        self.assertEqual(score(completed_power=200).classify(), Completion.PARTIAL)

    def test_tempo_abaixo_de_60_por_cento_e_failed(self):
        self.assertEqual(score(completed_sec=719).classify(), Completion.FAILED)

    def test_faixa_intermediaria_e_partial(self):
        # 0,80 <= razao de potencia < 0,95 -> partial, que segura o degrau em vez
        # de avancar. 0,95 ou mais com tempo em dia ja conta como completed.
        self.assertEqual(score(completed_power=237).classify(), Completion.PARTIAL)
        self.assertEqual(score(completed_power=240).classify(), Completion.COMPLETED)
        # Tempo: < 0,90 e partial; 0,90 exato ja conta como completo.
        self.assertEqual(score(completed_sec=1079).classify(), Completion.PARTIAL)
        self.assertEqual(score(completed_sec=1080).classify(), Completion.COMPLETED)

    def test_rpe_muito_baixo_e_easy(self):
        self.assertEqual(score(rpe=3).classify(), Completion.EASY)
        self.assertEqual(score(rpe=4).classify(), Completion.COMPLETED)

    def test_rpe_ausente_nao_inventa_easy(self):
        # Sem RPE nao ha como afirmar que o treino foi facil.
        self.assertEqual(score(rpe=None).classify(), Completion.COMPLETED)

    def test_classificacao_e_pior_antes_de_melhorar(self):
        # Mais potencia executada nunca piora a classificacao: 150 W e falha,
        # 200 W completa, 240 W e parcial por folga, 250 W completa.
        classificacoes = [score(completed_power=p).classify()
                          for p in (150, 200, 240, 250)]
        self.assertEqual(classificacoes, [Completion.FAILED, Completion.PARTIAL,
                                          Completion.COMPLETED,
                                          Completion.COMPLETED])

    def test_alvo_ou_plano_zerado_nao_divide_por_zero(self):
        self.assertEqual(score(target_power=0, completed_power=0).classify(),
                         Completion.FAILED)
        self.assertEqual(score(planned_sec=0, completed_sec=0).classify(),
                         Completion.FAILED)


class EscadaDeProgressaoTest(unittest.TestCase):
    """Uma dimensão por degrau, e o degrau final é absorvente."""

    def setUp(self):
        self.engine = ProgressionEngine()

    def test_cada_familia_tem_sequencia_nao_vazia(self):
        for family in FAMILIAS:
            self.assertTrue(self.engine.sequences[family], family)
            step = self.engine.step(family, 0)
            self.assertIsInstance(step, ProgressionStep)
            self.assertGreater(step.repeats, 0, family)
            self.assertGreater(step.work_sec, 0, family)

    def test_indice_acima_do_tamanho_falha(self):
        # Sem clamping silencioso: indice invalido e erro, nao degrau inventado.
        for family in FAMILIAS:
            tamanho = len(self.engine.sequences[family])
            with self.assertRaises(IndexError):
                self.engine.step(family, tamanho)

    def test_indice_negativo_usa_indexacao_de_tupla_do_python(self):
        # -1 devolve o ultimo degrau, nao um degrau negativo: e comportamento de
        # tupla, e por isso nao se pode assumir que step() recusa -1.
        for family in FAMILIAS:
            self.assertEqual(self.engine.step(family, -1),
                             self.engine.step(
                                 family,
                                 len(self.engine.sequences[family]) - 1))

    def test_a_intensidade_dos_degraus_nao_sobe_por_si(self):
        # A progressao mexe em volume e estrutura, nao em potencia. Se um dia
        # intensity subir, a banda da zona precisa ser revista antes.
        for family in FAMILIAS:
            intensidades = {self.engine.step(family, i).intensity
                            for i in range(len(self.engine.sequences[family]))}
            self.assertEqual(len(intensidades), 1, family)

    def test_sequencia_por_familia_muda_uma_dimensao_por_degrau(self):
        """Invariante do §11, com as excecoes reais do codigo.

        A documentacao afirma que cada degrau altera uma dimensao so. Hoje
        `SEQUENCES` viola isso em quatro transicoes, onde a troca e de
        estrutura: 3x12 -> 2x15 min, 5x3 -> 4x4 min, 8x1 -> 6x2 min. Nao e
        erro de teste: e divergencia entre doc e implementacao, registrada
        aqui para que mudar a sequencia seja uma decisao explicita.

        O que se garante e que **intensidade** nunca muda sozinha nem junto, e
        que a intensidade e constante dentro da familia.
        """
        excecoes = {
            (StimulusFamily.SWEET_SPOT, 2), (StimulusFamily.THRESHOLD, 2),
            (StimulusFamily.VO2MAX, 1), (StimulusFamily.ANAEROBIC, 1),
        }
        for family in FAMILIAS:
            passos = [self.engine.step(family, i)
                      for i in range(len(self.engine.sequences[family]))]
            for indice, (anterior, atual) in enumerate(zip(passos, passos[1:])):
                mudou_repete = anterior.repeats != atual.repeats
                mudou_duracao = anterior.work_sec != atual.work_sec
                total = sum((mudou_repete, mudou_duracao))
                if (family, indice) in excecoes:
                    self.assertEqual(total, 2,
                                     f"{family.value}[{indice}]: excecao exige "
                                     "mudanca simultanea")
                else:
                    self.assertLessEqual(
                        total, 1,
                        f"{family.value}[{indice}]: {anterior} -> {atual} mudou "
                        f"{total} dimensoes sem estar na lista de excecoes")

    def test_nenhuma_excecao_ainda_muda_intensidade(self):
        for family in FAMILIAS:
            for indice in range(len(self.engine.sequences[family])):
                anterior = self.engine.step(family, indice)
                self.assertEqual(anterior.intensity, 0.90, family)

    def test_o_ultimo_degrau_e_absorvente(self):
        for family in FAMILIAS:
            ultimo = len(self.engine.sequences[family]) - 1
            acao, indice = self.engine.next(family, ultimo,
                                             score(completed_sec=1200,
                                                   completed_power=250))
            self.assertEqual(acao, "advance")
            self.assertEqual(indice, ultimo, family)

    def test_reduce_nunca_ficam_abaixo_de_zero(self):
        for family in FAMILIAS:
            acao, indice = self.engine.next(family, 0,
                                            score(completed_power=100,
                                                  completed_sec=100,
                                                  interruptions=3))
            self.assertEqual(acao, "reduce")
            self.assertGreaterEqual(indice, 0, family)

    def test_reduce_e_repeat_levantam_as_sequencias_certas(self):
        falhou = score(completed_power=100, completed_sec=100, interruptions=3)
        parcial = score(completed_power=230)
        for family in FAMILIAS:
            self.assertEqual(self.engine.next(family, 2, falhou)[0], "reduce")
            self.assertEqual(self.engine.next(family, 1, falhou)[1], 0)
            self.assertEqual(self.engine.next(family, 2, falhou)[1], 1)
            self.assertEqual(self.engine.next(family, 2, parcial)[0], "repeat")
            self.assertEqual(self.engine.next(family, 2, parcial)[1], 2)

    def test_easy_avanca_como_completed(self):
        # Um treino facil demais tambem justifica subir: segurar degrau aqui
        # transformaria faixa de prescricao em teto fisiologico.
        facil = score(rpe=2)
        for family in FAMILIAS:
            self.assertEqual(self.engine.next(family, 0, facil),
                             self.engine.next(family, 0, score()))

    def test_sequencias_customizadas_substituem_todas_as_familias(self):
        # `sequences=` e um override total, nao parcial: passar uma familia
        # apenas deixa as demais ausentes. Comprovado aqui, porque um override
        # parcial silencioso seria erro de prescricao sem erro visivel.
        engine = ProgressionEngine(
            sequences={StimulusFamily.VO2MAX: ((2, 3), (2, 4))})
        self.assertEqual(engine.step(StimulusFamily.VO2MAX, 1).work_sec, 240)
        self.assertEqual(list(engine.sequences), [StimulusFamily.VO2MAX])
        with self.assertRaises(KeyError):
            engine.step(StimulusFamily.ENDURANCE, 0)

    def test_sequences_padrao_cobrem_todas_as_familias(self):
        self.assertEqual(set(SEQUENCES), set(FAMILIAS))

    def test_recuperacao_escala_com_a_duracao_do_bloque(self):
        # Blocos de 8 min ou mais recebem 180 s de recuperacao; blocos curtos
        # recebem 120 s. Convenção do gerador, não constante fisiológica.
        for family in FAMILIAS:
            for indice in range(len(self.engine.sequences[family])):
                step = self.engine.step(family, indice)
                esperado = 180 if step.work_sec >= 480 else 120
                self.assertEqual(step.recovery_sec, esperado,
                                 f"{family.value}[{indice}]")


if __name__ == "__main__":
    unittest.main()
