"""UI-4 — acesso canonico a campos + compatibilidade com payload legado.

O dominio le por nome canonico (`field(record, "training_load")`); records
normalizados resolvem na hora, e dicts brutos legados continuam legiveis pela
tabela de aliases do boundary (`provider_fields`). Nenhum `icu_*` aqui.
"""
import unittest

from src.provider import TrainingEvent
from src.provider_fields import canonical, field, is_completed


class FieldAccessTest(unittest.TestCase):
    def test_record_normalizado_tem_prioridade(self):
        record = TrainingEvent(raw={"icu_training_load": 50.0},
                               normalized={"training_load": 50.0, "ctl": 42.0})
        self.assertEqual(field(record, "training_load"), 50.0)
        self.assertEqual(field(record, "ctl"), 42.0)

    def test_dict_cru_legado_resolve_por_alias(self):
        raw = {"icu_training_load": 60.0, "icu_ctl": 40.0, "icu_atl": 35.0,
               "icu_tsb": 5.0, "icu_ftp": 200.0}
        self.assertEqual(field(raw, "training_load"), 60.0)
        self.assertEqual(field(raw, "ctl"), 40.0)
        self.assertEqual(field(raw, "atl"), 35.0)
        self.assertEqual(field(raw, "tsb"), 5.0)
        self.assertEqual(field(raw, "ftp"), 200.0)

    def test_alias_wellness(self):
        raw = {"id": "2026-10-01", "restingHR": 48, "sleepSecs": 28800,
               "hrvSDNN": 70}
        self.assertEqual(field(raw, "day"), "2026-10-01")
        self.assertEqual(field(raw, "resting_hr"), 48)
        self.assertEqual(field(raw, "sleep_secs"), 28800)
        self.assertEqual(field(raw, "hrv_sdnn"), 70)

    def test_ausente_devolve_default(self):
        self.assertIsNone(field({}, "training_load"))
        self.assertEqual(field({}, "ctl", 7), 7)
        self.assertEqual(field(None, "ctl", 3), 3)


class IsCompletedTest(unittest.TestCase):
    def test_record_com_evidencia(self):
        self.assertTrue(is_completed(TrainingEvent(
            raw={}, normalized={"paired_activity_id": "a", "activity_id": None})))
        self.assertTrue(is_completed(TrainingEvent(
            raw={}, normalized={"paired_activity_id": None, "activity_id": "x"})))
        self.assertFalse(is_completed(TrainingEvent(
            raw={}, normalized={"paired_activity_id": None, "activity_id": None})))

    def test_dict_cru(self):
        self.assertTrue(is_completed({"paired_activity_id": "a"}))
        self.assertTrue(is_completed({"activity_id": "x"}))
        self.assertFalse(is_completed({"name": "planejado"}))


class CanonicalTest(unittest.TestCase):
    def test_nao_expoe_nomes_legados_e_e_json_safe(self):
        raw = {"id": 7, "start_date_local": "2026-10-01T07:00:00",
               "icu_training_load": 55.0, "icu_ctl": 42.0,
               "external_id": "hermes-plan-2026-10-01",
               "paired_activity_id": "a1"}
        out = canonical(raw)
        self.assertEqual(out["training_load"], 55.0)
        self.assertEqual(out["ctl"], 42.0)
        self.assertEqual(out["external_id"], "hermes-plan-2026-10-01")
        self.assertTrue(out["is_completed"])
        for key in out:
            self.assertNotIn("icu_", key)

    def test_wellness_sem_completion(self):
        out = canonical({"id": "2026-10-01", "restingHR": 48},
                        with_completion=False)
        self.assertNotIn("is_completed", out)
        self.assertEqual(out["resting_hr"], 48)


if __name__ == "__main__":
    unittest.main()
