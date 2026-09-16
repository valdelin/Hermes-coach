import unittest
from datetime import date, timedelta

from src.plan import (build_plan, event_payload, reconcile, templates,
                      weekly_template, workout_text, orphan_external_ids,
                      REST, FOCUS_THRESHOLD)


class BuildPlanTest(unittest.TestCase):
    def test_gera_dias_e_respeita_tamanho(self):
        plan = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 10, 1))
        self.assertLessEqual(len(plan), 7)
        self.assertTrue(all(w["day"] >= "2026-10-01" for w in plan))

    def test_tsb_baixo_comeca_em_zona2(self):
        plan = build_plan([], -20, ftp=182, days=1,
                          start=date(2026, 9, 28))  # segunda
        self.assertEqual(plan[0]["focus"], weekly_template(-20)[0])

    def test_external_id_estavel(self):
        plan = build_plan([], 2, ftp=182, days=2,
                          start=date(2026, 9, 28))  # segunda
        self.assertEqual(plan[0]["external_id"], "hermes-plan-2026-09-28")

    def test_nunca_treina_sabado_domingo(self):
        for tsb in (-30, -20, -10, 0, 3, 10, 30):
            plan = build_plan([], tsb, ftp=182, days=21,
                              start=date(2026, 9, 14))  # segunda
            for w in plan:
                weekday = date.fromisoformat(w["day"]).weekday()
                self.assertLessEqual(weekday, 4,
                                     f"{w['day']} caiu no fim de semana (tsb {tsb})")

    def test_preenche_todos_os_dias_de_semana(self):
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14))  # segunda, 2 semanas
        days = [date.fromisoformat(w["day"]) for w in plan]
        self.assertEqual(len(days), 10)
        self.assertEqual(set(d.weekday() for d in days), {0, 1, 2, 3, 4})

    def test_orcamento_rolante_respeita_orcamento_semanal(self):
        from src.plan import weekly_budget
        plan = build_plan([], 0, ftp=182, days=21,
                          start=date(2026, 9, 14))  # segunda
        budget = weekly_budget(40)
        for i, w in enumerate(plan):
            day = date.fromisoformat(w["day"])
            janela = sum(x["tss"] for x in plan
                         if 0 <= (day - date.fromisoformat(x["day"])).days < 7)
            self.assertLessEqual(janela, budget + 1,
                                 f"carga estourou no {w['day']}: {janela} > {budget}")

    def test_fit_budget_reduz_carga_seguinte(self):
        from src.plan import _fit_budget, FOCUS_SWEETSPOT
        from src.coach import WorkoutParams, estimate_tss
        params = build_plan([], 0, ftp=182, days=1,
                            start=date(2026, 9, 14))[0]["params"]
        p = WorkoutParams(**params)
        tss = estimate_tss(p, 182)
        recent = [(date(2026, 9, 14), 90), (date(2026, 9, 15), 90)]
        p2, tss2 = _fit_budget(p, tss, recent, budget=160, ftp=182)
        self.assertLess(estimate_tss(p2, 182), tss,
                        "carga deveria cair para caber no orcamento")


class ReconcileTest(unittest.TestCase):
    def test_treino_perdido_insere_recuperacao(self):
        plan = build_plan([], 2, ftp=182, days=5,
                          start=date.today() - timedelta(days=2))
        plan, missed = reconcile(plan, [], ftp=182)
        self.assertTrue(missed)
        nomes = [w["name"] for w in plan]
        self.assertTrue(any("Recuperacao" in n for n in nomes))

    def test_treino_feito_nao_conta_como_perdido(self):
        plan = build_plan([], 2, ftp=182, days=2,
                          start=date(2026, 9, 28))
        events = [{"external_id": plan[0]["external_id"],
                   "paired_activity_id": "41234",
                   "start_date_local": "2026-09-28T07:00:00"}]
        plan, missed = reconcile(plan, events, ftp=182)
        self.assertNotIn(plan[0]["day"], [m["day"] for m in missed])


class EventPayloadTest(unittest.TestCase):
    def test_formato_de_evento(self):
        plan = build_plan([], 2, ftp=182, days=1,
                          start=date(2026, 9, 28))
        payload = event_payload(plan[0], ftp=182)
        self.assertEqual(payload["category"], "WORKOUT")
        self.assertEqual(payload["target"], "POWER")
        self.assertEqual(payload["external_id"], "hermes-plan-2026-09-28")
        self.assertIn("Bloco principal", payload["description"])
        self.assertRegex(payload["description"], r"- \d+m \d+%")

    def test_texto_descricao_nativo(self):
        plan = build_plan([], 2, ftp=182, days=1,
                          start=date(2026, 9, 28))
        lines = workout_text(plan[0]).splitlines()
        self.assertEqual(lines[0], plan[0]["name"])
        self.assertTrue(any(l.startswith(f"{plan[0]['params']['repeats']}x")
                            for l in lines))
        self.assertTrue(any("Aquecimento" in l for l in lines))
        self.assertTrue(any("Desaquecimento" in l for l in lines))

    def test_zone_mapper(self):
        foreach = [1.15, 0.98, 0.7, 0.4]
        expect = ["Z4", "Z3", "Z2", "Z1"]
        from src.plan import _zone
        self.assertEqual([_zone(x) for x in foreach], expect)


class OrphanTest(unittest.TestCase):
    def test_pega_so_eventos_fora_do_plano(self):
        plan = [{"day": "2026-09-21", "external_id": "hermes-plan-2026-09-21"}]
        events = [
            {"external_id": "hermes-plan-2026-09-21"},
            {"external_id": "hermes-plan-2026-09-19"},
            {"external_id": "outro-app-2026-09-19"},
            {"external_id": None},
        ]
        self.assertEqual(orphan_external_ids(plan, events),
                         ["hermes-plan-2026-09-19"])

    def test_respeita_janela_start(self):
        plan = [{"day": "2026-09-21", "external_id": "hermes-plan-2026-09-21"},
                {"day": "2026-09-18", "external_id": "hermes-plan-2026-09-18"}]
        events = [{"external_id": "hermes-plan-2026-09-18"}]
        self.assertEqual(orphan_external_ids(plan, events, start="2026-09-19"),
                         ["hermes-plan-2026-09-18"])

    def test_plano_vazio_apaga_tudo(self):
        events = [
            {"external_id": "hermes-plan-2026-09-17"},
            {"external_id": "hermes-plan-2026-09-19"},
        ]
        self.assertEqual(orphan_external_ids([], events),
                         ["hermes-plan-2026-09-17", "hermes-plan-2026-09-19"])


if __name__ == "__main__":
    unittest.main()