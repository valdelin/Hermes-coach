"""FTP-H8: o evento de teste de FTP nao pode carregar workout estruturado.

Bug observado: um evento "Ramp Test (FTP)" era publicado com a descricao/
workout builder de uma sessao Z2 continua (30 min a 55%), o que fazia o
Zwift executar recovery no dia do teste.

Estes testes fixam o contrato:
- o dia do teste e um evento informativo (sem passos prescritivos);
- o titulo nao promete um protocolo que o Hermes nao possui;
- apenas o dia D0 recebe a intencao de teste (nao ha transformacao de
  treino alheio por titulo);
- nenhum caminho cria FtpReference nem muta o historico de FTP.
"""

import os
import tempfile
import unittest
from datetime import date, timedelta

from src import plan as plan_mod
from src.application import Application, push_workouts
from src.coach import last_ftp_test
from src.plan import (
    FTP_TEST_INTENT_EXTERNAL,
    FTP_TEST_INTENT_KEY,
    build_plan,
    event_payload,
    workout_text,
)

START = date(2026, 9, 21)  # segunda-feira
TEST_DAY = "2026-09-25"    # sexta-feira


def _plan(**kwargs):
    return build_plan([], 4, ftp=182, days=14, start=START,
                      goal="ftp-builder", **kwargs)


def _steps(text):
    """Passos do workout builder do Intervals: linhas iniciadas por '- '."""
    return [line for line in text.splitlines() if line.strip().startswith("- ")]


class FakeProvider:
    """Provider offline: so captura o batch publicado."""

    def __init__(self):
        self.batch = None

    def events(self, oldest=None, newest=None):
        return []

    def create_events(self, payloads, upsert=True):
        self.batch = payloads
        return 200, payloads

    def delete_events(self, external_ids):
        return 200, {"eventsDeleted": 0}

    def delete_event(self, event_id):
        return 200


class FtpTestEventContractTest(unittest.TestCase):
    def setUp(self):
        self.plan = _plan(ftp_test_date=TEST_DAY)
        self.by_day = {w["day"]: w for w in self.plan}
        self.test_day = self.by_day[TEST_DAY]

    def test_evento_de_teste_nao_exporta_workout_z2(self):
        payload = event_payload(self.test_day, ftp=182)
        self.assertEqual(_steps(payload["description"]), [],
                         "evento de teste nao pode carregar passos prescritivos")
        self.assertNotIn("%", payload["description"],
                         "descricao do teste nao pode prescrever percentual de FTP")

    def test_titulo_nao_promete_ramp_test(self):
        payload = event_payload(self.test_day, ftp=182)
        self.assertNotIn("Ramp", payload["name"])
        self.assertIn("FTP Test", payload["name"])
        self.assertNotIn("Ramp", " ".join(w["name"] for w in self.plan))

    def test_intencao_e_estrutural_e_exclusiva_do_d0(self):
        self.assertEqual(self.test_day[FTP_TEST_INTENT_KEY],
                         FTP_TEST_INTENT_EXTERNAL)
        com_marcador = [w["day"] for w in self.plan
                        if w.get(FTP_TEST_INTENT_KEY)]
        self.assertEqual(com_marcador, [TEST_DAY])

    def test_teste_nao_prescreve_carga(self):
        self.assertEqual(self.test_day["tss"], 0.0)
        self.assertEqual(self.test_day["planned_duration"], 0)

    def test_workout_text_do_teste_nao_gera_passos(self):
        self.assertEqual(_steps(workout_text(self.test_day, 182)), [])

    def test_dias_de_preparacao_e_recuperacao_continuam_estruturados(self):
        for day, name in (("2026-09-23", "Recuperacao (pre-teste FTP)"),
                          ("2026-09-24", "Spin facil (pre-teste FTP)")):
            workout = self.by_day[day]
            self.assertEqual(workout["name"], f"{day} - {name}")
            self.assertNotIn(FTP_TEST_INTENT_KEY, workout)
            self.assertGreater(len(_steps(workout_text(workout, 182))), 0)
            self.assertGreater(workout["tss"], 0)
        # D+1 cai no sabado (fora da agenda): descanso natural, nada criado.
        self.assertNotIn("2026-09-26", self.by_day)

    def test_recuperacao_pos_teste_continua_estruturada_na_agenda(self):
        # Teste na quinta: D+1 = sexta (dia de treino) e continua prescrito.
        plan = _plan(ftp_test_date="2026-09-24")
        by_day = {w["day"]: w for w in plan}
        after = by_day["2026-09-25"]
        self.assertEqual(after["name"],
                         "2026-09-25 - Recuperacao (pos-teste FTP)")
        self.assertNotIn(FTP_TEST_INTENT_KEY, after)
        self.assertGreater(len(_steps(workout_text(after, 182))), 0)
        self.assertGreater(after["tss"], 0)

    def test_treino_normal_permanece_inalterado(self):
        base = {w["day"]: w for w in _plan()}
        prep_days = {"2026-09-23", "2026-09-24", TEST_DAY, "2026-09-26"}
        for day, workout in base.items():
            if day in prep_days:
                continue
            self.assertEqual(self.by_day[day], workout)

    def test_payload_publicado_nao_contem_recovery_no_dia_do_teste(self):
        provider = FakeProvider()
        push_workouts(
            provider,
            plan=self.plan,
            start=START.isoformat(),
            ftp=182,
            fthr=None,
            lang="pt",
            event_payload_fn=event_payload,
            prev_same_focus_fn=lambda _plan, _w: None,
            orphan_external_ids_fn=lambda *_a, **_k: [],
            manual_duplicate_ids_fn=lambda *_a, **_k: [],
            dry_run=False,
        )
        by_day = {p["start_date_local"][:10]: p for p in provider.batch}
        test_payload = by_day[TEST_DAY]
        self.assertEqual(_steps(test_payload["description"]), [])
        self.assertNotIn("Zona 2", test_payload["description"])
        # os dias vizinhos continuam sendo sessoes prescritas de verdade
        self.assertGreater(len(_steps(by_day["2026-09-24"]["description"])), 0)

    def test_publicacao_nao_toca_historico_de_ftp(self):
        provider = FakeProvider()
        cwd = os.getcwd()
        with tempfile.TemporaryDirectory() as tmp:
            os.chdir(tmp)
            try:
                push_workouts(
                    provider, plan=self.plan, start=START.isoformat(),
                    ftp=182, fthr=None, lang="pt",
                    event_payload_fn=event_payload,
                    prev_same_focus_fn=lambda _plan, _w: None,
                    orphan_external_ids_fn=lambda *_a, **_k: [],
                    manual_duplicate_ids_fn=lambda *_a, **_k: [],
                    dry_run=False,
                )
                self.assertEqual(os.listdir(tmp), [],
                                 "publicar o teste nao pode escrever evidencia/"
                                 "referencia de FTP")
            finally:
                os.chdir(cwd)


class FtpTestPersistenceTest(unittest.TestCase):
    """O marcador e estado persistido: precisa sobreviver ao plan.json e ao
    enrich (id/lifecycle), senao o proximo push volta a publicar Z2."""

    def test_marcador_sobrevive_ao_plan_json_e_ao_enrich(self):
        plan = _plan(ftp_test_date=TEST_DAY)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.json")
            plan_mod.save_plan(plan, path=path, goal="ftp-builder")
            loaded = plan_mod.load_plan(path)
            enriched = Application.enrich_plan(loaded)
        by_day = {w["day"]: w for w in enriched}
        test_day = by_day[TEST_DAY]
        self.assertEqual(test_day[FTP_TEST_INTENT_KEY],
                         FTP_TEST_INTENT_EXTERNAL)
        self.assertIn("id", test_day)
        payload = event_payload(test_day, ftp=182)
        self.assertEqual(_steps(payload["description"]), [])
        self.assertNotIn("Ramp", payload["name"])


class FtpTestKeywordTest(unittest.TestCase):
    """Deteccao de teste de FTP existente: sem falso positivo por texto solto."""

    def _last(self, name, day="2026-07-01"):
        return last_ftp_test([{"name": name,
                              "start_date_local": f"{day}T07:00:00"}])

    def test_reconhece_titulos_de_teste(self):
        for name in ("Ramp Test", "FTP Test", "FTP Retest",
                     "Teste de FTP", "2026-07-01 - FTP Test"):
            self.assertEqual(self._last(name), "2026-07-01", name)

    def test_prova_nao_e_teste_de_ftp(self):
        self.assertIsNone(self._last("Prova: dia de prova"))

    def test_treino_com_ftp_no_nome_nao_e_teste(self):
        for name in ("FTP Builder - Zona 2", "Treino de FTP baixo"):
            self.assertIsNone(self._last(name), name)

    def test_nenhum_protocolo_e_inferido_do_texto(self):
        # O Hermes nao classifica protocolo a partir do titulo: o unico sinal
        # estrutural e o marcador do dia D0. Um "Ramp Test" importado do
        # provider nao vira FtpProtocol.RAMP_TEST por causa do nome.
        self.assertFalse(hasattr(plan_mod, "protocol_from_name"))


class FtpTestReconcileProtectionTest(unittest.TestCase):
    """P2: ajuste automatico por carga extra nao pode apagar o dia do teste.

    O dia D0 e uma DATA escolhida pelo atleta (ou externa). Se a recuperacao
    do treino extra cair nesse dia, o teste seria substituido por
    "Recuperacao (plano ajustado)" sem aviso -- exatamente o que o gate
    impede. A recuperacao vai para o proximo dia de treino livre.
    """

    ALL_DAYS = tuple(range(7))

    def _plan(self):
        today = date.today()
        test_day = today + timedelta(days=1)
        plan = build_plan([], 0, ftp=182, days=10, start=today,
                          training_days=self.ALL_DAYS, goal="ftp-builder",
                          ftp_test_date=test_day.isoformat())
        return plan, today, test_day

    def _plan_without_post_test_recovery(self):
        """Plano em que o dia seguinte ao teste esta livre (sem a recuperacao
        pos-teste que o build insere): exercita o desvio da recuperacao."""
        plan, today, test_day = self._plan()
        return [w for w in plan if "pos-teste" not in w["name"]], today, test_day

    def _extra_today(self, today, load=200.0):
        return [{"day": today, "load": load}]

    def test_carga_extra_nao_substitui_o_dia_do_teste(self):
        plan, today, test_day = self._plan()
        before = [dict(w) for w in plan if w["day"] == test_day.isoformat()][0]
        report = {}

        from src.plan import _adjust_for_extra_workouts
        adjusted = _adjust_for_extra_workouts(
            plan, self._extra_today(today), ftp=182,
            training_days=self.ALL_DAYS, report=report)

        after = [dict(w) for w in adjusted if w["day"] == test_day.isoformat()]
        self.assertEqual(len(after), 1, "o dia do teste nao pode desaparecer")
        self.assertEqual(after[0]["name"], before["name"])
        self.assertEqual(after[0].get(FTP_TEST_INTENT_KEY),
                         FTP_TEST_INTENT_EXTERNAL)
        self.assertEqual(after[0]["tss"], 0.0)
        self.assertEqual(after[0]["planned_duration"], 0)
        self.assertNotIn("Recuperacao", after[0]["name"])
        # nenhuma recuperacao automatica pode cair no dia do teste
        self.assertFalse(any(w["day"] == test_day.isoformat()
                             and "Recuperacao (plano ajustado)" in w["name"]
                             for w in adjusted))

    def test_recuperacao_vai_para_o_proximo_dia_livre(self):
        plan, today, test_day = self._plan_without_post_test_recovery()
        report = {}
        from src.plan import _adjust_for_extra_workouts
        adjusted = _adjust_for_extra_workouts(
            plan, self._extra_today(today), ftp=182,
            training_days=self.ALL_DAYS, report=report)

        recovery = [w for w in adjusted
                    if "Recuperacao (plano ajustado)" in w["name"]]
        self.assertEqual(len(recovery), 1,
                         "a recuperacao do extra continua sendo programada")
        self.assertNotEqual(recovery[0]["day"], test_day.isoformat())
        self.assertEqual(report["ftp_test_preserved"], test_day.isoformat())
        self.assertEqual(report["recovery_day"], recovery[0]["day"])

    def test_recuperacao_nunca_sobrescreve_dia_marcado(self):
        from src.plan import _insert_recovery
        plan, _today, test_day = self._plan()
        result = _insert_recovery(plan, test_day.isoformat(), ftp=182,
                                  training_days=self.ALL_DAYS,
                                  on=test_day.isoformat())
        self.assertEqual(result, plan,
                         "_insert_recovery nao pode reescrever o dia do teste")

    def test_sem_marcador_o_ajuste_reage_como_antes(self):
        """Sem o marcador, a recuperacao volta a ocupar o dia alvo (prova que
        a autoridade e o marcador estrutural, nao o titulo)."""
        from src.plan import _adjust_for_extra_workouts
        plan, today, test_day = self._plan()
        for w in plan:
            w.pop(FTP_TEST_INTENT_KEY, None)
        report = {}
        adjusted = _adjust_for_extra_workouts(
            plan, self._extra_today(today), ftp=182,
            training_days=self.ALL_DAYS, report=report)
        target = [w for w in adjusted if w["day"] == test_day.isoformat()][0]
        self.assertIn("Recuperacao (plano ajustado)", target["name"])
        self.assertEqual(report, {})

    def test_reconcile_preserva_o_marcador_e_anuncia_o_desvio(self):
        from src.plan import reconcile
        plan, today, test_day = self._plan_without_post_test_recovery()
        events = [{"external_id": None, "paired_activity_id": "999",
                   "start_date_local": f"{today}T10:00:00",
                   "icu_training_load": 200.0}]
        adjusted, _missed, info = reconcile(
            plan, events, ftp=182, training_days=self.ALL_DAYS)
        test = [w for w in adjusted if w["day"] == test_day.isoformat()][0]
        self.assertEqual(test.get(FTP_TEST_INTENT_KEY),
                         FTP_TEST_INTENT_EXTERNAL)
        self.assertNotIn("Recuperacao", test["name"])
        self.assertEqual(info["ftp_test_preserved"], test_day.isoformat())
        self.assertIsNotNone(info["recovery_day"])
        self.assertNotEqual(info["recovery_day"], test_day.isoformat())
