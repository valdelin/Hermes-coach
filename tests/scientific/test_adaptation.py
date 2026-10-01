"""Adaptação: estado de stimulus, não medida de VO₂max, de limiar ou de potência.

Contrato em `docs/EMBASAMENTO-CIENTIFICO.md` §8. O que estas travas defendem:

* `AdaptationState` é **MODELO COMPUTACIONAL**, uma soma de contribuições com
  teto em 1,0. Não é medida fisiológica e o valor não é legível como "VO₂max",
  "potência aeróbica" ou qualquer quantity mensurável.
* `apply()` é **puro**: devolve novo estado, não muta o original. Um motor que
  mutasse o estado permitiria contabilizar o mesmo treino duas vezes.
* A contribuição de um estímulo é fixa e limitada ao domínio que o estímulo
  afeta. Z2 não constrói VO₂max, e sprint não constrói base aeróbica.
* `decay()` é monotônico: mais dias sem estímulo nunca aumenta adaptação, e
  dias negativos também não.
"""
import unittest

from src.adaptation import (CONTRIBUTIONS, DOMAINS, AdaptationState)

ESTIMULOS = tuple(CONTRIBUTIONS)


def cheio(valor=1.0):
    return AdaptationState(**{domain: valor for domain in DOMAINS})


class DominiosTest(unittest.TestCase):
    def test_o_estado_expoe_exatamente_os_seis_dominios(self):
        self.assertEqual(len(DOMAINS), 6)
        self.assertEqual(set(AdaptationState().__dict__), set(DOMAINS))

    def test_o_estado_inicial_e_zero_em_todos_os_dominios(self):
        self.assertEqual(AdaptationState(), AdaptationState(
            aerobic_base=0, threshold=0, vo2max=0, muscular_endurance=0,
            anaerobic=0, neuromuscular=0))

    def test_todo_estimulo_tem_contribuicao_para_dominio_declarado(self):
        # Nenhum estimulo escreve em dominio fora de DOMAINS: chave solta
        # quebraria AdaptationState(**values) silenciosamente.
        for estimulo, contribuicoes in CONTRIBUTIONS.items():
            self.assertTrue(contribuicoes, estimulo)
            for dominio, valor in contribuicoes.items():
                self.assertIn(dominio, DOMAINS, estimulo)
                self.assertGreater(valor, 0, estimulo)

    def test_z2_constroi_base_e_nao_vo2max(self):
        # A atribuicao de dominio por zona e regra do sistema. Z2 sustenta
        # base aerobica; VO2max vem de Z5.
        estado = AdaptationState().apply("zone2")
        self.assertGreater(estado.aerobic_base, 0)
        self.assertEqual(estado.vo2max, 0)
        self.assertEqual(estado.threshold, 0)

    def test_sprint_constroi_neuromuscular_e_nao_base_aerobica(self):
        estado = AdaptationState().apply("sprint")
        self.assertGreater(estado.neuromuscular, 0)
        self.assertEqual(estado.aerobic_base, 0)
        self.assertEqual(estado.vo2max, 0)

    def test_estimulo_desconhecido_nao_altera_nada(self):
        # Treino fora do vocabulario nao soma contribuicao nem levanta erro:
        # passar por um mapper invalido deixaria a carga sem destino.
        estado = cheio(.5)
        self.assertEqual(estado.apply("ftp_test"), estado)
        self.assertEqual(estado.apply(""), estado)


class AplicacaoTest(unittest.TestCase):
    def test_apply_e_puro(self):
        original = AdaptationState()
        resultado = original.apply("vo2max")
        self.assertEqual(original.vo2max, 0)
        self.assertGreater(resultado.vo2max, 0)
        self.assertIsNot(original, resultado)

    def test_apply_soma_a_contribuicao_exata(self):
        for estimulo in ESTIMULOS:
            estado = AdaptationState().apply(estimulo)
            for dominio, valor in CONTRIBUTIONS[estimulo].items():
                self.assertAlmostEqual(getattr(estado, dominio), valor,
                                       msg=estimulo)

    def test_estimulos_independentes_acumulam(self):
        # zone2 + threshold + vo2max: cada um alimenta seu dominio e nenhum
        # toca o campo do outro.
        estado = (AdaptationState().apply("zone2").apply("threshold")
                  .apply("vo2max"))
        self.assertAlmostEqual(estado.aerobic_base, .08)
        self.assertAlmostEqual(estado.threshold, .10)
        self.assertAlmostEqual(estado.vo2max, .12)
        self.assertEqual(estado.neuromuscular, 0)

    def test_o_teto_e_um_e_nao_so_acumula(self):
        # Many sessions de Z5 somam, mas o estado satura em 1,0. Sem teto o
        # "estado de adaptacao" viraria contador de sessoes, sem significado.
        estado = cheio()
        for _ in range(50):
            estado = estado.apply("vo2max")
        self.assertEqual(estado.vo2max, 1.0)

    def test_o_teto_e_aplicado_por_dominio(self):
        estado = AdaptationState(vo2max=1.0)
        apos = estado.apply("zone2")
        self.assertEqual(apos.vo2max, 1.0)
        self.assertAlmostEqual(apos.aerobic_base, .08)

    def test_a_combinacao_mais_forte_permanece_dentro_do_teto(self):
        estado = cheio()
        for estimulo in ESTIMULOS:
            estado = estado.apply(estimulo)
        for dominio in DOMAINS:
            self.assertLessEqual(getattr(estado, dominio), 1.0, dominio)

    def test_estimulo_repetido_e_monotono(self):
        anterior = AdaptationState()
        for _ in range(5):
            atual = anterior.apply("threshold")
            self.assertGreaterEqual(atual.threshold, anterior.threshold)
            anterior = atual


class DecaimentoTest(unittest.TestCase):
    def test_decay_e_puro(self):
        original = cheio(.8)
        resultado = original.decay(10)
        self.assertEqual(original.threshold, .8)
        self.assertLess(resultado.threshold, .8)

    def test_decay_reduz_todos_os_dominios_na_proporcao(self):
        # O fator e unico para os seis dominios: decaimento uniforme, sem
        # hierarquia entre dominios.
        estado = cheio(.8)
        resultado = estado.decay(10, daily_rate=.01)
        self.assertAlmostEqual(resultado.threshold, .8 * .90)
        for dominio in DOMAINS:
            self.assertAlmostEqual(getattr(resultado, dominio),
                                   .8 * .90, msg=dominio)

    def test_mais_dias_nunca_aumenta_adaptacao(self):
        anterior = cheio(1.0)
        for dias in (0, 1, 7, 30, 90, 365, 10000):
            atual = anterior.decay(dias)
            for dominio in DOMAINS:
                self.assertLessEqual(getattr(atual, dominio),
                                     getattr(anterior, dominio), dominio)
            anterior = atual

    def test_taxa_negativa_amplifica_por_falta_de_teto_superior(self):
        """Limitação real do modelo, travada como documentação viva.

        `decay` só limita por baixo (`max(0, ...)`). Com `daily_rate` negativa ou
        `days` negativo, o fator passa de 1 e a "adaptação" cresce acima do
        estado anterior — o nome `decay` deixa de descrever o comportamento.
        Não corrigido aqui porque mudar isso altera o motor fora do escopo do
        P3-01; fica registrado para decisão.
        """
        estado = cheio(.5)
        self.assertGreater(estado.decay(5, daily_rate=-.1).vo2max, .5)
        self.assertGreater(estado.decay(-5).vo2max, .5)
        # O piso de 0 so e alcancavel com dias e taxa positivos: com taxa
        # negativa o fator cresce e nunca chega ao piso.
        self.assertEqual(cheio(.5).decay(5, daily_rate=.2).vo2max, 0.0)

    def test_decaimento_nunca_produz_valor_negativo(self):
        estado = cheio(.5)
        resultado = estado.decay(10000)
        for dominio in DOMAINS:
            self.assertGreaterEqual(getattr(resultado, dominio), 0.0, dominio)

    def test_a_taxa_padrao_de_um_por_cento_por_dia(self):
        # Convenção do modelo: 1% ao dia, 50 dias para meia adaptação. Heurística
        # do Hermes, não constante medida.
        self.assertAlmostEqual(cheio(1.0).decay(50).vo2max, .50)

    def test_estimulo_posterior_acumula_sobre_o_valor_decaido(self):
        # apply depois de decay parte do estado restante, e nao de um reset:
        # o modelo acumula sobre a memoria que sobrou, respeitando o teto.
        estado = cheio(1.0).decay(50)
        self.assertAlmostEqual(estado.vo2max, .50)
        self.assertAlmostEqual(estado.apply("vo2max").vo2max, .62)
        # Com o estado cheio, o mesmo estimulo satura no teto.
        self.assertEqual(cheio(1.0).apply("vo2max").vo2max, 1.0)


if __name__ == "__main__":
    unittest.main()
