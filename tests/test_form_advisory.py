"""POL-1 — policy advisory de Form relativo, sem prescricao."""
import contextlib
import io
import json
import math
import tempfile
import tokenize
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src import form_advisory
from src.application import Application
from src.form_advisory import (DEFAULT_FORM_ADVISORY_THRESHOLD, FormAdvisoryStatus,
                               evaluate_form_advisory,
                               validate_form_advisory_threshold)
from src.snapshot import TrainingSnapshot

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


def _boom():
    raise AssertionError("Form advisory nao pode chamar provider")


def _code_only(path):
    source = Path(path).read_text(encoding="utf-8")
    return " ".join(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type not in (tokenize.COMMENT, tokenize.STRING))


class PurePolicyTest(unittest.TestCase):
    def test_casos_basicos(self):
        cases = [
            (-29.9, FormAdvisoryStatus.NORMAL),
            (-30.0, FormAdvisoryStatus.HIGH_NEGATIVE_FORM),
            (-30.1, FormAdvisoryStatus.HIGH_NEGATIVE_FORM),
            (-10.0, FormAdvisoryStatus.NORMAL),
            (0.0, FormAdvisoryStatus.NORMAL),
            (10.0, FormAdvisoryStatus.NORMAL),
            (None, FormAdvisoryStatus.UNAVAILABLE),
        ]
        for form_pct, expected in cases:
            with self.subTest(form_pct=form_pct):
                result = evaluate_form_advisory(form_pct)
                self.assertIs(result.status, expected)
                self.assertEqual(result.threshold, -30.0)
                self.assertEqual(result.form_pct, form_pct)

    def test_threshold_customizado(self):
        self.assertIs(
            evaluate_form_advisory(-25.0, threshold=-20).status,
            FormAdvisoryStatus.HIGH_NEGATIVE_FORM)
        self.assertIs(
            evaluate_form_advisory(-25.0, threshold=-40).status,
            FormAdvisoryStatus.NORMAL)

    def test_default_centralizado(self):
        self.assertEqual(DEFAULT_FORM_ADVISORY_THRESHOLD, -30.0)
        self.assertEqual(evaluate_form_advisory(-30.0).threshold,
                         DEFAULT_FORM_ADVISORY_THRESHOLD)

    def test_threshold_invalido_falha_explicito(self):
        for value in (None, "-30", math.nan, math.inf, -math.inf, 0, 1, True):
            with self.subTest(threshold=value):
                with self.assertRaises(ValueError):
                    validate_form_advisory_threshold(value)

    def test_form_nao_numerico_ou_nan_e_indisponivel(self):
        for value in ("-30", math.nan, math.inf, True):
            with self.subTest(form_pct=value):
                result = evaluate_form_advisory(value)
                self.assertIs(result.status, FormAdvisoryStatus.UNAVAILABLE)
                self.assertIsNone(result.form_pct)

    def test_message_e_neutra_sem_prescricao(self):
        result = evaluate_form_advisory(-35.0)
        self.assertIn("limiar advisory", result.message)
        for prohibited in ("deload", "reduz", "troca", "cancela", "prescreve"):
            self.assertNotIn(prohibited, result.message.lower())

    def test_serializacao(self):
        result = evaluate_form_advisory(-30.0)
        payload = result.to_dict()
        self.assertEqual(payload, {
            "status": "high_negative_form",
            "form_pct": -30.0,
            "threshold": -30.0,
            "message": "Form relativo atingiu o limiar advisory configurado.",
        })
        self.assertEqual(json.loads(json.dumps(payload)), payload)


class ApplicationIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.plan_file = root / "plan.json"
        self.snapshot_file = root / "training_snapshot.json"
        self.app = Application(plan_path=self.plan_file, env_path=root / ".env",
                               snapshot_path=self.snapshot_file,
                               client_factory=_boom)

    def tearDown(self):
        self.tmp.cleanup()

    def _snapshot(self, metrics, captured=T0):
        snapshot = TrainingSnapshot.capture(
            wellness=[{"id": "2026-10-03", "restingHR": 50, "hrv": 60,
                       "sleepSecs": 8 * 3600}],
            events=[], activities=[], metrics=metrics, provider="intervals",
            now=captured)
        self.app.save_training_snapshot(snapshot)

    def test_snapshot_local_para_advisory_sem_provider(self):
        self._snapshot({"ctl": 100.0, "atl": 132.0, "tsb": -32.0})
        result = self.app.get_form_advisory(now=T0)
        self.assertIs(result.status, FormAdvisoryStatus.HIGH_NEGATIVE_FORM)
        self.assertEqual(result.form_pct, -32.0)

    def test_sem_pmc_e_unavailable(self):
        self._snapshot(None)
        result = self.app.get_form_advisory(now=T0)
        self.assertIs(result.status, FormAdvisoryStatus.UNAVAILABLE)
        self.assertIsNone(result.form_pct)

    def test_advisory_e_readiness_heuristic_coexistem(self):
        self._snapshot({"ctl": 100.0, "atl": 132.0, "tsb": -32.0})
        readiness = self.app.get_readiness_view(
            today=T0.date(), now=T0)
        advisory = self.app.get_form_advisory(now=T0)
        self.assertEqual(readiness.heuristic_level, "green")
        self.assertIs(advisory.status, FormAdvisoryStatus.HIGH_NEGATIVE_FORM)
        self.assertEqual(readiness.pmc.form_pct, advisory.form_pct)

    def test_snapshot_stale_nao_bloqueia_advisory(self):
        self._snapshot({"ctl": 100.0, "tsb": -32.0})
        later = T0 + timedelta(days=3)
        result = self.app.get_form_advisory(now=later)
        readiness = self.app.get_readiness_view(today=T0.date(), now=later)
        self.assertIs(result.status, FormAdvisoryStatus.HIGH_NEGATIVE_FORM)
        self.assertEqual(readiness.freshness.status, "stale")

    def test_query_nao_tem_side_effects_nem_stdout(self):
        self.app.save_plan([{"day": "2026-10-03", "name": "A",
                            "external_id": "e1"}], goal="ftp-builder")
        self._snapshot({"ctl": 100.0, "tsb": -32.0})
        plan_before = self.plan_file.read_text(encoding="utf-8")
        snapshot_before = self.snapshot_file.read_text(encoding="utf-8")
        plan_mtime = self.plan_file.stat().st_mtime_ns
        snapshot_mtime = self.snapshot_file.stat().st_mtime_ns
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            result = self.app.get_form_advisory(now=T0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIs(result.status, FormAdvisoryStatus.HIGH_NEGATIVE_FORM)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), plan_before)
        self.assertEqual(self.snapshot_file.read_text(encoding="utf-8"),
                         snapshot_before)
        self.assertEqual(self.plan_file.stat().st_mtime_ns, plan_mtime)
        self.assertEqual(self.snapshot_file.stat().st_mtime_ns, snapshot_mtime)


class ArchitectureGuardrailTest(unittest.TestCase):
    def test_policy_nao_recalcula_form_nem_importa_prescricao(self):
        code = _code_only(form_advisory.__file__)
        for prohibited in ("derive_form_pct", "PmcView", "ReadinessAction",
                           "readiness_decision", "build_plan", "reconcile",
                           "save_plan", "provider", "requests"):
            self.assertNotIn(prohibited, code)

    def test_view_nao_contem_threshold_da_policy(self):
        import src.ui_state as ui_state
        code = _code_only(ui_state.__file__)
        self.assertNotIn("-30", code)
        self.assertNotIn("FormAdvisory", code)

    def test_policy_nao_tem_acao_prescritiva(self):
        code = _code_only(form_advisory.__file__)
        for prohibited in ("DELOAD", "REDUCE", "REPLACE", "CANCEL", "SKIP"):
            self.assertNotIn(prohibited, code)


if __name__ == "__main__":
    unittest.main()
