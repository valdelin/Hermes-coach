"""Prontidão: suporte ao treino, nunca diagnóstico clínico.

Contrato em `docs/EMBASAMENTO-CIENTIFICO.md` §6 e §7. As travas que importam:

* Prontidão **não é diagnóstico**. O RED significa "reduzir a exigência do
  treino de hoje", não "algo está errado com o atleta". Nenhum campo aqui
  justifica diagnóstico clínico e nenhum teste pode sugerir isso.
* Ausência de sinal **não é sinal ruim**: campo `None` não conta como poor e
  reduz a confiança, em vez de virar zero.
* Confiança é a fração de sinais observados: 7 eixos, denominador fixo.
* YELLOW com apenas um sinal ruim tem que continuar YELLOW, nunca RED. RED
  exige 3 eixos abaixo de 0,4 **e** média abaixo de 0,5.
* GREEN exige 0,7 de média e nenhum eixo abaixo de 0,4.
"""
import unittest

from src.readiness_assessment import (ReadinessAssessment, ReadinessLevel)

EIXOS = ("hrv_score", "rhr_score", "sleep_score", "subjective_fatigue_score",
         "recent_load_score", "performance_score", "consistency_score")


def todos(valor):
    return ReadinessAssessment(**{eixo: valor for eixo in EIXOS})


class MediaEConfiancaTest(unittest.TestCase):
    def test_media_usa_somente_os_eixos_observados(self):
        # Preencher so VRM e sono: media sobre 2 eixos, nao sobre 7.
        avaliacao = ReadinessAssessment(hrv_score=.8, sleep_score=.6)
        self.assertAlmostEqual(avaliacao.overall_readiness, .7)

    def test_nenhum_sinal_nao_produz_media_nem_veredito(self):
        avaliacao = ReadinessAssessment()
        self.assertIsNone(avaliacao.overall_readiness)
        # Sem dado nenhum o sistema e conservador, nao verde e nao vermelho.
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)

    def test_confianca_conta_os_eixos_observados(self):
        self.assertEqual(ReadinessAssessment().confidence, 0)
        avaliacao = ReadinessAssessment(hrv_score=.8, rhr_score=.8)
        self.assertAlmostEqual(avaliacao.confidence, 2 / 7)
        self.assertEqual(todos(.9).confidence, 1.0)

    def test_confianca_e_um_numero_de_sete_eixos(self):
        # Denominador fixo: confidence nunca supera 1 mesmo com todos os eixos.
        for eixo in EIXOS:
            self.assertLessEqual(
                ReadinessAssessment(**{eixo: 1.0}).confidence, 1.0)

    def test_media_e_limitada_ao_intervalo_que_se_declara(self):
        avaliacao = todos(.9)
        self.assertLessEqual(avaliacao.overall_readiness, 1.0)
        self.assertGreaterEqual(avaliacao.overall_readiness, 0.0)


class LimiarDeNivelTest(unittest.TestCase):
    """Os limiares do sistema, fixados como regra dedecisao do Hermes."""

    def test_tudo_alto_e_green(self):
        self.assertEqual(todos(.9).level(), ReadinessLevel.GREEN)

    def test_media_abaixo_de_0_7_e_yellow(self):
        # 0,7 exato e GREEN; abaixo e YELLOW.
        self.assertEqual(todos(.7).level(), ReadinessLevel.GREEN)
        self.assertEqual(todos(.69).level(), ReadinessLevel.YELLOW)

    def test_media_igual_a_um_ou_mais_nao_e_veredito_automatico(self):
        # Sete eixos perfeitos sao GREEN por media, nao por ausencia de ruido:
        # o sistema nao tem ceticismo sobre leitura perfeita, e isso esta
        # registrado como limitacao, nao como invariante.
        self.assertEqual(todos(1.0).level(), ReadinessLevel.GREEN)

    def test_um_eixo_ruim_so_leva_a_yellow(self):
        avaliacao = ReadinessAssessment(
            **{eixo: (.2 if eixo == "hrv_score" else .9) for eixo in EIXOS})
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)
        self.assertNotEqual(avaliacao.level(), ReadinessLevel.RED)

    def test_red_exige_tres_eixos_ruins_e_media_baixa(self):
        avaliacao = ReadinessAssessment(
            **{eixo: (.1 if eixo in EIXOS[:3] else .5) for eixo in EIXOS})
        self.assertLess(avaliacao.overall_readiness, .5)
        self.assertEqual(avaliacao.level(), ReadinessLevel.RED)

    def test_tres_eixos_ruins_com_o_resto_em_1_nao_e_red(self):
        # Os dois criterios sao independentes: tres eixos abaixo de 0,4 nao
        # bastam se a media dos outros quatro mantiver o conjunto acima de 0,5.
        avaliacao = ReadinessAssessment(
            **{eixo: (.2 if eixo in EIXOS[:3] else 1.0) for eixo in EIXOS})
        self.assertGreater(avaliacao.overall_readiness, .5)
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)

    def test_cinco_eixos_ruins_dispara_red(self):
        avaliacao = ReadinessAssessment(
            **{eixo: (.2 if eixo in EIXOS[:5] else 1.0) for eixo in EIXOS})
        self.assertEqual(avaliacao.level(), ReadinessLevel.RED)

    def test_ausencia_de_eixo_ruim_nao_conta_como_ruim(self):
        # Dois eixos muito baixos e cinco ausentes: poor_signals = 2, entao
        # YELLOW, e a confianca avisa que a leitura e fraca.
        avaliacao = ReadinessAssessment(hrv_score=.2, sleep_score=.2)
        self.assertEqual(avaliacao.level(), ReadinessLevel.YELLOW)
        self.assertAlmostEqual(avaliacao.confidence, 2 / 7)

    def test_limiar_ruim_e_estrito(self):
        # 0,4 exato conta como sinal bom; abaixo conta como ruim.
        no_limiar = ReadinessAssessment(
            **{eixo: (.4 if eixo == "sleep_score" else .9) for eixo in EIXOS})
        self.assertEqual(no_limiar.level(), ReadinessLevel.GREEN)


class AjusteDeTreinoTest(unittest.TestCase):
    """O RED corta mais, e o GREEN nao mexe em nada."""

    def test_green_nao_sugere_ajuste(self):
        self.assertEqual(todos(.9).adjustments(), ())

    def test_yellow_sugere_apenas_intensidade_e_volume(self):
        self.assertEqual(todos(.5).adjustments(), ("intensity", "volume"))

    def test_red_sugere_adaptacao_do_treino_inteiro(self):
        esperado = ("intensity", "volume", "intervals", "recovery")
        self.assertEqual(ReadinessAssessment().adjustments(),
                         ("intensity", "volume"))
        avaliacao = ReadinessAssessment(
            **{eixo: (.2 if eixo in EIXOS[:5] else 1.0) for eixo in EIXOS})
        self.assertEqual(avaliacao.adjustments(), esperado)

    def test_ajuste_red_e_superset_do_ajuste_yellow(self):
        # Nunca reduzir intervals sem reduzir intensidade e volume primeiro:
        # cortar os intervalos isoladamente quebraria a ordem de reducao.
        amarelo = set(todos(.5).adjustments())
        vermelho = set(ReadinessAssessment(
            **{eixo: (.2 if eixo in EIXOS[:5] else 1.0)
               for eixo in EIXOS}).adjustments())
        self.assertTrue(amarelo < vermelho)

    def test_ajuste_e_consistente_com_o_nivel(self):
        for avaliacao in (todos(.9), todos(.5), ReadinessAssessment(),
                          ReadinessAssessment(hrv_score=.8, sleep_score=.8)):
            self.assertEqual(avaliacao.adjustments(),
                             {ReadinessLevel.GREEN: (),
                              ReadinessLevel.YELLOW: ("intensity", "volume"),
                              ReadinessLevel.RED: ("intensity", "volume",
                                                  "intervals",
                                                  "recovery")}[avaliacao.level()])


if __name__ == "__main__":
    unittest.main()
