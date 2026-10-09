import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.application import Application
from src.ftp_evidence import (Advice, AdviceKind, FtpEvidence,
                              FtpEvidenceRepository, FtpEvidenceSource,
                              advise_ftp, evidence_to_reference,
                              observed_at_from_provider)
from src.ftp_history import (FtpHistoryRepository, FtpProtocol,
                             FtpReference, FtpReferenceSource)

T0 = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)


def evidence(eid="ev-1", watts=250, *, source=FtpEvidenceSource.BEST_20_MIN,
             observed=None, protocol=None, proposes_new=None,
             quality_ok=True, activity_id="a-1"):
    observed = observed or T0
    best20 = round(watts / 0.95, 1) if isinstance(watts, (int, float)) else None
    return FtpEvidence(
        id=eid, value_watts=watts, observed_at=observed, recorded_at=observed,
        source=source, protocol=protocol, activity_id=activity_id,
        workout_id="w-1", provider="intervals", best20=best20,
        quality_ok=quality_ok, proposes_new=proposes_new, notes="teste")


def reference(watts=250, ref_id="ftp-1", effective_from=None):
    effective_from = effective_from or T0
    return FtpReference(
        id=ref_id, value_watts=watts, effective_from=effective_from,
        recorded_at=effective_from, source=FtpReferenceSource.USER_ENTERED,
        protocol=FtpProtocol.RAMP_TEST)


class FtpEvidenceTest(unittest.TestCase):
    def test_valid_evidence_preserves_fields(self):
        entry = evidence(source=FtpEvidenceSource.FTP_SCAN,
                         protocol=FtpProtocol.FTP_20_MIN, proposes_new=True)
        self.assertEqual(entry.value_watts, 250.0)
        self.assertIs(entry.source, FtpEvidenceSource.FTP_SCAN)
        self.assertEqual(FtpEvidence.from_dict(entry.to_dict()), entry)

    def test_invalid_watts_are_rejected(self):
        for watts in (0, -1, None):
            with self.subTest(watts=watts):
                with self.assertRaises(ValueError):
                    evidence(watts=watts)

    def test_naive_timestamps_are_rejected(self):
        naive = datetime(2026, 10, 1, 8, 0)
        with self.assertRaises(ValueError):
            evidence(observed=naive)

    def test_observed_at_from_provider_normalizes_to_utc(self):
        parsed = observed_at_from_provider("2026-10-05T07:30:00")
        self.assertEqual(parsed, datetime(2026, 10, 5, 7, 30,
                                          tzinfo=timezone.utc))

    def test_observed_at_fallback_day_uses_0730(self):
        parsed = observed_at_from_provider(None, default_day="2026-10-05")
        self.assertEqual(parsed, datetime(2026, 10, 5, 7, 30,
                                          tzinfo=timezone.utc))

    def test_observed_at_aware_datetime_passthrough(self):
        aware = datetime(2026, 10, 5, 7, 30, tzinfo=timezone.utc)
        self.assertEqual(observed_at_from_provider(aware), aware)


class AdviseFtpTest(unittest.TestCase):
    def test_sem_evidencia(self):
        advice = advise_ftp((), None)
        self.assertEqual(advice.kind, AdviceKind.NO_EVIDENCE)
        self.assertFalse(advice.suggests_confirmation)

    def test_scan_que_nao_propoe_novo_nao_e_utilizado(self):
        entry = evidence(source=FtpEvidenceSource.FTP_SCAN, proposes_new=False)
        advice = advise_ftp((entry,), None)
        self.assertEqual(advice.kind, AdviceKind.NO_EVIDENCE)

    def test_sem_canonico_sugere_confirmar(self):
        advice = advise_ftp((evidence(),), None)
        self.assertEqual(advice.kind, AdviceKind.CONFIRM_PROPOSITION)
        self.assertEqual(advice.value_watts, 250.0)
        self.assertTrue(advice.suggests_confirmation)

    def test_estimativa_acima_do_canonico_sugere_revisar(self):
        advice = advise_ftp((evidence(watts=260),), reference(watts=250))
        self.assertEqual(advice.kind, AdviceKind.REVIEW_SUGGESTED)
        self.assertFalse(advice.can_lower)

    def test_estimativa_dentro_nao_rebaixa(self):
        advice = advise_ftp((evidence(watts=240),), reference(watts=250))
        self.assertEqual(advice.kind, AdviceKind.WITHIN_CURRENT)
        self.assertFalse(advice.can_lower)

    def test_resultado_de_teste_pode_rebaixar(self):
        advice = advise_ftp(
            (evidence(source=FtpEvidenceSource.USER_REPORTED_TEST, watts=240),),
            reference(watts=250))
        self.assertEqual(advice.kind, AdviceKind.REVIEW_SUGGESTED)
        self.assertTrue(advice.can_lower)

    def test_resultado_de_teste_dentro_fica_within(self):
        advice = advise_ftp(
            (evidence(source=FtpEvidenceSource.HERMES_TEST, watts=255),),
            reference(watts=250))
        self.assertEqual(advice.kind, AdviceKind.WITHIN_CURRENT)

    def test_evidencia_mais_recente_vence(self):
        old = evidence("ev-old", 240, observed=T0 - timedelta(days=7))
        new = evidence("ev-new", 270, observed=T0)
        advice = advise_ftp((old, new), reference(watts=250))
        self.assertEqual(advice.value_watts, 270.0)
        self.assertEqual(advice.evidence_id, "ev-new")

    def test_diferenca_estimar_dentro_do_limiar(self):
        advice = advise_ftp((evidence(watts=256),), reference(watts=250))
        self.assertEqual(advice.kind, AdviceKind.WITHIN_CURRENT)


class EvidenceToReferenceTest(unittest.TestCase):
    def test_mapping_preserva_provenance(self):
        entry = evidence(source=FtpEvidenceSource.HERMES_TEST,
                         protocol=FtpProtocol.FTP_20_MIN)
        ref = evidence_to_reference(entry, reference_id="ftp-ev-1",
                                    effective_from=T0)
        self.assertEqual(ref.value_watts, 250.0)
        self.assertIs(ref.source, FtpReferenceSource.HERMES_TEST)
        self.assertIs(ref.protocol, FtpProtocol.FTP_20_MIN)
        self.assertEqual(ref.evidence_id, "ev-1")
        self.assertEqual(ref.evidence_activity_id, "a-1")
        self.assertEqual(ref.provider, "intervals")

    def test_source_mapping_por_tipo(self):
        for source, expected in (
                (FtpEvidenceSource.HERMES_TEST, FtpReferenceSource.HERMES_TEST),
                (FtpEvidenceSource.COACH_ENTRY, FtpReferenceSource.COACH_DEFINED),
                (FtpEvidenceSource.FTP_SCAN, FtpReferenceSource.USER_ENTERED),
                (FtpEvidenceSource.USER_REPORTED_TEST,
                 FtpReferenceSource.USER_ENTERED)):
            with self.subTest(source=source):
                entry = evidence(source=source)
                ref = evidence_to_reference(entry, reference_id="road-1",
                                            effective_from=T0)
                self.assertIs(ref.source, expected)

    def test_reference_id_vazio_rejeitado(self):
        entry = evidence()
        with self.assertRaises(ValueError):
            evidence_to_reference(entry, reference_id="  ",
                                  effective_from=T0)


class FtpEvidenceRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.path = Path(self.tmp) / "ftp_evidence.json"
        self.repo = FtpEvidenceRepository(self.path)

    def test_roundtrip(self):
        self.repo.save((evidence("ev-1", 250), evidence("ev-2", 270)))
        loaded = self.repo.load()
        self.assertEqual([entry.id for entry in loaded], ["ev-1", "ev-2"])

    def test_ausencia_de_arquivo_retorna_vazio(self):
        self.assertEqual(self.repo.load(), ())

    def test_id_duplicado_na_gravacao_e_rejeitado(self):
        self.repo.save((evidence("ev-1", 250),))
        with self.assertRaises(ValueError):
            self.repo.save((evidence("ev-1", 250), evidence("ev-1", 260)))


class ApplicationFtpEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        base = Path(self.tmp)
        self.app = Application(
            plan_path=base / "plan.json",
            env_path=base / ".env",
            ftp_history_path=base / "ftp_history.json",
            ftp_evidence_path=base / "ftp_evidence.json",
        )

    def test_confirmar_evidencia_cria_referencia_canonica(self):
        self.app.record_ftp_evidence(
            evidence(source=FtpEvidenceSource.HERMES_TEST,
                     protocol=FtpProtocol.FTP_20_MIN,
                     activity_id="act-9"))
        ref = self.app.confirm_ftp_evidence("ev-1", now=T0)
        self.assertEqual(ref.value_watts, 250.0)
        self.assertIs(ref.source, FtpReferenceSource.HERMES_TEST)
        self.assertEqual(ref.evidence_id, "ev-1")
        current = self.app.get_current_ftp_reference(T0)
        self.assertIsNotNone(current)
        self.assertEqual(current.id, ref.id)
        persisted = FtpHistoryRepository(
            Path(self.tmp) / "ftp_history.json").load()
        self.assertEqual(persisted.references[0].evidence_id, "ev-1")

    def test_advice_depois_de_confirmar_passa_a_within(self):
        self.app.record_ftp_evidence(evidence())
        self.assertEqual(self.app.get_ftp_advice(T0).kind,
                         AdviceKind.CONFIRM_PROPOSITION)
        self.app.confirm_ftp_evidence("ev-1", now=T0,
                                      effective_from=T0 - timedelta(days=1))
        advice = self.app.get_ftp_advice(T0)
        self.assertEqual(advice.kind, AdviceKind.WITHIN_CURRENT)

    def test_evidencia_duplicada_e_rejeitada(self):
        self.app.record_ftp_evidence(evidence("ev-1", 250))
        with self.assertRaises(ValueError):
            self.app.record_ftp_evidence(evidence("ev-1", 260))

    def test_confirmar_evidencia_inexistente_levanta(self):
        with self.assertRaises(ValueError):
            self.app.confirm_ftp_evidence("ev-nao-existe", now=T0)

    def test_duas_referencias_ativas_no_mesmo_effective_levantam(self):
        self.app.record_ftp_evidence(evidence("ev-a", 250))
        self.app.record_ftp_evidence(evidence("ev-b", 260))
        self.app.confirm_ftp_evidence("ev-a", now=T0, reference_id="ref-a")
        with self.assertRaises(ValueError):
            self.app.confirm_ftp_evidence("ev-b", now=T0, reference_id="ref-b")


if __name__ == "__main__":
    unittest.main()