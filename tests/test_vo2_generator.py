import unittest

from src.coach import FOCUS_ZONE5_VO2MAX, ZONE_BANDS
from src.vo2_generator import (DEFAULT_INTENSITY_RANGE, ProgressionLever,
                               VO2Family, VO2Workout, Z5_CEILING, evaluate,
                               generate, generate_mixed, next_step,
                               progression_ledger)


class VO2GeneratorTest(unittest.TestCase):
    LONG = VO2Family.LONG_INTERVALS
    SHORT = VO2Family.SHORT_INTERVALS
    VAR = VO2Family.VARIABLE_INTERVALS

    def test_templates_4x4_5x3_3x5(self):
        four = generate_mixed(self.LONG, 0)
        five = generate_mixed(self.LONG, 1)
        three = generate_mixed(self.LONG, 2)
        self.assertEqual((four.repetitions, four.interval_duration), (4, 240))
        self.assertEqual((five.repetitions, five.interval_duration), (5, 180))
        self.assertEqual((three.repetitions, three.interval_duration), (3, 300))

    def test_faixa_configuravel_nao_fixa_em_115(self):
        default = generate_mixed(self.LONG, 0)
        self.assertEqual(default.work_power_range, (1.06, 1.20))
        custom = generate_mixed(self.LONG, 0, (1.02, 1.12))
        self.assertEqual(custom.work_power_range, (1.02, 1.12))
        self.assertNotEqual(custom.work_power_range[0], 1.15)

    def test_trabalho_total_e_tempo_de_sessao(self):
        workout = generate_mixed(self.LONG, 0)
        self.assertEqual(workout.total_work_time, 960)
        self.assertEqual(workout.total_session_time, 960 + 3 * 180)

    def test_familias_tem_intervalos_distintos(self):
        self.assertEqual(generate_mixed(self.SHORT, 0).interval_duration, 60)
        self.assertEqual(generate_mixed(self.VAR, 0).interval_duration, 180)

    def test_escada_de_duracao_muda_so_a_duracao(self):
        low = generate(self.LONG, ProgressionLever.INTERVAL_DURATION, 0)
        mid = generate(self.LONG, ProgressionLever.INTERVAL_DURATION, 1)
        high = generate(self.LONG, ProgressionLever.INTERVAL_DURATION, 2)
        self.assertEqual({low.repetitions, mid.repetitions, high.repetitions}, {4})
        self.assertEqual([low.interval_duration, mid.interval_duration,
                          high.interval_duration], [180, 240, 300])

    def test_escada_de_repeticoes_muda_so_as_repeticoes(self):
        steps = [generate(self.LONG, ProgressionLever.REPETITIONS, i)
                 for i in range(3)]
        self.assertEqual({s.interval_duration for s in steps}, {240})
        self.assertEqual([s.repetitions for s in steps], [3, 4, 5])

    def test_escada_de_tempo_total_muda_uma_variavel_por_degrau(self):
        steps = [generate(self.LONG, ProgressionLever.TOTAL_WORK_TIME, i)
                 for i in range(3)]
        self.assertEqual([(s.repetitions, s.interval_duration) for s in steps],
                         [(4, 240), (4, 300), (5, 300)])

    def test_escada_de_intensidade_muda_so_a_intensidade(self):
        steps = [generate(self.LONG, ProgressionLever.INTENSITY, i,
                          (1.06, 1.16)) for i in range(3)]
        self.assertEqual({(s.repetitions, s.interval_duration) for s in steps},
                         {(4, 240)})
        self.assertEqual([s.work_power_range for s in steps],
                         [(1.06, 1.16), (1.06, 1.18), (1.06, 1.20)])

    def test_intensidade_nao_atravessa_o_teto_de_z5(self):
        for step in range(3):
            for family in (self.LONG, self.SHORT, self.VAR):
                workout = generate(family, ProgressionLever.INTENSITY, step)
                self.assertLessEqual(workout.work_power_range[1], Z5_CEILING)
        self.assertEqual(DEFAULT_INTENSITY_RANGE[1], Z5_CEILING)

    def test_faixa_padrao_sem_folga_nao_sobe(self):
        steps = [generate(self.LONG, ProgressionLever.INTENSITY, i).work_power_range
                 for i in range(3)]
        self.assertEqual(set(steps), {DEFAULT_INTENSITY_RANGE})

    def test_faixa_padrao_e_a_banda_z5_declarada(self):
        self.assertEqual(DEFAULT_INTENSITY_RANGE,
                         ZONE_BANDS[FOCUS_ZONE5_VO2MAX])
        self.assertEqual(Z5_CEILING, ZONE_BANDS[FOCUS_ZONE5_VO2MAX][1])

    def test_escada_satura_no_ultimo_degrau(self):
        self.assertEqual(next_step(self.LONG, ProgressionLever.TOTAL_WORK_TIME, 2), 2)
        self.assertEqual(next_step(self.LONG, ProgressionLever.TOTAL_WORK_TIME, 9), 2)

    def test_ledger_muda_uma_dimensao_por_degrau(self):
        for lever in ProgressionLever:
            workouts = [workout for _, workout in
                        progression_ledger(self.LONG, lever)]
            for previous, current in zip(workouts, workouts[1:]):
                changed = sum((previous.repetitions != current.repetitions,
                               previous.interval_duration != current.interval_duration,
                               previous.work_power_range != current.work_power_range))
                self.assertLessEqual(changed, 1, f"{lever} mudou {changed} dimensoes")

    def test_recuperacao_escala_com_a_duracao_do_intervalo(self):
        self.assertLess(generate_mixed(self.SHORT, 0).recovery_duration,
                        generate_mixed(self.LONG, 0).recovery_duration)

    def test_avalia_intensidade_duracao_recuperacao(self):
        report = evaluate(generate_mixed(self.LONG, 0))
        self.assertEqual(set(report), {"intensity_ok", "work_in_range",
                                       "recovery_proportional"})
        self.assertTrue(all(report.values()))
        self.assertFalse(evaluate(generate_mixed(self.LONG, 0),
                                  (1.02, 1.10))["intensity_ok"])

    def test_trabalho_acumulado_fora_da_faixa_e_detectado(self):
        excessive = VO2Workout(self.LONG, 300, 10, DEFAULT_INTENSITY_RANGE,
                               180, 0.40, 3000, 2, ProgressionLever.TOTAL_WORK_TIME)
        self.assertFalse(evaluate(excessive)["work_in_range"])
        too_short = VO2Workout(self.LONG, 60, 3, DEFAULT_INTENSITY_RANGE,
                               60, 0.40, 180, 0, ProgressionLever.TOTAL_WORK_TIME)
        self.assertFalse(evaluate(too_short)["work_in_range"])
        poor_recovery = VO2Workout(self.LONG, 300, 4, DEFAULT_INTENSITY_RANGE,
                                   60, 0.40, 1200, 0, ProgressionLever.TOTAL_WORK_TIME)
        self.assertFalse(evaluate(poor_recovery)["recovery_proportional"])

    def test_potencia_de_recuperacao_e_configuravel(self):
        self.assertEqual(generate_mixed(self.LONG, 0).recovery_power, 0.40)
        self.assertEqual(DEFAULT_INTENSITY_RANGE, (1.06, 1.20))


if __name__ == "__main__":
    unittest.main()
