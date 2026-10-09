"""#58-D -- WorkoutExecutionView factual, local e sem inferencia."""
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.activity_stream_cache import ActivityStreamCache
from src.application import Application
from src.provider import ActivityStream, ActivityStreamPoint
from src.snapshot import TrainingSnapshot
from src.ui_state import LinkageStatus


T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
DAY = "2026-10-04"
EID = "hermes-plan-2026-10-04"


def _event(event_id=7, activity_id="a1"):
    return {"id": event_id, "external_id": EID,
            "paired_activity_id": activity_id}


def _activity(activity_id="a1", **overrides):
    result = {
        "id": activity_id, "moving_time": 1800, "elapsed_time": 1900,
        "distance": 15000, "total_elevation_gain": 120,
        "average_power": 185, "icu_weighted_avg_watts": 205,
        "average_heartrate": 145, "icu_training_load": 42,
    }
    result.update(overrides)
    return result


class WorkoutExecutionViewTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.calls = 0

        def _boom():
            self.calls += 1
            raise AssertionError("WorkoutExecutionView nao pode pedir provider")

        self.app = Application(
            plan_path=root / "plan.json", snapshot_path=root / "snapshot.json",
            activity_stream_cache_path=root / "streams.json", client_factory=_boom)
        self.app.save_plan([{
            "day": DAY, "name": "Limiar", "focus": "threshold",
            "planned_duration": 2400, "tss": 61.0, "ftp_watts": 210,
            "external_id": EID,
        }], absorbed_ids=[EID])
        self.workout_id = self.app.load_plan()[0]["id"]

    def tearDown(self):
        self.tmp.cleanup()

    def _save_snapshot(self, *, events=(), activities=(), now=T0):
        TrainingSnapshot.capture(events=events, activities=activities,
                                 provider="intervals", now=now).save(
                                     self.app._snapshot_file())

    def test_unique_pair_separates_planned_observed_and_provider_metrics(self):
        self._save_snapshot(events=[_event()], activities=[_activity()])
        view = self.app.get_workout_execution_view(
            self.workout_id, today=date(2026, 10, 3), now=T0)

        self.assertEqual(view.workout_id, self.workout_id)
        self.assertEqual(view.planned.focus, "threshold")
        self.assertEqual(view.planned.duration_sec, 2400.0)
        self.assertEqual(view.planned.tss, 61.0)
        self.assertEqual(view.planned.ftp_watts, 210.0)
        self.assertEqual(view.linkage_status, LinkageStatus.PAIRED)
        self.assertEqual(view.provider_external_id, EID)
        self.assertEqual(view.provider_event_id, 7)
        self.assertEqual(view.activity_id, "a1")
        self.assertEqual(view.observed_activity.normalized_power, 205.0)
        self.assertEqual(view.observed_activity.provider_training_load, 42.0)
        self.assertIsNone(view.stream.aligned)
        self.assertFalse(view.stream.available)
        self.assertEqual(view.snapshot_freshness.status, "fresh")
        self.assertEqual(self.calls, 0)

    def test_no_snapshot_is_unknown_not_evidence_or_missed(self):
        view = self.app.get_workout_execution_view(self.workout_id, now=T0)

        self.assertEqual(view.linkage_status, LinkageStatus.NO_EVIDENCE)
        self.assertFalse(view.snapshot_available)
        self.assertEqual(view.snapshot_freshness.status, "unknown")
        self.assertEqual(view.lifecycle_declared, "planned")
        self.assertIsNone(view.activity_id)

    def test_event_without_activity_is_no_evidence_but_keeps_event_provenance(self):
        self._save_snapshot(events=[_event(activity_id=None)])
        view = self.app.get_workout_execution_view(self.workout_id, now=T0)

        self.assertEqual(view.linkage_status, LinkageStatus.NO_EVIDENCE)
        self.assertEqual(view.provider_event_id, 7)
        self.assertIsNone(view.activity_id)

    def test_duplicate_events_are_ambiguous_regardless_of_order(self):
        events = [_event(event_id=7, activity_id="a1"),
                  _event(event_id=8, activity_id="a2")]
        self._save_snapshot(events=events, activities=[_activity("a1"), _activity("a2")])
        first = self.app.get_workout_execution_view(self.workout_id, now=T0)
        self._save_snapshot(events=list(reversed(events)),
                            activities=[_activity("a1"), _activity("a2")])
        second = self.app.get_workout_execution_view(self.workout_id, now=T0)

        self.assertEqual(first.linkage_status, LinkageStatus.AMBIGUOUS)
        self.assertEqual(second.linkage_status, LinkageStatus.AMBIGUOUS)
        self.assertIsNone(first.provider_event_id)
        self.assertIsNone(first.activity_id)
        self.assertEqual(first.to_dict(), second.to_dict())

    def test_activity_unavailable_differs_from_no_evidence(self):
        self._save_snapshot(events=[_event()])
        view = self.app.get_workout_execution_view(self.workout_id, now=T0)

        self.assertEqual(view.linkage_status, LinkageStatus.ACTIVITY_UNAVAILABLE)
        self.assertEqual(view.activity_id, "a1")
        self.assertIsNone(view.observed_activity)

    def test_zero_observations_are_not_converted_to_none(self):
        self._save_snapshot(events=[_event()], activities=[_activity(
            moving_time=0, elapsed_time=0, distance=0,
            total_elevation_gain=0, average_power=0,
            icu_weighted_avg_watts=0, average_heartrate=0,
            icu_training_load=0)])
        view = self.app.get_workout_execution_view(self.workout_id, now=T0)

        observed = view.observed_activity
        self.assertEqual(observed.moving_time_sec, 0.0)
        self.assertEqual(observed.average_power, 0.0)
        self.assertEqual(observed.provider_training_load, 0.0)

    def test_absent_activity_metrics_stay_none(self):
        self._save_snapshot(events=[_event()], activities=[_activity(
            icu_weighted_avg_watts=None, average_heartrate=None,
            icu_training_load=None)])
        view = self.app.get_workout_execution_view(self.workout_id, now=T0)

        self.assertIsNone(view.observed_activity.normalized_power)
        self.assertIsNone(view.observed_activity.average_hr)
        self.assertIsNone(view.observed_activity.provider_training_load)

    def test_stream_absent_does_not_remove_paired_activity(self):
        self._save_snapshot(events=[_event()], activities=[_activity()])
        view = self.app.get_workout_execution_view(self.workout_id, now=T0)

        self.assertEqual(view.linkage_status, LinkageStatus.PAIRED)
        self.assertIsNotNone(view.observed_activity)
        self.assertFalse(view.stream.available)

    def test_unaligned_stream_is_exposed_without_repair(self):
        self._save_snapshot(events=[_event()], activities=[_activity()])
        stream = ActivityStream(
            provider="intervals", activity_id="a1", alignment="length_mismatch",
            available_fields=("power",), time_samples=3, power_samples=2,
            points=())
        ActivityStreamCache().with_stream(stream).save(
            self.app._activity_stream_cache_file())

        view = self.app.get_workout_execution_view(self.workout_id, now=T0)
        self.assertTrue(view.stream.available)
        self.assertFalse(view.stream.aligned)
        self.assertEqual(view.stream.available_fields, ("power",))

    def test_stale_snapshot_remains_available_as_provenance(self):
        self._save_snapshot(events=[_event()], activities=[_activity()], now=T0)
        view = self.app.get_workout_execution_view(
            self.workout_id, now=T0 + timedelta(days=3))

        self.assertTrue(view.snapshot_available)
        self.assertEqual(view.snapshot_freshness.status, "stale")
        self.assertEqual(view.linkage_status, LinkageStatus.PAIRED)

    def test_query_is_read_only_and_never_resolves_provider(self):
        self._save_snapshot(events=[_event()], activities=[_activity()])
        stream = ActivityStream(
            provider="intervals", activity_id="a1", alignment="aligned",
            available_fields=("power",), points=(ActivityStreamPoint(0, power=0),))
        ActivityStreamCache().with_stream(stream).save(
            self.app._activity_stream_cache_file())
        plan_before = self.app.plan_path.read_bytes()
        snapshot_before = self.app._snapshot_file().read_bytes()
        cache_before = self.app._activity_stream_cache_file().read_bytes()

        view = self.app.get_workout_execution_view(self.workout_id, now=T0)

        self.assertEqual(view.linkage_status, LinkageStatus.PAIRED)
        self.assertEqual(self.app.plan_path.read_bytes(), plan_before)
        self.assertEqual(self.app._snapshot_file().read_bytes(), snapshot_before)
        self.assertEqual(self.app._activity_stream_cache_file().read_bytes(), cache_before)
        self.assertEqual(self.calls, 0)


if __name__ == "__main__":
    unittest.main()
