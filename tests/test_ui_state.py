"""UI-5 — ApplicationState/PlanView/WorkoutView (contratos de leitura).

Cobre: leitura 100% local (sem provider), separacao declared/effective,
completion local, freshness, serializacao e ausencia de side effects.
"""
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src import ui_state
from src.application import Application
from src.lifecycle import (LIFECYCLE_CANCELLED, LIFECYCLE_COMPLETED,
                           LIFECYCLE_MISSED, LIFECYCLE_PLANNED,
                           set_completion)
from src.provider import ProviderUnavailable
from src.ui_state import ApplicationState, PlanView, WorkoutView

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 3)


def _boom():
    raise AssertionError("query de estado nao pode pedir provider")


class _Provider:
    provider_name = "intervals"

    def __init__(self, events=None, wellness=None, fail=False):
        self._events = list(events or [])
        self._wellness = list(wellness or [])
        self.fail = fail

    def events(self, oldest=None, newest=None):
        if self.fail:
            raise ProviderUnavailable("offline")
        return list(self._events)

    def wellness(self, oldest=None, newest=None):
        if self.fail:
            raise ProviderUnavailable("offline")
        return list(self._wellness)


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.plan_file = self.root / "plan.json"
        self.snap_file = self.root / "training_snapshot.json"
        self.app = Application(plan_path=self.plan_file,
                               env_path=self.root / ".env",
                               client_factory=_boom,
                               snapshot_path=self.snap_file)

    def tearDown(self):
        self.tmp.cleanup()

    def _save(self, workouts, **meta):
        self.app.save_plan(workouts, **meta)
        return self.app.load_plan()


class PlanViewTest(_Base):
    def test_plano_vazio(self):
        view = self.app.plan_view(today=TODAY)
        self.assertIsInstance(view, PlanView)
        self.assertFalse(view.has_plan)
        self.assertEqual(view.workouts, ())
        self.assertEqual(view.workout_count, 0)
        self.assertEqual(view.completed_count, 0)
        self.assertEqual(view.missed_count, 0)
        self.assertIsNone(view.start_date)
        self.assertIsNone(view.end_date)
        self.assertIsNone(view.next_workout)

    def test_plano_existente_expoe_identidade_local(self):
        self._save([{"day": "2026-10-05", "name": "Z2 60min", "focus": "z2",
                     "external_id": "hermes-plan-2026-10-05", "tss": 55.0,
                     "planned_duration": 60, "hr_mode": False}],
                   goal="ftp-builder", race_date="2026-12-01")
        view = self.app.plan_view(today=TODAY)
        self.assertTrue(view.has_plan)
        self.assertEqual(view.workout_count, 1)
        self.assertEqual(view.start_date, "2026-10-05")
        self.assertEqual(view.end_date, "2026-10-05")
        self.assertEqual(view.meta.goal, "ftp-builder")
        self.assertEqual(view.meta.race_date, "2026-12-01")
        w = view.workouts[0]
        self.assertTrue(w.id)
        self.assertEqual(w.day, "2026-10-05")
        self.assertEqual(w.title, "Z2 60min")
        self.assertEqual(w.focus, "z2")
        self.assertEqual(w.tss, 55.0)
        self.assertEqual(w.planned_duration, 60)

    def test_next_workout_derivado_sem_prescricao(self):
        self._save([
            {"day": "2026-10-01", "name": "passado", "external_id": "a"},
            {"day": "2026-10-05", "name": "futuro", "external_id": "b"},
        ])
        view = self.app.plan_view(today=TODAY)
        self.assertEqual(view.next_workout.day, "2026-10-05")

    def test_plano_legado_sem_id_lifecycle(self):
        self.plan_file.write_text(json.dumps([
            {"day": "2026-10-05", "name": "A", "tss": 40.0,
             "external_id": "hermes-plan-2026-10-05"}]), encoding="utf-8")
        view = self.app.plan_view(today=TODAY)
        w = view.workouts[0]
        self.assertTrue(w.id)
        self.assertEqual(w.lifecycle_declared, LIFECYCLE_PLANNED)
        self.assertIsNone(w.completion)

    def test_provider_linkage_opcional(self):
        self._save([{"day": "2026-10-05", "name": "A", "external_id": "e1"},
                    {"day": "2026-10-06", "name": "B"}])
        view = self.app.plan_view(today=TODAY, provider_name="intervals")
        com_link, sem_link = view.workouts
        self.assertEqual(com_link.provider_link.provider, "intervals")
        self.assertEqual(com_link.provider_link.external_id, "e1")
        self.assertIsNone(sem_link.provider_link)

    def test_cancelled_nao_e_concluido(self):
        wid = self._save([{"day": "2026-10-05", "name": "A",
                           "external_id": "e1"}])[0]["id"]
        self.app.cancel_workout(wid)
        w = self.app.plan_view(today=TODAY).workouts[0]
        self.assertEqual(w.lifecycle_declared, LIFECYCLE_CANCELLED)
        self.assertEqual(w.lifecycle_effective, LIFECYCLE_CANCELLED)
        self.assertFalse(w.completed)

    def test_dia_passado_sem_evidencia_e_missed(self):
        self._save([{"day": "2026-10-01", "name": "A", "external_id": "e1"}])
        w = self.app.plan_view(today=TODAY).workouts[0]
        self.assertEqual(w.lifecycle_declared, LIFECYCLE_PLANNED)
        self.assertEqual(w.lifecycle_effective, LIFECYCLE_MISSED)
        self.assertFalse(w.completed)

    def test_completion_local_alimenta_o_efetivo(self):
        wid = self._save([{"day": "2026-10-01", "name": "A",
                           "external_id": "e1"}])[0]["id"]
        self.app.mark_completed(wid, source="provider_match",
                                observed_at="2026-10-01",
                                provider_event_id=7, activity_id="a1")
        w = self.app.plan_view(today=TODAY).workouts[0]
        self.assertTrue(w.completed)
        self.assertEqual(w.lifecycle_declared, LIFECYCLE_COMPLETED)
        self.assertEqual(w.lifecycle_effective, LIFECYCLE_COMPLETED)
        self.assertEqual(w.completion.source, "provider_match")
        self.assertEqual(w.completion.observed_at, "2026-10-01")
        self.assertEqual(w.completion.activity_id, "a1")
        self.assertEqual(w.completion.provider_event_id, 7)
        self.assertEqual(w.provider_link.activity_id, "a1")
        self.assertFalse(w.conflict)

    def test_conflito_nao_e_escondido(self):
        """Evidencia de provider + estado declarado incompativel = conflito
        visivel, nao sobrescrita."""
        wid = self._save([{"day": "2026-10-05", "name": "A",
                           "external_id": "e1"}])[0]["id"]
        plano = self.app.load_plan()
        treino = next(w for w in plano if w["id"] == wid)
        treino.update(set_completion(treino, source="provider_match",
                                     activity_id="a1"))
        treino["lifecycle"] = LIFECYCLE_CANCELLED
        self.app.save_plan(plano)
        w = self.app.plan_view(today=TODAY).workouts[0]
        self.assertTrue(w.conflict)
        self.assertEqual(w.lifecycle_declared, LIFECYCLE_CANCELLED)
        self.assertFalse(w.completed)

    def test_declared_nao_e_sobrescrito_pelo_efetivo(self):
        wid = self._save([{"day": "2026-10-01", "name": "A",
                           "external_id": "e1"}])[0]["id"]
        self.app.cancel_workout(wid)
        self.assertEqual(self.app.workout_lifecycle(wid), LIFECYCLE_CANCELLED)

    def test_ordena_por_dia_e_ignora_meta(self):
        self._save([{"day": "2026-10-09", "name": "B", "external_id": "b"},
                    {"day": "2026-10-05", "name": "A", "external_id": "a"}])
        view = self.app.plan_view(today=TODAY)
        self.assertEqual([w.day for w in view.workouts],
                         ["2026-10-05", "2026-10-09"])


class ApplicationStateTest(_Base):
    def test_sem_plano_e_sem_snapshot(self):
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertIsInstance(state, ApplicationState)
        self.assertFalse(state.plan.has_plan)
        self.assertIsNone(state.snapshot)

    def test_sem_provider_consulta_estado(self):
        self._save([{"day": "2026-10-05", "name": "A", "external_id": "e1"}])
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertTrue(state.plan.has_plan)
        self.assertEqual(state.plan.workout_count, 1)

    def test_snapshot_fresh_stale_e_unknown(self):
        provider = _Provider(events=[{"id": 1, "icu_training_load": 55.0,
                                      "icu_ctl": 42.0}],
                             wellness=[{"id": "2026-10-03",
                                        "restingHR": 48}])
        result = self.app.sync_provider_state(provider=provider, today=TODAY,
                                              now=T0)
        self.assertTrue(result.ok)

        fresh = self.app.get_application_state(today=TODAY, now=T0)
        self.assertEqual(fresh.snapshot.provider, "intervals")
        self.assertEqual(fresh.snapshot.events[0]["training_load"], 55.0)
        self.assertEqual(fresh.snapshot.wellness[0]["resting_hr"], 48)
        self.assertEqual(fresh.snapshot.captured_at, T0.isoformat())
        self.assertEqual(fresh.snapshot.freshness.status, "fresh")
        self.assertEqual(fresh.snapshot.freshness.age_seconds, 0.0)

        later = T0 + timedelta(days=3)
        stale = self.app.get_application_state(today=TODAY, now=later)
        self.assertEqual(stale.snapshot.freshness.status, "stale")
        self.assertGreater(stale.snapshot.freshness.age_seconds, 0)

    def test_freshness_unknown_sem_sync(self):
        self._save([{"day": "2026-10-05", "name": "A", "external_id": "e1"}])
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertIsNone(state.snapshot)
        self.assertEqual(ui_state.build_freshness_view(None), None)

    def test_offline_serve_ultimo_estado_persistido(self):
        self._save([{"day": "2026-10-05", "name": "A", "external_id": "e1"}])
        self.app.sync_provider_state(
            provider=_Provider(events=[{"id": 1, "icu_training_load": 10.0}]),
            today=TODAY, now=T0)
        falho = Application(plan_path=self.plan_file,
                            env_path=self.root / ".env",
                            client_factory=_boom,
                            snapshot_path=self.snap_file)
        state = falho.get_application_state(today=TODAY, now=T0)
        self.assertTrue(state.plan.has_plan)
        self.assertEqual(state.snapshot.events[0]["training_load"], 10.0)

    def test_provider_indisponivel_nao_afeta_a_query(self):
        self._save([{"day": "2026-10-05", "name": "A", "external_id": "e1"}])
        falho = self.app.sync_provider_state(provider=_Provider(fail=True),
                                             today=TODAY, now=T0)
        self.assertFalse(falho.ok)
        self.assertIn("offline", falho.error)
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertTrue(state.plan.has_plan)
        self.assertIsNone(state.snapshot)

    def test_sem_metadata(self):
        self.plan_file.write_text(json.dumps([
            {"day": "2026-10-05", "name": "A", "external_id": "e1"}]),
            encoding="utf-8")
        state = self.app.get_application_state(today=TODAY, now=T0)
        self.assertIsNone(state.plan.meta.goal)
        self.assertIsNone(state.plan.meta.race_date)
        self.assertIsNone(state.plan.meta.ftp_test_date)


class SideEffectFreeTest(_Base):
    def test_query_nao_escreve_nao_sincroniza_nao_altera_estado(self):
        self._save([{"day": "2026-10-01", "name": "A", "external_id": "e1"},
                    {"day": "2026-10-05", "name": "B", "external_id": "e2"}],
                   goal="ftp-builder")
        self.app.sync_provider_state(
            provider=_Provider(events=[{"id": 1, "icu_training_load": 10.0}]),
            today=TODAY, now=T0)
        plano_antes = self.plan_file.read_text(encoding="utf-8")
        snap_antes = self.snap_file.read_text(encoding="utf-8")
        stat_antes = self.plan_file.stat()

        # client_factory levanta -> prova que nada de provider foi chamado.
        state = self.app.get_application_state(today=TODAY, now=T0)

        self.assertTrue(state.plan.has_plan)
        self.assertIsNotNone(state.snapshot)
        self.assertEqual(self.plan_file.read_text(encoding="utf-8"),
                         plano_antes)
        self.assertEqual(self.snap_file.read_text(encoding="utf-8"),
                         snap_antes)
        self.assertEqual(self.plan_file.stat().st_mtime_ns,
                         stat_antes.st_mtime_ns)
        # lifecycle intacto (nada virou completed por consulta)
        estados = [(w.lifecycle_declared, w.lifecycle_effective)
                   for w in state.plan.workouts]
        self.assertEqual(estados, [(LIFECYCLE_PLANNED, LIFECYCLE_MISSED),
                                   (LIFECYCLE_PLANNED, LIFECYCLE_PLANNED)])

    def test_repetir_a_query_da_o_mesmo_estado(self):
        self._save([{"day": "2026-10-05", "name": "A", "external_id": "e1"}])
        primeiro = self.app.get_application_state(today=TODAY, now=T0)
        segundo = self.app.get_application_state(today=TODAY, now=T0)
        self.assertEqual(primeiro.to_dict(), segundo.to_dict())

    def test_views_sao_imutaveis(self):
        view = self.app.plan_view(today=TODAY)
        with self.assertRaises(Exception):
            view.has_plan = False  # type: ignore[misc]
        with self.assertRaises(Exception):
            view.workouts[0].completed = True  # type: ignore[misc]


class SerializationTest(_Base):
    def test_to_dict_deterministico_e_serializavel(self):
        self._save([{"day": "2026-10-05", "name": "A", "focus": "z2",
                     "external_id": "e1", "tss": 40.0,
                     "planned_duration": 45}], goal="ftp-builder")
        state = self.app.get_application_state(today=TODAY, now=T0)
        payload = state.to_dict()
        json.dumps(payload)  # serializavel
        self.assertEqual(payload, state.to_dict())
        w = payload["plan"]["workouts"][0]
        self.assertTrue(w["id"])
        self.assertEqual(w["lifecycle"], LIFECYCLE_PLANNED)
        self.assertEqual(w["lifecycle_declared"], LIFECYCLE_PLANNED)
        self.assertEqual(w["lifecycle_effective"], LIFECYCLE_PLANNED)
        self.assertIsNone(w["completion"])
        self.assertEqual(w["tss"], 40.0)

    def test_enums_e_none_serializam_texto(self):
        self._save([{"day": "2026-10-01", "external_id": "e1"}])
        payload = self.app.get_application_state(today=TODAY, now=T0).to_dict()
        w = payload["plan"]["workouts"][0]
        self.assertEqual(w["lifecycle_effective"], LIFECYCLE_MISSED)
        self.assertIsNone(w["title"])
        self.assertIsNone(w["focus"])
        self.assertIsNone(w["completion"])
        self.assertIsNone(payload["snapshot"])

    def test_view_nao_contem_objeto_de_provider(self):
        self.app.sync_provider_state(
            provider=_Provider(events=[{"id": 1, "icu_training_load": 10.0}]),
            today=TODAY, now=T0)
        payload = self.app.get_application_state(today=TODAY, now=T0).to_dict()
        bruto = json.dumps(payload)
        self.assertNotIn("provider_request", bruto)
        for chave in ("icu_training_load", "icu_ctl", "paired_activity_id",
                      "IntervalsAdapter", "provider_error"):
            self.assertNotIn(chave, bruto)


class BoundaryTest(unittest.TestCase):
    @staticmethod
    def _code_only():
        """Fonte sem comentarios nem literais (docstrings): testa o CODIGO, nao a
        prosa que explica por que o limite existe."""
        import io
        import tokenize
        src = Path(ui_state.__file__).read_text(encoding="utf-8")
        return " ".join(
            tok.string for tok in tokenize.generate_tokens(
                io.StringIO(src).readline)
            if tok.type not in (tokenize.COMMENT, tokenize.STRING))

    def test_view_nao_conhece_payload_do_provider(self):
        codigo = self._code_only()
        for token in ("icu_", "paired_activity_id", "IntervalsApiError",
                      "requests.", "IntervalsAdapter", "plan.json", "load_plan"):
            self.assertNotIn(token, codigo)

    def test_view_nao_importa_application_ou_provider(self):
        codigo = self._code_only()
        self.assertNotIn("application", codigo)
        self.assertNotIn("provider_capabilities", codigo)

    def test_workout_view_lifecycle_atalho_efetivo(self):
        view = WorkoutView(id="x", day="2026-10-05",
                           lifecycle_declared=LIFECYCLE_PLANNED,
                           lifecycle_effective=LIFECYCLE_MISSED)
        self.assertEqual(view.lifecycle, LIFECYCLE_MISSED)


if __name__ == "__main__":
    unittest.main()