"""Guardrails offline do contrato INSIGHT M1 v2."""
from __future__ import annotations

import dataclasses
from datetime import datetime, timezone
from pathlib import Path
import unittest

from src.insight.contract import (
    FactClassification, InsightAdvisory, InsightFact, InsightPresentation,
    InsightSource, InsightView, ObservedExecution, ObservationAvailability,
    PrescribedSessionSummary, validate_presentation_payload,
)
from src.ftp_evidence import FtpEvidence, FtpEvidenceSource
from src.ftp_history import FtpReference, FtpReferenceSource


VALID_PAYLOAD = {
    "headline": "Estado disponível",
    "explanation": "O estado upstream foi apresentado sem decisão nova.",
    "next_action_text": "Consulte o treino planejado no Hermes.",
    "caution_text": None,
}


class InsightFactTest(unittest.TestCase):
    def test_valid_fact_is_immutable(self) -> None:
        fact = InsightFact("ftp_evidence", 210, FactClassification.OBSERVED, "W")
        self.assertEqual(fact.classification, FactClassification.OBSERVED)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            fact.key = "other"  # type: ignore[misc]

    def test_fact_rejects_invalid_classification_and_value(self) -> None:
        with self.assertRaisesRegex(ValueError, "classification"):
            InsightFact("x", "value", "canonical")  # type: ignore[arg-type]
        with self.assertRaisesRegex(ValueError, "value"):
            InsightFact("x", True, FactClassification.OBSERVED)

    def test_fact_rejects_non_finite_floats(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "finito"):
                    InsightFact("x", value, FactClassification.OBSERVED)

    def test_ftp_evidence_and_confirmed_reference_remain_distinct_facts(self) -> None:
        now = datetime(2026, 10, 13, tzinfo=timezone.utc)
        evidence = FtpEvidence("evidence-1", 210, now, now, FtpEvidenceSource.PROVIDER_FTP)
        reference = FtpReference("reference-1", 205, now, now, FtpReferenceSource.COACH_DEFINED)
        evidence_fact = InsightFact("ftp_evidence", evidence.value_watts, FactClassification.OBSERVED, "W")
        reference_fact = InsightFact("confirmed_ftp_reference", reference.value_watts, FactClassification.DERIVED, "W")
        self.assertNotEqual(type(evidence), type(reference))
        self.assertNotEqual(evidence_fact.key, reference_fact.key)
        self.assertNotEqual(evidence_fact.value, reference_fact.value)
        self.assertNotEqual(evidence_fact.classification, FactClassification.PRESCRIPTION)


class InsightViewTest(unittest.TestCase):
    def test_view_is_immutable_and_preserves_missing(self) -> None:
        view = InsightView(schema_version=1, subject="athlete")
        self.assertEqual(view.facts, ())
        self.assertIsNone(view.advisory)
        self.assertIsNone(view.prescribed_session)
        self.assertIsNone(view.observed_execution)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            view.subject = "other"  # type: ignore[misc]

    def test_missing_does_not_create_healthy_completed_or_advisory(self) -> None:
        view = InsightView(
            schema_version=1, subject="athlete",
            observed_execution=ObservedExecution(ObservationAvailability.UNAVAILABLE),
        )
        self.assertEqual(view.observed_execution.availability, ObservationAvailability.UNAVAILABLE)
        self.assertIsNone(view.observed_execution.summary)
        self.assertIsNone(view.advisory)

    def test_planned_and_observed_are_separate(self) -> None:
        view = InsightView(
            schema_version=1, subject="athlete",
            prescribed_session=PrescribedSessionSummary("Sessão planejada"),
            observed_execution=ObservedExecution(ObservationAvailability.UNAVAILABLE),
            provenance=(InsightSource("local snapshot"),),
        )
        self.assertIsNotNone(view.prescribed_session)
        self.assertEqual(view.observed_execution.availability, ObservationAvailability.UNAVAILABLE)

    def test_advisory_is_only_carried_from_upstream(self) -> None:
        advisory = InsightAdvisory("Advice já existente")
        view = InsightView(schema_version=1, subject="athlete", advisory=advisory)
        self.assertIs(view.advisory, advisory)


class InsightPresentationTest(unittest.TestCase):
    def test_presentation_is_immutable(self) -> None:
        presentation = InsightPresentation(**VALID_PAYLOAD)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            presentation.headline = "other"  # type: ignore[misc]

    def test_valid_payload_and_none_caution(self) -> None:
        self.assertEqual(validate_presentation_payload(VALID_PAYLOAD), ())

    def test_schema_rejects_non_object_missing_extra_invalid_type_and_empty_text(self) -> None:
        self.assertEqual(validate_presentation_payload([]), ("payload deve ser objeto",))
        self.assertIn("campo obrigatorio ausente: headline", validate_presentation_payload({}))
        self.assertIn("campo extra: other", validate_presentation_payload({**VALID_PAYLOAD, "other": "x"}))
        self.assertEqual(validate_presentation_payload({**VALID_PAYLOAD, "headline": 1}), ("headline deve ser texto",))
        self.assertEqual(validate_presentation_payload({**VALID_PAYLOAD, "headline": "  "}), ("headline nao pode ser vazio",))
        self.assertEqual(validate_presentation_payload({**VALID_PAYLOAD, "caution_text": 1}), ("caution_text deve ser texto",))

    def test_all_forbidden_fields_are_rejected(self) -> None:
        forbidden = (
            "focus", "foco", "duration", "duracao", "duration_min", "duracao_min",
            "intensity", "intensidade", "ftp", "watts", "power", "tss", "lifecycle",
            "readiness", "progression", "provider_payload",
        )
        for field in forbidden:
            with self.subTest(field=field):
                self.assertEqual(
                    validate_presentation_payload({**VALID_PAYLOAD, field: "forbidden"}),
                    (f"campo extra: {field}",),
                )


class ArchitectureBoundaryTest(unittest.TestCase):
    def test_core_boundaries_do_not_import_insight(self) -> None:
        root = Path(__file__).resolve().parent.parent
        for relative in ("src/plan.py", "src/readiness.py", "src/ftp_history.py",
                         "src/ftp_evidence.py", "src/provider.py"):
            with self.subTest(path=relative):
                source = (root / relative).read_text(encoding="utf-8")
                self.assertNotIn("insight", source.lower())

    def test_contract_has_no_legacy_threshold_or_default_ftp(self) -> None:
        contract = (Path(__file__).resolve().parent.parent / "src/insight/contract.py").read_text(encoding="utf-8")
        self.assertNotIn("TSB <= -20", contract)
        self.assertNotIn("DEFAULT_FTP", contract)
