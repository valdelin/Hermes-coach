import unittest
from datetime import date, timedelta

from src.plan import (build_plan, event_payload, reconcile, templates,
                      weekly_template, workout_text, orphan_external_ids,
                      parse_training_days, _next_training_day,
                      _reduce_next_hard,
                      DEFAULT_TRAINING_DAYS,
                      REST, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_ZONE2)


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

    def test_build_preserva_treino_de_hoje_do_plano_atual(self):
        today = date.today()
        if today.weekday() >= 5:
            self.skipTest("hoje e fim de semana")
        existing = [{"day": today.isoformat(), "focus": "zone2",
                     "planned_duration": 2400,
                     "name": f"{today} - Recuperacao (plano ajustado)",
                     "params": {"on_sec": 1200}, "tss": 14.0,
                     "external_id": f"hermes-plan-{today}"}]
        plan = build_plan([], -7, ftp=182, days=5, existing=existing)
        self.assertEqual(plan[0]["day"], today.isoformat())
        self.assertIn("Recuperacao (plano ajustado)", plan[0]["name"])

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


class TrainingDaysTest(unittest.TestCase):
    def test_parse_nomes_ingles(self):
        self.assertEqual(parse_training_days("mon,tue,wed,thu,fri"),
                         DEFAULT_TRAINING_DAYS)
        self.assertEqual(parse_training_days("sun,mon"),
                         (0, 6))

    def test_parse_nomes_portugues(self):
        self.assertEqual(parse_training_days("seg,ter,qua,qui,sex"),
                         DEFAULT_TRAINING_DAYS)
        self.assertEqual(parse_training_days("seg,qua,sex"), (0, 2, 4))

    def test_parse_ausente_ou_invalido_usa_default(self):
        self.assertEqual(parse_training_days(""), DEFAULT_TRAINING_DAYS)
        self.assertEqual(parse_training_days(None), DEFAULT_TRAINING_DAYS)
        self.assertEqual(parse_training_days("seg,quarta,sex"),
                         DEFAULT_TRAINING_DAYS)

    def test_parse_deduplica_e_ordena(self):
        self.assertEqual(parse_training_days("fri,mon,fri"), (0, 4))

    def test_agenda_custom_so_treina_nos_dias_configurados(self):
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14),  # segunda
                          training_days=(0, 2, 4))  # seg, qua, sex
        days = [date.fromisoformat(w["day"]) for w in plan]
        self.assertEqual(len(days), 6)  # 2 semanas x 3 dias
        self.assertTrue(all(d.weekday() in (0, 2, 4) for d in days))

    def test_agenda_com_fim_de_semana_incluido(self):
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14),  # segunda
                          training_days=(0, 6))  # seg e domingo
        days = [date.fromisoformat(w["day"]) for w in plan]
        self.assertTrue(all(d.weekday() in (0, 6) for d in days))
        self.assertEqual(len(days), 4)  # 2 segundas + 2 domingos

    def test_foco_usa_posicao_da_agenda_nao_dia_da_semana(self):
        weekly = weekly_template(0)  # [Z2, SS, Z2, SS, VO2]
        plan = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14),  # segunda
                          training_days=(0, 2, 4))
        # seg=pos0->Z2, qua=pos1->SS, sex=pos2->Z2 (agenda de 3 dias)
        by_day = {w["day"]: w["focus"] for w in plan}
        self.assertEqual(by_day["2026-09-14"], weekly[0])
        self.assertEqual(by_day["2026-09-16"], weekly[1])
        self.assertEqual(by_day["2026-09-18"], weekly[2])

    def test_next_training_day_respeita_agenda(self):
        self.assertEqual(_next_training_day("2026-09-25", (0, 2, 4)),
                         "2026-09-28")  # sex -> seg (fim de semana fora)
        self.assertEqual(_next_training_day("2026-09-23", (0, 2, 4)),
                         "2026-09-25")  # qua -> sex
        self.assertEqual(_next_training_day("2026-09-25",
                                            DEFAULT_TRAINING_DAYS),
                         "2026-09-28")

    def test_build_prorroga_treino_de_hoje_fim_de_semana(self):
        existing = [{"day": "2026-09-13", "focus": "zone2",
                     "planned_duration": 2400,
                     "name": "2026-09-13 - Treino de Zona 2",
                     "params": {"on_sec": 1200}, "tss": 14.0,
                     "external_id": "hermes-plan-2026-09-13"}]
        plan = build_plan([], 0, ftp=182, days=5, existing=existing,
                          start=date(2026, 9, 28),
                          training_days=(0, 6))  # domingo treina
        days = [w["day"] for w in plan]
        # dia nao treinado nao entra nem quando estava no plano anterior
        self.assertNotIn("2026-09-13", days)


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

    def test_duas_perdas_nao_reduzem_o_mesmo_limiar_duas_vezes(self):
        from src.plan import _reduce_next_hard
        from src.coach import WorkoutParams
        base = WorkoutParams(focus=FOCUS_THRESHOLD, on_sec=480, on_power=0.98)
        params = dict(base.__dict__)
        plan = [
            {"day": "2026-09-23", "focus": FOCUS_THRESHOLD,
             "planned_duration": 2400, "name": "2026-09-23 - Treino de Limiar FTP",
             "params": params, "tss": 30.0,
             "external_id": "hermes-plan-2026-09-23"},
        ]
        reduced_ids = set()
        p1 = _reduce_next_hard(plan, "2026-09-21", 182, reduced_ids)
        p2 = _reduce_next_hard(p1, "2026-09-22", 182, reduced_ids)
        self.assertEqual(p2[0]["params"]["on_power"],
                         round(0.98 * 0.95, 3),
                         "o mesmo Limiar deve ser reduzido uma unica vez")

    def test_extra_pesado_insere_recuperacao_no_proximo_dia(self):
        today = date.today()
        plan = build_plan([], 0, ftp=182, days=10,
                          start=today)
        prev_names = [w["name"] for w in plan]
        anchor = (today - timedelta(days=2)).isoformat()
        events = [{"external_id": None, "paired_activity_id": "999",
                   "start_date_local": f"{anchor}T10:00:00",
                   "icu_training_load": 100.0}]
        plan2, missed = reconcile(plan, events, ftp=182)
        self.assertFalse(missed)
        nomes = [w["name"] for w in plan2]
        self.assertTrue(any("Recuperacao" in n for n in nomes),
                        "treino cheio fora do plano deveria gerar recuperacao")
        rec = next(w for w in plan2 if "Recuperacao" in w["name"])
        self.assertIn(rec["day"], [w["day"] for w in plan])

    def test_extra_leve_nao_mexe_no_plano(self):
        today = date.today()
        plan = build_plan([], 0, ftp=182, days=5, start=today)
        anchor = (today - timedelta(days=1)).isoformat()
        events = [{"external_id": None, "paired_activity_id": "123",
                   "start_date_local": f"{anchor}T10:00:00",
                   "icu_training_load": 15.0}]
        plan2, missed = reconcile(plan, events, ftp=182)
        self.assertFalse(missed)
        self.assertEqual(plan, plan2)

    def test_treino_planejado_e_feito_nao_conta_como_extra(self):
        today = date.today()
        plan = build_plan([], 0, ftp=182, days=5, start=today)
        anchor = (today - timedelta(days=3)).isoformat()
        events = [{"external_id": "hermes-plan-sabado",
                   "paired_activity_id": "999",
                   "start_date_local": f"{anchor}T10:00:00",
                   "icu_training_load": 100.0}]
        plan2, missed = reconcile(plan, events, ftp=182)
        self.assertFalse(missed)
        self.assertEqual(plan, plan2)

    def test_extra_nao_empilha_com_recuperacao_ja_programada(self):
        today = date.today()
        plan = build_plan([], 0, ftp=182, days=5, start=today)
        anchor = (today - timedelta(days=4)).isoformat()
        events = [{"external_id": None, "paired_activity_id": "999",
                   "start_date_local": f"{anchor}T10:00:00",
                   "icu_training_load": 100.0}]
        plan_a, _ = reconcile(plan, events, ftp=182)
        plan_b, _ = reconcile(plan_a, events, ftp=182)
        ocorrencias = [w for w in plan_b if "Recuperacao" in w["name"]]
        self.assertEqual(len(ocorrencias), 1,
                         "reconcile repetido nao pode empilhar recuperacoes")

    def test_extra_fora_da_janela_de_7_dias_ignorado(self):
        today = date.today()
        plan = build_plan([], 0, ftp=182, days=5, start=today)
        old = (today - timedelta(days=30)).isoformat()
        events = [{"external_id": None, "paired_activity_id": "999",
                   "start_date_local": f"{old}T10:00:00",
                   "icu_training_load": 100.0}]
        from src.plan import _adjust_for_extra_workouts, _done_and_extra
        done, extras = _done_and_extra(events)
        plan2 = _adjust_for_extra_workouts(plan, extras, ftp=182)
        self.assertEqual(plan, plan2)


class EventPayloadTest(unittest.TestCase):
    def test_formato_de_evento(self):
        plan = build_plan([], 2, ftp=182, days=1,
                          start=date(2026, 9, 28))
        payload = event_payload(plan[0], ftp=182)
        self.assertEqual(payload["category"], "WORKOUT")
        self.assertEqual(payload["target"], "POWER")
        self.assertEqual(payload["external_id"], "hermes-plan-2026-09-28")
        self.assertIn("Agora voce vai entrar em", payload["description"])
        self.assertRegex(payload["description"], r"- .* \d+m \d+%")

    def test_texto_descricao_nativo(self):
        plan = build_plan([], 2, ftp=182, days=1,
                          start=date(2026, 9, 28))
        lines = workout_text(plan[0]).splitlines()
        self.assertEqual(lines[0], plan[0]["name"])
        reps = plan[0]["params"]["repeats"]
        ons = [l for l in lines if l.startswith("- Agora voce vai entrar em")]
        self.assertEqual(len(ons), reps,
                         "cada repeticao vira um passo com mensagem propria")
        self.assertTrue(any("Aquecimento" in l for l in lines))
        self.assertTrue(any("Desaquecimento" in l for l in lines))

    def test_intervalos_achatados_sem_marcador_nx(self):
        plan = build_plan([], 2, ftp=182, days=1,
                          start=date(2026, 9, 28))
        lines = workout_text(plan[0]).splitlines()
        self.assertFalse(any(l.strip() == "3x" for l in lines),
                         "sem grupo Nx: passos devem ser individuais")
        esperado = 1 + plan[0]["params"]["repeats"] * 2 + 1
        self.assertEqual(len([l for l in lines if l.startswith("- ")]), esperado)

    def test_mensagem_explicativa_sem_porcento_no_texto(self):
        """O parser do Intervals trunca o cue no primeiro '%' ou no primeiro
        padrao de duracao abreviado ('6m'/'30s'/'1h'): o texto explicativo
        deve usar 'por cento' e 'minutos' por extenso; so o target usa %."""
        import re as _re
        plan = build_plan([], 2, ftp=182, days=1,
                          start=date(2026, 9, 28))
        lines = workout_text(plan[0]).splitlines()
        for l in lines:
            if not l.startswith("- "):
                continue
            cue = " ".join(l[2:].split(" ")[:-2])  # remove duracao+target final
            self.assertNotIn("%", cue,
                             f"cue nao pode conter %: {cue!r}")
            self.assertIsNone(_re.search(r"\d+[hms]", cue),
                              f"cue nao pode ter duracao abreviada: {cue!r}")

    def test_descricao_em_ingles(self):
        plan = build_plan([], 2, ftp=182, days=1,
                          start=date(2026, 9, 28))
        desc = workout_text(plan[0], lang="en")
        self.assertIn("Now you'll ride", desc)
        self.assertIn("percent of your FTP", desc)
        self.assertNotIn("Agora voce vai entrar", desc)

    def test_progressao_do_volume(self):
        plan = build_plan([], 2, ftp=182, days=5,
                          start=date(2026, 9, 21))  # semana cheia
        sweet = [w for w in plan if w["focus"] == FOCUS_SWEETSPOT]
        self.assertGreaterEqual(len(sweet), 2)
        prev = {"params": {**sweet[0]["params"], "on_sec": 440}}  # 3x440 vs 3x480 = -2min
        desc = workout_text(sweet[1], prev=prev)
        self.assertIn("2 minutos a mais", desc)
        prev = {"params": {**sweet[0]["params"], "on_sec": 520}}  # 3x520 vs 3x480 = +2min
        desc = workout_text(sweet[1], prev=prev)
        self.assertIn("2 minutos a menos", desc)
        desc = workout_text(sweet[1], prev=sweet[0])
        self.assertIn("Mesma carga", desc)
        desc = workout_text(sweet[1])
        self.assertNotIn("ultimo treino", desc)

    def test_zone2_um_bloco_continuo(self):
        plan = build_plan([], -20, ftp=182, days=1,
                          start=date(2026, 9, 28))  # zona 2 com tsb baixo
        desc = workout_text(plan[0])
        self.assertIn("bloco continuo", desc)
        self.assertEqual(plan[0]["params"]["repeats"], 1)
        self.assertEqual(desc.count("Agora voce vai entrar em"), 1)

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