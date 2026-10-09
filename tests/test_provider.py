"""UI-3 — contratos, capabilities e records normalizados do provider.

Prova a mecanica dos records normalizados (atributos normalizados + payload
original preservado para consumidores legados) sem depender de nomes `icu_*`:
a traducao concreta do Intervals e testada em `test_intervals_adapter.py`.
"""
import unittest

from src.provider import (ActivitySnapshot, ProviderAuthError, ProviderCapability,
                          ProviderError, ProviderOperationError,
                          ProviderUnavailable, TrainingEvent,
                          WellnessSnapshot, provider_capabilities)


class NormalizedRecordTest(unittest.TestCase):
    def test_atributos_normalizados(self):
        event = TrainingEvent(raw={"icu_training_load": 61.0}, normalized={
            "provider_event_id": 42, "training_load": 61.0, "ctl": 55.5,
            "atl": 48.2, "tsb": 7.3, "external_id": "hermes-plan-2026-10-01",
            "paired_activity_id": "i123"})
        self.assertEqual(event.provider_event_id, 42)
        self.assertEqual(event.training_load, 61.0)
        self.assertEqual(event.ctl, 55.5)
        self.assertEqual(event.atl, 48.2)
        self.assertEqual(event.tsb, 7.3)
        self.assertEqual(event.external_id, "hermes-plan-2026-10-01")
        self.assertEqual(event.paired_activity_id, "i123")

    def test_payload_original_preservado(self):
        raw = {"icu_training_load": 61.0, "name": "x"}
        event = TrainingEvent(raw=raw, normalized={"training_load": 61.0})
        self.assertEqual(event["icu_training_load"], 61.0)
        self.assertEqual(event.get("icu_training_load"), 61.0)
        self.assertEqual(dict(event), raw)
        self.assertEqual(event.raw, raw)
        self.assertEqual(event.normalized()["training_load"], 61.0)

    def test_valor_none_nao_quebra(self):
        event = TrainingEvent(raw={"id": 1}, normalized={
            "provider_event_id": 1, "training_load": None, "ctl": None})
        self.assertIsNone(event.training_load)
        self.assertIsNone(event.ctl)
        self.assertIsNone(event.get("nao_existe"))
        with self.assertRaises(KeyError):
            event["nao_existe"]

    def test_desconhecido_dispara_attribute_error(self):
        with self.assertRaises(AttributeError):
            TrainingEvent(raw={}, normalized={}).nao_existe

    def test_is_completed_por_linkage(self):
        self.assertTrue(TrainingEvent(raw={}, normalized={
            "paired_activity_id": "a", "activity_id": None}).is_completed)
        self.assertTrue(TrainingEvent(raw={}, normalized={
            "paired_activity_id": None, "activity_id": 9}).is_completed)
        self.assertFalse(TrainingEvent(raw={}, normalized={
            "provider_event_id": 1, "paired_activity_id": None,
            "activity_id": None}).is_completed)


class WellnessAndActivityTest(unittest.TestCase):
    def test_wellness_normalizada(self):
        snapshot = WellnessSnapshot(raw={"restingHR": 47}, normalized={
            "day": "2026-10-01", "resting_hr": 47, "hrv": 72, "sleep_secs": 27000})
        self.assertEqual(snapshot.day, "2026-10-01")
        self.assertEqual(snapshot.resting_hr, 47)
        self.assertEqual(snapshot.hrv, 72)
        self.assertEqual(snapshot.sleep_secs, 27000)
        # Item access legado continua identico.
        self.assertEqual(snapshot["restingHR"], 47)

    def test_activity_normalizada(self):
        activity = ActivitySnapshot(raw={"icu_training_load": 58}, normalized={
            "provider_activity_id": "i1", "day": "2026-09-23",
            "training_load": 58, "avg_power": 133, "np": 147})
        self.assertEqual(activity.provider_activity_id, "i1")
        self.assertEqual(activity.day, "2026-09-23")
        self.assertEqual(activity.training_load, 58)
        self.assertEqual(activity.avg_power, 133)
        self.assertEqual(activity.np, 147)
        self.assertEqual(activity["icu_training_load"], 58)


class CapabilitiesTest(unittest.TestCase):
    def test_enum_de_capabilities(self):
        self.assertEqual(ProviderCapability.READ_EVENTS.value, "read_events")
        self.assertEqual(ProviderCapability.WRITE_WORKOUTS.value,
                         "write_workouts")
        self.assertEqual(ProviderCapability.COMPLETION_LINKS.value,
                         "completion_links")

    def test_helper_le_capabilities_do_provider(self):
        class _P:
            capabilities = frozenset({ProviderCapability.READ_EVENTS})

        self.assertEqual(provider_capabilities(_P()),
                         frozenset({ProviderCapability.READ_EVENTS}))

    def test_helper_sem_capabilities_retorna_vazio(self):
        self.assertEqual(provider_capabilities(object()), frozenset())


class ErrorTaxonomyTest(unittest.TestCase):
    def test_hierarquia(self):
        for exc in (ProviderUnavailable, ProviderAuthError,
                    ProviderOperationError):
            self.assertTrue(issubclass(exc, ProviderError))
        self.assertTrue(issubclass(ProviderError, Exception))


if __name__ == "__main__":
    unittest.main()
