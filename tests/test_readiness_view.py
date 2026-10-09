"""RDY-1 — ReadinessView local: observacoes, derivacoes e heuristica existente.

Nenhum teste depende do relogio real: `today`/`now` sao sempre explicitos.
"""
import contextlib
import io
import json
import tempfile
import tokenize
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from src import readiness, ui_state
from src.application import Application
from src.snapshot import TrainingSnapshot

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 3)


def _boom():
    raise AssertionError("ReadinessView nao pode chamar provider")


def _code_only(path):
    source = Path(path).read_text(encoding="utf-8")
    return " ".join(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type not in (tokenize.COMMENT, tokenize.STRING))


class _Base(unittest.TestCase):
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

    def _snapshot(self, *, wellness=None, metrics=None, captured=T0):
        snap = TrainingSnapshot.capture(
            wellness=wellness or [], events=[], activities=[], metrics=metrics,
            provider="intervals", now=captured)
        self.app.save_training_snapshot(snap)
        return snap


class BasicViewTest(_Base):
    def test_sem_snapshot_e_indisponivel_sem_objeto_artificial(self):
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertFalse(view.available)
        self.assertEqual(view.target_day, "2026-10-03")
        self.assertIsNone(view.reference_day)
        self.assertIsNone(view.wellness)
        self.assertIsNone(view.pmc)
        self.assertIsNone(view.freshness)
        self.assertIsNone(view.heuristic_level)
        self.assertEqual(view.heuristic_observations, ())

    def test_wellness_completo_expoe_apenas_observados(self):
        self._snapshot(wellness=[
            {"id": "2026-10-01", "restingHR": 50, "hrv": 60,
             "sleepSecs": 8 * 3600, "readiness": 80, "stress": 20},
            {"id": "2026-10-02", "restingHR": 51, "hrv": 62,
             "sleepSecs": 7 * 3600, "readiness": 70, "stress": 25},
        ])
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertTrue(view.available)
        self.assertEqual(view.reference_day, "2026-10-02")
        self.assertEqual(view.wellness.day, "2026-10-02")
        self.assertEqual(view.wellness.resting_hr, 51.0)
        self.assertEqual(view.wellness.hrv, 62.0)
        self.assertEqual(view.wellness.sleep_secs, 7 * 3600.0)
        self.assertEqual(view.wellness.readiness_score, 70.0)
        self.assertEqual(view.wellness.stress, 25.0)
        self.assertIsNone(view.wellness.sleep_score)

    def test_wellness_parcial_preserva_ausencia(self):
        self._snapshot(wellness=[{"id": "2026-10-02", "hrvSDNN": 71}])
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertTrue(view.available)
        self.assertEqual(view.wellness.hrv_sdnn, 71.0)
        self.assertIsNone(view.wellness.hrv)
        self.assertIsNone(view.wellness.resting_hr)
        self.assertIsNone(view.wellness.sleep_secs)
        self.assertIsNone(view.wellness.readiness_score)

    def test_eixos_separam_modelo_implementacao_e_dados_do_dia(self):
        self._snapshot(wellness=[{"id": "2026-10-02", "hrv": 71}])
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertEqual((view.model_axis_count, view.implemented_axis_count,
                          view.available_axis_count), (7, 3, 1))
        states = {axis.axis: axis for axis in view.axis_states}
        self.assertTrue(states["hrv_score"].available)
        self.assertTrue(states["rhr_score"].implemented)
        self.assertFalse(states["rhr_score"].available)
        self.assertFalse(states["performance_score"].implemented)

    def test_sem_wellness_expoe_cobertura_sem_classificacao(self):
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertEqual((view.model_axis_count, view.implemented_axis_count,
                          view.available_axis_count), (7, 3, 0))
        self.assertIsNone(view.heuristic_score)
        self.assertIsNone(view.heuristic_level)

    def test_target_e_reference_day_sao_distintos_e_explicitos(self):
        self._snapshot(wellness=[{"id": "2026-10-04", "restingHR": 50,
                                  "hrv": 60, "sleepSecs": 8 * 3600}])
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertEqual(view.target_day, "2026-10-03")
        self.assertEqual(view.reference_day, "2026-10-04")


class PmcAndFreshnessTest(_Base):
    def test_reutiliza_pmc_e_form_pct_sem_recalcular(self):
        self._snapshot(
            wellness=[{"id": "2026-10-03", "restingHR": 50, "hrv": 60,
                       "sleepSecs": 8 * 3600}],
            metrics={"ctl": 100.0, "atl": 125.0, "tsb": -25.0})
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertEqual((view.pmc.ctl, view.pmc.atl, view.pmc.tsb,
                          view.pmc.form_pct), (100.0, 125.0, -25.0, -25.0))

    def test_pmc_ausente_nao_impede_wellness(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertTrue(view.available)
        self.assertIsNone(view.pmc)

    def test_form_pct_none_e_preservado(self):
        self._snapshot(
            wellness=[{"id": "2026-10-03", "restingHR": 50}],
            metrics={"ctl": 0.0, "atl": 10.0, "tsb": -5.0})
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertIsNone(view.pmc.form_pct)
        self.assertEqual((view.pmc.ctl, view.pmc.atl, view.pmc.tsb),
                         (0.0, 10.0, -5.0))

    def test_snapshot_stale_expoe_sinais_e_freshness(self):
        self._snapshot(
            wellness=[{"id": "2026-10-03", "restingHR": 50}],
            metrics={"ctl": 100.0, "tsb": -25.0})
        view = self.app.get_readiness_view(
            today=TODAY, now=T0 + timedelta(days=3))
        self.assertEqual(view.freshness.status, "stale")
        self.assertEqual(view.pmc.form_pct, -25.0)


class HeuristicTest(_Base):
    def test_preserva_classificacao_existente_sem_action(self):
        self._snapshot(wellness=[
            {"id": "2026-10-01", "restingHR": 50, "hrv": 60,
             "sleepSecs": 8 * 3600, "readiness": 80},
            {"id": "2026-10-02", "restingHR": 50, "hrv": 60,
             "sleepSecs": 5 * 3600, "readiness": 80},
        ])
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertEqual(view.heuristic_level, "yellow")
        self.assertTrue(dict(view.heuristic_signals)["sleep_short"])
        sleep = next(x for x in view.heuristic_observations
                     if x.axis == "sleep_score")
        self.assertTrue(sleep.flagged)
        self.assertEqual(sleep.source, "wellness.sleep_secs")
        self.assertFalse(hasattr(view, "action"))
        self.assertFalse(hasattr(view, "advice"))

    def test_nao_chama_readiness_decision_policy(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50,
                                  "hrv": 60, "sleepSecs": 8 * 3600}])
        with mock.patch.object(readiness, "readiness_decision",
                               side_effect=AssertionError("policy chamada")):
            view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertEqual(view.heuristic_level, "green")

    def test_heuristic_none_sem_wellness(self):
        self._snapshot(metrics={"ctl": 100.0, "tsb": -10.0})
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        self.assertFalse(view.available)
        self.assertIsNone(view.heuristic_level)
        self.assertEqual(view.heuristic_confidence, 0.0)
        self.assertEqual(view.pmc.form_pct, -10.0)


class OfflineAndSerializationTest(_Base):
    def test_query_e_offline_e_sem_side_effects(self):
        self.app.save_plan([{"day": "2026-10-03", "name": "A",
                            "external_id": "e1"}], goal="ftp-builder")
        self._snapshot(
            wellness=[{"id": "2026-10-03", "restingHR": 50, "hrv": 60,
                       "sleepSecs": 8 * 3600}],
            metrics={"ctl": 100.0, "tsb": -25.0})
        plan_before = self.plan_file.read_text(encoding="utf-8")
        snapshot_before = self.snapshot_file.read_text(encoding="utf-8")
        mtime_before = self.snapshot_file.stat().st_mtime_ns

        with contextlib.redirect_stdout(io.StringIO()) as out:
            view = self.app.get_readiness_view(today=TODAY, now=T0)

        self.assertEqual(out.getvalue(), "")
        self.assertTrue(view.available)
        self.assertEqual(view.pmc.form_pct, -25.0)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"), plan_before)
        self.assertEqual(self.snapshot_file.read_text(encoding="utf-8"),
                         snapshot_before)
        self.assertEqual(self.snapshot_file.stat().st_mtime_ns, mtime_before)

    def test_serializacao_estavel(self):
        self._snapshot(
            wellness=[{"id": "2026-10-03", "restingHR": 50, "hrv": 60,
                       "sleepSecs": 8 * 3600}],
            metrics={"ctl": 100.0, "atl": 125.0, "tsb": -25.0})
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        payload = view.to_dict()
        self.assertEqual(payload, view.to_dict())
        self.assertEqual(payload["target_day"], "2026-10-03")
        self.assertEqual(payload["pmc"]["form_pct"], -25.0)
        self.assertEqual(payload["freshness"]["status"], "fresh")
        self.assertEqual(payload["wellness"]["sleep_score"], None)
        json.dumps(payload)

    def test_views_sao_imutaveis(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self.app.get_readiness_view(today=TODAY, now=T0)
        with self.assertRaises(Exception):
            view.available = False  # type: ignore[misc]


class BoundaryTest(unittest.TestCase):
    def test_view_nao_conhece_provider_nem_campos_crus(self):
        code = _code_only(ui_state.__file__)
        for token in ("icu_", "paired_activity_id", "IntervalsAdapter",
                      "requests", "provider_fields"):
            self.assertNotIn(token, code)

    def test_view_nao_chama_fluxos_prescritivos(self):
        code = _code_only(ui_state.__file__)
        for token in ("readiness_decision", "assess_daily_readiness",
                      "ReadinessAction", "mark_completed", "save_plan"):
            self.assertNotIn(token, code)


if __name__ == "__main__":
    unittest.main()
