"""UI-1 — Application seam.

Prova que os casos de uso locais (config e persistencia de plano) podem ser
chamados fora da CLI e sem construir client externo, e que o provider e
injetavel pelo composition root (nada de `get_client()` escondido).
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from src.application import (Application, assess_daily_readiness, build_workouts,
                              push_workouts, reconcile_workouts,
                              recovery_outlook, summarize_period)
from src.athlete_profile import AthletePhysiologicalProfile, FtpSource
from src.ftp_history import FtpProtocol, FtpReference, FtpReferenceSource
from src.plan import DEFAULT_FTP, build_plan, event_payload
from src.snapshot import TrainingSnapshot


class _FakeProvider:
    def __init__(self):
        self.event_calls = 0
        self.wellness_calls = 0

    def events(self, oldest, newest):
        self.event_calls += 1
        return [{"id": 1, "icu_ctl": 10.0}]

    def wellness(self, oldest, newest):
        self.wellness_calls += 1
        return [{"day": oldest, "restingHR": 50}]


class FakeProviderInjectionTest(unittest.TestCase):
    def test_client_usa_factory_injetado_sem_rede(self):
        fake = _FakeProvider()
        app = Application(client_factory=lambda: fake)
        self.assertIs(app.client(), fake)
        self.assertEqual(app.client().events("a", "b"), [{"id": 1, "icu_ctl": 10.0}])
        self.assertEqual(fake.event_calls, 1)


class LocalUseCasesTest(unittest.TestCase):
    """Casos de uso locais nao tocam provider algum."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan_file = self.root / "plan.json"
        self.env_file = self.root / ".env"
        self.env_file.write_text(
            "HERMES_TEST_FTP=200\nHERMES_TEST_GOAL=ftp-builder\n",
            encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _app(self):
        calls = {"client": 0}

        def _boom():
            calls["client"] += 1
            raise AssertionError("caso de uso local nao pode pedir provider")

        return Application(plan_path=self.plan_file, env_path=self.env_file,
                           client_factory=_boom), calls

    def test_salvar_e_ler_plano_preserva_formato(self):
        app, _ = self._app()
        workouts = [{"day": "2026-10-03", "name": "Z2", "focus": "z2",
                     "tss": 40.0, "planned_duration": 3600}]
        app.save_plan(workouts, goal="ftp-builder", race_date=None,
                      ftp_test_date=None, ftp_candidates=[],
                      absorbed_ids=["hermes-plan-2026-10-03"])
        loaded = app.load_plan()
        # Dados originais preservados; identidade/lifecycle anexados (UI-2).
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0]["day"], "2026-10-03")
        self.assertEqual(loaded[0]["tss"], 40.0)
        self.assertTrue(loaded[0]["id"])
        self.assertEqual(loaded[0]["lifecycle"], "planned")
        meta = app.load_plan_meta()
        self.assertEqual(meta["goal"], "ftp-builder")
        self.assertEqual(meta["absorbed_ids"], ["hermes-plan-2026-10-03"])

    def test_leitura_de_plano_ausente_retorna_vazio_sem_rede(self):
        app, calls = self._app()
        self.assertEqual(app.load_plan(), [])
        self.assertEqual(app.load_plan_meta()["absorbed_ids"], [])
        self.assertEqual(calls["client"], 0)

    def test_config_injetada_nao_depende_do_repo(self):
        app, _ = self._app()
        self.assertEqual(app.get_env("HERMES_TEST_FTP"), "200")
        self.assertEqual(app.get_env("HERMES_TEST_GOAL"), "ftp-builder")
        self.assertIsNone(app.get_env("HERMES_TEST_NAO_EXISTE"))

    def test_plano_escrito_com_meta_usa_formato_workouts(self):
        app, _ = self._app()
        app.save_plan([{"day": "2026-10-04", "name": "X"}], goal="ftp-builder")
        data = json.loads(self.plan_file.read_text(encoding="utf-8"))
        self.assertIn("workouts", data)
        self.assertEqual(data["goal"], "ftp-builder")

    def test_plano_sem_meta_preserva_lista_pura(self):
        app, _ = self._app()
        app.save_plan([{"day": "2026-10-04", "name": "X"}])
        data = json.loads(self.plan_file.read_text(encoding="utf-8"))
        self.assertIsInstance(data, list)
        loaded = app.load_plan()
        self.assertEqual(loaded[0]["day"], "2026-10-04")
        self.assertEqual(loaded[0]["name"], "X")
        self.assertEqual(loaded[0]["lifecycle"], "planned")

    def test_profile_e_view_local_sem_provider_com_contexto_configurado(self):
        self.env_file.write_text(
            "FTP=182\nFTHR=172\nWEEKLY_HOURS=6.5\n"
            "TRAINING_DAYS=seg,qua,sex\nLONG_DAY=dom\n", encoding="utf-8")
        app, calls = self._app()
        snapshot = TrainingSnapshot.capture(
            wellness=[{"day": "2026-10-03", "restingHR": 48}])
        snapshot.save(app._snapshot_file())
        with mock.patch.dict(os.environ, {}, clear=True):
            profile = app.get_athlete_physiological_profile(
                today=date(2026, 10, 3))
            # O .env carrega, mas FTP nao e mais fonte fisiologica do profile.
            self.assertEqual(os.environ.get("FTP"), "182")

        self.assertIsInstance(profile, AthletePhysiologicalProfile)
        self.assertIsNone(profile.ftp)
        self.assertIsNone(profile.ftp_source)
        self.assertIsNone(profile.ftp_confidence)
        self.assertEqual(profile.threshold_hr, 172)
        self.assertEqual(profile.weekly_training_hours, 6.5)
        self.assertEqual(profile.training_days, (0, 2, 4))
        self.assertEqual(profile.preferred_long_day, 6)
        self.assertEqual(profile.resting_hr, 48)
        self.assertEqual(calls["client"], 0)

    def test_profile_nao_altera_plano_prescricao_snapshot_ou_payload(self):
        app, calls = self._app()
        app.save_plan([{"day": "2026-10-06", "name": "Z2", "focus": "zone2",
                       "tss": 40.0, "planned_duration": 3600}], goal="ftp-builder")
        TrainingSnapshot.capture(
            wellness=[{"day": "2026-10-03", "restingHR": 48}]).save(
                app._snapshot_file())
        plan_json_before = self.plan_file.read_text(encoding="utf-8")
        snapshot_before = app._snapshot_file().read_text(encoding="utf-8")
        kwargs = {"ftp": 182, "days": 5, "start": date(2026, 9, 14)}
        report_before, report_after = {}, {}
        before = build_plan([], 0, **kwargs, phase_report=report_before)

        with mock.patch.dict(os.environ, {}, clear=True):
            profile = app.get_athlete_physiological_profile(
                today=date(2026, 10, 3))

        self.assertEqual(DEFAULT_FTP, 182)
        after = build_plan([], 0, **kwargs, phase_report=report_after)
        self.assertIsNone(profile.ftp)
        self.assertIsNone(profile.ftp_source)
        self.assertIsNone(profile.threshold_hr)
        self.assertEqual(profile.training_days, ())
        self.assertEqual(after, before)
        self.assertEqual(report_after, report_before)
        self.assertEqual([event_payload(w, ftp=182) for w in after],
                         [event_payload(w, ftp=182) for w in before])
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"),
                         plan_json_before)
        self.assertEqual(app._snapshot_file().read_text(encoding="utf-8"),
                         snapshot_before)
        self.assertEqual(calls["client"], 0)


class AthleteProfileFtpHistoryTest(unittest.TestCase):
    """FTP-H1 — `profile.ftp` reflete somente a `FtpReference` canonica.

    Query local/read-only: sem provider, sem escrita e sem fallback de
    `.env`/`DEFAULT_FTP`/estimativas. O tempo vem do caller; `FtpHistory`
    decide a referencia vigente.
    """

    NOW = datetime(2026, 10, 7, 12, 0, tzinfo=timezone.utc)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan_file = self.root / "plan.json"
        self.env_file = self.root / ".env"
        self.history_file = self.root / "ftp_history.json"
        self.env_file.write_text("FTP=250\nFTHR=172\n", encoding="utf-8")
        self.calls = 0

        def _boom():
            self.calls += 1
            raise AssertionError("profile nao pode chamar provider")

        self.app = Application(plan_path=self.plan_file, env_path=self.env_file,
                               ftp_history_path=self.history_file,
                               client_factory=_boom)

    def tearDown(self):
        self.tmp.cleanup()

    def _ref(self, watts, *, ref_id="ftp-1", effective_from=None,
             source=FtpReferenceSource.USER_ENTERED,
             protocol=FtpProtocol.RAMP_TEST, supersedes=None):
        instant = effective_from or self.NOW
        return FtpReference(id=ref_id, value_watts=watts,
                            effective_from=instant, recorded_at=instant,
                            source=source, protocol=protocol,
                            supersedes_reference_id=supersedes)

    def _profile(self, *, now=NOW, today=None):
        with mock.patch.dict(os.environ, {}, clear=True):
            return self.app.get_athlete_physiological_profile(
                today=today, now=now)

    def _tree(self):
        return {path.name: path.read_bytes()
                for path in sorted(self.root.iterdir())}

    def test_sem_historico_env_e_default_nao_preenchem_o_profile(self):
        self.assertEqual(DEFAULT_FTP, 182)
        profile = self._profile()
        self.assertFalse(self.history_file.exists())
        self.assertIsNone(profile.ftp)
        self.assertIsNone(profile.ftp_source)
        self.assertIsNone(profile.ftp_confidence)
        self.assertEqual(profile.threshold_hr, 172)
        self.assertEqual(self.calls, 0)

    def test_env_ftp_e_carregado_mas_nao_alimenta_o_profile(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            profile = self.app.get_athlete_physiological_profile(now=self.NOW)
            self.assertEqual(os.environ.get("FTP"), "250")
        self.assertIsNone(profile.ftp)

    def test_history_vence_env(self):
        self.app.save_ftp_reference(self._ref(265))
        profile = self._profile()
        self.assertEqual(profile.ftp, 265)
        self.assertIs(profile.ftp_source, FtpSource.USER)
        self.assertIsNone(profile.ftp_confidence)

    def test_history_mais_antigo_que_env_ainda_vence(self):
        self.env_file.write_text("FTP=280\nFTHR=172\n", encoding="utf-8")
        self.app.save_ftp_reference(self._ref(260))
        self.assertEqual(self._profile().ftp, 260)

    def test_referencia_futura_nao_e_anticipada(self):
        self.app.save_ftp_reference(
            self._ref(300, effective_from=self.NOW + timedelta(days=1)))
        profile = self._profile(now=self.NOW)
        self.assertIsNone(profile.ftp)
        self.assertIsNone(profile.ftp_source)

    def test_history_existe_mas_nenhuma_referencia_esta_vigorante(self):
        self.app.save_ftp_reference(
            self._ref(300, effective_from=self.NOW + timedelta(days=1)))
        history = self.app.get_ftp_history()
        self.assertEqual(len(history.references), 1)
        self.assertIsNone(self.app.get_ftp_at(self.NOW))
        with mock.patch.dict(os.environ, {}, clear=True):
            profile = self.app.get_athlete_physiological_profile(now=self.NOW)
            self.assertEqual(os.environ.get("FTP"), "250")
        self.assertIsNone(profile.ftp)

    def test_referencia_exatamente_vigorante_e_usada(self):
        self.app.save_ftp_reference(self._ref(265, effective_from=self.NOW))
        self.assertEqual(self._profile(now=self.NOW).ftp, 265)

    def test_multiplos_refs_o_mais_recente_vence(self):
        self.app.save_ftp_reference(self._ref(250, ref_id="ftp-1"))
        self.app.save_ftp_reference(self._ref(
            265, ref_id="ftp-2", effective_from=self.NOW + timedelta(days=10)))
        self.assertEqual(self._profile(now=self.NOW).ftp, 250)
        self.assertEqual(
            self._profile(now=self.NOW + timedelta(days=11)).ftp, 265)

    def test_correcao_supersedes_e_respeitada(self):
        self.app.save_ftp_reference(self._ref(250, ref_id="ftp-1"))
        self.app.save_ftp_reference(
            self._ref(255, ref_id="ftp-1-corrected", supersedes="ftp-1"))
        profile = self._profile()
        self.assertEqual(profile.ftp, 255)
        history = self.app.get_ftp_history()
        self.assertEqual(len(history.references), 2)
        self.assertEqual(len(history.active_references), 1)

    def test_toda_origem_canonica_chega_ao_profile_sem_falsificacao(self):
        casos = {
            FtpReferenceSource.USER_ENTERED: FtpSource.USER,
            FtpReferenceSource.HERMES_TEST: FtpSource.CONFIRMED,
            FtpReferenceSource.ZWIFT_TEST: FtpSource.CONFIRMED,
            FtpReferenceSource.OTHER_PLATFORM_TEST: FtpSource.CONFIRMED,
            FtpReferenceSource.COACH_DEFINED: FtpSource.CONFIRMED,
        }
        for source, expected in casos.items():
            with self.subTest(source=source):
                self.history_file.unlink(missing_ok=True)
                self.app.save_ftp_reference(self._ref(
                    265, source=source, protocol=FtpProtocol.FTP_20_MIN))
                profile = self._profile()
                self.assertEqual(profile.ftp, 265)
                self.assertIs(profile.ftp_source, expected)

    def test_protocolo_ramp_nao_vira_fonte_ramp(self):
        self.app.save_ftp_reference(self._ref(
            265, source=FtpReferenceSource.HERMES_TEST,
            protocol=FtpProtocol.RAMP_TEST))
        profile = self._profile()
        self.assertIs(profile.ftp_source, FtpSource.CONFIRMED)
        self.assertIsNot(profile.ftp_source, FtpSource.RAMP)
        self.assertIsNot(profile.ftp_source, FtpSource.FTP20)

    def test_referencia_canonica_nao_inventa_confianca(self):
        self.app.save_ftp_reference(self._ref(265))
        self.assertIsNone(self._profile().ftp_confidence)

    def test_consulta_e_offline_read_only_e_neutra(self):
        self.app.save_plan([{"day": "2026-10-06", "name": "Z2",
                             "focus": "zone2", "tss": 40.0,
                             "planned_duration": 3600}], goal="ftp-builder")
        TrainingSnapshot.capture(now=self.NOW).save(self.app._snapshot_file())
        self.app.save_ftp_reference(self._ref(265))
        before = self._tree()

        profile = self._profile()

        self.assertEqual(profile.ftp, 265)
        self.assertEqual(self._tree(), before)
        self.assertEqual(self.calls, 0)

    def test_now_naive_nao_e_convertido_silenciosamente(self):
        self.app.save_ftp_reference(self._ref(265))
        with self.assertRaises(ValueError):
            self.app.get_athlete_physiological_profile(
                now=datetime(2026, 10, 7, 12, 0))
        self.assertEqual(self.calls, 0)

    def test_divergencia_transitoria_profile_canonico_vs_build_legado(self):
        """TRANSITIONAL_DIVERGENCE: profile usa history, build continua no .env."""
        from src.training_plan import get_ftp
        self.app.save_ftp_reference(self._ref(265))
        profile = self._profile()
        with mock.patch.dict(os.environ, {"FTP": "250"}):
            self.assertEqual(get_ftp(), 250)
        self.assertEqual(profile.ftp, 265)
        self.assertEqual(self.calls, 0)


class CompositionRootFallbackTest(unittest.TestCase):
    def test_sem_factory_cai_no_get_client_do_cli(self):
        import src.training_plan as tp
        expected = object()
        with mock.patch.object(tp, "get_client", return_value=expected) as factory:
            app = Application()
            self.assertIs(app.client(), expected)
            factory.assert_called_once_with()

    def test_factory_injetada_vence_sobre_composition_root(self):
        import src.training_plan as tp
        injected = object()
        with mock.patch.object(tp, "get_client") as composition_root:
            app = Application(client_factory=lambda: injected)
            self.assertIs(app.client(), injected)
            composition_root.assert_not_called()

    def test_modulo_top_level_homonimo_nao_desvia_o_composition_root(self):
        """Regressao: um `training_plan.py` em `sys.path` nao vence `src.*`."""
        import src.training_plan as package_training_plan

        expected = object()
        previous_path = list(sys.path)
        previous_top_level = sys.modules.pop("training_plan", None)
        with tempfile.TemporaryDirectory() as directory:
            shadow = Path(directory) / "training_plan.py"
            shadow.write_text(
                "def get_client():\n"
                "    raise AssertionError('shadow training_plan was imported')\n",
                encoding="utf-8")
            try:
                sys.path.insert(0, directory)
                with mock.patch.object(package_training_plan, "get_client",
                                       return_value=expected) as legitimate:
                    self.assertIs(Application().client(), expected)
                    legitimate.assert_called_once_with()
                self.assertNotIn("training_plan", sys.modules)
            finally:
                sys.path[:] = previous_path
                sys.modules.pop("training_plan", None)
                if previous_top_level is not None:
                    sys.modules["training_plan"] = previous_top_level

    def test_cli_direta_carrega_o_composition_root(self):
        """`python3 src/training_plan.py` continua sendo entry point valido."""
        root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "src/training_plan.py", "--help"], cwd=root,
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Plano de treinos Hermes", result.stdout)

    def test_fallback_top_level_so_funciona_no_modo_script(self):
        """A compatibilidade direta nao muda a origem do uso como pacote."""
        root = Path(__file__).resolve().parent.parent
        src = root / "src"
        code = (
            "import sys;"
            f"sys.path.insert(0, {str(src)!r});"
            "import application, training_plan;"
            "expected = object();"
            "training_plan.get_client = lambda: expected;"
            "assert application.Application().client() is expected"
        )
        result = subprocess.run(
            [sys.executable, "-c", code], cwd=root,
            capture_output=True, text=True, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)


class _Provider:
    """Provider fake das camadas superiores; nunca toca a rede."""

    def __init__(self, events=None, wellness=None):
        self._events = list(events or [])
        self._wellness = list(wellness or [])
        self.calls = []
        self.deleted_batches = []
        self.deleted_ids = []
        self.created = None

    def events(self, oldest, newest):
        self.calls.append(("events", oldest, newest))
        return list(self._events)

    def wellness(self, oldest, newest):
        self.calls.append(("wellness", oldest, newest))
        return list(self._wellness)

    def delete_events(self, ids):
        self.deleted_batches.append(list(ids))
        return 200, {"eventsDeleted": len(ids)}

    def delete_event(self, event_id):
        self.deleted_ids.append(event_id)
        return 204

    def create_events(self, batch):
        self.created = list(batch)
        return 200, batch


def _readiness_stub(is_adaptive=False, applies_to_day=None, illness=False):
    trace = SimpleNamespace(illness_alert=illness, composite_low=False,
                            coverage=1.0, observations=(), missing=(),
                            stale_days=None, reference_day=applies_to_day)
    decisao = SimpleNamespace(is_adaptive=is_adaptive,
                              applies_to_day=applies_to_day, reason="motivo")
    module = SimpleNamespace(
        assess_readiness_assessment=lambda wellness, days: (None, trace),
        readiness_decision=lambda *a, **k: decisao)
    return module, decisao, trace


def _recovery_module(*, rows_state=None, schedule=None, history=None):
    state = rows_state or {"peak_ctl": 60.0, "current_ctl": 30.0,
                           "current_atl": 20.0}
    return SimpleNamespace(
        fetch_full_history=lambda provider: list(history or []),
        actual_daily_load=lambda events: {},
        state=lambda rows: dict(state),
        weekly_volume=lambda daily: 80.0,
        calibrated_state=lambda st, vol: None,
        ramp_schedule=lambda target, vol, ramp, weeks: list(schedule or []))


def _silent(fn, *args, **kwargs):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        result = fn(*args, **kwargs)
    if buf.getvalue():
        raise AssertionError("caso de uso nao pode escrever em stdout")
    return result


class BuildUseCaseTest(unittest.TestCase):
    def test_build_sem_cli_passa_readiness_report_e_nao_imprime(self):
        provider = _Provider(events=[{"id": 1}])
        readiness_mod, decisao, trace = _readiness_stub()
        captured = {}

        def fake_build(events, tsb, **kwargs):
            captured["events"] = events
            captured["tsb"] = tsb
            captured["kwargs"] = kwargs
            kwargs["readiness_report"]["aplicada_em"] = ["2026-10-03"]
            return [{"day": "2026-10-03", "tss": 40.0, "name": "x"}]

        result = _silent(
            build_workouts, provider, today=date(2026, 10, 3), days=60,
            days_plan=14, ftp=200, fthr=None, goal="ftp-builder",
            periodization=None, race_date=None, weekly_hours=None,
            long_day=None, hr_mode=False, ftp_test_date=None,
            training_days=(0, 1, 2, 3, 4), existing=None,
            latest_metrics_fn=lambda events: SimpleNamespace(tsb=5.0),
            build_plan_fn=fake_build, readiness_module=readiness_mod,
            recovery_module=_recovery_module(), pmc_rows_fn=lambda *a: ([], False))

        self.assertEqual(len(result.plan), 1)
        self.assertEqual(result.tsb, 5.0)
        # UI-2: o caso de uso entrega identidade/lifecycle ja anexados.
        self.assertTrue(result.plan[0]["id"])
        self.assertEqual(result.plan[0]["lifecycle"], "planned")
        self.assertEqual(result.readiness_report["aplicada_em"], ["2026-10-03"])
        self.assertIs(captured["kwargs"]["readiness"], decisao)
        self.assertIs(captured["kwargs"]["readiness_report"],
                      result.readiness_report)

    def test_build_recovery_sem_historico_ignora_rampa_com_aviso(self):
        provider = _Provider()
        readiness_mod, _, _ = _readiness_stub()
        captured = {}

        def fake_build(events, tsb, **kwargs):
            captured.update(kwargs)
            return [{"day": "2026-10-03", "tss": 40.0}]

        result = _silent(
            build_workouts, provider, today=date(2026, 10, 3), days=60,
            days_plan=14, ftp=200, fthr=None, goal=None, periodization=None,
            race_date=None, weekly_hours=None, long_day=None, hr_mode=False,
            ftp_test_date=None, training_days=(0, 1, 2, 3, 4), existing=None,
            latest_metrics_fn=lambda events: None, build_plan_fn=fake_build,
            readiness_module=readiness_mod, recovery_module=_recovery_module(),
            pmc_rows_fn=lambda *a: ([], False), recovery=True)

        self.assertIsNone(result.recovery_ramp)
        self.assertIn("sem treinos feitos", result.recovery_warning)
        self.assertIsNone(captured["recovery_ramp"])

    def test_build_recovery_com_historico_gera_teto_semanal(self):
        provider = _Provider()
        readiness_mod, _, _ = _readiness_stub()
        rec = _recovery_module(history=[{"activity_id": "a"}],
                               schedule=[80.0, 89.0])

        result = _silent(
            build_workouts, provider, today=date(2026, 10, 3), days=60,
            days_plan=14, ftp=200, fthr=None, goal=None, periodization=None,
            race_date=None, weekly_hours=None, long_day=None, hr_mode=False,
            ftp_test_date=None, training_days=(0, 1, 2, 3, 4), existing=None,
            latest_metrics_fn=lambda events: None,
            build_plan_fn=lambda *a, **k: [{"day": "2026-10-03"}],
            readiness_module=readiness_mod, recovery_module=rec,
            pmc_rows_fn=lambda *a: ([(date(2026, 1, 1), 1, 1, 0)], False),
            recovery=True, ramp_pts=9, recovery_weeks=12)

        self.assertEqual(result.recovery_ramp, [80.0, 89.0])
        self.assertIn("teto semanal de retorno", result.ramp_label)


class ReconcileUseCaseTest(unittest.TestCase):
    def test_reconcile_sem_cli_usa_budget_e_absorbed_ids(self):
        provider = _Provider(events=[{"id": 1}])
        captured = {}

        def fake_reconcile(plan, events, ftp, training_days, budget,
                           absorbed_ids):
            captured.update(ftp=ftp, training_days=training_days,
                            budget=budget, absorbed_ids=absorbed_ids)
            return plan, [{"day": "x"}], {"absorbed_ids": ["hermes-plan-x"],
                                          "absorbed_tss": 1.0}

        result = _silent(
            reconcile_workouts, provider, plan=[{"day": "2026-10-03"}],
            meta={"goal": "ftp-builder", "absorbed_ids": ["old"]}, ftp=200,
            training_days=(0, 1, 2, 3, 4), days=14, today=date(2026, 10, 3),
            budget_window_days=60, goal_budget_scale={"ftp-builder": 1.0},
            reconcile_fn=fake_reconcile,
            weekly_budget_fn=lambda load, td, scale: 100.0,
            avg_load_fn=lambda events: 50.0)

        self.assertEqual(captured["absorbed_ids"], ["old"])
        self.assertEqual(captured["budget"], 100.0)
        self.assertEqual(result.info["absorbed_ids"], ["hermes-plan-x"])
        # days < janela -> segunda leitura do provider (historico do budget).
        self.assertEqual(len(provider.calls), 2)

    def test_reconcile_janela_longa_nao_relê(self):
        provider = _Provider(events=[{"id": 1}])
        result = _silent(
            reconcile_workouts, provider, plan=[], meta={"absorbed_ids": []},
            ftp=200, training_days=(0, 1, 2, 3, 4), days=60,
            today=date(2026, 10, 3), budget_window_days=60,
            goal_budget_scale={}, reconcile_fn=lambda *a, **k: ([], [], {}),
            weekly_budget_fn=lambda *a: 0.0, avg_load_fn=lambda *a: 0.0)
        self.assertEqual(result.plan, [])
        self.assertEqual(len(provider.calls), 1)


class PushUseCaseTest(unittest.TestCase):
    def _run(self, dry_run):
        provider = _Provider(events=[{"external_id": "hermes-plan-2026-10-01"}])
        plan = [{"day": "2026-10-02", "name": "x"}]
        return provider, _silent(
            push_workouts, provider, plan=plan, start="2026-10-02", ftp=200,
            fthr=None, lang="pt",
            event_payload_fn=lambda w, ftp, lang, prev, fthr: dict(w),
            prev_same_focus_fn=lambda plan, w: None,
            orphan_external_ids_fn=lambda plan, recent, start: [
                "hermes-plan-2026-10-01", "hermes-plan-2026-11-30"],
            manual_duplicate_ids_fn=lambda plan, recent, start: [999],
            dry_run=dry_run)

    def test_push_calcula_orfaos_dentro_do_horizonte_e_executa(self):
        provider, result = self._run(dry_run=False)
        self.assertEqual(len(result.batch), 1)
        self.assertEqual(result.orphans, ["hermes-plan-2026-10-01"])
        self.assertEqual(result.beyond, ["hermes-plan-2026-11-30"])
        self.assertEqual(result.dup_ids, [999])
        self.assertTrue(result.executed)
        self.assertEqual(provider.deleted_batches, [["hermes-plan-2026-10-01"]])
        self.assertEqual(provider.deleted_ids, [999])
        self.assertEqual(result.created, 1)

    def test_push_dry_run_nao_chama_provider_escrita(self):
        provider, result = self._run(dry_run=True)
        self.assertFalse(result.executed)
        self.assertEqual(provider.deleted_batches, [])
        self.assertEqual(provider.deleted_ids, [])
        self.assertIsNone(provider.created)


class SummaryUseCaseTest(unittest.TestCase):
    def test_summary_resolve_periodo_e_agrega_sem_print(self):
        provider = _Provider()
        result = _silent(
            summarize_period, provider, period="week", anchor=date(2026, 10, 3),
            start=None, end=None, plan_days=None,
            resolve_period_fn=lambda anchor, period, start, end, plan_days: (
                date(2026, 9, 28), date(2026, 10, 4)),
            done_activities_fn=lambda provider, s, e: [{"day": "2026-10-01"}],
            summarize_fn=lambda rows: {"sessions": len(rows)})
        self.assertEqual(result.start, date(2026, 9, 28))
        self.assertEqual(result.end, date(2026, 10, 4))
        self.assertEqual(result.agg, {"sessions": 1})


class RecoveryUseCaseTest(unittest.TestCase):
    def test_recovery_outlook_deriva_estado_e_rampa(self):
        provider = _Provider()
        result = _silent(
            recovery_outlook, provider, recovery_module=_recovery_module(
                history=[{"paired_activity_id": "a"}], schedule=[70.0, 79.0]),
            pmc_rows_fn=lambda *a: ([(date(2026, 1, 1), 1, 2, 3)], True),
            ramp_pts=9, weeks=12, today=date(2026, 10, 3))
        self.assertEqual(result.event_count, 1)
        self.assertEqual(result.done_count, 1)
        self.assertTrue(result.anchored)
        self.assertEqual(result.schedule, [70.0, 79.0])

    def test_recovery_sem_serie_retorna_none(self):
        provider = _Provider()
        self.assertIsNone(_silent(
            recovery_outlook, provider, recovery_module=_recovery_module(),
            pmc_rows_fn=lambda *a: ([], False), ramp_pts=9, weeks=12,
            today=date(2026, 10, 3)))


class ReadinessUseCaseTest(unittest.TestCase):
    def _elig(self, workout, eligible=True, state="publicada", reason="ok"):
        return SimpleNamespace(workout=workout, eligible=eligible,
                               state=state, reason=reason)

    def _base(self, decisao_module, eligibility, events=None, tsb=5.0):
        return _silent(
            assess_daily_readiness, _Provider(events=events or []),
            plan=[{"day": "2026-10-03", "focus": "sweetspot",
                   "params": {"a": 1}, "tss": 40.0, "name": "base"}],
            meta={}, today=date(2026, 10, 3), now=None, days=7, ftp=200,
            training_days=(0, 1, 2, 3, 4), weekly_hours=None, long_day=None,
            periodization=None, tsb_adapt_limit=0.0,
            latest_metrics_fn=lambda events: SimpleNamespace(tsb=tsb)
            if events else None,
            build_plan_fn=self._build_plan, readiness_module=decisao_module,
            eligibility_fn=lambda plan, events, today, now: eligibility)

    @staticmethod
    def _build_plan(events, tsb, readiness, **kwargs):
        if readiness is None:
            return [{"day": "2026-10-03", "focus": "sweetspot",
                     "params": {"a": 1}, "tss": 40.0, "name": "base"}]
        kwargs["readiness_report"]["aplicada_em"] = ["2026-10-03"]
        return [{"day": "2026-10-03", "focus": "sweetspot",
                 "params": {"a": 1}, "tss": 30.0, "name": "reduzido"}]

    def test_check_propoe_quando_leitura_reduz_e_dia_e_hoje(self):
        module, decisao, _ = _readiness_stub(is_adaptive=True,
                                             applies_to_day="2026-10-03")
        result = self._base(module, self._elig(
            {"day": "2026-10-03", "focus": "sweetspot", "params": {"a": 1},
             "tss": 40.0, "name": "base"}))
        self.assertEqual(result.status, "propose")
        self.assertEqual(result.autor, "prontidao")
        self.assertIs(result.decisao, decisao)

    def test_check_nao_adaptativo(self):
        module, _, _ = _readiness_stub(is_adaptive=False)
        result = self._base(module, self._elig(None, eligible=False))
        self.assertEqual(result.status, "not_adaptive")

    def test_check_leitura_de_outro_dia_nao_transfere(self):
        module, _, _ = _readiness_stub(is_adaptive=True,
                                       applies_to_day="2026-10-02")
        result = self._base(module, self._elig(
            {"day": "2026-10-03", "focus": "sweetspot", "params": {"a": 1},
             "tss": 40.0, "name": "base"}))
        self.assertEqual(result.status, "wrong_day")

    def test_check_sem_sessao_elegivel(self):
        module, _, _ = _readiness_stub(is_adaptive=True,
                                       applies_to_day="2026-10-03")
        result = self._base(module, self._elig(None, eligible=False,
                                               reason="sem sessao"))
        self.assertEqual(result.status, "not_eligible")

    def test_check_already_quando_plano_ja_reflete_proposta(self):
        module, _, _ = _readiness_stub(is_adaptive=True,
                                       applies_to_day="2026-10-03")
        result = self._base(module, self._elig(
            {"day": "2026-10-03", "focus": "sweetspot", "params": {"a": 1},
             "tss": 30.0, "name": "reduzido"}))
        self.assertEqual(result.status, "already")

    def test_check_tsb_vence_quando_leitura_nao_muda_nada(self):
        module, _, _ = _readiness_stub(is_adaptive=True,
                                       applies_to_day="2026-10-03")

        def no_change(events, tsb, readiness, **kwargs):
            if readiness is not None:
                kwargs["readiness_report"]["aplicada_em"] = ["2026-10-03"]
            return [{"day": "2026-10-03", "focus": "sweetspot",
                     "params": {"a": 1}, "tss": 40.0, "name": "base"}]

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            result = assess_daily_readiness(
                _Provider(events=[{"id": 1}]),
                plan=[{"day": "2026-10-03", "focus": "sweetspot",
                       "params": {"a": 1}, "tss": 45.0, "name": "base"}],
                meta={}, today=date(2026, 10, 3), now=None, days=7, ftp=200,
                training_days=(0, 1, 2, 3, 4), weekly_hours=None, long_day=None,
                periodization=None, tsb_adapt_limit=5.0,
                latest_metrics_fn=lambda events: SimpleNamespace(tsb=0.0),
                build_plan_fn=no_change, readiness_module=module,
                eligibility_fn=lambda plan, events, today, now: self._elig(
                    {"day": "2026-10-03", "focus": "sweetspot",
                     "params": {"a": 1}, "tss": 45.0, "name": "base"}))
        self.assertEqual(buf.getvalue(), "")
        self.assertEqual(result.status, "tsb_wins")

    def test_check_rebuild_propagates_active_recovery_days(self):
        module, _, _ = _readiness_stub(is_adaptive=True,
                                       applies_to_day="2026-10-03")
        active = {"day": "2026-10-03", "focus": "zone2",
                  "params": {"on_power": 0.60}, "tss": 21.0,
                  "name": "Recuperacao ativa (Z2)"}
        captured = []

        def spy_build(events, tsb, readiness, **kwargs):
            captured.append(kwargs)
            if readiness is not None:
                kwargs["readiness_report"]["aplicada_em"] = ["2026-10-03"]
            return [active]

        result = _silent(
            assess_daily_readiness, _Provider(events=[{"id": 1}]),
            plan=[active], meta={}, today=date(2026, 10, 3), now=None,
            days=7, ftp=200, training_days=(0, 1, 2, 3, 4),
            weekly_hours=None, long_day=None, periodization=None,
            tsb_adapt_limit=0.0,
            latest_metrics_fn=lambda events: SimpleNamespace(tsb=5.0),
            build_plan_fn=spy_build, readiness_module=module,
            eligibility_fn=lambda plan, events, today, now: self._elig(active),
            active_recovery_days=(1, 3))

        self.assertEqual(len(captured), 2)
        for kwargs in captured:
            self.assertEqual(kwargs["active_recovery_days"], (1, 3))
        self.assertEqual(result.com["name"], "Recuperacao ativa (Z2)")

    def test_check_rebuild_propagates_minimum_regular_duration(self):
        module, _, _ = _readiness_stub(is_adaptive=True,
                                       applies_to_day="2026-10-03")
        regular = {"day": "2026-10-03", "focus": "sweetspot",
                   "params": {"a": 1}, "tss": 40.0, "name": "base"}
        captured = []

        def spy_build(events, tsb, readiness, **kwargs):
            captured.append(kwargs)
            if readiness is not None:
                kwargs["readiness_report"]["aplicada_em"] = ["2026-10-03"]
            return [regular]

        _silent(
            assess_daily_readiness, _Provider(events=[{"id": 1}]),
            plan=[regular], meta={}, today=date(2026, 10, 3), now=None,
            days=7, ftp=200, training_days=(0, 1, 2, 3, 4),
            weekly_hours=None, long_day=None, periodization=None,
            tsb_adapt_limit=0.0,
            latest_metrics_fn=lambda events: SimpleNamespace(tsb=5.0),
            build_plan_fn=spy_build, readiness_module=module,
            eligibility_fn=lambda plan, events, today, now: self._elig(regular),
            min_regular_duration_sec=3600)

        self.assertEqual(len(captured), 2)
        for kwargs in captured:
            self.assertEqual(kwargs["min_regular_duration_sec"], 3600)

    def test_check_default_minimum_duration_preserves_legacy_build_arguments(self):
        module, _, _ = _readiness_stub(is_adaptive=True,
                                       applies_to_day="2026-10-03")
        captured = []

        def spy_build(events, tsb, readiness, **kwargs):
            captured.append(kwargs)
            if readiness is not None:
                kwargs["readiness_report"]["aplicada_em"] = ["2026-10-03"]
            return [{"day": "2026-10-03", "focus": "sweetspot",
                     "params": {"a": 1}, "tss": 40.0, "name": "base"}]

        _silent(
            assess_daily_readiness, _Provider(events=[{"id": 1}]),
            plan=[{"day": "2026-10-03", "focus": "sweetspot",
                   "params": {"a": 1}, "tss": 40.0, "name": "base"}],
            meta={}, today=date(2026, 10, 3), now=None, days=7, ftp=200,
            training_days=(0, 1, 2, 3, 4), weekly_hours=None, long_day=None,
            periodization=None, tsb_adapt_limit=0.0,
            latest_metrics_fn=lambda events: SimpleNamespace(tsb=5.0),
            build_plan_fn=spy_build, readiness_module=module,
            eligibility_fn=lambda plan, events, today, now: self._elig(
                {"day": "2026-10-03", "focus": "sweetspot",
                 "params": {"a": 1}, "tss": 40.0, "name": "base"}))
        self.assertEqual(len(captured), 2)
        for kwargs in captured:
            self.assertIsNone(kwargs["min_regular_duration_sec"])


class WorkoutLifecycleApplicationTest(unittest.TestCase):
    """UI-2 — identidade e lifecycle acessiveis/manipulaveis via Application,
    sem provider/rede."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan_file = self.root / "plan.json"

        def _boom():
            raise AssertionError("operacao local nao pode pedir provider")
        self.app = Application(plan_path=self.plan_file,
                               env_path=self.root / ".env",
                               client_factory=_boom)

    def tearDown(self):
        self.tmp.cleanup()

    def _seed(self, workouts, goal="ftp-builder"):
        self.app.save_plan(workouts, goal=goal)
        return self.app.load_plan()

    def test_dois_treinos_recebem_ids_distintos(self):
        loaded = self._seed([
            {"day": "2026-10-03", "name": "A",
             "external_id": "hermes-plan-2026-10-03"},
            {"day": "2026-10-04", "name": "B",
             "external_id": "hermes-plan-2026-10-04"},
        ])
        ids = [w["id"] for w in loaded]
        self.assertNotEqual(ids[0], ids[1])
        self.assertEqual([w["lifecycle"] for w in loaded],
                         ["planned", "planned"])

    def test_lifecycle_persiste_e_reload_mantem_id(self):
        loaded = self._seed([{"day": "2026-10-03", "name": "A",
                              "external_id": "hermes-plan-2026-10-03"}])
        wid = loaded[0]["id"]
        self.app.set_workout_lifecycle(wid, "cancelled")
        reloaded = self.app.load_plan()
        self.assertEqual(reloaded[0]["id"], wid)
        self.assertEqual(reloaded[0]["lifecycle"], "cancelled")
        self.assertEqual(self.app.workout_lifecycle(wid), "cancelled")

    def test_transicao_invalida_levanta_value_error(self):
        loaded = self._seed([{"day": "2026-10-03", "name": "A",
                              "external_id": "hermes-plan-2026-10-03"}])
        wid = loaded[0]["id"]
        self.app.set_workout_lifecycle(wid, "completed")
        with self.assertRaises(ValueError):
            self.app.set_workout_lifecycle(wid, "planned")

    def test_id_desconhecido_levanta_key_error(self):
        self._seed([{"day": "2026-10-03", "name": "A",
                     "external_id": "hermes-plan-2026-10-03"}])
        with self.assertRaises(KeyError):
            self.app.set_workout_lifecycle("nao-existe", "completed")

    def test_postpone_e_cancel_sao_operacoes_locais(self):
        loaded = self._seed([{"day": "2026-10-03", "name": "A",
                              "external_id": "hermes-plan-2026-10-03"}])
        wid = loaded[0]["id"]
        self.app.postpone_workout(wid)
        self.assertEqual(self.app.workout_lifecycle(wid), "postponed")
        self.app.cancel_workout(wid)
        self.assertEqual(self.app.workout_lifecycle(wid), "cancelled")

    def test_derive_completed_uses_provider_evidence_only_as_evidence(self):
        loaded = self._seed([{"day": "2026-10-01", "name": "A",
                              "focus": "z2",
                              "external_id": "hermes-plan-2026-10-01"}])
        wid = loaded[0]["id"]
        events = [{"external_id": "hermes-plan-2026-10-01",
                   "paired_activity_id": "a1",
                   "start_date_local": "2026-10-01T07:30:00"}]
        self.assertEqual(
            self.app.derive_workout_lifecycle(wid, events=events,
                                              today=date(2026, 10, 3)),
            "completed")
        # Sem evidencia e dia passado -> missed.
        self.assertEqual(
            self.app.derive_workout_lifecycle(wid, events=[],
                                              today=date(2026, 10, 3)),
            "missed")
        # Dia futuro -> planned.
        self.assertEqual(
            self.app.derive_workout_lifecycle(wid, events=[],
                                              today=date(2026, 9, 30)),
            "planned")

    def test_derive_respeita_lifecycle_declarado(self):
        loaded = self._seed([{"day": "2026-10-01", "name": "A",
                              "focus": "z2",
                              "external_id": "hermes-plan-2026-10-01"}])
        wid = loaded[0]["id"]
        self.app.set_workout_lifecycle(wid, "cancelled")
        self.assertEqual(
            self.app.derive_workout_lifecycle(wid, events=[],
                                              today=date(2026, 10, 3)),
            "cancelled")


class ProviderBoundaryTest(unittest.TestCase):
    """UI-3: a Application consome records normalizados, sem conhecer `icu_*`."""

    class _Client:
        def events(self, oldest=None, newest=None):
            return [{"id": 7, "start_date_local": "2026-10-01T07:00:00",
                     "icu_training_load": 55.0, "icu_ctl": 42.0,
                     "icu_atl": 38.0, "external_id": "hermes-plan-2026-10-01",
                     "paired_activity_id": "a1"}]

        def wellness(self, oldest=None, newest=None):
            return [{"id": "2026-10-01", "restingHR": 48, "hrv": 70}]

    def test_build_recebe_records_normalizados(self):
        from src.intervals_adapter import IntervalsAdapter

        provider = IntervalsAdapter(self._Client())
        readiness_mod, _, _ = _readiness_stub()
        captured = {}

        def fake_build(events, tsb, **kwargs):
            captured["events"] = events
            return [{"day": "2026-10-03", "tss": 40.0}]

        result = _silent(
            build_workouts, provider, today=date(2026, 10, 3), days=60,
            days_plan=14, ftp=200, fthr=None, goal=None, periodization=None,
            race_date=None, weekly_hours=None, long_day=None, hr_mode=False,
            ftp_test_date=None, training_days=(0, 1, 2, 3, 4), existing=None,
            latest_metrics_fn=lambda events: SimpleNamespace(tsb=1.0),
            build_plan_fn=fake_build, readiness_module=readiness_mod,
            recovery_module=_recovery_module(),
            pmc_rows_fn=lambda *a: ([], False))

        event = captured["events"][0]
        # A Application/dominio acessam pelo nome normalizado, nao por icu_*.
        self.assertEqual(event.training_load, 55.0)
        self.assertEqual(event.ctl, 42.0)
        self.assertEqual(event.atl, 38.0)
        self.assertEqual(event.external_id, "hermes-plan-2026-10-01")
        self.assertTrue(event.is_completed)
        self.assertEqual(result.plan[0]["lifecycle"], "planned")

    def test_provider_capabilities_expostas_sem_rede(self):
        from src.intervals_adapter import IntervalsAdapter
        from src.provider import ProviderCapability

        app = Application(client_factory=lambda: IntervalsAdapter(self._Client()))
        caps = app.provider_capabilities()
        self.assertIn(ProviderCapability.WRITE_WORKOUTS, caps)
        self.assertIn(ProviderCapability.COMPLETION_LINKS, caps)

    def test_event_is_done_aceita_record_e_dict(self):
        from src.application import _event_is_done
        from src.provider import TrainingEvent

        self.assertTrue(_event_is_done(
            TrainingEvent(raw={}, normalized={"paired_activity_id": "a",
                                              "activity_id": None})))
        self.assertTrue(_event_is_done({"activity_id": "x"}))
        self.assertFalse(_event_is_done(
            TrainingEvent(raw={}, normalized={"paired_activity_id": None,
                                              "activity_id": None})))

    def test_application_nao_conhece_campos_icu(self):
        """A Application so fala dos records normalizados, nao de `icu_*`."""
        import src.application as application

        source = Path(application.__file__).read_text(encoding="utf-8")
        for leaked in ("icu_ctl", "icu_atl", "icu_tsb", "icu_training_load"):
            self.assertNotIn(leaked, source)


if __name__ == "__main__":
    unittest.main()
