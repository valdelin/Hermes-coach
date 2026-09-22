import contextlib
import io
import tempfile
import types
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from src import training_plan as tp
from src.plan import (build_plan, load_plan_meta, save_plan,
                      DEFAULT_FTP, DEFAULT_TRAINING_DAYS)


class _FakeClient:
    """IntervalsClient fake: nenhuma rede nos testes."""

    def events(self, **params):
        return []

    def wellness(self, **params):
        return []


def steady_power(watts, minutes=50):
    return [watts] * int(minutes * 60)


class _ScanClient(_FakeClient):
    """Fake com o fluxo do ftp-scan: 1 evento fora do plano, 50 min a 200W."""

    def __init__(self):
        self.puts = []

    def events(self, **params):
        return [{"external_id": "zwift-x", "paired_activity_id": "i1",
                 "start_date_local": "2026-09-18T19:00:00",
                 "name": "Zwift - pedal fora"}]

    def activity(self, activity_id):
        return {"source": "UPLOAD", "type": "VirtualRide",
                "moving_time": 50 * 60, "device_watts": True,
                "stream_types": ["time", "watts"],
                "icu_weighted_avg_watts": 200, "icu_pm_ftp": 190}

    def activity_streams(self, activity_id, types=("watts", "time")):
        power = steady_power(200, 50)
        return {"watts": power, "time": list(range(len(power)))}

    def sport_settings(self):
        return [{"id": 31898, "types": ["Ride", "VirtualRide"],
                 "indoor_ftp": 182, "ftp": 183,
                 "created": "x", "updated": "y"}]

    def put_sport_settings(self, sport_settings_id, payload):
        self.puts.append((sport_settings_id, payload))
        return 200, payload


class _NoopReconcile:
    """Substituto puro de src.plan.reconcile (nao altera o plano)."""

    def __call__(self, plan, events, ftp=DEFAULT_FTP,
                 training_days=DEFAULT_TRAINING_DAYS):
        return plan, []


class ReconcileMetaTest(unittest.TestCase):
    """BUG #8: cmd_reconcile regravava plan.json com save_plan() sem a meta
    (goal/race_date/ftp_test_date) -> virava lista pura e a meta sumia."""

    def test_reconcile_preserva_meta_do_plan_json(self):
        plan = build_plan([], 0, ftp=182, days=2, goal="ftp-builder",
                          start=date(2026, 9, 14))
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "plan.json"
            save_plan(plan, str(path), goal="ftp-builder", race_date=None,
                      ftp_test_date="2026-10-22")

            orig_plan_file, orig_client, orig_reconcile = (
                tp.PLAN_FILE, tp.get_client, tp.reconcile)
            try:
                tp.PLAN_FILE = path
                tp.get_client = lambda: _FakeClient()
                tp.reconcile = _NoopReconcile()
                args = types.SimpleNamespace(days=7, show=False)
                tp.cmd_reconcile(args)
            finally:
                tp.PLAN_FILE, tp.get_client, tp.reconcile = (
                    orig_plan_file, orig_client, orig_reconcile)

            self.assertEqual(load_plan_meta(str(path)),
                             {"goal": "ftp-builder", "race_date": None,
                              "ftp_test_date": "2026-10-22", "ftp_candidates": {}})

    def test_reconcile_formato_antigo_sem_meta_continua_lista_pura(self):
        plan = build_plan([], 0, ftp=182, days=2, start=date(2026, 9, 14))
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "plan.json"
            save_plan(plan, str(path))  # sem GOAL -> formato antigo
            orig_plan_file, orig_client, orig_reconcile = (
                tp.PLAN_FILE, tp.get_client, tp.reconcile)
            try:
                tp.PLAN_FILE = path
                tp.get_client = lambda: _FakeClient()
                tp.reconcile = _NoopReconcile()
                args = types.SimpleNamespace(days=7, show=False)
                tp.cmd_reconcile(args)
            finally:
                tp.PLAN_FILE, tp.get_client, tp.reconcile = (
                    orig_plan_file, orig_client, orig_reconcile)
            self.assertEqual(load_plan_meta(str(path)),
                             {"goal": None, "race_date": None,
                              "ftp_test_date": None, "ftp_candidates": {}})


def _scan_fixture():
    """Monta tmp dir isolado: plan.json com meta + .env fake. Devolve
    (tmp, root, env, path, orig) e patcheia PLAN_FILE/ENV_FILE/PROJECT_ROOT."""
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    env = root / ".env"
    env.write_text("FTP=182\n", encoding="utf-8")
    path = root / "plan.json"
    save_plan([], str(path), goal="ftp-builder", race_date=None,
              ftp_test_date=None)
    orig = (tp.PLAN_FILE, tp.ENV_FILE, tp.PROJECT_ROOT,
            tp.get_client, tp.get_ftp)
    tp.PLAN_FILE = path
    tp.ENV_FILE = env
    tp.PROJECT_ROOT = root
    return tmp, root, env, path, orig


def _restore_scan(orig):
    (tp.PLAN_FILE, tp.ENV_FILE, tp.PROJECT_ROOT,
     tp.get_client, tp.get_ftp) = orig


class ScanFtpTest(unittest.TestCase):
    """FTP sugerido a partir de treino fora do plano (#6)."""

    def _run(self, answer):
        fake = _ScanClient()
        tmp, root, env, path, orig = _scan_fixture()
        try:
            tp.get_client = lambda: fake
            tp.get_ftp = lambda: 182
            args = types.SimpleNamespace(days=45)
            with mock.patch("builtins.input", return_value=answer):
                tp.cmd_ftp_scan(args)
        finally:
            _restore_scan(orig)
        return tmp, fake, root, env, path

    def test_aplica_com_confirmacao(self):
        tmp, fake, root, env, path = self._run("s")
        try:
            # .env e backup atualizados
            self.assertIn("FTP=190", env.read_text())
            self.assertIn("FTP=190", (root / ".env.bak").read_text())
            # Intervals atualizado: PUT na entrada Ride, sem created/updated
            self.assertEqual(len(fake.puts), 1)
            sid, payload = fake.puts[0]
            self.assertEqual(sid, 31898)
            self.assertEqual(payload["indoor_ftp"], 190)
            self.assertNotIn("created", payload)
            self.assertNotIn("updated", payload)
            # meta registra o candidato como aplicado
            rec = load_plan_meta(str(path))["ftp_candidates"]["i1"]
            self.assertTrue(rec["suggests_new"])
            self.assertTrue(rec["applied"])
            self.assertEqual(rec["proposed_ftp"], 190)
        finally:
            tmp.cleanup()

    def test_nao_aplica_sem_confirmacao(self):
        tmp, fake, root, env, path = self._run("n")
        try:
            self.assertEqual(fake.puts, [])
            self.assertIn("FTP=182", env.read_text())
            self.assertFalse((root / ".env.bak").exists())
            rec = load_plan_meta(str(path))["ftp_candidates"]["i1"]
            self.assertFalse(rec["applied"])
        finally:
            tmp.cleanup()


class BuildPreservesFtpCandidatesTest(unittest.TestCase):
    def test_build_nao_apaga_candidatos_da_meta(self):
        tmp, root, env, path, orig = _scan_fixture()
        try:
            save_plan([], str(path), goal="ftp-builder", race_date=None,
                      ftp_test_date=None,
                      ftp_candidates={"i1": {"activity_id": "i1",
                                             "proposed_ftp": 190,
                                             "applied": False}})
            tp.get_client = lambda: _FakeClient()
            tp.get_ftp = lambda: 182
            tp.get_goal = lambda: "ftp-builder"
            tp.get_race_date = lambda: None
            tp.get_weekly_hours = lambda: None
            tp.get_long_day = lambda: None
            tp.get_training_days = lambda: DEFAULT_TRAINING_DAYS
            tp.build_plan = lambda *a, **k: []
            args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None)
            tp.cmd_build(args)
            meta = load_plan_meta(str(path))
            self.assertEqual(meta["ftp_candidates"]["i1"]["proposed_ftp"], 190)
        finally:
            _restore_scan(orig)
            tmp.cleanup()


class PendingFtpHintTest(unittest.TestCase):
    def test_info_mostra_aviso_quando_candidato_pendente(self):
        tmp, root, env, path, orig = _scan_fixture()
        try:
            save_plan([], str(path), goal="ftp-builder", race_date=None,
                      ftp_test_date=None,
                      ftp_candidates={"i1": {
                          "activity_id": "i1", "day": "2026-09-18",
                          "name": "Pedal fora", "proposed_ftp": 190,
                          "suggests_new": True, "applied": False}})
            tp.get_client = lambda: _FakeClient()
            tp.get_ftp = lambda: 182
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                tp.cmd_info(types.SimpleNamespace(days=7))
            self.assertIn("ftp-scan", out.getvalue())
        finally:
            _restore_scan(orig)
            tmp.cleanup()

    def test_info_sem_aviso_quando_nada_pendente(self):
        tmp, root, env, path, orig = _scan_fixture()
        try:
            tp.get_client = lambda: _FakeClient()
            tp.get_ftp = lambda: 182
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                tp.cmd_info(types.SimpleNamespace(days=7))
            self.assertNotIn("ftp-scan", out.getvalue())
        finally:
            _restore_scan(orig)
            tmp.cleanup()


if __name__ == "__main__":
    unittest.main()