"""INSIGHT-5 — Application -> InsightView local, read-only e offline."""
from __future__ import annotations

import math
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from src.application import Application
from src.ftp_evidence import FtpEvidence, FtpEvidenceRepository, FtpEvidenceSource
from src.ftp_history import (FtpHistory, FtpHistoryRepository, FtpProtocol,
                             FtpReference, FtpReferenceSource)
from src.insight.contract import (FactClassification, InsightView,
                                  ObservationAvailability)
from src.snapshot import TrainingSnapshot


TODAY = date(2026, 10, 3)
NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
EXTERNAL_ID = "hermes-plan-2026-10-04"


class ApplicationInsightViewTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.calls = 0

        def forbidden_client():
            self.calls += 1
            raise AssertionError("get_insight_view nao pode pedir provider")

        self.app = Application(
            plan_path=self.root / "plan.json", env_path=self.root / ".env",
            snapshot_path=self.root / "training_snapshot.json",
            ftp_history_path=self.root / "ftp_history.json",
            ftp_evidence_path=self.root / "ftp_evidence.json",
            client_factory=forbidden_client)
        self.app.env_path.write_text("FTP=250\n", encoding="utf-8")
        self.app.save_plan([{
            "day": "2026-10-04", "name": "Limiar", "focus": "threshold",
            "planned_duration": 2400, "tss": 61.0, "ftp_watts": 210,
            "external_id": EXTERNAL_ID,
        }])
        self.workout_id = self.app.load_plan()[0]["id"]

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _save_snapshot(self, *, observed: bool = False, complete: bool = True) -> None:
        events = [{"id": 7, "external_id": EXTERNAL_ID,
                   "paired_activity_id": "activity-1"}] if observed else []
        activities = [{"id": "activity-1", "moving_time": 1800}] if observed else []
        wellness = [{"id": "2026-10-03", "restingHR": 48, "hrv": 70,
                     "sleepSecs": 27000}] if complete else []
        metrics = ({"ctl": 42, "atl": 38, "tsb": 4, "ftp": 250}
                   if complete else None)
        TrainingSnapshot.capture(events=events, activities=activities,
                                 wellness=wellness, metrics=metrics,
                                 provider="intervals", now=NOW).save(
                                     self.app._snapshot_file())

    @staticmethod
    def _facts(view):
        return {fact.key: fact for fact in view.facts}

    def _write_ftp_records(self) -> None:
        reference = FtpReference(
            id="ftp-ref", value_watts=265, effective_from=NOW, recorded_at=NOW,
            source=FtpReferenceSource.HERMES_TEST,
            protocol=FtpProtocol.RAMP_TEST)
        evidence = FtpEvidence(
            id="ftp-evidence", value_watts=270, observed_at=NOW, recorded_at=NOW,
            source=FtpEvidenceSource.PROVIDER_PM_FTP)
        FtpHistoryRepository(self.app.ftp_history_path).save(FtpHistory((reference,)))
        FtpEvidenceRepository(self.app.ftp_evidence_path).save((evidence,))

    def test_returns_allowlisted_facts_with_authority_and_subject(self) -> None:
        self._save_snapshot()

        view = self.app.get_insight_view(
            subject="Atleta A", workout_id=self.workout_id, today=TODAY, now=NOW)

        self.assertIsInstance(view, InsightView)
        self.assertEqual(view.schema_version, 1)
        self.assertEqual(view.subject, "Atleta A")
        facts = self._facts(view)
        expected = {
            "ctl": (42.0, FactClassification.OBSERVED, None),
            "atl": (38.0, FactClassification.OBSERVED, None),
            "tsb": (4.0, FactClassification.OBSERVED, None),
            "form_pct": (4 / 42 * 100, FactClassification.DERIVED, "%"),
            "hrv": (70.0, FactClassification.OBSERVED, None),
            "rhr": (48.0, FactClassification.OBSERVED, "bpm"),
            "sleep_secs": (27000.0, FactClassification.OBSERVED, "s"),
            "heuristic_level": ("green", FactClassification.HEURISTIC, None),
            "heuristic_score": (0.8000000000000002,
                                FactClassification.HEURISTIC, None),
            "heuristic_confidence": (0.42857142857142855,
                                      FactClassification.HEURISTIC, None),
            "planned_duration_sec": (2400.0, FactClassification.PRESCRIPTION, "s"),
            "planned_tss": (61.0, FactClassification.PRESCRIPTION, "TSS"),
            "planned_ftp_watts": (210.0, FactClassification.PRESCRIPTION, "W"),
        }
        self.assertEqual(set(facts), set(expected))
        for key, (value, classification, unit) in expected.items():
            with self.subTest(key=key):
                self.assertEqual(facts[key].value, value)
                self.assertIs(facts[key].classification, classification)
                self.assertEqual(facts[key].unit, unit)
        self.assertEqual(view.prescribed_session.summary, "Limiar")
        self.assertEqual(view.observed_execution.availability,
                         ObservationAvailability.UNAVAILABLE)
        self.assertIsNone(view.advisory)
        self.assertEqual(tuple(source.name for source in view.provenance),
                         ("readiness_view", "workout_execution_view", "local_plan"))

    def test_optional_or_unknown_workout_and_invalid_subject(self) -> None:
        self._save_snapshot()
        no_workout = self.app.get_insight_view(
            subject="athlete", today=TODAY, now=NOW)
        self.assertIsNone(no_workout.prescribed_session)
        self.assertIsNone(no_workout.observed_execution)
        with self.assertRaises(KeyError):
            self.app.get_insight_view(subject="athlete", workout_id="missing",
                                      today=TODAY, now=NOW)
        for subject in ("", " \t ", None):
            with self.subTest(subject=subject):
                with self.assertRaises(ValueError):
                    self.app.get_insight_view(subject=subject, today=TODAY, now=NOW)  # type: ignore[arg-type]

    def test_observed_activity_changes_only_execution_availability(self) -> None:
        self._save_snapshot(observed=True)

        view = self.app.get_insight_view(
            subject="athlete", workout_id=self.workout_id, today=TODAY, now=NOW)

        self.assertIsNotNone(view.prescribed_session)
        self.assertEqual(view.observed_execution.availability,
                         ObservationAvailability.OBSERVED)
        self.assertIsNone(view.observed_execution.summary)

    def test_missing_data_and_absent_assessment_are_omitted(self) -> None:
        self._save_snapshot(complete=False)

        view = self.app.get_insight_view(subject="athlete", today=TODAY, now=NOW)

        self.assertEqual(view.facts, ())
        self.assertEqual(view.provenance, ())

    def test_facts_are_safe_static_and_unique(self) -> None:
        self._save_snapshot()
        view = self.app.get_insight_view(
            subject="athlete", workout_id=self.workout_id, today=TODAY, now=NOW)

        keys = [fact.key for fact in view.facts]
        self.assertEqual(len(keys), len(set(keys)))
        for fact in view.facts:
            with self.subTest(key=fact.key):
                self.assertRegex(fact.key, r"^[a-z][a-z0-9_]*$")
                self.assertNotIsInstance(fact.value, bool)
                if isinstance(fact.value, float):
                    self.assertTrue(math.isfinite(fact.value))

    def test_is_deterministic_offline_and_does_not_write_or_promote_ftp(self) -> None:
        self._save_snapshot()
        self._write_ftp_records()
        paths = (self.app.plan_path, self.app._snapshot_file(),
                 self.app.ftp_history_path, self.app.ftp_evidence_path)
        before = {path: path.read_bytes() for path in paths}
        planned_before = self.app.get_workout(self.workout_id)

        first = self.app.get_insight_view(
            subject="athlete", workout_id=self.workout_id, today=TODAY, now=NOW)
        second = self.app.get_insight_view(
            subject="athlete", workout_id=self.workout_id, today=TODAY, now=NOW)

        self.assertEqual(first, second)
        self.assertEqual({path: path.read_bytes() for path in paths}, before)
        self.assertEqual(self.app.get_workout(self.workout_id), planned_before)
        self.assertEqual(self.calls, 0)
        fact_keys = {fact.key for fact in first.facts}
        self.assertNotIn("ftp", fact_keys)
        self.assertNotIn("ftp_evidence", fact_keys)
        self.assertNotIn("canonical_ftp", fact_keys)
        self.assertEqual(self.app.get_ftp_history().references[0].value_watts, 265)
        self.assertEqual(self.app.get_ftp_evidence()[0].value_watts, 270)

    def test_insight_package_remains_ftp_agnostic(self) -> None:
        insight_root = Path(__file__).resolve().parent.parent / "src" / "insight"
        source = "\n".join(path.read_text(encoding="utf-8")
                             for path in insight_root.glob("*.py"))
        for token in ("ftp_history", "ftp_evidence", "FtpReference", "FtpEvidence",
                      "DEFAULT_FTP"):
            with self.subTest(token=token):
                self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
