"""Distribuição de intensidade: contabilidade de minutos reais, não prescrição.

Contrato em `docs/EMBASAMENTO-CIENTIFICO.md` §13. O que estas travas defendem:

* `IntensityDistributionEngine` **agrega minutos efetivamente registrados**.
  Os modelos (`POLARIZED`, `PYRAMIDAL`, `THRESHOLD_HEAVY`, `CUSTOM`) são
  **rótulos de conversa, não proporções prescritas**. O módulo não define o
  que "polarizado" significa em minutos: ele apenas conta o que aconteceu.
* Porcentagem é sempre sobre o total observado. Semana vazia devolve 0/0/0, não
  `NaN` e não divisão por zero.
* `IntensityMinutes` é frozen e a soma component-a-component: agregar é
  somar minutos em cada faixa, nunca repor a distribuição no modelo.
* `custom` é aceito e **guardado sem validação** — é a única coisa que o motor
  faz com ele. Ele não altera a contagem. Registrar isso é mais honesto do que
  fingir que existe um uso.
"""
import dataclasses
import unittest

from src.intensity_distribution import (IntensityDistributionEngine,
                                        IntensityDistributionModel,
                                        IntensityMinutes,
                                        WeeklyIntensityReport)

MODELOS = tuple(IntensityDistributionModel)


def minutos(low=0, moderate=0, high=0):
    return IntensityMinutes(low=low, moderate=moderate, high=high)


class IntensityMinutesTest(unittest.TestCase):
    def test_total_e_a_soma_das_tres_faixas(self):
        self.assertAlmostEqual(minutos(300, 120, 45).total, 465)

    def test_padrao_e_zero_nas_tres_faixas(self):
        self.assertEqual(minutos(), IntensityMinutes(0, 0, 0))
        self.assertEqual(minutos().total, 0)

    def test_soma_e_component_a_component(self):
        a = minutos(300, 120, 45)
        b = minutos(60, 30, 15)
        self.assertEqual(a + b, IntensityMinutes(360, 150, 60))

    def test_soma_nao_sobrescreve_a_faixa_alta_com_a_baixa(self):
        # Somar tudo em `low` destruiria a informação de onde veio o minuto.
        a = minutos(0, 0, 100)
        b = minutos(0, 0, 100)
        self.assertEqual((a + b).high, 200)
        self.assertEqual((a + b).low, 0)

    def test_a_soma_e_pura(self):
        a = minutos(100, 50, 10)
        original = IntensityMinutes(100, 50, 10)
        a + minutos(1, 1, 1)
        self.assertEqual(a, original)

    def test_minutos_e_imutavel(self):
        m = minutos(10, 20, 30)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            m.low = 99

    def test_total_de_valores_negativos_e_permitido_nas_entradas(self):
        # O motor nao valida os minutos de entrada: ele conta. Um valor
        # negativo aqui é dado ruim de entrada, e a validação é do chamador.
        # Registrado como limite, não como invariante.
        self.assertAlmostEqual(minutos(100, -50, 0).total, 50)


class PorcentagensTest(unittest.TestCase):
    def test_porcentagens_somam_100_quando_ha_tempo(self):
        relatorio = WeeklyIntensityReport(minutos(300, 150, 50))
        p = relatorio.percentages
        self.assertAlmostEqual(sum(p.values()), 100.0)

    def test_porcentagens_sao_sobre_o_total_observado(self):
        relatorio = WeeklyIntensityReport(minutos(300, 150, 50))
        p = relatorio.percentages
        self.assertAlmostEqual(p["low"], 60.0)
        self.assertAlmostEqual(p["moderate"], 30.0)
        self.assertAlmostEqual(p["high"], 10.0)

    def test_semana_vazia_devolve_zero_para_as_tres_faixas(self):
        # 0/0 seria NaN, e NaN num relatório semanal chega ao plano como número
        # inválido. O guard `if not total` existe para isso.
        relatorio = WeeklyIntensityReport(minutos())
        self.assertEqual(relatorio.percentages,
                         {"low": 0, "moderate": 0, "high": 0})

    def test_o_guard_zero_cobre_tambem_minutos_que_se_cancelam(self):
        # Se minutos de faixas diferentes se anulam, o total é 0 e o mesmo
        # guard se aplica: não há divisão por zero em nenhum caminho.
        relatorio = WeeklyIntensityReport(minutos(100, -100, 0))
        self.assertEqual(relatorio.minutes.total, 0)
        self.assertEqual(relatorio.percentages,
                         {"low": 0, "moderate": 0, "high": 0})

    def test_as_tres_chaves_sempre_existem(self):
        for m in (minutos(), minutos(1, 0, 0), minutos(0, 1, 0), minutos(0, 0, 1)):
            self.assertEqual(set(WeeklyIntensityReport(m).percentages),
                             {"low", "moderate", "high"})

    def test_uma_faixa_zerada_preserva_as_outras_percentuais(self):
        p = WeeklyIntensityReport(minutos(600, 0, 0)).percentages
        self.assertAlmostEqual(p["low"], 100.0)
        self.assertAlmostEqual(p["moderate"], 0.0)
        self.assertAlmostEqual(p["high"], 0.0)


class MotorDeAgregacaoTest(unittest.TestCase):
    def test_semanas_parciais_somam_na_ordem_certa(self):
        # Agregar é somar; não há realocação por modelo. UmPolarized que
        #拉到 90% de low mas o registro é 50% é agregado como 50%.
        motor = IntensityDistributionEngine()
        sessoes = [minutos(120, 60, 20), minutos(180, 30, 10),
                   minutos(60, 90, 30)]
        relatorio = motor.weekly_report(sessoes)
        self.assertEqual(relatorio.minutes, IntensityMinutes(360, 180, 60))
        self.assertAlmostEqual(relatorio.minutes.total, 600)

    def test_ordem_das_sessoes_nao_altera_o_total(self):
        sessoes = [minutos(120, 60, 20), minutos(180, 30, 10)]
        a = IntensityDistributionEngine().weekly_report(sessoes)
        b = IntensityDistributionEngine().weekly_report(list(reversed(sessoes)))
        self.assertEqual(a.minutes, b.minutes)

    def test_lista_vazia_gera_relatorio_vazio_e_nao_erro(self):
        relatorio = IntensityDistributionEngine().weekly_report([])
        self.assertEqual(relatorio.minutes.total, 0)
        self.assertEqual(relatorio.percentages,
                         {"low": 0, "moderate": 0, "high": 0})

    def test_agregar_e_puro(self):
        # O motor não guarda estado entre chamadas: a soma começa em zero toda
        # vez. Sem isso, o relatório semanal cresceria a cada leitura.
        motor = IntensityDistributionEngine()
        sessoes = [minutos(300, 150, 50)]
        primeiro = motor.weekly_report(sessoes)
        segundo = motor.weekly_report(sessoes)
        self.assertEqual(primeiro.minutes, segundo.minutes)
        self.assertAlmostEqual(segundo.minutes.low, 300)


class ModelosComoRotulosTest(unittest.TestCase):
    def test_o_vocabulario_de_modelos_e_fechado(self):
        self.assertEqual({m.value for m in MODELOS},
                         {"polarized", "pyramidal", "threshold_heavy", "custom"})

    def test_o_modelo_nao_altera_a_agregacao(self):
        """O invariante mais importante do módulo.

        O nome do modelo não mexe em um minuto. Se `POLARIZED` reescrevesse
        proporções, o relatório deixaria de ser registro e viraria prescrição
        retroativa — exatamente o que a docstring do motor proíbe ao dizer que
        modelos são rótulos.
        """
        sessoes = [minutos(300, 150, 50)]
        relatorios = {m: IntensityDistributionEngine(model=m).weekly_report(sessoes)
                      for m in MODELOS}
        referencia = relatorios[MODELOS[0]]
        for modelo, relatorio in relatorios.items():
            self.assertEqual(relatorio.minutes, referencia.minutes, modelo)
            self.assertEqual(relatorio.percentages, referencia.percentages,
                             modelo)

    def test_custom_e_guardado_sem_validacao_e_sem_uso(self):
        # `custom` entra no construtor e fica ali. O módulo não valida, não
        # interpola e não usa. Registrado como é, em vez de fingir uso.
        motor = IntensityDistributionEngine(custom={"low": 90})
        self.assertEqual(motor.custom, {"low": 90})
        relatorio = motor.weekly_report([minutos(10, 10, 10)])
        self.assertEqual(relatorio.minutes, IntensityMinutes(10, 10, 10))

    def test_custom_aceita_qualquer_tipo_sem_levantar_erro(self):
        # Nenhum type check no construtor: um `custom` errado só apareceria como
        # problema no consumidor, se algum dia existir consumidor.
        for valor in (None, 0, "texto", {"a": 1}, [1, 2]):
            motor = IntensityDistributionEngine(custom=valor)
            self.assertEqual(motor.custom, valor)

    def test_modelo_invalido_e_recusado(self):
        # Aqui sim há validação: um nome de modelo que não existe é erro de
        # configuração, não um rótulo livre.
        with self.assertRaises(ValueError):
            IntensityDistributionEngine(model="pyramidal_discreto")

    def test_modelo_padrao_e_custom(self):
        self.assertEqual(IntensityDistributionEngine().model,
                         IntensityDistributionModel.CUSTOM)
        self.assertIsNone(IntensityDistributionEngine().custom)


class RelatorioSemanalTest(unittest.TestCase):
    def test_relatorio_e_imutavel(self):
        relatorio = WeeklyIntensityReport(minutos(10, 20, 30))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            relatorio.minutes = minutos(1, 1, 1)

    def test_o_total_do_relatorio_rebate_no_minutes(self):
        relatorio = WeeklyIntensityReport(minutos(10, 20, 30))
        self.assertAlmostEqual(relatorio.minutes.total, 60)
        self.assertAlmostEqual(sum(relatorio.percentages.values()), 100.0)

    def test_semanas_reais_somam_para_cem_por_cento(self):
        # Um caso de uso concreto: 4 sessões, uma pirâmide implícita.
        motor = IntensityDistributionEngine()
        semana = [minutos(60, 20, 10), minutos(45, 30, 15),
                  minutos(0, 40, 20), minutos(30, 15, 25)]
        relatorio = motor.weekly_report(semana)
        self.assertAlmostEqual(sum(relatorio.percentages.values()), 100.0)
        self.assertAlmostEqual(relatorio.minutes.total, 310)


if __name__ == "__main__":
    unittest.main()
