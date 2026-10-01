import unittest
from datetime import date

from src.plan import (FOCUS_SWEETSPOT, FOCUS_ZONE2, TrainingPlanState,
                      build_plan, phase_weekly_template, training_phase,
                      training_plan_state)
from src.readiness import Readiness


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

    def test_tsb_baixo_adapta_primeira_sessao_de_qualidade_sem_mudar_fase(self):
        low = self._plan(-20)
        adequate = self._plan(0)
        quality_index = next(i for i, workout in enumerate(adequate)
                             if workout["focus"] == FOCUS_SWEETSPOT)
        self.assertEqual(low[quality_index]["focus"], FOCUS_ZONE2)
        self.assertEqual(adequate[quality_index]["focus"], FOCUS_SWEETSPOT)
        self.assertEqual(
            training_plan_state("ftp-builder", None, self.START, 220, 200, -20).phase,
            training_plan_state("ftp-builder", None, self.START, 220, 200, 0).phase)

    def test_readiness_desfavoravel_adapta_primeira_sessao_de_qualidade(self):
        readiness = Readiness({"rhr_rising": True}, False, "RHR alto", True)
        plan = self._plan(0, readiness=readiness)
        self.assertEqual(plan[0]["focus"], FOCUS_ZONE2)

    def test_tsb_adequado_e_readiness_favoravel_mantem_sessao_planejada(self):
        readiness = Readiness({"rhr_rising": False}, False, "normal", True)
        expected = self._plan(0)
        actual = self._plan(0, readiness=readiness)
        self.assertEqual(actual[0], expected[0])

    def test_readiness_ausente_nao_adapta(self):
        self.assertEqual(self._plan(0), self._plan(0, readiness=None))

    def test_sessao_z2_planejada_permanece_z2(self):
        plan = self._plan(-20, goal="active-off-season")
        self.assertEqual(plan[0]["focus"], FOCUS_ZONE2)


if __name__ == "__main__":
    unittest.main()
