import json
import math
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src.activity_stream_cache import ActivityStreamCache
from src.application import Application
from src.ftp_history import (FtpHistory, FtpHistoryRepository, FtpProtocol,
                             FtpReference, FtpReferenceSource, SCHEMA_VERSION)
from src.snapshot import TrainingSnapshot
from src.plan import build_plan, event_payload


T0 = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


def reference(ref_id="ftp-1", watts=250, *, effective_from=T0,
              recorded_at=T0, supersedes=None, source=FtpReferenceSource.USER_ENTERED,
              protocol=FtpProtocol.RAMP_TEST):
    return FtpReference(
        id=ref_id, value_watts=watts, effective_from=effective_from,
        recorded_at=recorded_at, source=source, protocol=protocol,
        evidence_activity_id="activity-1", evidence_workout_id="workout-1",
        provider="intervals", notes="confirmado", supersedes_reference_id=supersedes)


class FtpReferenceTest(unittest.TestCase):
    def test_valid_reference_preserves_source_protocol_and_timestamps(self):
        ref = reference()
        self.assertEqual(ref.value_watts, 250.0)
        self.assertIs(ref.source, FtpReferenceSource.USER_ENTERED)
        self.assertIs(ref.protocol, FtpProtocol.RAMP_TEST)
        self.assertEqual(FtpReference.from_dict(ref.to_dict()), ref)

    def test_invalid_watts_are_rejected(self):
        for watts in (None, 0, -1, math.nan, math.inf, -math.inf):
            with self.subTest(watts=watts):
                with self.assertRaises(ValueError):
                    reference(watts=watts)

    def test_default_ftp_number_is_valid_when_explicitly_confirmed(self):
        self.assertEqual(reference(watts=182).value_watts, 182.0)

    def test_naive_timestamps_are_rejected(self):
        naive = datetime(2026, 10, 1, 8, 0)
        with self.assertRaises(ValueError):
            reference(effective_from=naive)
        with self.assertRaises(ValueError):
            reference(recorded_at=naive)


class FtpHistoryTest(unittest.TestCase):
    def setUp(self):
        self.first = reference("ftp-1", 250)
        self.second = reference("ftp-2", 260,
                                effective_from=T0 + timedelta(days=30),
                                recorded_at=T0 + timedelta(days=31))

    def test_empty_history_is_unknown_even_with_operational_default_elsewhere(self):
        self.assertIsNone(FtpHistory().resolve_ftp_at(T0))

    def test_resolve_does_not_extrapolate_before_first_reference(self):
        history = FtpHistory((self.first,))
        self.assertIsNone(history.resolve_ftp_at(T0 - timedelta(seconds=1)))

    def test_resolves_at_between_and_after_references(self):
        history = FtpHistory((self.first, self.second))
        self.assertEqual(history.resolve_ftp_at(T0), self.first)
        self.assertEqual(history.resolve_ftp_at(T0 + timedelta(days=29)), self.first)
        self.assertEqual(history.resolve_ftp_at(T0 + timedelta(days=30)), self.second)
        self.assertEqual(history.current_reference(T0 + timedelta(days=60)), self.second)

    def test_resolution_compares_timezone_aware_instants_not_iso_strings(self):
        history = FtpHistory((self.first,))
        same_instant = datetime(2026, 10, 1, 10, 0,
                                tzinfo=timezone(timedelta(hours=2)))
        self.assertEqual(history.resolve_ftp_at(same_instant), self.first)

    def test_resolution_is_independent_of_input_order(self):
        ordered = FtpHistory((self.first, self.second))
        reversed_history = FtpHistory((self.second, self.first))
        instant = T0 + timedelta(days=45)
        self.assertEqual(ordered, reversed_history)
        self.assertEqual(ordered.resolve_ftp_at(instant), reversed_history.resolve_ftp_at(instant))

    def test_real_change_adds_another_active_reference(self):
        history = FtpHistory((self.first,)).with_reference(self.second)
        self.assertEqual(history.references, (self.first, self.second))
        self.assertEqual(history.active_references, (self.first, self.second))

    def test_correction_preserves_audit_record_and_replaces_eligibility(self):
        correction = reference("ftp-1-corrected", 255, recorded_at=T0 + timedelta(hours=1),
                               supersedes="ftp-1")
        history = FtpHistory((self.first, correction))
        self.assertEqual(history.references, (self.first, correction))
        self.assertEqual(history.active_references, (correction,))
        self.assertEqual(history.resolve_ftp_at(T0), correction)

    def test_dangling_correction_is_invalid(self):
        dangling = reference("ftp-2", 260, supersedes="missing")
        with self.assertRaises(ValueError):
            FtpHistory((self.first, dangling))

    def test_correction_must_keep_original_effective_from(self):
        correction = reference("ftp-2", 260, supersedes="ftp-1",
                               effective_from=T0 + timedelta(days=1))
        with self.assertRaises(ValueError):
            FtpHistory((self.first, correction))

    def test_correction_cycle_is_invalid(self):
        a = reference("a", 250, supersedes="b")
        b = reference("b", 251, supersedes="a")
        with self.assertRaises(ValueError):
            FtpHistory((a, b))

    def test_active_references_cannot_share_effective_from(self):
        same_time = reference("ftp-2", 260)
        with self.assertRaises(ValueError):
            FtpHistory((self.first, same_time))

    def test_resolution_requires_timezone_aware_timestamp(self):
        with self.assertRaises(ValueError):
            FtpHistory((self.first,)).resolve_ftp_at(datetime(2026, 10, 2))


class FtpHistoryPersistenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ftp_history.json"
        self.repository = FtpHistoryRepository(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_loads_empty_history(self):
        self.assertEqual(self.repository.load(), FtpHistory())

    def test_roundtrip_preserves_envelope_references_and_optionals(self):
        correction = reference("ftp-1-corrected", 255,
                               recorded_at=T0 + timedelta(hours=1), supersedes="ftp-1")
        history = FtpHistory((reference(), correction), athlete_id="athlete-local")
        self.repository.save(history)

        raw = json.loads(self.path.read_text(encoding="utf-8"))
        self.assertEqual(raw["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.repository.load(), history)

    def test_unknown_schema_and_corrupt_json_are_not_silently_accepted(self):
        self.path.write_text('{"schema_version": 99, "references": []}', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.repository.load()
        self.path.write_text("not json", encoding="utf-8")
        with self.assertRaises(json.JSONDecodeError):
            self.repository.load()


class FtpHistoryApplicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.plan_path = root / "plan.json"
        self.snapshot_path = root / "training_snapshot.json"
        self.cache_path = root / "activity_streams.json"
        self.history_path = root / "ftp_history.json"
        self.env_path = root / ".env"
        self.env_path.write_text("FTP=999\n", encoding="utf-8")
        self.calls = 0

        def _boom():
            self.calls += 1
            raise AssertionError("FTP history local nao pode chamar provider")

        self.app = Application(
            plan_path=self.plan_path, env_path=self.env_path,
            snapshot_path=self.snapshot_path, activity_stream_cache_path=self.cache_path,
            ftp_history_path=self.history_path, client_factory=_boom)
        self.app.save_plan([{"day": "2026-10-02", "name": "Z2", "focus": "zone2"}])
        TrainingSnapshot.capture(now=T0).save(self.snapshot_path)
        ActivityStreamCache().save(self.cache_path)

    def tearDown(self):
        self.tmp.cleanup()

    def test_getters_are_local_and_do_not_read_env_as_history(self):
        plan_before = self.plan_path.read_bytes()
        snapshot_before = self.snapshot_path.read_bytes()
        cache_before = self.cache_path.read_bytes()
        env_before = self.env_path.read_bytes()
        planned = build_plan([], 0, ftp=200, days=1, start=date(2026, 10, 2))
        payload_before = event_payload(planned[0])

        self.assertEqual(self.app.get_ftp_history(), FtpHistory())
        self.assertIsNone(self.app.get_ftp_at(T0))
        self.assertIsNone(self.app.get_current_ftp_reference(T0))

        self.assertFalse(self.history_path.exists())
        self.assertEqual(self.plan_path.read_bytes(), plan_before)
        self.assertEqual(self.snapshot_path.read_bytes(), snapshot_before)
        self.assertEqual(self.cache_path.read_bytes(), cache_before)
        self.assertEqual(self.env_path.read_bytes(), env_before)
        self.assertEqual(build_plan([], 0, ftp=200, days=1, start=date(2026, 10, 2)),
                         planned)
        self.assertEqual(event_payload(planned[0]), payload_before)
        self.assertEqual(self.calls, 0)

    def test_explicit_save_only_changes_dedicated_history_file(self):
        plan_before = self.plan_path.read_bytes()
        snapshot_before = self.snapshot_path.read_bytes()
        cache_before = self.cache_path.read_bytes()
        env_before = self.env_path.read_bytes()
        ref = reference()

        self.app.save_ftp_reference(ref)

        self.assertEqual(self.app.get_ftp_at(T0), ref)
        self.assertEqual(self.plan_path.read_bytes(), plan_before)
        self.assertEqual(self.snapshot_path.read_bytes(), snapshot_before)
        self.assertEqual(self.cache_path.read_bytes(), cache_before)
        self.assertEqual(self.env_path.read_bytes(), env_before)
        self.assertEqual(self.calls, 0)


if __name__ == "__main__":
    unittest.main()
