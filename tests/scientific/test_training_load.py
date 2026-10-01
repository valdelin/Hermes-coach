"""Propriedades de Training Load: TSS, CTL, ATL e TSB.

O que estas travas defendem, do `docs/EMBASAMENTO-CIENTIFICO.md` §7 e §8:

* TSS é **metodologia de indústria**, e a fórmula é `horas x IF² x 100`.
* Sem NP ou FTP válido, a carga é `None` — o motor **não fabrica** NP a partir
  de potência média, duração ou sessão planejada.
* NP é desconhecida em segmentos de 30 s ou menos.
* CTL usa tc de 42 dias, ATL 7 dias; TSB = CTL − ATL.
* Uma EWMA nunca ultrapassa o próprio valor de entrada: é suavização, não
  amplificação.
"""
import math
import unittest

from src.impulse_response import (MIN_NORMALIZED_POWER_DURATION_SEC,
                                  ImpulseResponseEngine, power_training_load)

HORA = 3600


class TssFormulaTest(unittest.TestCase):
    """TSS = horas x (NP/FTP)^2 x 100."""

    def test_corresponde_a_formula_declarada(self):
        for duration, np, ftp in ((HORA, 200, 250), (2 * HORA, 150, 250),
                                  (HORA, 250, 250), (90 * 60, 180, 200)):
            horas = duration / HORA
            esperado = horas * (np / ftp) ** 2 * 100
            self.assertAlmostEqual(power_training_load(duration, np, ftp),
                                   esperado, places=6)

    def test_e_quadratico_na_intensidade(self):
        # IF^2: dobrar a intensidade quadruplica a carga. E' a propriedade que
        # faz workload pesado custar caro — nao e escolha de implementacao.
        base = power_training_load(HORA, 100, 250)
        dobro = power_training_load(HORA, 200, 250)
        self.assertAlmostEqual(dobro, base * 4, places=6)

    def test_e_invariante_a_escala_de_ftp(self):
        # Mesma relacao de intensidade, FTP diferente: mesma carga.
        self.assertAlmostEqual(power_training_load(HORA, 200, 250),
                               power_training_load(HORA, 300, 375), places=6)

    def test_carga_a_um_ano_de_1_hora_a_100_ftp(self):
        # Trava de contrato: 1h a 100% FTP = 100 TSS, por construcao.
        self.assertAlmostEqual(power_training_load(HORA, 100, 100), 100.0,
                               places=6)

    def test_carga_e_linear_na_duracao(self):
        uma = power_training_load(HORA, 200, 250)
        duas = power_training_load(2 * HORA, 200, 250)
        self.assertAlmostEqual(duas, 2 * uma, places=6)

    def test_nunca_e_negativa(self):
        for duration in (HORA, 2 * HORA, 600):
            for np in (10, 100, 400):
                value = power_training_load(duration, np, 250)
                self.assertGreaterEqual(value, 0.0)


class TssNaoInventaTest(unittest.TestCase):
    """Ausencia de dado vira `None`, nunca estimativa silenciosa."""

    def test_sem_np_ou_sem_ftp_desconhecido(self):
        self.assertIsNone(power_training_load(HORA, None, 250))
        self.assertIsNone(power_training_load(HORA, 200, None))
        self.assertIsNone(power_training_load(HORA, 200, 0))
        self.assertIsNone(power_training_load(HORA, 200, -10))

    def test_segmento_curto_da_30s_ou_menos_e_desconhecido(self):
        # A razao do guardrail: NP depende da janela analisada, e em 30 s ela
        # nao informa. O motor prefere desconhecer a estimar.
        self.assertEqual(MIN_NORMALIZED_POWER_DURATION_SEC, 30)
        for duration in (1, 10, 29, 30):
            self.assertIsNone(power_training_load(duration, 300, 250),
                              f"duração {duration}s deveria ser desconhecida")
        self.assertIsNotNone(power_training_load(31, 300, 250))

    def test_duracao_ou_potencia_zero_depende_do_contrato_de_potencia(self):
        # Com NP/FTP válidos, zero é zero. Sem eles, continua desconhecido.
        self.assertEqual(power_training_load(0, 200, 250), 0.0)
        self.assertEqual(power_training_load(HORA, 0, 250), 0.0)
        self.assertIsNone(power_training_load(0, None, 250))
        self.assertIsNone(power_training_load(HORA, 200, 0))

    def test_treino_planejado_nao_e_carga_executada(self):
        # estimated_tss vive em outro campo; power_training_load só responde
        # a NP observada. Um plano de 2h a 90% FTP não pode virar carga
        # executada sem NP.
        self.assertIsNone(power_training_load(2 * HORA, None, 250))


class CtlAtlTsbTest(unittest.TestCase):
    """EWMA 42/7: suavização, não amplificação."""

    def setUp(self):
        self.engine = ImpulseResponseEngine()

    def test_constantes_de_tempo_do_modelo(self):
        self.assertEqual(self.engine.tc_ctl, 42)
        self.assertEqual(self.engine.tc_atl, 7)

    def test_tsb_e_a_diferenca_entre_ctl_e_atl(self):
        metrics = self.engine.compute_metrics([80] * 30)
        self.assertAlmostEqual(metrics["tsb_form"],
                               metrics["ctl_fitness"] - metrics["atl_fatigue"],
                               places=6)

    def test_ewma_nunca_ultrapassa_a_entrada(self):
        # Propriedade central: com serie constante, CTL/ATL tendem ao valor e
        # nunca o excedem. Se isto quebrar, o modelo amplifica carga.
        for value in (10, 50, 100, 300):
            metrics = self.engine.compute_metrics([value] * 200)
            self.assertLessEqual(metrics["ctl_fitness"], value + 1e-9)
            self.assertLessEqual(metrics["atl_fatigue"], value + 1e-9)

    def test_ewma_converge_para_o_valor_constante(self):
        value = 100
        metrics = self.engine.compute_metrics([value] * 400)
        self.assertAlmostEqual(metrics["ctl_fitness"], value, places=1)
        self.assertAlmostEqual(metrics["atl_fatigue"], value, places=1)

    def test_ctl_e_mais_lento_que_atl(self):
        # tc 42 > 7: apos um unico dia alto, ATL sobe mais que CTL. E' a assimetria
        # que faz TSB cair num treino isolado e recuperar devagar.
        metrics = self.engine.compute_metrics([100])
        self.assertGreater(metrics["atl_fatigue"], metrics["ctl_fitness"])
        self.assertLess(metrics["tsb_form"], 0)

    def test_tsb_negativo_apos_carga_e_recupera_em_repouso(self):
        carregado = self.engine.compute_metrics([100] * 10)
        self.assertLess(carregado["tsb_form"], 0)
        recuperado = self.engine.compute_metrics([100] * 10 + [0] * 30)
        self.assertGreater(recuperado["tsb_form"], carregado["tsb_form"])
        self.assertGreater(recuperado["tsb_form"], 0)

    def test_serie_vazia_e_identidade_do_estado_inicial(self):
        metrics = self.engine.compute_metrics([], initial_ctl=50, initial_atl=20)
        self.assertEqual(metrics["ctl_fitness"], 50)
        self.assertEqual(metrics["atl_fatigue"], 20)
        self.assertEqual(metrics["tsb_form"], 30)

    def test_tsb_e_limitado_ao_intervalo_da_diferenca(self):
        # TSB nao pode estar fora de [-max, max] do historico considerado.
        for history in ([100] * 5, [0] * 5, [50, 120, 10, 90], [200] * 30 + [0] * 30):
            metrics = self.engine.compute_metrics(history)
            self.assertGreaterEqual(metrics["tsb_form"], -200 + 1e-9)
            self.assertLessEqual(metrics["tsb_form"], 200 + 1e-9)

    def test_monotonicidade_em_carga_constante(self):
        # Com carga diaria constante, CTL e monotono crescente: mais tempo de
        # exposicao produz mais fitness estimado.
        previous = -1.0
        for days in (1, 5, 15, 30, 60):
            ctl = self.engine.compute_metrics([80] * days)["ctl_fitness"]
            self.assertGreater(ctl, previous)
            previous = ctl

    def test_repouso_derruba_fadiga_mais_rapido_que_fitness(self):
        # A assimetria tc 7 vs tc 42: em repouso, ATL decai mais rapido que CTL
        # cai, entao TSB sobe. E' o que faz "descansar" funcionar no modelo.
        # Uma semana de repouso e uma constante de tempo de ATL: a fadiga
        # cai para ~1/e do valor carregado, enquanto o fitness retem a maior
        # parte. E' a assimetria que faz TSB subir em recuperacao.
        carregado = self.engine.compute_metrics([120] * 14)
        descansado = self.engine.compute_metrics([120] * 14 + [0] * 7)
        self.assertLess(descansado["atl_fatigue"], carregado["atl_fatigue"] * 0.4)
        self.assertGreater(descansado["ctl_fitness"],
                           carregado["ctl_fitness"] * 0.8)
        self.assertGreater(descansado["tsb_form"], carregado["tsb_form"])
        self.assertLess(descansado["tsb_form"], 0)

    def test_fadiga_decai_mais_rapido_que_sobe(self):
        # Meia-vida de ATL (tc 7) e ~4,9 dias; CTL (tc 42) e ~29 dias. Este
        # teste trava a ordem das meias-vidas, nao os numeros, para que ajustar
        # tc seja uma decisao explicita e nao um efeito colateral.
        engine = self.engine
        carregado = engine.compute_metrics([100] * 10)
        descansado = engine.compute_metrics([100] * 10 + [0] * 7)
        # Quedas relativas ao valor carregado, nao a 100: o que se compara e a
        # rapidez de cada serie.
        queda_atl = 1 - descansado["atl_fatigue"] / carregado["atl_fatigue"]
        queda_ctl = 1 - descansado["ctl_fitness"] / carregado["ctl_fitness"]
        self.assertGreater(queda_atl, queda_ctl * 2)
        self.assertGreater(queda_atl, 0.5)
        self.assertLess(queda_ctl, 0.25)

    def test_constantes_sao_exponenciais_e_nao_lineares(self):
        # A implementacao e 1 - exp(-1/tc). Se virar 1/tc, a constante de tempo
        # muda de sentido e a comparacao com o Intervals.icu perde sentido.
        for tc, key in ((self.engine.tc_ctl, "ctl_fitness"),
                        (self.engine.tc_atl, "atl_fatigue")):
            expected = 100 * (1 - math.exp(-1 / tc))
            self.assertAlmostEqual(self.engine.compute_metrics([100])[key],
                                   expected, places=1)


if __name__ == "__main__":
    unittest.main()
