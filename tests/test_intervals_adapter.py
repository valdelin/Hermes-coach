"""UI-3 — IntervalsAdapter: traducao, capabilities, push e erros. Sem rede."""
import unittest

import requests

from src.intervals_adapter import DEFAULT_CAPABILITIES, IntervalsAdapter
from src.intervals_client import IntervalsApiError
from src.provider import (ActivitySnapshot, ProviderAuthError, ProviderCapability,
                          ProviderOperationError, ProviderUnavailable,
                          TrainingEvent, WellnessSnapshot)


class _FakeClient:
    def __init__(self, *, events=None, wellness=None, activity=None,
                 error=None):
        self._events = events or []
        self._wellness = wellness or []
        self._activity = activity or {}
        self._error = error
        self.calls = []
        self.created = None
        self.deleted_batches = []
        self.deleted_ids = []

    def _maybe_raise(self):
        if self._error is not None:
            raise self._error

    def events(self, oldest=None, newest=None):
        self.calls.append(("events", oldest, newest))
        self._maybe_raise()
        return list(self._events)

    def wellness(self, oldest=None, newest=None):
        self.calls.append(("wellness", oldest, newest))
        self._maybe_raise()
        return list(self._wellness)

    def activity(self, activity_id):
        self.calls.append(("activity", activity_id))
        self._maybe_raise()
        return dict(self._activity)

    def create_events(self, payloads):
        self.created = list(payloads)
        return 200, list(payloads)

    def delete_events(self, external_ids):
        self.deleted_batches.append(list(external_ids))
        return 200, {"eventsDeleted": len(external_ids)}

    def delete_event(self, event_id):
        self.deleted_ids.append(event_id)
        return 204


class TranslationTest(unittest.TestCase):
    def test_events_normalizados_e_linkage_preservado(self):
        client = _FakeClient(events=[{
            "id": 1, "start_date_local": "2026-10-01T07:00:00",
            "icu_training_load": 50.0, "icu_ctl": 40.0,
            "external_id": "hermes-plan-2026-10-01",
            "paired_activity_id": "a1"}])
        adapter = IntervalsAdapter(client)
        events = adapter.events(oldest="2026-09-01", newest="2026-10-01")

        self.assertEqual(len(events), 1)
        self.assertIsInstance(events[0], TrainingEvent)
        self.assertEqual(events[0].training_load, 50.0)
        self.assertEqual(events[0].ctl, 40.0)
        self.assertEqual(events[0].external_id, "hermes-plan-2026-10-01")
        self.assertEqual(client.calls,
                         [("events", "2026-09-01", "2026-10-01")])

    def test_wellness_normalizado(self):
        client = _FakeClient(wellness=[{"id": "2026-10-01", "restingHR": 46,
                                        "hrv": 70}])
        adapter = IntervalsAdapter(client)
        wellness = adapter.wellness(oldest="2026-09-24", newest="2026-10-01")
        self.assertIsInstance(wellness[0], WellnessSnapshot)
        self.assertEqual(wellness[0].resting_hr, 46)
        self.assertEqual(wellness[0].hrv, 70)

    def test_activity_normalizada(self):
        client = _FakeClient(activity={"id": "i1", "icu_training_load": 58,
                                       "moving_time": 3225})
        adapter = IntervalsAdapter(client)
        activity = adapter.activity("i1")
        self.assertIsInstance(activity, ActivitySnapshot)
        self.assertEqual(activity.training_load, 58)
        self.assertEqual(activity.moving_time, 3225)

    def test_resposta_vazia_ou_none_vira_lista_vazia(self):
        adapter = IntervalsAdapter(_FakeClient(events=None, wellness=None))
        self.assertEqual(adapter.events(), [])
        self.assertEqual(adapter.wellness(), [])

    def test_campos_ausentes_viram_none(self):
        adapter = IntervalsAdapter(_FakeClient(events=[{"id": 3}]))
        event = adapter.events()[0]
        self.assertEqual(event.provider_event_id, 3)
        self.assertIsNone(event.training_load)
        self.assertIsNone(event.ctl)
        self.assertIsNone(event.external_id)
        self.assertFalse(event.is_completed)

    def test_external_ids_preservados_como_linkage(self):
        adapter = IntervalsAdapter(_FakeClient(events=[{
            "external_id": "hermes-plan-2026-10-01",
            "paired_activity_id": "i9", "activity_id": 9}]))
        event = adapter.events()[0]
        self.assertEqual(event.external_id, "hermes-plan-2026-10-01")
        self.assertEqual(event.paired_activity_id, "i9")
        self.assertEqual(event.activity_id, 9)


class CapabilitiesTest(unittest.TestCase):
    def test_declara_capabilities_padrao(self):
        adapter = IntervalsAdapter(_FakeClient())
        self.assertIn(ProviderCapability.READ_EVENTS, adapter.capabilities)
        self.assertIn(ProviderCapability.READ_WELLNESS, adapter.capabilities)
        self.assertIn(ProviderCapability.READ_ACTIVITIES, adapter.capabilities)
        self.assertIn(ProviderCapability.WRITE_WORKOUTS, adapter.capabilities)
        self.assertIn(ProviderCapability.COMPLETION_LINKS, adapter.capabilities)
        self.assertEqual(adapter.capabilities, DEFAULT_CAPABILITIES)

    def test_capabilities_injetaveis(self):
        adapter = IntervalsAdapter(_FakeClient(),
                                   capabilities={ProviderCapability.READ_EVENTS})
        self.assertEqual(adapter.capabilities,
                         frozenset({ProviderCapability.READ_EVENTS}))


class PushDelegationTest(unittest.TestCase):
    def test_create_delete_delegam_ao_client(self):
        client = _FakeClient()
        adapter = IntervalsAdapter(client)
        status, body = adapter.create_events([{"external_id": "e1"}])
        self.assertEqual(status, 200)
        self.assertEqual(client.created, [{"external_id": "e1"}])

        adapter.delete_events(["hermes-plan-2026-10-01"])
        self.assertEqual(client.deleted_batches,
                         [["hermes-plan-2026-10-01"]])

        adapter.delete_event(7)
        self.assertEqual(client.deleted_ids, [7])


class ErrorBoundaryTest(unittest.TestCase):
    def test_401_vira_provider_auth_error(self):
        adapter = IntervalsAdapter(
            _FakeClient(error=IntervalsApiError("credenciais", status=401)))
        with self.assertRaises(ProviderAuthError):
            adapter.events()

    def test_5xx_vira_provider_unavailable(self):
        adapter = IntervalsAdapter(
            _FakeClient(error=IntervalsApiError("instavel", status=503)))
        with self.assertRaises(ProviderUnavailable):
            adapter.wellness()

    def test_rede_sem_status_vira_provider_unavailable(self):
        adapter = IntervalsAdapter(
            _FakeClient(error=IntervalsApiError("sem rede", status=None)))
        with self.assertRaises(ProviderUnavailable):
            adapter.events()

    def test_4xx_operacional_vira_provider_operation_error(self):
        adapter = IntervalsAdapter(
            _FakeClient(error=IntervalsApiError("not found", status=404)))
        with self.assertRaises(ProviderOperationError):
            adapter.activity("x")

    def test_erro_de_requests_tambem_e_contido(self):
        adapter = IntervalsAdapter(
            _FakeClient(error=requests.exceptions.ConnectionError("boom")))
        with self.assertRaises(ProviderOperationError):
            adapter.events()


if __name__ == "__main__":
    unittest.main()
