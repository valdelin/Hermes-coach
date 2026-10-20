"""INSIGHT-6 — presentation offline opt-in no adapter CLI."""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from src.ftp_evidence import FtpEvidenceRepository
from src.ftp_history import FtpHistory, FtpHistoryRepository
from src.insight.render import fallback_presentation
from src.snapshot import TrainingSnapshot


SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "hermes_agent.py"
SPEC = importlib.util.spec_from_file_location("hermes_agent_insight", SCRIPT)
agent = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = agent
SPEC.loader.exec_module(agent)

NOW = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)


class InsightCliTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.calls = 0

        def forbidden_client():
            self.calls += 1
            raise AssertionError("insight CLI nao pode pedir provider")

        from src.application import Application
        self.app = Application(
            plan_path=root / "plan.json", snapshot_path=root / "snapshot.json",
            ftp_history_path=root / "ftp_history.json",
            ftp_evidence_path=root / "ftp_evidence.json",
            client_factory=forbidden_client)
        self.app.save_plan([{
            "day": "2026-10-04", "name": "Limiar", "focus": "threshold",
            "planned_duration": 2400, "tss": 61.0, "ftp_watts": 210,
            "external_id": "hermes-plan-2026-10-04",
        }])
        self.workout_id = self.app.load_plan()[0]["id"]
        TrainingSnapshot.capture(now=NOW).save(self.app._snapshot_file())
        FtpHistoryRepository(self.app.ftp_history_path).save(FtpHistory())
        FtpEvidenceRepository(self.app.ftp_evidence_path).save(())

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def _files(self):
        paths = (self.app.plan_path, self.app._snapshot_file(),
                 self.app.ftp_history_path, self.app.ftp_evidence_path)
        return {path: path.read_bytes() for path in paths}

    @staticmethod
    def _run(argv):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = agent.main(argv)
        return code, output.getvalue()

    def test_feature_flag_matrix_is_opt_in_and_fail_closed(self) -> None:
        from src.insight.config import INSIGHT_ENABLED_ENV

        self.assertEqual(agent.INSIGHT_ENABLED_ENV, INSIGHT_ENABLED_ENV)
        for value in (None, "", "0", "false", "FALSE", "no", "off", "unexpected"):
            with self.subTest(value=value):
                with mock.patch.dict(os.environ, {}, clear=True):
                    if value is not None:
                        os.environ[agent.INSIGHT_ENABLED_ENV] = value
                    self.assertFalse(agent.insight_enabled())
        for value in ("1", "true", "TRUE", "yes", "on"):
            with self.subTest(value=value):
                self.assertTrue(agent.insight_enabled(value))

    def test_off_does_not_build_view_or_fallback_and_is_invariant(self) -> None:
        before = self._files()
        with mock.patch.dict(os.environ, {}, clear=True), \
                mock.patch.object(agent, "build_insight_application") as build, \
                mock.patch("src.insight.render.fallback_presentation") as fallback:
            code, output = self._run(["insight"])

        self.assertEqual(code, 0)
        self.assertEqual(output, "Insight is disabled.\n")
        build.assert_not_called()
        fallback.assert_not_called()
        self.assertEqual(self._files(), before)
        self.assertEqual(self.calls, 0)

    def test_on_uses_real_view_and_deterministic_fallback_only(self) -> None:
        before = self._files()
        expected_view = self.app.get_insight_view(
            subject="athlete", workout_id=self.workout_id, now=NOW)
        expected = fallback_presentation(expected_view)
        with mock.patch.dict(os.environ, {agent.INSIGHT_ENABLED_ENV: "on"}, clear=True), \
                mock.patch.object(agent, "build_insight_application", return_value=self.app), \
                mock.patch.object(self.app, "get_insight_view", wraps=self.app.get_insight_view) as view, \
                mock.patch("src.insight.render.fallback_presentation", wraps=fallback_presentation) as fallback:
            code, output = self._run([
                "insight", "--subject", "athlete", "--workout-id", self.workout_id])

        self.assertEqual(code, 0)
        view.assert_called_once_with(subject="athlete", workout_id=self.workout_id)
        fallback.assert_called_once()
        self.assertEqual(output, "\n".join((
            "INSIGHT", f"headline: {expected.headline}",
            f"explanation: {expected.explanation}",
            f"next_action_text: {expected.next_action_text}", "")))
        self.assertNotIn("caution_text:", output)
        self.assertEqual(self._files(), before)
        self.assertEqual(self.calls, 0)

    def test_both_flags_on_route_through_application_without_leaking_secret(self) -> None:
        from src.insight.config import INSIGHT_ONLINE_ENABLED_ENV
        from src.insight.runtime import InsightRuntimeResult, InsightRuntimeStatus

        expected_view = self.app.get_insight_view(
            subject="athlete", workout_id=self.workout_id, now=NOW)
        presentation = fallback_presentation(expected_view)
        result = InsightRuntimeResult(
            presentation=presentation, status=InsightRuntimeStatus.SUCCESS,
            provenance=None)
        env = {agent.INSIGHT_ENABLED_ENV: "on", INSIGHT_ONLINE_ENABLED_ENV: "on",
               "OPENAI_API_KEY": "__SECRET_OPENAI_API_KEY__"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(agent, "build_insight_application", return_value=self.app), \
                mock.patch.object(
                    self.app, "get_insight_runtime_result", return_value=result) as wired:
            code, output = self._run([
                "insight", "--subject", "athlete", "--workout-id", self.workout_id])

        self.assertEqual(code, 0)
        self.assertNotIn("__SECRET_OPENAI_API_KEY__", output)
        self.assertIn(presentation.headline, output)
        kwargs = wired.call_args.kwargs
        self.assertTrue(kwargs["config"].insight_enabled)
        self.assertTrue(kwargs["config"].online_enabled)
        self.assertEqual(kwargs["workout_id"], self.workout_id)
        self.assertIsNotNone(kwargs["executed_at"].tzinfo)
        self.assertEqual(self.calls, 0)

    def test_cmd_insight_uses_injected_clock(self) -> None:
        import argparse
        from src.insight.runtime import InsightRuntimeResult, InsightRuntimeStatus

        presentation = fallback_presentation(
            self.app.get_insight_view(
                subject="athlete", workout_id=self.workout_id, now=NOW))
        result = InsightRuntimeResult(
            presentation=presentation, status=InsightRuntimeStatus.FALLBACK_DISABLED,
            provenance=None)
        args = argparse.Namespace(subject="athlete", workout_id=self.workout_id)
        with mock.patch.dict(
                os.environ, {agent.INSIGHT_ENABLED_ENV: "on"}, clear=True), \
                mock.patch.object(agent, "build_insight_application", return_value=self.app), \
                mock.patch.object(
                    self.app, "get_insight_runtime_result", return_value=result) as wired, \
                contextlib.redirect_stdout(io.StringIO()):
            code = agent.cmd_insight(args, now=NOW)

        self.assertEqual(code, 0)
        self.assertEqual(wired.call_args.kwargs["executed_at"], NOW)

    def test_default_subject_and_missing_workout_follow_contract(self) -> None:
        with mock.patch.dict(os.environ, {agent.INSIGHT_ENABLED_ENV: "yes"}, clear=True), \
                mock.patch.object(agent, "build_insight_application", return_value=self.app):
            code, _ = self._run(["insight"])
            self.assertEqual(code, 0)
            with self.assertRaises(KeyError):
                agent.main(["insight", "--workout-id", "missing"])

    def test_script_entry_point_stays_importable_without_repo_root(self) -> None:
        import subprocess
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"], cwd=self.tmp.name,
            capture_output=True, text=True)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertNotIn("ModuleNotFoundError", completed.stderr)

    def test_presentation_fields_are_print_only_not_domain_control(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        tree = ast.parse(source)
        printer = next(node for node in ast.walk(tree)
                       if isinstance(node, ast.FunctionDef)
                       and node.name == "print_insight_presentation")
        segment = ast.get_source_segment(source, printer)
        self.assertIn("presentation.next_action_text", segment)
        self.assertNotIn("if presentation.next_action_text", segment)
        command = next(node for node in ast.walk(tree)
                       if isinstance(node, ast.FunctionDef) and node.name == "cmd_insight")
        command_source = ast.get_source_segment(source, command)
        for forbidden in ("save_", "sync_", "record_", "confirm_", "client(",
                          "provider", "generate", "requests", "http"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, command_source)


if __name__ == "__main__":
    unittest.main()
