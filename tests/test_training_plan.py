import contextlib
import io
import json
import os
import re
import tempfile
import types
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from src import training_plan as tp
from src import plan as src_plan
from src import recovery as src_recovery
from src.plan import (avg_load, build_plan, load_plan, load_plan_meta, reconcile,
                      save_plan, weekly_budget, DEFAULT_FTP,
                      DEFAULT_TRAINING_DAYS)


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
                 training_days=DEFAULT_TRAINING_DAYS, budget=None,
                 absorbed_ids=None):
        return plan, [], {"absorbed_tss": 0.0, "missed_tss": 0.0,
                          "absorbable_tss": 0.0,
                          "already_absorbed_tss": 0.0,
                          "absorbed_ids": list(absorbed_ids or ())}


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
                               "ftp_test_date": "2026-10-22", "ftp_candidates": {},
                               "absorbed_ids": [], "block_context": None})

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
                               "ftp_test_date": None, "ftp_candidates": {},
                               "absorbed_ids": [], "block_context": None})

    def test_reconcile_show_nao_persiste_plan_json(self):
        """`--show` e consultivo, inclusive quando reconciliation mudaria o plano."""
        plan = build_plan([], 0, ftp=182, days=2, goal="ftp-builder",
                          start=date(2026, 9, 14))
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / "plan.json"
            save_plan(plan, str(path), goal="ftp-builder", race_date=None,
                      ftp_test_date="2026-10-22")
            before = path.read_bytes()
            orig_plan_file, orig_client, orig_reconcile = (
                tp.PLAN_FILE, tp.get_client, tp.reconcile)
            try:
                tp.PLAN_FILE = path
                tp.get_client = lambda: _FakeClient()
                tp.reconcile = _NoopReconcile()
                tp.cmd_reconcile(types.SimpleNamespace(days=7, show=True))
            finally:
                tp.PLAN_FILE, tp.get_client, tp.reconcile = (
                    orig_plan_file, orig_client, orig_reconcile)

            self.assertEqual(path.read_bytes(), before)

    def test_reconcile_nao_reabsorve_falta_apos_salvar_e_recarregar(self):
        """#40: execucoes independentes nao podem compensar a mesma falta duas vezes."""
        fixed_today = date(2026, 10, 1)

        class FixedDate(date):
            @classmethod
            def today(cls):
                return fixed_today

        with mock.patch.object(src_plan, "date", FixedDate), \
                mock.patch.object(tp, "date", FixedDate):
            history = [{"external_id": f"history-{index}",
                        "paired_activity_id": f"activity-{index}",
                        "start_date_local": (fixed_today - timedelta(days=40 - index)
                                             ).isoformat() + "T07:00:00",
                        "icu_training_load": 45.0}
                       for index in range(15)]
            plan = build_plan(history, 2, ftp=182, days=12,
                              start=fixed_today - timedelta(days=7))
            past = [workout for workout in plan
                    if workout["day"] < fixed_today.isoformat()]
            missed = next(workout for workout in reversed(past)
                          if workout["focus"] == "sweetspot")
            events = history + [
                {"external_id": workout["external_id"],
                 "paired_activity_id": f"done-{index}",
                 "start_date_local": workout["day"] + "T07:00:00",
                 "icu_training_load": workout["tss"]}
                for index, workout in enumerate(past)
                if workout["external_id"] != missed["external_id"]
            ]

            class Client:
                def events(self, **_params):
                    return events

            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "plan.json"
                save_plan(plan, str(path), goal="ftp-builder", race_date=None)
                original = (tp.PLAN_FILE, tp.get_client, tp.get_ftp,
                            tp.get_training_days)
                try:
                    tp.PLAN_FILE = path
                    tp.get_client = lambda: Client()
                    tp.get_ftp = lambda: 182
                    tp.get_training_days = lambda: (0, 1, 2, 3, 4)
                    args = types.SimpleNamespace(days=45, show=False)
                    tp.cmd_reconcile(args)
                    first_run = {workout["external_id"]: workout["tss"]
                                 for workout in load_plan(path)}
                    first_meta = load_plan_meta(path)

                    # Nova execucao le o arquivo que a primeira acabou de gravar.
                    tp.cmd_reconcile(args)
                    second_run = {workout["external_id"]: workout["tss"]
                                  for workout in load_plan(path)}
                    second_meta = load_plan_meta(path)
                finally:
                    (tp.PLAN_FILE, tp.get_client, tp.get_ftp,
                     tp.get_training_days) = original

        self.assertEqual(first_run, second_run)
        self.assertEqual(first_meta["absorbed_ids"], [missed["external_id"]])
        self.assertEqual(second_meta["absorbed_ids"], first_meta["absorbed_ids"])

    def test_ids_absorvidos_permitem_nova_falta_sem_repetir_a_antiga(self):
        """#40: A ja absorvido e B novo sao tratados uma unica vez cada."""
        fixed_today = date(2026, 10, 1)

        class FixedDate(date):
            @classmethod
            def today(cls):
                return fixed_today

        with mock.patch.object(src_plan, "date", FixedDate):
            history = [{"external_id": f"history-{index}",
                        "paired_activity_id": f"activity-{index}",
                        "start_date_local": (fixed_today - timedelta(days=40 - index)
                                             ).isoformat() + "T07:00:00",
                        "icu_training_load": 45.0}
                       for index in range(15)]
            plan = build_plan(history, 2, ftp=182, days=12,
                              start=fixed_today - timedelta(days=7))
            missed = [workout for workout in plan
                      if (workout["day"] < fixed_today.isoformat()
                          and workout["focus"] == "sweetspot")]
            self.assertEqual(len(missed), 2)
            events = history + [
                {"external_id": workout["external_id"],
                 "paired_activity_id": f"done-{index}",
                 "start_date_local": workout["day"] + "T07:00:00",
                 "icu_training_load": workout["tss"]}
                for index, workout in enumerate(plan)
                if (workout["day"] < fixed_today.isoformat()
                    and workout["external_id"] not in
                    {missed[0]["external_id"], missed[1]["external_id"]})
            ]
            budget = weekly_budget(avg_load(events))
            _first_plan, _, first_info = reconcile(
                plan, events, ftp=182, budget=budget)
            _mixed_plan, _, mixed_info = reconcile(
                plan, events, ftp=182, budget=budget,
                absorbed_ids=[missed[0]["external_id"]])

        self.assertGreater(first_info["absorbed_tss"], 0)
        self.assertEqual(set(first_info["absorbed_ids"]),
                         {missed[0]["external_id"], missed[1]["external_id"]})
        self.assertEqual(mixed_info["absorbable_tss"], missed[1]["tss"])
        self.assertGreater(mixed_info["absorbed_tss"], 0)
        self.assertEqual(set(mixed_info["absorbed_ids"]),
                         {missed[0]["external_id"], missed[1]["external_id"]})


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
            tp.get_client, tp.get_ftp, tp.build_plan)
    tp.PLAN_FILE = path
    tp.ENV_FILE = env
    tp.PROJECT_ROOT = root
    return tmp, root, env, path, orig


def _restore_scan(orig):
    (tp.PLAN_FILE, tp.ENV_FILE, tp.PROJECT_ROOT,
     tp.get_client, tp.get_ftp, tp.build_plan) = orig


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

    def test_scan_registra_evidencia_no_ftp_evidence(self):
        """FTP-H2: candidato validado vira evidencia local (nunca referencia)."""
        import json as _json
        tmp, fake, root, env, path = self._run("n")
        try:
            evidence_path = Path(tmp.name) / "ftp_evidence.json"
            self.assertTrue(evidence_path.exists())
            data = _json.loads(evidence_path.read_text())
            rec = next(e for e in data["evidence"] if e["id"] == "scan-i1")
            self.assertEqual(rec["value_watts"], 190)  # 20min 200W x 0.95
            self.assertEqual(rec["source"], "ftp_scan")
            self.assertTrue(rec["proposes_new"])
            self.assertTrue(rec["quality_ok"])
            self.assertEqual(rec["activity_id"], "i1")
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
                                             "applied": False}},
                      absorbed_ids=["hermes-plan-2026-09-01"])
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
            self.assertEqual(meta["absorbed_ids"], ["hermes-plan-2026-09-01"])
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


class NoPowerModeTest(unittest.TestCase):
    """Issue #3: plano sem medidor de potencia (modo FC com FTHR)."""

    def _fixture_with_fthr(self, fthr="182"):
        tmp = tempfile.TemporaryDirectory()
        root = Path(tmp.name)
        env = root / ".env"
        env.write_text(f"FTP=182\nFTHR={fthr}\n", encoding="utf-8")
        path = root / "plan.json"
        save_plan([], str(path), goal="ftp-builder", race_date=None,
                  ftp_test_date=None)
        orig = (tp.PLAN_FILE, tp.ENV_FILE, tp.PROJECT_ROOT,
                tp.get_client, tp.get_ftp)
        tp.PLAN_FILE = path
        tp.ENV_FILE = env
        tp.PROJECT_ROOT = root
        return tmp, root, env, path, orig

    def _restore(self, orig):
        (tp.PLAN_FILE, tp.ENV_FILE, tp.PROJECT_ROOT,
         tp.get_client, tp.get_ftp) = orig
        # load_env usa setdefault: limpa o FTHR injetado pelo .env do teste
        # para nao vazar para os testes seguintes.
        os.environ.pop("FTHR", None)

    def test_get_fthr_ler_env(self):
        tmp, root, env, path, orig = self._fixture_with_fthr("182")
        try:
            self.assertEqual(tp.get_fthr(), 182)
        finally:
            self._restore(orig)
            tmp.cleanup()

    def test_get_fthr_ausente_ou_invalido(self):
        tmp, root, env, path, orig = self._fixture_with_fthr("")
        try:
            self.assertIsNone(tp.get_fthr())
        finally:
            self._restore(orig)
            tmp.cleanup()

        tmp, root, env, path, orig = self._fixture_with_fthr("abc")
        out = io.StringIO()
        try:
            with contextlib.redirect_stdout(out):
                val = tp.get_fthr()
            self.assertIsNone(val)
            self.assertIn("aviso", out.getvalue())
        finally:
            self._restore(orig)
            tmp.cleanup()

    def test_build_no_power_sem_fthr_aborta(self):
        tmp, root, env, path, orig = self._fixture_with_fthr("")
        try:
            tp.get_client = lambda: _FakeClient()
            tp.get_ftp = lambda: 182
            tp.get_goal = lambda: "ftp-builder"
            tp.get_race_date = lambda: None
            tp.get_weekly_hours = lambda: None
            tp.get_long_day = lambda: None
            tp.get_ftp_test_date = lambda: None
            args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None,
                                         no_power=True)
            out = io.StringIO()
            plan = None
            with contextlib.redirect_stdout(out):
                plan = tp.cmd_build(args)
            self.assertIsNone(plan)
            self.assertIn("--no-power", out.getvalue())
            self.assertIn("FTHR", out.getvalue())
        finally:
            self._restore(orig)
            tmp.cleanup()

    def test_build_no_power_carimba_hr_mode_e_avisa(self):
        tmp, root, env, path, orig = self._fixture_with_fthr("182")
        try:
            tp.get_client = lambda: _FakeClient()
            tp.get_ftp = lambda: 182
            tp.get_goal = lambda: "ftp-builder"
            tp.get_race_date = lambda: None
            tp.get_weekly_hours = lambda: None
            tp.get_long_day = lambda: None
            tp.get_ftp_test_date = lambda: None
            args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None,
                                         no_power=True)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                tp.cmd_build(args)
            self.assertIn("sem medidor de potencia", out.getvalue())
            meta = load_plan_meta(str(path))
            workouts = load_plan(str(path))
            self.assertTrue(all(w.get("hr_mode") for w in workouts),
                            "workouts devem carregar hr_mode")
            self.assertEqual(meta["goal"], "ftp-builder")
        finally:
            self._restore(orig)
            tmp.cleanup()

    def test_build_imprime_fase_advisory(self):
        tmp, root, env, path, orig = self._fixture_with_fthr("182")
        try:
            tp.get_client = lambda: _FakeClient()
            tp.get_ftp = lambda: 182
            tp.get_goal = lambda: "ftp-builder"
            tp.get_race_date = lambda: None
            tp.get_weekly_hours = lambda: None
            tp.get_long_day = lambda: None
            tp.get_ftp_test_date = lambda: None
            args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None,
                                         no_power=False)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                tp.cmd_build(args)
            self.assertIn("Fase do plano: build", out.getvalue())
            meta = load_plan_meta(str(path))
            self.assertEqual(meta["goal"], "ftp-builder")
        finally:
            self._restore(orig)
            tmp.cleanup()

    def test_push_envia_target_heart_rate_no_modo_fc(self):
        _client = _FakeClient()
        tmp, root, env, path, orig = self._fixture_with_fthr("182")
        try:
            plan = build_plan([], 2, ftp=182, days=1,
                              start=date(2026, 9, 28), hr_mode=True)
            save_plan(plan, str(path), goal="ftp-builder", race_date=None,
                      ftp_test_date=None)
            orig_client, orig_plan_file = tp.get_client, tp.PLAN_FILE
            tp.PLAN_FILE = path
            tp.get_client = lambda: _client
            sent = []

            def fake_create_events(batch):
                sent.extend(batch)
                return 200, batch

            _client.create_events = fake_create_events
            args = types.SimpleNamespace(start="2026-09-28", dry_run=False)
            tp.cmd_push(args)
            self.assertEqual(sent[0]["target"], "HR")
            self.assertIn("FTHR", sent[0]["description"])
            self.assertIn("RPE", sent[0]["description"])
            tp.get_client, tp.PLAN_FILE = orig_client, orig_plan_file
        finally:
            self._restore(orig)
            tmp.cleanup()


class _RecoveryClient(_FakeClient):
    """Historico paginado: 2 treinos feitos em 2026, 2 em 2021 e 1 planejado
    nao-feito (deve ficar fora da carga real)."""

    def events(self, **params):
        oldest = params.get("oldest", "")[:10]
        if oldest and oldest >= "2026-09-15":
            return [
                {"id": "r1", "paired_activity_id": "p1",
                 "start_date_local": "2026-09-16T00:00:00",
                 "icu_training_load": 33, "name": "feito 1"},
                {"id": "r2", "paired_activity_id": "p2",
                 "start_date_local": "2026-09-18T00:00:00",
                 "icu_training_load": 41, "name": "feito 2"},
                {"id": "r3", "start_date_local": "2026-09-19T00:00:00",
                 "icu_training_load": 55, "name": "planejado nao-feito"},
            ]
        if oldest and "2021-10-15" <= oldest < "2026-09-15":
            return [
                {"id": "o1", "paired_activity_id": "po1",
                 "start_date_local": "2021-12-01T00:00:00",
                 "icu_training_load": 60, "name": "antigo 1"},
                {"id": "o2", "paired_activity_id": "po2",
                 "start_date_local": "2021-12-08T00:00:00",
                 "icu_training_load": 70, "name": "antigo 2"},
            ]
        return []


class _SummaryClient(_FakeClient):
    """1 treino feito (dia) + 1 planejado-nao-feito que deve ficar fora.

    `many_loads=True` gera uma temporada deterministic de treinos seg-sex
    nos ultimos ~70 dias, para exercitar PMC e carga semanal.
    """

    def __init__(self, many_loads=False):
        self.many_loads = many_loads

    def activity(self, aid):
        if not self.many_loads:
            return {"name": "Zwift - Treino de Limiar FTP", "type": "VirtualRide",
                    "moving_time": 3225, "distance": 24732.67,
                    "total_elevation_gain": 175.0, "icu_training_load": 58,
                    "icu_average_watts": 133, "icu_weighted_avg_watts": 147,
                    "average_heartrate": 153}
        day = date.fromisoformat(aid.split("_")[1])
        return {"name": "Treino", "type": "VirtualRide",
                "moving_time": 3600, "distance": 30000.0 + (day.toordinal() % 97) * 100,
                "icu_training_load": 30 + day.toordinal() % 41,
                "icu_average_watts": 140, "icu_weighted_avg_watts": 148,
                "average_heartrate": 150}

    def events(self, **params):
        if not self.many_loads:
            return [
                {"id": "s1", "paired_activity_id": "i1",
                 "start_date_local": "2026-09-23T15:37:38",
                 "name": "Treino de Limiar FTP",
                 "icu_training_load": 58},
                {"id": "s2", "start_date_local": "2026-09-23T00:00:00",
                 "name": "nao feito"},
            ]
        oldest = date.fromisoformat(params.get("oldest", "")[:10])
        newest = date.fromisoformat(params.get("newest", "")[:10])
        out = []
        d = oldest
        while d <= newest:
            if d.weekday() < 5:  # seg-sex, igual ao padrao do plano
                out.append({"id": f"s_{d.isoformat()}",
                            "paired_activity_id": f"a_{d.isoformat()}",
                            "start_date_local": f"{d}T18:00:00",
                            "name": "Treino",
                            "icu_training_load": 30 + d.toordinal() % 41})
            d += timedelta(days=1)
        return out


class SummaryCliTest(unittest.TestCase):
    def test_cmd_summary_relata_dia_e_detalhe_por_treino(self):
        orig_client = tp.get_client
        tp.get_client = lambda: _SummaryClient()
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tp.cmd_summary(types.SimpleNamespace(
                    period="day", date=date(2026, 9, 23), chart="none",
                    start=None, end=None))
            out = buf.getvalue()
            self.assertIn("=== RESUMO DO DIA", out)
            self.assertIn("carga total: 58 TSS", out)
            self.assertIn("Treino de Limiar", out)
        finally:
            tp.get_client = orig_client

    def test_cmd_summary_com_pmc_traer_graficos(self):
        orig_client = tp.get_client
        tp.get_client = lambda: _SummaryClient(many_loads=True)
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tp.cmd_summary(types.SimpleNamespace(
                    period="week", date=date(2026, 9, 23), chart="auto",
                    export=None, start=None, end=None))
            out = buf.getvalue()
            self.assertIn("=== PMC (fitness/fadiga/form) ===", out)
            self.assertIn("CTL", out)
            self.assertIn("ATL", out)
            self.assertIn("TSB", out)
            self.assertIn("=== CARGA SEMANAL ===", out)
            self.assertIn("TSS/semana", out)
        finally:
            tp.get_client = orig_client

    def test_cmd_summary_export_html_gera_arquivo(self):
        orig_client = tp.get_client
        tp.get_client = lambda: _SummaryClient()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                path = os.path.join(tmp, "resumo.html")
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf):
                    tp.cmd_summary(types.SimpleNamespace(
                        period="day", date=date(2026, 9, 23), chart="none",
                        export=path, start=None, end=None))
                self.assertIn(f"Exportado: {path}", buf.getvalue())
                with open(path, encoding="utf-8") as f:
                    html = f.read()
                self.assertIn("Treino de Limiar FTP", html)
                self.assertIn("<svg ", html)
                self.assertIn("58 TSS", html)
        finally:
            tp.get_client = orig_client

    def test_summary_export_usa_mesma_sessao_canonica_para_metadados_e_perfil(self):
        class _Readiness:
            def to_dict(self):
                return {"available": True, "reference_day": "2026-10-06",
                        "heuristic_level": "GREEN", "heuristic_score": .8,
                        "heuristic_confidence": .43}

        class _App:
            def load_plan(self):
                return [{
                    "day": "2026-10-06", "focus": "zone2",
                    "planned_duration": 3840,
                    "name": "2026-10-06 - Treino de Zona 2",
                    "tss": 51.0, "intensity_factor": .69, "ftp_watts": 183,
                    "params": {
                        "warmup_sec": 600, "warmup_power_low": .55,
                        "warmup_power_high": .75, "repeats": 2,
                        "on_sec": 1140, "on_power": .75,
                        "off_sec": 180, "off_power": .55,
                        "cooldown_sec": 600, "cooldown_power_low": .70,
                        "cooldown_power_high": .45,
                    },
                }]

            def get_readiness_view(self, *, today):
                self.readiness_day = today
                return _Readiness()

        rows = [{"name": "Atividade concluída diferente", "day": "2026-10-05",
                 "type": "VirtualRide", "time_s": 3600, "distance_m": 0,
                 "elevation_m": 0, "load": 99.0, "avg_power": None,
                 "np": None, "avg_hr": None}]
        agg = tp.activity_summary.summarize(rows)
        app = _App()
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "resumo.html")
            args = types.SimpleNamespace(export=path, theme=None, period="2m")
            tp._summary_export(
                app, _SummaryClient(many_loads=True), args,
                date(2026, 8, 7), date(2026, 10, 5), rows, agg,
                today=date(2026, 10, 6))
            with open(path, encoding="utf-8") as f:
                html = f.read()
        self.assertEqual(app.readiness_day, date(2026, 10, 6))
        self.assertIn("Treino de Zona 2", html)
        self.assertIn("1h04", html)
        self.assertIn("51 TSS", html)
        self.assertIn('class="planned-profile"', html)
        self.assertIn('&quot;planned_tss&quot;:51.0', html)
        self.assertNotIn('&quot;planned_tss&quot;:99.0', html)


class SummaryVazioEDateTest(unittest.TestCase):
    """Duas regressoes do resumo (Prompt 40).

    1) Periodo sem treinos FEITOS nao podia engolir `--export`: o early
       return em `cmd_summary` abortava antes de `_summary_export` e o
       arquivo nunca era criado (exit 0, sem aviso).
    2) `--date` aceitava str (explícito) E date (default): a mistura de
       tipos levava `period_range`/`resolve_period` a TypeError e
       `done_activities` a AttributeError.
    """

    def _run_cmd_summary(self, args, *, app=None):
        patches = [
            mock.patch.object(tp, "get_client", return_value=_FakeClient()),
            (mock.patch.object(tp, "_make_app", return_value=app)
             if app is not None else mock.patch.object(
                 tp, "PLAN_FILE", Path(tempfile.mkdtemp()) / "plan.json")),
        ]
        buf = io.StringIO()
        with patches[0], patches[1]:
            with contextlib.redirect_stdout(buf):
                tp.cmd_summary(args)
        return buf.getvalue()

    def _main_summary(self, *extra):
        with mock.patch.object(tp, "get_client", return_value=_FakeClient()), \
             mock.patch.object(tp, "PLAN_FILE",
                               Path(tempfile.mkdtemp()) / "plan.json"):
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tp.main(["summary", *extra])
        return buf.getvalue()

    # -- 1. periodo vazio + export ------------------------------------
    def test_cmd_summary_export_com_periodo_vazio_gera_o_arquivo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vazio.html")
            out = self._run_cmd_summary(types.SimpleNamespace(
                period="day", date=date(2026, 10, 7), chart="none",
                export=path, start=None, end=None))
            self.assertIn("=== RESUMO DO DIA (2026-10-07 a 2026-10-07)", out)
            self.assertIn("Nenhum treino feito no periodo.", out)
            self.assertIn(f"Exportado: {path}", out)
            self.assertTrue(os.path.exists(path))
            with open(path, encoding="utf-8") as f:
                html = f.read()
        self.assertIn("<!doctype html>", html)
        self.assertIn("Nenhum treino foi realizado neste período.", html)
        # o hero nao tem mais KPI/status (PROMPT 37 §7): o RESUMO continua
        # existindo no relatorio de periodo vazio.
        self.assertIn('data-report-section="summary"', html)
        self.assertIn('data-report-group="resumo"', html)
        self.assertNotIn("<tbody></tbody>", html)

    def test_cmd_summary_export_vazio_renderiza_treino_planejado_e_prontidao(self):
        class _Readiness:
            def to_dict(self):
                return {
                    "target_day": date.today().isoformat(),
                    "model_axis_count": 7, "implemented_axis_count": 3,
                    "available_axis_count": 2, "heuristic_level": "GREEN",
                    "heuristic_score": .8, "axis_states": [
                        {"axis": "sleep", "label": "Sono",
                         "available": True, "implemented": True},
                        {"axis": "hrv", "label": "HRV",
                         "available": True, "implemented": True},
                    ],
                }

        class _App:
            def client(self):
                return _FakeClient()

            def load_plan(self):
                return [{
                    "day": date.today().isoformat(), "focus": "zone2",
                    "planned_duration": 3840,
                    "name": "2026-10-07 - Treino de Zona 2",
                    "tss": 51.0, "intensity_factor": .69, "ftp_watts": 183,
                    "params": {
                        "warmup_sec": 600, "warmup_power_low": .55,
                        "warmup_power_high": .75, "repeats": 2,
                        "on_sec": 1140, "on_power": .75,
                        "off_sec": 180, "off_power": .55,
                        "cooldown_sec": 600, "cooldown_power_low": .70,
                        "cooldown_power_high": .45,
                    },
                }]

            def get_readiness_view(self, *, today):
                return _Readiness()

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vazio.html")
            out = self._run_cmd_summary(
                types.SimpleNamespace(period="day", date=date(2026, 10, 7),
                                      chart="none", export=path,
                                      start=None, end=None),
                app=_App())
            self.assertIn(f"Exportado: {path}", out)
            with open(path, encoding="utf-8") as f:
                html = f.read()
        self.assertIn("Nenhum treino foi realizado neste período.", html)
        self.assertIn("Treino de Zona 2", html)
        self.assertIn('class="planned-profile"', html)
        self.assertIn("Leitura parcial", html)
        self.assertIn("0,80", html)

    def test_summary_export_periodo_vazio_sem_plano_nem_prontidao_e_valido(self):
        class _App:
            def load_plan(self):
                return []

            def get_readiness_view(self, *, today):
                return None

        rows = []
        agg = tp.activity_summary.summarize(rows)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vazio.html")
            args = types.SimpleNamespace(export=path, theme=None, period="day")
            with contextlib.redirect_stdout(io.StringIO()):
                tp._summary_export(
                    _App(), _FakeClient(), args,
                    date(2026, 10, 7), date(2026, 10, 7), rows, agg,
                    today=date(2026, 10, 7))
            with open(path, encoding="utf-8") as f:
                html = f.read()
        self.assertIn("<!doctype html>", html)
        self.assertIn("Nenhum treino foi realizado neste período.", html)
        self.assertIn("Sem dados suficientes", html)
        self.assertNotIn("<tbody></tbody>", html)

    # -- 1b. forma canonica do relatorio (PROMPT 37) -------------------
    def test_export_vazio_preserva_ordem_canonica_e_titulo_de_periodo(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vazio.html")
            self._run_cmd_summary(types.SimpleNamespace(
                period="day", date=date(2026, 10, 7), chart="none",
                export=path, start=None, end=None))
            with open(path, encoding="utf-8") as f:
                html = f.read()
        order = ["summary", "readiness", "planned-workout", "pmc",
                 "weekly-load", "vo2", "ftp", "adherence", "activities"]
        self.assertEqual(re.findall(r'data-report-section="([^"]+)"', html),
                         order)
        self.assertEqual(re.findall(r'data-report-group="([^"]+)"', html),
                         ["resumo", "hoje", "evolucao", "plano", "detalhes"])
        self.assertIn("Resumo do dia", html)
        self.assertIn("07 out 2026", html)
        self.assertIn("<b>—</b><small>CUMPRIMENTO</small>", html)
        self.assertIn("Ainda não há sessões concluídas ou perdidas neste "
                      "período.", html)

    # -- 2. `--date` vira `date` na borda do argparse ------------------
    def test_main_summary_periodo_day_usa_date_canonico(self):
        out = self._main_summary("--period", "day", "--date", "2026-10-07")
        self.assertIn("(2026-10-07 a 2026-10-07)", out)

    def test_main_summary_periodo_week_ancora_7_dias(self):
        out = self._main_summary("--period", "week", "--date", "2026-10-07")
        self.assertIn("(2026-10-01 a 2026-10-07)", out)

    def test_main_summary_periodo_month_ancora_30_dias(self):
        out = self._main_summary("--period", "month", "--date", "2026-10-07")
        self.assertIn("(2026-09-08 a 2026-10-07)", out)

    def test_main_summary_duracao_livre_45d_ancora_no_dia_pedido(self):
        out = self._main_summary("--period", "45d", "--date", "2026-10-07")
        self.assertIn("(2026-08-24 a 2026-10-07)", out)

    def test_main_summary_sem_date_ancora_em_ontem(self):
        out = self._main_summary("--period", "day")
        ontem = (date.today() - timedelta(days=1)).isoformat()
        self.assertIn(f"({ontem} a {ontem})", out)

    def test_main_summary_date_invalido_sai_com_erro_de_uso(self):
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            with self.assertRaises(SystemExit) as ctx:
                tp.main(["summary", "--date", "2026-13-99"])
        self.assertEqual(ctx.exception.code, 2)
        self.assertIn("YYYY-MM-DD", err.getvalue())


class ReportIndicatorsTest(unittest.TestCase):
    """Fontes dos indicadores do relatório (PROMPT 37, seções 29–40).

    Regras: VO₂ sem fonte real -> `None`; FTP atual só da configuração real
    (`DEFAULT_FTP` nunca vira medição); série só de `ftp_candidates` com
    `applied=True`; `ftp_watts` das sessões NÃO é histórico fisiológico.
    """

    def _indicators(self, plan, *, env_ftp=None, end=date(2026, 10, 7)):
        plan_path = Path(tempfile.mkdtemp()) / "plan.json"
        plan_path.write_text(json.dumps(plan), encoding="utf-8")
        with mock.patch.object(tp, "load_env"), \
             mock.patch.object(tp, "PLAN_FILE", plan_path), \
             mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("FTP", None)
            if env_ftp is not None:
                os.environ["FTP"] = env_ftp
            return tp._ftp_indicators(end=end)

    def test_vo2_indicators_e_none_por_faltar_fonte_real(self):
        self.assertIsNone(tp._vo2_indicators())

    def test_ftp_atual_vem_da_configuracao_real(self):
        ind = self._indicators({"workouts": []}, env_ftp="182")
        self.assertEqual(ind["value"], 182)
        self.assertEqual(ind["source"], ".env FTP")
        self.assertEqual(ind["unit"], "W")

    def test_sem_configuracao_nao_usa_default_ftp(self):
        ind = self._indicators({"workouts": [], "ftp_candidates": {}})
        self.assertIsNone(ind["value"])
        self.assertIsNone(ind["source"])
        self.assertEqual(ind["series"], [])

    def test_serie_usa_somente_candidatos_aplicados_e_datados(self):
        plan = {"workouts": [], "ftp_candidates": {
            "a-old": {"day": "2026-05-01", "proposed_ftp": 180,
                      "applied": True},
            "a-new": {"day": "2026-06-01", "proposed_ftp": 184,
                      "applied": True},
            "a-pending": {"day": "2026-07-01", "proposed_ftp": 190,
                          "applied": False},
            "a-undated": {"proposed_ftp": 195, "applied": True},
        }}
        ind = self._indicators(plan, env_ftp="182")
        self.assertEqual(ind["series"],
                         [("2026-05-01", 180), ("2026-06-01", 184)])
        # o valor do .env nao tem dia de medicao registrada
        self.assertIsNone(ind["date"])

    def test_ftp_watts_do_workout_nao_vira_serie_fisiologica(self):
        plan = {"workouts": [{"day": "2026-09-01", "ftp_watts": 200}],
                "ftp_candidates": {}}
        ind = self._indicators(plan, env_ftp="182")
        self.assertEqual(ind["series"], [])
        self.assertEqual(ind["value"], 182)

    def test_serie_e_recortada_para_12_meses(self):
        plan = {"workouts": [], "ftp_candidates": {
            "old": {"day": "2024-01-10", "proposed_ftp": 170,
                    "applied": True},
            "recent": {"day": "2026-03-10", "proposed_ftp": 184,
                       "applied": True},
        }}
        ind = self._indicators(plan, env_ftp="182", end=date(2026, 10, 7))
        self.assertEqual(ind["series"], [("2026-03-10", 184)])


class RecoveryCliTest(unittest.TestCase):
    def test_cmd_recovery_relata_estado_e_pico(self):
        orig_client = tp.get_client
        tp.get_client = lambda: _RecoveryClient()
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tp.cmd_recovery(types.SimpleNamespace(weeks=0, ramp_pts=9))
            out = buf.getvalue()
            self.assertIn("=== AGORA ===", out)
            self.assertIn("=== ONDE VOCE JA ESTEVE ===", out)
            self.assertIn("pico de CTL", out)
            # debounce: pico vem da fase antiga (treinos de 2021)
            self.assertRegex(out, r"pico de CTL: \d")
        finally:
            tp.get_client = orig_client

    def test_cmd_recovery_ancora_nos_valores_reais_quando_disponiveis(self):
        orig_client = tp.get_client
        tp.get_client = lambda: _RecoveryRealClient()
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                tp.cmd_recovery(types.SimpleNamespace(weeks=0, ramp_pts=9))
            out = buf.getvalue()
            self.assertIn("(PMC real do Intervals: serie ancorada", out)
            # com icu_ctl real presente, o pico reportado e o da API, nao o
            # reconstruido; abre mao do rigidez do numero e so exige contexto
            self.assertRegex(out, r"pico de CTL: \d")
            self.assertIn("ESTIMATIVA DE RETORNO AO CTL PICO", out)
        finally:
            tp.get_client = orig_client


class _RecoveryRealClient(_FakeClient):
    """Igual ao _RecoveryClient, mas os eventos FEITOS carregam icu_ctl/icu_atl
    (pipeline interna do Intervals), exercitando a serie ancorada."""

    def events(self, **params):
        base = _RecoveryClient().events(**params)
        out = []
        for e in base:
            e = dict(e)
            if e.get("paired_activity_id"):
                e["icu_ctl"] = 18.0
                e["icu_atl"] = 22.0
            out.append(e)
        return out


class BuildRecoveryTest(unittest.TestCase):
    """#19: `build --recovery` ora o plano pelos tetos da rampa de retorno."""

    def test_build_recovery_respeita_tetos_da_rampa(self):
        tmp, root, env, path, orig = _scan_fixture()
        try:
            tp.get_client = lambda: _FakeClient()
            tp.get_ftp = lambda: 182
            tp.get_goal = lambda: None
            tp.get_race_date = lambda: None
            tp.get_weekly_hours = lambda: None
            tp.get_long_day = lambda: None
            tp.get_ftp_test_date = lambda: None
            rows = [(date(2026, 8, 1), 30.0, 20.0, 10.0),
                    (date(2026, 8, 2), 31.0, 21.0, 10.0)]
            with mock.patch.object(tp.recovery, "fetch_full_history",
                                   return_value=[]), \
                 mock.patch.object(tp.recovery, "actual_daily_load",
                                   return_value={date(2026, 8, 1): 30.0}), \
                 mock.patch.object(tp.recovery, "pmc_series",
                                   return_value=rows), \
                 mock.patch.object(tp.recovery, "state") as st, \
                 mock.patch.object(tp.recovery, "weekly_volume",
                                   return_value=80.0):
                st.return_value = {"current_ctl": 30.0, "current_atl": 20.0,
                                   "current_tsb": 10.0, "peak_ctl": 50.0}
                args = types.SimpleNamespace(days=60, days_plan=14, ftp_test=None,
                                             recovery=True, ramp_pts=9,
                                             recovery_weeks=12)
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    plan = tp.cmd_build(args)
            self.assertIsNotNone(plan)
            self.assertIn("teto semanal", out.getvalue())
            ramp = src_recovery.ramp_schedule(50, 80, 9, weeks=14)[:2]
            by_week = {0: 0.0, 1: 0.0}
            for w in plan:
                wk = (date.fromisoformat(w["day"]) - date.today()).days // 7
                if wk in by_week:
                    by_week[wk] += w["tss"]
            slack = 30.0  # piso de TSS de um treino; veja RecoveryBudgetTest
            self.assertLessEqual(by_week[0], ramp[0] + slack,
                                 f"semana 1 estourou: {by_week[0]:.1f}")
            self.assertLessEqual(by_week[1], ramp[1] + slack,
                                 f"semana 2 estourou: {by_week[1]:.1f}")
        finally:
            _restore_scan(orig)
            tmp.cleanup()


class SummaryChartDataTest(unittest.TestCase):
    """O PMC do resumo acompanha a janela do periodo (>= 90d), sem travamento
    em trailing 90d -- assim o relatorio de semestre mostra os 6 meses."""

    class _RecClient(_FakeClient):
        def __init__(self):
            self.calls = []

        def events(self, **params):
            self.calls.append(params)
            return []

    def test_semestre_estende_pmc_para_180_dias(self):
        c = self._RecClient()
        anchor = date(2026, 9, 24)
        start = anchor - timedelta(days=179)
        serie = [(start + timedelta(days=i), i, i, 0) for i in range(180)]
        with mock.patch.object(tp.recovery, "actual_daily_load",
                               return_value={}), \
             mock.patch.object(tp.recovery, "pmc_series",
                               return_value=serie):
            pmc_rows, weeks = tp._summary_chart_data(c, start, anchor, [])
        self.assertEqual(c.calls[0]["oldest"], start.isoformat())
        self.assertEqual(c.calls[0]["newest"], anchor.isoformat())
        self.assertEqual(len(pmc_rows), 180)
        self.assertEqual(weeks, [])

    def test_mes_mantem_pmc_de_90_dias(self):
        c = self._RecClient()
        anchor = date(2026, 9, 24)
        start = anchor - timedelta(days=29)
        with mock.patch.object(tp.recovery, "actual_daily_load",
                               return_value={}), \
             mock.patch.object(tp.recovery, "pmc_series",
                               return_value=[]):
            tp._summary_chart_data(c, start, anchor, [])
        self.assertEqual(c.calls[0]["oldest"],
                         (anchor - timedelta(days=89)).isoformat())

    def test_prefere_pmc_real_do_intervals_quando_existe(self):
        c = self._RecClient()
        anchor = date(2026, 9, 24)
        start = anchor - timedelta(days=179)
        real_events = [
            {"start_date_local": f"{(anchor - timedelta(days=40))}T18:00:00",
             "icu_ctl": "25.9", "icu_atl": "54.3", "icu_training_load": "57"},
        ]
        with mock.patch.object(tp, "real_pmc_by_day",
                               return_value={anchor - timedelta(days=40):
                                             (25.9, 54.3)}), \
             mock.patch.object(tp.recovery, "pmc_series_anchored") as anchored, \
             mock.patch.object(tp.recovery, "pmc_series") as rebuild, \
             mock.patch.object(c, "events", return_value=real_events):
            anchored.return_value = [(start + timedelta(days=i),
                                      i * 0.1, i * 0.2, i * 0.1 - i * 0.2)
                                     for i in range(180)]
            pmc_rows, weeks = tp._summary_chart_data(c, start, anchor, [])
        anchored.assert_called_once()
        rebuild.assert_not_called()  # serie real preferida, sem reconstrucao
        self.assertEqual(len(pmc_rows), 180)
        self.assertEqual(weeks, [])

    def test_cai_na_reconstrucao_quando_sem_valores_reais(self):
        c = self._RecClient()
        anchor = date(2026, 9, 24)
        start = anchor - timedelta(days=179)
        serie = [(start + timedelta(days=i), i, i, 0) for i in range(180)]
        with mock.patch.object(tp, "real_pmc_by_day",
                               return_value={}), \
             mock.patch.object(tp.recovery, "actual_daily_load",
                               return_value={}), \
             mock.patch.object(tp.recovery, "pmc_series_anchored") as anchored, \
             mock.patch.object(tp.recovery, "pmc_series",
                               return_value=serie):
            pmc_rows, weeks = tp._summary_chart_data(c, start, anchor, [])
        anchored.assert_not_called()
        self.assertEqual(len(pmc_rows), 180)


class ModelClient(_FakeClient):
    """Fake com historico de metricas (ctl/atl) ao longo da janela (#33)."""

    def __init__(self):
        self._events = [
            {"start_time_local": "2026-09-10", "tsb": "-30", "ctl": "40",
             "atl": "70", "tss": "50"},
            {"start_time_local": "2026-09-20", "tsb": "-25", "ctl": "38",
             "atl": "63", "tss": "60"},
            {"start_time_local": "2026-09-26", "tsb": "-28", "ctl": "26",
             "atl": "54", "tss": "55"},
        ]

    def events(self, **params):
        return self._events


class CmdModelTest(unittest.TestCase):
    def test_bootstrap_presente_bate_com_a_api(self):
        client = ModelClient()
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
                mock.patch.object(tp, "get_client", return_value=client), \
                mock.patch.object(tp, "PLAN_FILE",
                                  Path(tempfile.mkdtemp()) / "plan.json"):
            tp.cmd_model(types.SimpleNamespace(days=60))
        text = out.getvalue()
        self.assertIn("bootstrap hoje", text,
                      "motor local parte do estado atual do Intervals")
        self.assertIn("Intervals.icu", text)
        self.assertIn("Diferenca", text)
        for line in text.splitlines():
            if line.startswith("Diferenca"):
                self.assertIn("CTL +0.0 / ATL +0.0 / TSB +0.0", line,
                              "diferenca ~0 por bootstrap presente")

    def test_sem_metricas_partede_zero(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out), \
                mock.patch.object(tp, "get_client", return_value=_FakeClient()), \
                mock.patch.object(tp, "PLAN_FILE",
                                  Path(tempfile.mkdtemp()) / "plan.json"):
            tp.cmd_model(types.SimpleNamespace(days=60))
        text = out.getvalue()
        self.assertIn("aviso: sem metricas validas", text)


class SummaryPlanStatusTest(unittest.TestCase):
    def test_projeta_consistencia_por_lifecycle_sem_inferir_da_descricao(self):
        class _View:
            def to_dict(self):
                return {"workouts": [
                    {"day": "2026-10-05", "lifecycle_effective": "completed"},
                    {"day": "2026-10-06", "lifecycle_effective": "missed"},
                    {"day": "2026-10-07", "lifecycle_effective": "planned"},
                ]}

        class _App:
            def plan_view(self, *, today):
                return _View()

        status = tp._report_plan_status(_App(), date(2026, 10, 6))
        self.assertEqual(status["summary"], {"done": 1, "missed": 1,
                                              "pending": 1})
        self.assertEqual(status["today"]["lifecycle_effective"], "missed")
        self.assertAlmostEqual(status["weeks"][0]["pct"], 50.0)


if __name__ == "__main__":
    unittest.main()
