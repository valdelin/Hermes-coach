"""UI-2 — Lifecycle local explicito do treino."""
import unittest
from datetime import date

from src import lifecycle


class DefaultAndEnsureTest(unittest.TestCase):
    def test_estado_inicial_e_planned(self):
        self.assertEqual(lifecycle.default_lifecycle(), lifecycle.LIFECYCLE_PLANNED)

    def test_ensure_anexa_planned_sem_mutar(self):
        workout = {"day": "2026-10-03"}
        enriched = lifecycle.ensure(workout)
        self.assertNotIn("lifecycle", workout)
        self.assertEqual(enriched["lifecycle"], "planned")

    def test_ensure_preserva_estado_declarado(self):
        workout = {"day": "2026-10-03", "lifecycle": "cancelled"}
        self.assertIs(lifecycle.ensure(workout), workout)
        self.assertEqual(workout["lifecycle"], "cancelled")

    def test_ensure_corrige_estado_invalido(self):
        workout = {"day": "2026-10-03", "lifecycle": "banana"}
        self.assertEqual(lifecycle.ensure(workout)["lifecycle"], "planned")


class DeriveTest(unittest.TestCase):
    def test_dia_futuro_ou_hoje_e_planned(self):
        self.assertEqual(
            lifecycle.derive(day="2026-10-04", today=date(2026, 10, 3)),
            "planned")
        self.assertEqual(
            lifecycle.derive(day="2026-10-03", today=date(2026, 10, 3)),
            "planned")

    def test_dia_passado_com_evidencia_e_completed(self):
        self.assertEqual(
            lifecycle.derive(day="2026-10-01", today=date(2026, 10, 3),
                             is_done=True),
            "completed")

    def test_dia_passado_sem_evidencia_e_missed(self):
        self.assertEqual(
            lifecycle.derive(day="2026-10-01", today=date(2026, 10, 3),
                             is_done=False),
            "missed")

    def test_estado_declarado_vence_a_derivacao(self):
        for declared in ("postponed", "substituted", "cancelled",
                         "completed", "missed"):
            self.assertEqual(
                lifecycle.derive(day="2026-10-01", today=date(2026, 10, 3),
                                 is_done=True, declared=declared),
                declared)


class TransitionTest(unittest.TestCase):
    def test_planned_para_estados_observados_e_locais(self):
        for new in lifecycle.ALL_LIFECYCLES:
            self.assertTrue(lifecycle.can_transition("planned", new))

    def test_completed_e_terminal(self):
        self.assertTrue(lifecycle.can_transition("completed", "completed"))
        self.assertFalse(lifecycle.can_transition("completed", "planned"))
        self.assertIn("completed", lifecycle.TERMINAL_LIFECYCLES)

    def test_cancelado_pode_reabrir(self):
        self.assertTrue(lifecycle.can_transition("cancelled", "planned"))
        self.assertFalse(lifecycle.can_transition("cancelled", "completed"))

    def test_validate_transition_levanta_em_invalida_e_desconhecida(self):
        with self.assertRaises(ValueError):
            lifecycle.validate_transition("completed", "planned")
        with self.assertRaises(ValueError):
            lifecycle.validate_transition("planned", "banana")

    def test_validate_transition_ok_e_idempotente(self):
        lifecycle.validate_transition("planned", "completed")
        lifecycle.validate_transition("postponed", "postponed")


if __name__ == "__main__":
    unittest.main()
