"""UI-2 — HermesWorkoutId: identidade local estavel e independente do provider."""
import tempfile
import unittest
from pathlib import Path

from src import workout_identity
from src.application import Application


class HermesWorkoutIdTest(unittest.TestCase):
    def test_id_e_uuid_valido_e_deterministico(self):
        a = workout_identity.for_day("2026-10-03")
        b = workout_identity.for_day("2026-10-03")
        self.assertEqual(a, b)
        self.assertTrue(workout_identity.is_valid(a))

    def test_dias_distintos_geram_ids_distintos(self):
        self.assertNotEqual(workout_identity.for_day("2026-10-03"),
                            workout_identity.for_day("2026-10-04"))

    def test_ensure_nao_muta_o_original(self):
        workout = {"day": "2026-10-03", "name": "X"}
        enriched = workout_identity.ensure(workout)
        self.assertNotIn("id", workout)
        self.assertTrue(enriched["id"])
        self.assertEqual(enriched["day"], "2026-10-03")

    def test_ensure_e_idempotente_e_preserva_id_existente(self):
        workout = {"day": "2026-10-03", "id": "id-fixo"}
        self.assertIs(workout_identity.ensure(workout), workout)
        self.assertEqual(workout["id"], "id-fixo")

    def test_ensure_sem_day_cai_no_external_id(self):
        workout = {"external_id": "hermes-plan-2026-10-03"}
        enriched = workout_identity.ensure(workout)
        self.assertTrue(workout_identity.is_valid(enriched["id"]))
        self.assertEqual(enriched["id"],
                         workout_identity.ensure(workout)["id"])

    def test_is_valid_rejeita_lixo(self):
        for bad in ("", "nao-uuid", None, 123):
            self.assertFalse(workout_identity.is_valid(bad))


class LegacyPlanIdentityTest(unittest.TestCase):
    """Plano antigo (sem id) continua carregando e recebe id estavel."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan_file = self.root / "plan.json"
        self.plan_file.write_text(
            '[{"day": "2026-10-03", "name": "Z2", "focus": "z2", '
            '"tss": 40.0, "planned_duration": 3600, '
            '"external_id": "hermes-plan-2026-10-03"}]',
            encoding="utf-8")
        self.app = Application(plan_path=self.plan_file,
                               env_path=self.root / ".env",
                               client_factory=lambda: (_ for _ in ()).throw(
                                   AssertionError("sem rede")))

    def tearDown(self):
        self.tmp.cleanup()

    def test_plano_legado_recebe_id_estavel_entre_leituras(self):
        first = self.app.load_plan()
        second = self.app.load_plan()
        self.assertEqual(first[0]["id"], second[0]["id"])
        self.assertTrue(workout_identity.is_valid(first[0]["id"]))
        self.assertEqual(first[0]["lifecycle"], "planned")

    def test_id_do_padrao_por_dia_bate_com_o_calculado(self):
        loaded = self.app.load_plan()
        self.assertEqual(loaded[0]["id"],
                         workout_identity.for_day("2026-10-03"))


if __name__ == "__main__":
    unittest.main()
