import contextlib
import io
import os
import tempfile
import types
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from src import training_plan as tp
from src import recovery as src_recovery
from src.plan import (build_plan, load_plan, load_plan_meta, save_plan,
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
                    period="day", date=date(2026, 9, 23), chart="none"))
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
                    export=None))
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
                        export=path))
                self.assertIn(f"Exportado: {path}", buf.getvalue())
                with open(path, encoding="utf-8") as f:
                    html = f.read()
                self.assertIn("Treino de Limiar FTP", html)
                self.assertIn("<svg ", html)
                self.assertIn("58 TSS", html)
        finally:
            tp.get_client = orig_client


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


if __name__ == "__main__":
    unittest.main()