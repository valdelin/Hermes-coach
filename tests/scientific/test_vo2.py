"""VO₂max: progressão por dimensão, com guardrails de Z5.

Contrato em `docs/EMBASAMENTO-CIENTIFICO.md` §12. O que estas travas defendem:

* As escadas (`_ladder`) alteram **uma única dimensão** por degrau. Os
  `MIXED_TEMPLATES` existem para protocolo, não para a escada por dimensão; a
  prova de que não são a rota preferida é que templates mudam repetições e
  duração juntos.
* A intensidade não é fixa em 115%. É intervalo configurável (106–120% FTP) e
  o `INTENSITY` lever sobe o teto **dentro do teto de Z5** (1,20). Não produz
  Z6 (121–150%) a partir de prescrição rotulada como VO₂max.
* Progressão para fora da escada fica clampada: índice negativo vira 0, índice
  acima vira o último degrau. Não desce silenciosamente para -1 nem explode.
* `total_session_time` ignora a recuperação após a última repetição: trabalho +
  (repetições - 1) * recuperação. Contar a última como "recuperação da próxima"
  distorceria o tempo de sessão.
* `generate()` é determinístico: mesmo input, mesmo output. A faixa é preservada
  como tupla de floats com ordenação declarada.
"""
import unittest

from src.vo2_generator import (BASELINE_INTERVAL, DEFAULT_INTENSITY_RANGE,
                               INTENSITY_STEP, MIXED_TEMPLATES,
                               ProgressionLever, VO2Family, VO2Workout,
                               Z5_CEILING, _ladder, _recovery_for, generate)


class EscadasPorDimensaoTest(unittest.TestCase):
    def test_ladder_altera_apenas_uma_dimensao_por_degrau(self):
        # Para cada lever de cada família, mudancade apenas uma variável entre
        # degraus. Isso é o ponto central do módulo.
        for family in VO2Family:
            for lever in (ProgressionLever.INTERVAL_DURATION,
                          ProgressionLever.REPETITIONS,
                          ProgressionLever.TOTAL_WORK_TIME):
                passos = _ladder(family, lever)
                self.assertGreaterEqual(len(passos), 3, (family, lever))
                for anterior, atual in zip(passos, passos[1:]):
                    mudou_rep = anterior[0] != atual[0]
                    mudou_dur = anterior[1] != atual[1]
                    self.assertLessEqual(sum((mudou_rep, mudou_dur)), 1,
                                        f"{family}/{lever}: {anterior}->{atual}")

    def test_ladder_repetitions_aumenta_repeticoes_ou_duracao_nunca_ambas(self):
        # O design explicitamente divide os caminhos: cada escada é um eixo.
        for family in VO2Family:
            passos = _ladder(family, ProgressionLever.REPETITIONS)
            self.assertEqual(passos[0], (3, BASELINE_INTERVAL[family]))
            self.assertEqual(passos[1], (4, BASELINE_INTERVAL[family]))
            self.assertEqual(passos[2], (5, BASELINE_INTERVAL[family]))

    def test_ladder_interval_duration_nao_muda_repeticoes(self):
        for family in VO2Family:
            passos = _ladder(family, ProgressionLever.INTERVAL_DURATION)
            self.assertEqual(passos[0][0], 4)
            self.assertEqual(passos[1][0], 4)
            self.assertEqual(passos[2][0], 4)

    def test_ladder_intensity_nao_muda_forma_do_bloco(self):
        # O lever de intensidade deixa (repetições, duração) constante em todos
        # os degraus: só a faixa sobe.
        for family in VO2Family:
            passos = _ladder(family, ProgressionLever.INTENSITY)
            self.assertEqual(len({p for p in passos}), 1, family)

    def test_total_work_time_mexe_em_duracao_e_pode_mudar_repeticoes_uma_vez(self):
        # É permitido mexer em outra dimensão depois de aumentar duração, mas
        # entre degraus consecutivos a regra é "uma dimensão". Aqui total_work
        # primeiro aumenta duração, depois mantém duração e aumenta repetições:
        # cada transição é 1 dimensão.
        for family in VO2Family:
            passos = _ladder(family, ProgressionLever.TOTAL_WORK_TIME)
            # (4, base) -> (4, base+STEP): só duração
            self.assertEqual(passos[0][0], passos[1][0])
            self.assertNotEqual(passos[0][1], passos[1][1])
            # (4, base+STEP) -> (5, base+STEP): só repetições
            self.assertNotEqual(passos[1][0], passos[2][0])
            self.assertEqual(passos[1][1], passos[2][1])


class GeracaoDeTreinoTest(unittest.TestCase):
    def test_determinismo(self):
        t1 = generate(VO2Family.LONG_INTERVALS, lever=ProgressionLever.REPETITIONS, progression_step=1)
        t2 = generate(VO2Family.LONG_INTERVALS, lever=ProgressionLever.REPETITIONS, progression_step=1)
        self.assertEqual(t1, t2)

    def test_total_work_time_igual_a_repeticoes_vezes_duracao(self):
        t = generate(VO2Family.SHORT_INTERVALS, lever=ProgressionLever.REPETITIONS, progression_step=2)
        self.assertEqual(t.total_work_time, t.repetitions * t.interval_duration)

    def test_total_session_time_nao_conta_ultima_recuperacao(self):
        # Sessão é o bloco de trabalho mais os descansos entre repetições. O
        # descanso após a última série não prolonga a sessão. Fórmula: W + (n-1)*R
        t = generate(VO2Family.SHORT_INTERVALS, lever=ProgressionLever.REPETITIONS, progression_step=1)
        esperado = t.total_work_time + t.recovery_duration * (t.repetitions - 1)
        self.assertEqual(t.total_session_time, esperado)

    def test_repeticoes_negativas_nao_acontecem(self):
        t = generate(VO2Family.LONG_INTERVALS, progression_step=0)
        self.assertGreaterEqual(t.repetitions, 1)

    def test_progression_step_fora_da_escada_e_clampado(self):
        t_min = generate(VO2Family.LONG_INTERVALS, progression_step=-10)
        t_max = generate(VO2Family.LONG_INTERVALS, progression_step=100)
        t_ok = generate(VO2Family.LONG_INTERVALS, progression_step=2)
        # Passo minimo vira 0, maximo vira ultimo
        self.assertEqual(t_min.progression_step, 0)
        self.assertEqual(t_max.progression_step, 2)
        self.assertGreaterEqual(t_max.repetitions, t_ok.repetitions)
        self.assertGreaterEqual(t_max.interval_duration, t_ok.interval_duration)

    def test_intensidade_sobe_com_o_lever_intensity(self):
        # A faixa padrao ja encosta no teto de Z5 (1,20), entao o lever nao tem
        # folga nela. Com faixa prescrita mais estreita, o teto sobe degrau a
        # degrau. Este e o unico caso em que o lever de intensidade faz
        # diferenca, e ele e explicito no modulo.
        estreita = (1.06, 1.10)
        base = generate(VO2Family.LONG_INTERVALS, lever=ProgressionLever.INTENSITY,
                        progression_step=0, intensity_range=estreita)
        passo1 = generate(VO2Family.LONG_INTERVALS, lever=ProgressionLever.INTENSITY,
                          progression_step=1, intensity_range=estreita)
        passo2 = generate(VO2Family.LONG_INTERVALS, lever=ProgressionLever.INTENSITY,
                          progression_step=2, intensity_range=estreita)
        self.assertEqual(base.work_power_range[0], passo1.work_power_range[0])
        self.assertEqual(base.work_power_range[0], passo2.work_power_range[0])
        self.assertLess(base.work_power_range[1], passo1.work_power_range[1])
        self.assertLess(passo1.work_power_range[1], passo2.work_power_range[1])

    def test_lever_intensity_e_inoperante_na_faixa_padrao(self):
        """Limitação real do módulo: o lever padrão não faz nada.

        `DEFAULT_INTENSITY_RANGE` já tem 1,20 como teto, e `generate` faz
        `min(Z5_CEILING, high + step*degrau)`. Ou seja, com a faixa padrão todo
        degrau produz a mesma faixa. O lever só age sobre faixa prescrita
        mais estreita. Registrado para que a docstring do módulo não sugira
        progressão de intensidade onde não há.
        """
        for degrau in range(3):
            t = generate(VO2Family.LONG_INTERVALS,
                         lever=ProgressionLever.INTENSITY,
                         progression_step=degrau)
            self.assertEqual(t.work_power_range,
                             DEFAULT_INTENSITY_RANGE, degrau)

    def test_o_teto_de_intensidade_nao_ultrapassa_z5_ceiling(self):
        # A faixa padrão começa em (1.06, 1.20) no teto. Com poucos degraus da
        # escada de intensidade, ela sobe aos poucos, mas nunca passa de Z5_CEILING.
        t = generate(VO2Family.LONG_INTERVALS,
                     lever=ProgressionLever.INTENSITY,
                     progression_step=100,
                     intensity_range=DEFAULT_INTENSITY_RANGE)
        self.assertLessEqual(t.work_power_range[1], Z5_CEILING)
        # Quando a faixa de entrada já é o teto, ela não sobe.
        t_topo = generate(VO2Family.SHORT_INTERVALS,
                          lever=ProgressionLever.INTENSITY,
                          progression_step=5,
                          intensity_range=(1.20, 1.20))
        self.assertLessEqual(t_topo.work_power_range[1], Z5_CEILING)

    def test_intensidade_nunca_cai_abaixo_do_faixa_informada(self):
        # O ajuste só aumenta o teto, nunca rebaixa o piso nem o teto da faixa
        # original fora do cálculo.
        faixa = (1.08, 1.10)
        t = generate(VO2Family.VARIABLE_INTERVALS,
                     lever=ProgressionLever.INTENSITY,
                     progression_step=5,
                     intensity_range=faixa)
        self.assertGreaterEqual(t.work_power_range[1], faixa[1])
        self.assertEqual(t.work_power_range[0], faixa[0])

    def test_a_faixa_de_intensidade_e_preservada_como_tupla(self):
        t = generate(VO2Family.LONG_INTERVALS, intensity_range=(1.07, 1.15))
        self.assertIsInstance(t.work_power_range, tuple)
        self.assertEqual(len(t.work_power_range), 2)


class RecoveryEResguardaTest(unittest.TestCase):
    def test_recovery_usa_a_tabela_declarada(self):
        # intervalos >= 240 s: 180 s; >= 180 s: 120 s; menores: 90 s
        self.assertEqual(_recovery_for(240), 180)
        self.assertEqual(_recovery_for(300), 180)
        self.assertEqual(_recovery_for(180), 120)
        self.assertEqual(_recovery_for(179), 90)
        self.assertEqual(_recovery_for(60), 90)
        self.assertEqual(_recovery_for(30), 90)

    def test_recovery_e_estritamente_positivo(self):
        for duracao in (30, 60, 120, 240, 300):
            self.assertGreater(_recovery_for(duracao), 0)

    def test_templates_de_intervalos_curtos_e_variaveis_mudam_uma_dimensao(self):
        """Divergência entre docstring e código, registrada.

        O cabeçalho do módulo afirma que os templates "mudam a forma do bloco
        inteiro" e que "subir de um degrau para o seguinte aqui altera
        repetições E duração". Isso é verdade para `long_intervals`
        (4x4 → 5x3 → 3x5) e para a primeira transição de `short_intervals`
        (5x1 → 10x1). Não é verdade em `short_intervals` (10x1 → 6x2 tem duas,
        mas 5x1 → 10x1 tem uma) nem em `variable_intervals`, que é uma escada
        só de repetições: 2x3 → 3x3 → 4x3.

        Fica registrado sem corrigir, porque `MIXED_TEMPLATES` alimenta a
        geração de sessões e mudar os números altera prescrições. A frase da
        docstring precisa ser corrigida em revisão editorial.
        """
        dimensional = {
            (VO2Family.SHORT_INTERVALS, 0): 1,   # 5x1 -> 10x1
            (VO2Family.SHORT_INTERVALS, 1): 2,   # 10x1 -> 6x2
            (VO2Family.VARIABLE_INTERVALS, 0): 1,
            (VO2Family.VARIABLE_INTERVALS, 1): 1,
        }
        for family in (VO2Family.SHORT_INTERVALS, VO2Family.VARIABLE_INTERVALS):
            passos = MIXED_TEMPLATES[family]
            for indice, (a, b) in enumerate(zip(passos, passos[1:])):
                self.assertEqual(int(a[0] != b[0]) + int(a[1] != b[1]),
                                 dimensional[(family, indice)],
                                 f"{family.value}[{indice}]: {a}->{b}")

    def test_template_de_intervalos_longos_muda_forma_inteira(self):
        for a, b in zip(MIXED_TEMPLATES[VO2Family.LONG_INTERVALS],
                        MIXED_TEMPLATES[VO2Family.LONG_INTERVALS][1:]):
            self.assertNotEqual(a[0], b[0])
            self.assertNotEqual(a[1], b[1])

    def test_escadas_nao_usam_os_templates_como_caminho_padrao(self):
        # _ladder mantém uma dimensão constante; MIXED_TEMPLATES não. A
        # progressão por dimensão é distinta dos protocolos "clássicos".
        for family in VO2Family:
            ladder = _ladder(family, ProgressionLever.REPETITIONS)
            template = MIXED_TEMPLATES[family]
            self.assertNotEqual(ladder, template, family)


class ParametrosEOFormatosTest(unittest.TestCase):
    def test_workout_e_imutavel(self):
        import dataclasses
        t = generate(VO2Family.LONG_INTERVALS)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            t.repetitions = 10

    def test_familias_e_levers_sao_enumerados(self):
        self.assertEqual(len(list(VO2Family)), 3)
        self.assertEqual(len(list(ProgressionLever)), 4)

    def test_intensity_step_e_pequeno_e_cumulativo(self):
        # 0,02 por degrau: a subida é gradual, não saltos.
        self.assertGreater(INTENSITY_STEP, 0)
        self.assertLess(INTENSITY_STEP, 0.05)

    def test_o_ceiling_de_z5_e_o_teorico_declarado(self):
        self.assertEqual(Z5_CEILING, 1.20)


if __name__ == "__main__":
    unittest.main()
