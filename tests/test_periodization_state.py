import unittest
from datetime import date

from src.plan import (FOCUS_SWEETSPOT, FOCUS_ZONE2, TrainingPlanState,
                      build_plan, phase_weekly_template, training_phase,
                      training_plan_state)
from src.readiness import Readiness, readiness_decision
from src.readiness_assessment import ReadinessAssessment


class TrainingPlanStateTest(unittest.TestCase):
    def _state(self, tsb=0, readiness=None, goal="ftp-builder"):
        return training_plan_state(
            goal=goal, race_date=None, day=date(2026, 9, 14),
            planned_load=220, current_load=180, tsb=tsb, readiness=readiness)

    def test_estado_expoe_o_contrato_do_plano(self):
        state = self._state()
        self.assertIsInstance(state, TrainingPlanState)
        self.assertEqual(state.goal, "ftp-builder")
        self.assertEqual(state.phase, "build")
        self.assertEqual(state.week_in_phase, 1)
        self.assertEqual(state.cycle_week, 2)
        self.assertEqual(state.planned_load, 220)
        self.assertEqual(state.current_load, 180)
        self.assertEqual(state.tsb, 0)
        self.assertIsNone(state.readiness)

    def test_tsb_nao_muda_fase_nem_alvo_semanal(self):
        low = self._state(tsb=-30)
        adequate = self._state(tsb=10)
        self.assertEqual(low.phase, adequate.phase)
        self.assertEqual(phase_weekly_template(low), phase_weekly_template(adequate))

    def test_race_proxima_entra_em_taper_sem_consultar_tsb(self):
        day = date(2026, 10, 10)
        self.assertEqual(training_phase("race", "2026-10-16", day), "taper")


class SessionAutoregulationTest(unittest.TestCase):
    START = date(2026, 9, 14)

    def _plan(self, tsb, readiness=None, goal="ftp-builder"):
        return build_plan([], tsb, ftp=200, days=5, start=self.START,
                          goal=goal, readiness=readiness)

    def _decisao(self, nivel, illness_alert=False):
        """Decisao de prontidao sintetica para os testes de adaptacao.

        Monta o `ReadinessDecision` pela MESMA politica de producao
        (`readiness_decision`), a partir de um `ReadinessAssessment` explicito.
        Nao monta o enum na mao: se a politica mudar, o teste muda junto em vez
        de continuar verificando um rotulo desatualizado.
        """
        escore = {"red": 0.2, "yellow": 0.6, "green": 0.8}[nivel]
        avaliacao = ReadinessAssessment(hrv_score=escore, rhr_score=escore,
                                        sleep_score=escore)
        return readiness_decision(avaliacao, illness_alert=illness_alert)

    def test_tsb_baixo_adapta_primeira_sessao_de_qualidade_sem_mudar_fase(self):
        low = self._plan(-20)
        adequate = self._plan(0)
        quality_index = next(i for i, workout in enumerate(adequate)
                             if workout["focus"] == FOCUS_SWEETSPOT)
        self.assertEqual(low[quality_index]["focus"], FOCUS_ZONE2)
        self.assertEqual(adequate[quality_index]["focus"], FOCUS_SWEETSPOT)
        next_quality = next(i for i, workout in enumerate(adequate[quality_index + 1:],
                                                           quality_index + 1)
                            if workout["focus"] != FOCUS_ZONE2)
        self.assertEqual(low[next_quality], adequate[next_quality])
        self.assertEqual(
            training_plan_state("ftp-builder", None, self.START, 220, 200, -20).phase,
            training_plan_state("ftp-builder", None, self.START, 220, 200, 0).phase)

    def test_readiness_desfavoravel_adapta_primeira_sessao_de_qualidade(self):
        """Issue #58 Passo A: sinal ruim isolado -> REDUCE, nao REPLACE.

        Ate aqui, qualquer sinal ligado disparava a troca por Z2. A politica
        nova separa as duas consequencias: sinal isolado (YELLOW) reduz volume
        preservando `focus` e intensidade; so RED ou o alerta de possivel
        doenca trocam a sessao. O `focus` continua intocado porque isso nao e
        mais uma troca de foco.
        """
        readiness = self._decisao("yellow")
        plan = self._plan(0, readiness=readiness)
        expected = self._plan(0)
        self.assertEqual(plan[0]["focus"], FOCUS_SWEETSPOT)
        self.assertEqual(plan[0]["params"]["on_power"],
                         expected[0]["params"]["on_power"])
# REDUCE mexe em volume, nao em intensidade: um degrau a menos de repeats.
        self.assertLess(plan[0]["params"]["repeats"],
                        expected[0]["params"]["repeats"])
        # A reducao vale para a primeira sessao de qualidade e so ela. As
        # demais nao podem ter sido cortadas: o `focus` e a `on_power` de cada
        # uma batem com o plano sem readiness. (O TSS delas pode até subir,
        # porque a reducao do dia 0 devolve orcamento para a janela rolante --
        # isso e o motor de orcamento funcionando, nao uma segunda reducao.)
        for ad, esp in zip(plan[1:], expected[1:]):
            self.assertEqual(ad["focus"], esp["focus"])
            self.assertEqual(ad["params"]["on_power"], esp["params"]["on_power"])
            self.assertGreaterEqual(ad["params"]["repeats"],
                                    esp["params"]["repeats"])
        self.assertEqual(
            training_plan_state("ftp-builder", None, self.START, 220, 200, 0,
                                readiness=readiness).phase,
            training_plan_state("ftp-builder", None, self.START, 220, 200, 0).phase)

    def test_readiness_red_troca_qualidade_por_recuperacao(self):
        plan = self._plan(0, readiness=self._decisao("red"))
        self.assertEqual(plan[0]["focus"], FOCUS_ZONE2)
        self.assertEqual(plan[1]["focus"], self._plan(0)[1]["focus"])

    def test_tsb_adequado_e_readiness_favoravel_mantem_sessao_planejada(self):
        readiness = Readiness({"rhr_rising": False}, False, "normal", True)
        expected = self._plan(0)
        actual = self._plan(0, readiness=readiness)
        self.assertEqual(actual[0], expected[0])

    def test_readiness_ausente_nao_adapta(self):
        self.assertEqual(self._plan(0), self._plan(0, readiness=None))

    def test_sessao_z2_planejada_permanece_z2(self):
        planned = self._plan(0, goal="active-off-season")
        adapted = self._plan(-20, goal="active-off-season")
        self.assertEqual(adapted[0], planned[0])


if __name__ == "__main__":
    unittest.main()
