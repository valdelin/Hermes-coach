"""HR-1 — CTL ramp rate observado, tendencia local e advisory opt-in."""
import contextlib
import io
import json
import math
import tempfile
import tokenize
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src import ctl_ramp_advisory, ui_state
from src.application import Application
from src.ctl_ramp_advisory import (CtlRampAdvisoryStatus,
                                   evaluate_ctl_ramp_advisory,
                                   validate_max_ramp_points)
from src.snapshot import TrainingSnapshot
from src.ui_state import (DEFAULT_CTL_RAMP_WINDOW_DAYS, build_ctl_ramp_view,
                          derive_ctl_ramp_rate)

T0 = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)
TARGET = date(2026, 10, 10)
BASELINE = date(2026, 10, 3)


def _boom():
    raise AssertionError("CTL ramp nao pode chamar provider")


def _code_only(path):
    source = Path(path).read_text(encoding="utf-8")
    return " ".join(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type not in (tokenize.COMMENT, tokenize.STRING))


class MetricTest(unittest.TestCase):
    def test_definicao_basica_positiva_negativa_e_zero(self):
        cases = [
            ({TARGET: 50, BASELINE: 45}, 5.0),
            ({TARGET: 45, BASELINE: 50}, -5.0),
            ({TARGET: 50, BASELINE: 50}, 0.0),
        ]
        for history, expected in cases:
            with self.subTest(history=history):
                self.assertEqual(derive_ctl_ramp_rate(
                    history, target_day=TARGET), expected)

    def test_floats_e_valores_negativos_observados(self):
        self.assertAlmostEqual(derive_ctl_ramp_rate(
            {TARGET: 50.75, BASELINE: 45.25}, target_day=TARGET), 5.5)
        self.assertEqual(derive_ctl_ramp_rate(
            {TARGET: -2.0, BASELINE: -5.0}, target_day=TARGET), 3.0)

    def test_gap_ou_ausencia_retorna_none_sem_interpolar(self):
        cases = [
            {},
            {TARGET: 50},
            {BASELINE: 45},
            {TARGET: None, BASELINE: 45},
            {TARGET: 50, BASELINE: None},
            {TARGET: 50, TARGET - timedelta(days=6): 45},
        ]
        for history in cases:
            with self.subTest(history=history):
                self.assertIsNone(derive_ctl_ramp_rate(
                    history, target_day=TARGET))

    def test_ordem_nao_importa_e_input_nao_muta(self):
        history = {BASELINE: 45.0, date(2026, 10, 8): 49.0, TARGET: 50.0}
        before = dict(history)
        self.assertEqual(derive_ctl_ramp_rate(history, target_day=TARGET), 5.0)
        self.assertEqual(history, before)

    def test_janela_configuravel(self):
        history = {TARGET: 50.0, TARGET - timedelta(days=14): 42.0}
        self.assertEqual(derive_ctl_ramp_rate(
            history, target_day=TARGET, window_days=14), 8.0)

    def test_janela_invalida_falha_explicita(self):
        for window in (0, -1, 7.0, None, True):
            with self.subTest(window=window):
                with self.assertRaises(ValueError):
                    derive_ctl_ramp_rate({}, target_day=TARGET,
                                         window_days=window)


class ViewTest(unittest.TestCase):
    def _snapshot(self, events=None, metrics=None, captured=T0):
        return TrainingSnapshot.capture(
            events=events or [], wellness=[], activities=[], metrics=metrics,
            provider="intervals", now=captured)

    def test_view_expoe_pontos_observados_e_unidade_implicita(self):
        snap = self._snapshot(events=[
            {"day": BASELINE.isoformat(), "icu_ctl": 45.0},
            {"day": TARGET.isoformat(), "icu_ctl": 50.0},
        ])
        snapshot = ui_state.build_snapshot_view(snap, now=T0)
        view = build_ctl_ramp_view(snapshot, target_day=TARGET)
        self.assertEqual(view.target_day, TARGET.isoformat())
        self.assertEqual(view.baseline_day, BASELINE.isoformat())
        self.assertEqual(view.window_days, 7)
        self.assertEqual(view.target_ctl, 50.0)
        self.assertEqual(view.baseline_ctl, 45.0)
        self.assertEqual(view.ramp_rate, 5.0)
        self.assertTrue(view.available)
        self.assertEqual(view.observed_days, 2)

    def test_view_gap_e_indisponivel(self):
        snap = self._snapshot(events=[
            {"day": BASELINE.isoformat(), "icu_ctl": 45.0},
        ])
        view = build_ctl_ramp_view(ui_state.build_snapshot_view(snap, now=T0),
                                   target_day=TARGET)
        self.assertIsNone(view.target_ctl)
        self.assertEqual(view.baseline_ctl, 45.0)
        self.assertIsNone(view.ramp_rate)
        self.assertFalse(view.available)

    def test_pmc_datado_e_ultima_observacao_do_mesmo_dia(self):
        snap = self._snapshot(
            events=[
                {"day": BASELINE.isoformat(), "icu_ctl": 45.0},
                {"day": TARGET.isoformat(), "icu_ctl": 48.0},
            ], metrics={"day": TARGET.isoformat(), "ctl": 50.0, "tsb": -10.0})
        view = build_ctl_ramp_view(ui_state.build_snapshot_view(snap, now=T0),
                                   target_day=TARGET)
        self.assertEqual(view.target_ctl, 50.0)
        self.assertEqual(view.ramp_rate, 5.0)

    def test_snapshot_stale_nao_bloqueia_metrica(self):
        snap = self._snapshot(events=[
            {"day": BASELINE.isoformat(), "icu_ctl": 45.0},
            {"day": TARGET.isoformat(), "icu_ctl": 50.0},
        ])
        later = T0 + timedelta(days=3)
        view = build_ctl_ramp_view(ui_state.build_snapshot_view(snap, now=later),
                                   target_day=TARGET)
        self.assertEqual(view.freshness.status, "stale")
        self.assertEqual(view.ramp_rate, 5.0)

    def test_serializacao(self):
        view = build_ctl_ramp_view(None, target_day=TARGET)
        payload = view.to_dict()
        self.assertEqual(payload["target_day"], TARGET.isoformat())
        self.assertEqual(payload["window_days"], DEFAULT_CTL_RAMP_WINDOW_DAYS)
        self.assertIsNone(payload["ramp_rate"])
        self.assertIsNone(payload["freshness"])
        self.assertEqual(json.loads(json.dumps(payload)), payload)


class AdvisoryTest(unittest.TestCase):
    def test_boundary_e_status(self):
        cases = [
            (None, 5.0, CtlRampAdvisoryStatus.UNAVAILABLE),
            (4.9, 5.0, CtlRampAdvisoryStatus.WITHIN_ADVISORY_RANGE),
            (5.0, 5.0, CtlRampAdvisoryStatus.HIGH_RAMP),
            (5.1, 5.0, CtlRampAdvisoryStatus.HIGH_RAMP),
            (-5.0, 5.0, CtlRampAdvisoryStatus.WITHIN_ADVISORY_RANGE),
        ]
        for rate, threshold, expected in cases:
            with self.subTest(rate=rate, threshold=threshold):
                self.assertIs(evaluate_ctl_ramp_advisory(
                    rate, max_ramp_points=threshold).status, expected)

    def test_threshold_customizado(self):
        self.assertIs(evaluate_ctl_ramp_advisory(
            5.0, max_ramp_points=6.0).status,
            CtlRampAdvisoryStatus.WITHIN_ADVISORY_RANGE)
        self.assertIs(evaluate_ctl_ramp_advisory(
            5.0, max_ramp_points=4.0).status,
            CtlRampAdvisoryStatus.HIGH_RAMP)

    def test_threshold_invalido(self):
        for value in (None, "5", math.nan, math.inf, -math.inf, -1, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_max_ramp_points(value)

    def test_serializacao_e_mensagem_neutra(self):
        advisory = evaluate_ctl_ramp_advisory(5.0, max_ramp_points=5.0)
        payload = advisory.to_dict()
        self.assertEqual(payload["status"], "high_ramp")
        self.assertEqual(payload["ramp_rate"], 5.0)
        self.assertEqual(payload["max_ramp_points"], 5.0)
        for word in ("reduz", "troca", "deload", "cancela"):
            self.assertNotIn(word, payload["message"].lower())


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

    def _save_snapshot(self):
        snap = TrainingSnapshot.capture(events=[
            {"day": BASELINE.isoformat(), "icu_ctl": 45.0},
            {"day": TARGET.isoformat(), "icu_ctl": 50.0},
        ], wellness=[], activities=[], provider="intervals", now=T0)
        self.app.save_training_snapshot(snap)

    def test_offline_local_view_e_advisory(self):
        self._save_snapshot()
        view = self.app.get_ctl_ramp_view(target_day=TARGET, now=T0)
        advisory = self.app.get_ctl_ramp_advisory(
            target_day=TARGET, max_ramp_points=5.0, now=T0)
        self.assertEqual(view.ramp_rate, 5.0)
        self.assertIs(advisory.status, CtlRampAdvisoryStatus.HIGH_RAMP)

    def test_query_nao_tem_side_effects_nem_stdout(self):
        self.app.save_plan([{"day": TARGET.isoformat(), "name": "A",
                            "external_id": "e1"}], goal="ftp-builder")
        self._save_snapshot()
        plan_before = self.plan_file.read_text(encoding="utf-8")
        snapshot_before = self.snapshot_file.read_text(encoding="utf-8")
        plan_mtime = self.plan_file.stat().st_mtime_ns
        snapshot_mtime = self.snapshot_file.stat().st_mtime_ns
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.app.get_ctl_ramp_advisory(
                target_day=TARGET, max_ramp_points=5.0, now=T0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), plan_before)
        self.assertEqual(self.snapshot_file.read_text(encoding="utf-8"),
                         snapshot_before)
        self.assertEqual(self.plan_file.stat().st_mtime_ns, plan_mtime)
        self.assertEqual(self.snapshot_file.stat().st_mtime_ns, snapshot_mtime)


class ArchitectureGuardrailTest(unittest.TestCase):
    def test_metric_nao_conhece_policy_nem_provider(self):
        code = _code_only(ui_state.__file__)
        for prohibited in ("CtlRampAdvisory", "max_ramp_points", "icu_",
                           "IntervalsAdapter", "provider_fields", "requests"):
            self.assertNotIn(prohibited, code)

    def test_policy_nao_recalcula_ctl_nem_importa_prescricao(self):
        code = _code_only(ctl_ramp_advisory.__file__)
        for prohibited in ("derive_ctl_ramp_rate", "CtlRampView", "PmcView",
                           "ReadinessAction", "readiness_decision", "build_plan",
                           "save_plan", "provider", "requests"):
            self.assertNotIn(prohibited, code)


if __name__ == "__main__":
    unittest.main()
