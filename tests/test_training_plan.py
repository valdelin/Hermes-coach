import tempfile
import types
import unittest
from datetime import date
from pathlib import Path

from src import training_plan as tp
from src.plan import (build_plan, load_plan_meta, save_plan,
                      DEFAULT_FTP, DEFAULT_TRAINING_DAYS)


class _FakeClient:
    """IntervalsClient fake: nenhuma rede nos testes."""

    def events(self, **params):
        return []


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
                              "ftp_test_date": "2026-10-22"})

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
                              "ftp_test_date": None})


if __name__ == "__main__":
    unittest.main()