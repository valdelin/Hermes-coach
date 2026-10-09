"""UI-4 — snapshot normalizado e freshness de sync (sem rede)."""
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.provider import TrainingEvent, WellnessSnapshot
from src.snapshot import (DEFAULT_STALE_AFTER_HOURS, FreshnessStatus,
                          SyncFreshness, TrainingSnapshot)

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


class SyncFreshnessTest(unittest.TestCase):
    def test_unknown_sem_sync(self):
        fresh = SyncFreshness.unknown()
        self.assertEqual(fresh.status(now=T0), FreshnessStatus.UNKNOWN)
        self.assertIsNone(fresh.age_seconds(now=T0))

    def test_fresh_e_stale_por_idade(self):
        fresh = SyncFreshness.captured(now=T0, provider="intervals")
        self.assertEqual(fresh.status(now=T0), FreshnessStatus.FRESH)
        later = T0 + timedelta(hours=DEFAULT_STALE_AFTER_HOURS + 1)
        self.assertEqual(fresh.status(now=later), FreshnessStatus.STALE)

    def test_roundtrip_dict(self):
        fresh = SyncFreshness.captured(now=T0, provider="intervals",
                                       stale_after_hours=12.0)
        again = SyncFreshness.from_dict(fresh.to_dict())
        self.assertEqual(again.synced_at, fresh.synced_at)
        self.assertEqual(again.stale_after_hours, 12.0)


class TrainingSnapshotTest(unittest.TestCase):
    def _events(self):
        return [TrainingEvent(
            raw={"id": 1, "icu_training_load": 55.0, "paired_activity_id": "a"},
            normalized={"provider_event_id": 1, "training_load": 55.0,
                        "paired_activity_id": "a"})]

    def test_capture_normaliza_e_carimba(self):
        snap = TrainingSnapshot.capture(
            events=self._events(),
            wellness=[WellnessSnapshot(raw={}, normalized={"resting_hr": 48})],
            provider="intervals", now=T0)
        self.assertEqual(snap.events[0]["training_load"], 55.0)
        self.assertTrue(snap.events[0]["is_completed"])
        self.assertEqual(snap.wellness[0]["resting_hr"], 48)
        self.assertEqual(snap.captured_at, T0.isoformat())
        self.assertEqual(snap.freshness.status(now=T0), FreshnessStatus.FRESH)

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "snapshot.json"
            snap = TrainingSnapshot.capture(events=self._events(), now=T0)
            snap.save(path)
            loaded = TrainingSnapshot.load(path)
            self.assertEqual(loaded.events, snap.events)
            self.assertEqual(loaded.provider, snap.provider)
            self.assertEqual(loaded.freshness.synced_at, snap.freshness.synced_at)

    def test_load_ausente_ou_corrompido_retorna_vazio_sem_erro(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nope.json"
            empty = TrainingSnapshot.load(missing)
            self.assertEqual(empty.events, [])
            self.assertEqual(empty.freshness.status(), FreshnessStatus.UNKNOWN)

            broken = Path(tmp) / "broken.json"
            broken.write_text("{not json", encoding="utf-8")
            self.assertEqual(TrainingSnapshot.load(broken).events, [])

    def test_from_dict_vazio(self):
        self.assertEqual(TrainingSnapshot.from_dict(None).events, [])
        self.assertEqual(TrainingSnapshot.from_dict({}).wellness, [])


if __name__ == "__main__":
    unittest.main()
