"""UI-4 — completion local, snapshot normalizado e sync freshness.

Prova o objetivo do UI-4: o Hermes mantem conclusao local persistida, o provider
entra como EVIDENCIA (nunca como estado ontologico), e a leitura local nao exige
provider. Nenhum `icu_*` aqui fora dos payloads de provider simulados.
"""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.application import Application
from src.provider import ProviderUnavailable
from src.snapshot import FreshnessStatus

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)

PLAN_EID = "hermes-plan-2026-10-01"


def _evidence(eid=PLAN_EID, activity="a1"):
    return {"id": 7, "start_date_local": "2026-10-01T07:00:00",
            "icu_training_load": 55.0, "icu_ctl": 42.0, "icu_atl": 38.0,
            "external_id": eid, "paired_activity_id": activity}


class _Provider:
    provider_name = "intervals"

    def __init__(self, events=None, wellness=None, fail=False):
        self._events = list(events or [])
        self._wellness = list(wellness or [])
        self.fail = fail

    def events(self, oldest=None, newest=None):
        if self.fail:
            raise ProviderUnavailable("offline")
        return list(self._events)

    def wellness(self, oldest=None, newest=None):
        if self.fail:
            raise ProviderUnavailable("offline")
        return list(self._wellness)


class _AppTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan_file = self.root / "plan.json"
        self.snap_file = self.root / "training_snapshot.json"

        def _boom():
            raise AssertionError("operacao local nao pode pedir provider")
        self.app = Application(plan_path=self.plan_file,
                               env_path=self.root / ".env",
                               client_factory=_boom,
                               snapshot_path=self.snap_file)

    def tearDown(self):
        self.tmp.cleanup()

    def _seed(self, workouts=None, goal="ftp-builder"):
        self.app.save_plan(workouts or [
            {"day": "2026-10-01", "name": "A", "focus": "z2",
             "external_id": PLAN_EID}], goal=goal)
        return self.app.load_plan()

    def _by_day(self):
        return {w["day"]: w for w in self.app.load_plan()}


class CompletionLocalTest(_AppTest):
    def test_evidencia_marca_completed_por_id_local(self):
        loaded = self._seed()
        wid = loaded[0]["id"]
        report = self.app.reconcile_completion(events=[_evidence()], now=T0)
        self.assertEqual(report["applied"], [wid])
        self.assertEqual(self.app.workout_lifecycle(wid), "completed")
        status = self.app.completion_status(wid)
        self.assertEqual(status["status"], "completed")
        self.assertEqual(status["completion"]["source"], "provider_match")
        self.assertEqual(status["completion"]["activity_id"], "a1")

    def test_completion_persiste_e_reload_preserva(self):
        wid = self._seed()[0]["id"]
        self.app.reconcile_completion(events=[_evidence()], now=T0)
        reloaded = Application(plan_path=self.plan_file, snapshot_path=self.snap_file)
        self.assertEqual(reloaded.completion_status(wid)["status"], "completed")
        self.assertEqual(reloaded.load_plan()[0]["id"], wid)

    def test_leitura_local_nao_exige_provider(self):
        wid = self._seed()[0]["id"]
        self.app.reconcile_completion(events=[_evidence()], now=T0)
        # client_factory continua sendo _boom; completion_status nao chama.
        self.assertEqual(self.app.completion_status(wid)["status"], "completed")

    def test_reconcile_repetido_e_idempotente(self):
        wid = self._seed()[0]["id"]
        first = self.app.reconcile_completion(events=[_evidence()], now=T0)
        second = self.app.reconcile_completion(events=[_evidence()], now=T0)
        self.assertEqual(first["applied"], [wid])
        self.assertEqual(second["applied"], [])
        self.assertEqual(second["unchanged"], [wid])
        self.assertEqual(self.app.workout_lifecycle(wid), "completed")

    def test_sem_match_nao_marca(self):
        wid = self._seed()[0]["id"]
        report = self.app.reconcile_completion(
            events=[_evidence(eid="hermes-plan-2026-11-30")], now=T0)
        self.assertEqual(report["matched"], 0)
        self.assertEqual(self.app.workout_lifecycle(wid), "planned")

    def test_estado_declarado_incompativel_nao_e_sobrescrito(self):
        wid = self._seed()[0]["id"]
        self.app.cancel_workout(wid)
        report = self.app.reconcile_completion(events=[_evidence()], now=T0)
        self.assertEqual(report["applied"], [])
        self.assertEqual(report["conflicts"],
                         [{"workout_id": wid, "declared": "cancelled"}])
        self.assertEqual(self.app.workout_lifecycle(wid), "cancelled")

    def test_completed_e_terminal(self):
        wid = self._seed()[0]["id"]
        self.app.mark_completed(wid, source="local", observed_at=T0.isoformat())
        with self.assertRaises(ValueError):
            self.app.set_workout_lifecycle(wid, "planned")


class SyncSnapshotTest(_AppTest):
    def test_sync_captura_snapshot_e_freshness(self):
        self._seed()
        provider = _Provider(events=[_evidence()],
                             wellness=[{"id": "2026-10-01", "restingHR": 48}])
        result = self.app.sync_provider_state(provider=provider, now=T0)
        self.assertTrue(result.ok)
        snap = self.app.load_training_snapshot()
        self.assertEqual(snap.provider, "intervals")
        self.assertEqual(snap.events[0]["training_load"], 55.0)
        self.assertEqual(snap.wellness[0]["resting_hr"], 48)
        self.assertEqual(snap.captured_at, T0.isoformat())
        self.assertEqual(self.app.sync_freshness().status(now=T0),
                         FreshnessStatus.FRESH)
        # Evidencia sincronizada tambem virou conclusao local.
        self.assertEqual(self.app.load_plan()[0]["lifecycle"], "completed")

    def test_freshness_unknown_sem_sync(self):
        self.assertEqual(self.app.sync_freshness().status(now=T0),
                         FreshnessStatus.UNKNOWN)
        self.assertEqual(self.app.load_training_snapshot().events, [])

    def test_provider_indisponivel_nao_corrompe_estado_local(self):
        wid = self._seed()[0]["id"]
        result = self.app.sync_provider_state(provider=_Provider(fail=True),
                                              now=T0)
        self.assertFalse(result.ok)
        self.assertIn("offline", result.error)
        self.assertEqual(result.freshness.status(now=T0), FreshnessStatus.UNKNOWN)
        # Estado local continua legivel e intacto.
        self.assertEqual(self.app.workout_lifecycle(wid), "planned")
        self.assertEqual(self.app.load_training_snapshot().events, [])

    def test_snapshot_nao_polui_plan_json(self):
        self._seed()
        self.app.sync_provider_state(provider=_Provider(events=[_evidence()]),
                                     now=T0)
        data = json.loads(self.plan_file.read_text(encoding="utf-8"))
        self.assertNotIn("events", data)
        self.assertNotIn("freshness", data)
        self.assertTrue(self.snap_file.is_file())


class BackwardCompatibilityTest(_AppTest):
    def test_plano_legado_sem_id_lifecycle_completion(self):
        self.plan_file.write_text(json.dumps([
            {"day": "2026-10-01", "name": "A", "tss": 40.0,
             "external_id": PLAN_EID}]), encoding="utf-8")
        loaded = self.app.load_plan()
        self.assertTrue(loaded[0]["id"])
        self.assertEqual(loaded[0]["lifecycle"], "planned")
        self.assertIsNone(loaded[0].get("completion"))

    def test_evento_legado_com_icu_migra_sem_quebrar(self):
        from src import plan as plan_mod
        workout = {"day": "2026-10-01", "external_id": PLAN_EID}
        self.assertEqual(
            plan_mod.session_execution_state(workout, [_evidence()]),
            plan_mod.SESSAO_CONCLUIDA)


if __name__ == "__main__":
    unittest.main()
