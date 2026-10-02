import unittest
from contextlib import contextmanager
from datetime import date, timedelta
from unittest import mock

import src.plan

from src.plan import (build_plan, event_payload, reconcile, templates,
                       weekly_template, phase_weekly_template, training_plan_state,
                       workout_text, orphan_external_ids,
                      manual_duplicate_ids,
                      parse_training_days, _next_training_day,
                      _reduce_next_hard, parse_fthr, hr_target_bpm,
                      weekly_budget, rpe_for_focus, adherence_report, FOCUS_VO2,
                      avg_load, DEFAULT_TRAINING_DAYS,
                      REST, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_ZONE2,
                      ABSORB_FOCUSES, ABSORB_SKIP_FOCUSES, _absorbable_tss,
                      _is_active_recovery,
                      _tsb_race_verdict)
from src.coach import (WorkoutParams, estimate_tss, zone_floor, zone_ceiling,
                       zone_band, focus_zone, ZONE_BANDS, FOCUS_ZONE,
                       ZONE_SWEETSPOT, FOCUS_ZONE1_RECOVERY,
                       FOCUS_ZONE2_ENDURANCE, FOCUS_ZONE3_TEMPO,
                       FOCUS_ZONE4_LIMIAR, FOCUS_ZONE5_VO2MAX,
                       FOCUS_ZONE6_ANAEROBICA, FOCUS_ENDURANCE)


def _Data(fixa):
    """`date` com `today()` fixado, para cenários que não seguem o calendário.

    `src.plan` importa `date` por nome, então o patch substitui o atributo do
    módulo — e precisa cobrir build e reconcile juntos.
    """
    return type("DataFixa", (date,),
                {"today": classmethod(lambda cls: fixa)})


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
        state = training_plan_state(None, None, date(2026, 9, 14), 200, 200, 0)
        weekly = phase_weekly_template(state)
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
    """Regras de absorvência de falta, com calendário congelado.

    Estes testes montam o cenário a partir de `date.today()`, então sem
    congelar a data a forma do plano muda com o dia da semana e a premissa
    "a falta foi absorvível" passa a depender do calendário. Já aconteceu:
    em 02/10/2026 (sexta) o último dia de treino passado passou a ser Limiar,
    que por regra **não** é absorvível, e o teste falhou por premissa — não por
    regressão. `DATA_FIXA` e a escolha explícita da falta absorvível existem
    para que a data não possa mais decidir o resultado.
    """

    DATA_FIXA = date(2026, 10, 1)  # quinta-feira: o cenário original

    @contextmanager
    def _cenario(self, foco_da_falta):
        """Cenário de falta única, com a data congelada durante todo o uso.

        O patch precisa cobrir **build e reconcile**: os dois leem
        `date.today()`, e um plano montado sob uma data e reconciliado sob
        outra produz faltas fantasma. Por isso o helper é context manager e
        entrega o cenário pronto, para o `reconcile` rodar dentro dele.

        O dia perdido é escolhido **pelo foco**, não pela posição: é a única
        forma de a premissa do teste não depender de qual dia da semana o
        calendário caiu.
        """
        with mock.patch.object(src.plan, "date", _Data(self.DATA_FIXA)):
            hist = [{"external_id": f"hist{i}",
                     "paired_activity_id": f"h{i}",
                     "start_date_local": (self.DATA_FIXA - timedelta(days=40 - i)
                                          ).isoformat() + "T07:00:00",
                     "icu_training_load": 45.0} for i in range(15)]
            plano = build_plan(hist, 2, ftp=182, days=12,
                               start=self.DATA_FIXA - timedelta(days=7))
            passados = [w for w in plano
                        if w["day"] < self.DATA_FIXA.isoformat()]
            if foco_da_falta is None:
                candidatos = [w for w in passados if _absorbable_tss([w]) == 0]
            else:
                candidatos = [w for w in passados
                              if w["focus"] == foco_da_falta]
            self.assertTrue(candidatos,
                            f"o cenário precisa de um dia {foco_da_falta!r} "
                            f"entre {[w['focus'] for w in passados]}")
            perdido = candidatos[-1]
            # A premissa é explícita aqui, e não implícita no calendário: o dia
            # escolhido é absorvível ou não, conforme o teste pede.
            self.assertEqual(_absorbable_tss([perdido]) > 0,
                             foco_da_falta is not None)
            feito_ids = {w["external_id"] for w in passados
                         if w["external_id"] != perdido["external_id"]}
            events = hist + [{"external_id": w["external_id"],
                              "paired_activity_id": f"i{i}",
                              "start_date_local": w["day"] + "T07:00:00",
                              "icu_training_load": w["tss"]}
                             for i, w in enumerate(
                                 [w for w in passados
                                  if w["external_id"] in feito_ids])]
            budget = weekly_budget(avg_load(events))
            antes = {w["external_id"]: w["tss"] for w in plano}
            yield plano, events, budget, antes

    def test_treino_perdido_de_zona_forte_nao_e_absorvido(self):
        """LIMIAR/VO2 perdidos não se substituem com mais volume.

        Este é o guardrail que impede a redistribuição: um treino de alta
        intensidade não é "reposto" com volume de base, porque o estímulo
        adaptativo não é substituível. A falta fica registrada e o build
        seguinte reprioriza conforme o TSB real.
        """
        with self._cenario(None) as (plano, events, _budget, _antes):
            _plano, missed, info = reconcile(plano, events, ftp=182)
        self.assertEqual(len(missed), 1)
        self.assertEqual(info["missed_tss"],
                         sum(float(w["tss"]) for w in missed))
        self.assertEqual(info["absorbable_tss"], 0.0)
        self.assertEqual(info["absorbed_tss"], 0.0)
        self.assertIn(missed[0]["focus"], ABSORB_SKIP_FOCUSES)

    def test_treino_perdido_e_absorvido_pelo_orcamento_nao_vira_recuperacao(self):
        # REGRA (Fase 2): treino perdido NAO insere "Recuperacao" e NAO reduz
        # -5% o proximo Limiar. A carga e redistribuida nos treinos Z2/Sweet
        # Spot posteriores que tem folga dentro do teto semanal (weekly_budget).
        # O plano e construido com os MESMOS eventos que o reconcile vera, para
        # que build e reconcile derivem o mesmo teto (avg_load coerente).
        with self._cenario(FOCUS_SWEETSPOT) as (plano, events, budget, antes):
            # `reconcile` devolve plano novo: a absorvência acontece numa copia,
            # entao a comparacao de carga precisa usar o plano devolvido.
            ajustado, missed, info = reconcile(plano, events, ftp=182)
            ganhos = [w for w in ajustado
                      if w["external_id"] in antes
                      and w["tss"] > antes[w["external_id"]]]
            janelas = {w["day"]: sum(
                x["tss"] for x in ajustado
                if 0 <= (date.fromisoformat(w["day"])
                         - date.fromisoformat(x["day"])).days < 7)
                for w in ajustado}
            plano = ajustado
        self.assertEqual(len(missed), 1)
        nomes = [w["name"] for w in plano]
        self.assertFalse(any("Recuperacao (plano ajustado)" in n for n in nomes),
                         "treino perdido nao deve virar recuperacao")
        self.assertEqual(info["missed_tss"],
                         sum(float(w["tss"]) for w in missed))
        self.assertGreater(info["absorbed_tss"], 0,
                           "a falta deveria ser redistribuida no orcamento")
        # algum treino ganhou carga (a falta foi redistribuida)
        self.assertTrue(ganhos, "nenhum treino absorveu a carga perdida")
        # ...mas nunca estourando o teto semanal
        for dia, janela in janelas.items():
            self.assertLessEqual(janela, budget + 1,
                                 f"absorcao estourou o teto em {dia}")

    def test_active_recovery_perdido_nao_e_compensado(self):
        # Active recovery (Z2 ~0.60) tem por PROPOSITO nao gerar carga.
        # Perder e praticamente sem custo fisiologico, logo nao se compensa
        # com mais volume: hacerlo contradiria o objetivo do proprio treino
        # (Seiler, Periodization Theory 3a ed., secao sobre sessoes perdidas).
        from src.plan import _is_active_recovery, _absorbable_tss
        rec = {"focus": "zone2", "tss": 14.0,
               "params": {"on_sec": 1200, "on_power": 0.60}}
        base = {"focus": "zone2", "tss": 24.0,
                "params": {"on_sec": 1800, "on_power": 0.70}}
        self.assertTrue(_is_active_recovery(rec))
        self.assertFalse(_is_active_recovery(base))
        self.assertEqual(_absorbable_tss([rec]), 0.0,
                         "active recovery perdido nao e absorvivel")
        self.assertEqual(_absorbable_tss([base]), 24.0,
                         "Z2 base e absorvivel")

    def test_alta_intensidade_perdida_nao_e_substituida_por_volume_z2(self):
        # VO2max/Limiar perdidos NAO se compensam com mais Z2: a adaptacao
        # aerobica vem da intensidade acima do LT1 (Seiler), nao de volume de
        # base. A falta fica como "debito" e o build seguinte reprioriza a
        # intensidade conforme o TSB real.
        from src.plan import _absorbable_tss
        vo2 = {"focus": "vo2max", "tss": 41.0,
               "params": {"on_sec": 180, "on_power": 1.15}}
        thr = {"focus": "threshold", "tss": 48.0,
               "params": {"on_sec": 480, "on_power": 0.98}}
        self.assertEqual(_absorbable_tss([vo2]), 0.0)
        self.assertEqual(_absorbable_tss([thr]), 0.0)
        self.assertEqual(_absorbable_tss([vo2, thr]), 0.0)
        # ...enquanto uma sessao mista soma so a parte de base
        base = {"focus": "sweetspot", "tss": 37.0,
                "params": {"on_sec": 480, "on_power": 0.88}}
        self.assertEqual(_absorbable_tss([vo2, thr, base]), 37.0)

    def test_falta_grande_nao_estoura_teto_fica_para_o_tsb_absorver(self):
        # Quando a carga perdida NAO cabe na folga do teto, nao se faz
        # compensacao artificial: o plano fica (quase) intacto e a carga nao
        # feita sobe o TSB, que e o proprio mecanismo de autorregulacao
        # (reduz a semana seguinte no build). Em nenhuma hipotese o teto
        # semanal pode ser furado.
        plan = build_plan([], 2, ftp=182, days=12,
                          start=date.today() - timedelta(days=7))
        antes = {w["external_id"]: w["tss"] for w in plan}
        plan, missed, info = reconcile(plan, [], ftp=182)  # tudo perdido
        self.assertTrue(missed)
        budget = weekly_budget(40.0)
        for w in plan:
            day = date.fromisoformat(w["day"])
            janela = sum(x["tss"] for x in plan
                         if 0 <= (day - date.fromisoformat(x["day"])).days < 7)
            self.assertLessEqual(janela, budget + 1,
                                 f"teto furado em {w['day']}: {janela} > {budget}")
        self.assertLessEqual(info["absorbed_tss"], info["missed_tss"])

    def test_absorcao_respeita_teto_maximo_de_crescimento(self):
        # Cada treino cresce no maximo ABSORB_MAX_GAIN de on_sec por chamada
        # (evita inflar um unico treino e criar um pico apos a falta).
        from src.plan import ABSORB_MAX_GAIN
        plan = build_plan([], 2, ftp=182, days=12,
                          start=date.today() - timedelta(days=7))
        antes = {w["external_id"]: w["params"]["on_sec"] for w in plan}
        plan, missed, info = reconcile(plan, [], ftp=182)
        for w in plan:
            if w["external_id"] in antes and w["params"]["on_sec"] > antes[w["external_id"]]:
                self.assertLessEqual(w["params"]["on_sec"],
                                     int(antes[w["external_id"]] * ABSORB_MAX_GAIN) + 1)

    def test_treino_feito_nao_conta_como_perdido(self):
        plan = build_plan([], 2, ftp=182, days=2,
                          start=date(2026, 9, 28))
        events = [{"external_id": plan[0]["external_id"],
                   "paired_activity_id": "41234",
                   "start_date_local": "2026-09-28T07:00:00"}]
        plan, missed, info = reconcile(plan, events, ftp=182)
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

    def test_reconcile_mix_realista_eventos(self):
        """Golden-path do reconcile: treinos hermes passados feitos, um perdido,
        extra pesado na janela de 7d (carga >= cap) e extra leve. Recuperacao
        para o perdido + para o extra pesado; o plano nao muda de tamanho."""
        today = date.today()
        # Fixture PICADA de forma deterministic (independe do dia da semana):
        # - start=today-6 garante >= 2 dias de treino passados em qualquer dia;
        # - perdido = past[0] (o mais antigo) => a recuperacao dele cai no
        #   proximo dia de treino, mais cedo;
        # - extra pesado ancorado em today-2 => a recuperacao do extra cai num
        #   dia DIFERENTE (senao o reconcile deduplica 'recuperacao ja
        #   programada' e o cenario so passava em qui/sex/sab).
        start = today - timedelta(days=6)
        plan = build_plan([], 0, ftp=182, days=12, start=start)
        past = [w for w in plan if w["day"] < today.isoformat()]
        self.assertGreaterEqual(len(past), 2,
                                "fixture precisa de pelo menos 2 dias passados")
        missed_one = past[0]  # apenas 1 perdido
        done = [w for w in past if w["day"] != missed_one["day"]]
        events = [{"external_id": w["external_id"], "paired_activity_id": "555",
                   "start_date_local": f"{w['day']}T10:00:00",
                   "icu_training_load": 45.0}
                  for w in done]
        anchor = today - timedelta(days=2)
        events += [
            {"external_id": None, "paired_activity_id": "777",
             "start_date_local": f"{anchor.isoformat()}T10:00:00",
             "icu_training_load": 100.0},
            {"external_id": None, "paired_activity_id": "888",
             "start_date_local": f"{anchor.isoformat()}T12:00:00",
             "icu_training_load": 10.0},
        ]
        plan2, missed, info = reconcile(plan, events, ftp=182)
        self.assertEqual([m["external_id"] for m in missed],
                         [missed_one["external_id"]],
                         "exatamente um treino perdido")
        # REGRA (Fase 2): o treino perdido e ABSORVIDO pelo orcamento (nao vira
        # recuperacao). O EXTRA PESADO, esse sim, dispara a regra de extras e
        # ainda insere recuperacao. Logo: 1 recuperacao (do extra), nao 2.
        nomes = [w["name"] for w in plan2 if "Recuperacao (plano ajustado)" in w["name"]]
        self.assertEqual(len(nomes), 1,
                         "somente o extra pesado gera recuperacao; o perdido e absorvido")
        self.assertEqual(len(plan2), len(plan),
                         "reconcile nao muda o tamanho do plano (substitui dias)")

    def test_reconcile_sem_extra_pesado_mantem_plano(self):
        """Sem treino extra esforcado na janela (e tudo feito em dia passado),
        o plano permanece intacto."""
        today = date.today()
        start = today - timedelta(days=4)
        plan = build_plan([], 0, ftp=182, days=12, start=start)
        past = [w for w in plan if w["day"] < today.isoformat()]
        events = [{"external_id": w["external_id"], "paired_activity_id": "555",
                   "start_date_local": f"{w['day']}T10:00:00",
                   "icu_training_load": 45.0}
                  for w in past]
        anchor = today - timedelta(days=1)
        events += [{"external_id": None, "paired_activity_id": "999",
                    "start_date_local": f"{anchor.isoformat()}T10:00:00",
                    "icu_training_load": 8.0}]  # leve, bem abaixo do cap
        plan2, missed, info = reconcile(plan, events, ftp=182)
        self.assertFalse(missed, "tudo feito em dia passado -> nada perdido")
        self.assertEqual(plan2, plan,
                         "extra leve nao pode alterar o plano")
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
        plan2, missed, info = reconcile(plan, events, ftp=182)
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
        plan2, missed, info = reconcile(plan, events, ftp=182)
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
        plan2, missed, info = reconcile(plan, events, ftp=182)
        self.assertFalse(missed)
        self.assertEqual(plan, plan2)

    def test_extra_nao_empilha_com_recuperacao_ja_programada(self):
        today = date.today()
        plan = build_plan([], 0, ftp=182, days=5, start=today)
        anchor = (today - timedelta(days=4)).isoformat()
        events = [{"external_id": None, "paired_activity_id": "999",
                   "start_date_local": f"{anchor}T10:00:00",
                   "icu_training_load": 100.0}]
        plan_a, _, _ = reconcile(plan, events, ftp=182)
        plan_b, _, _ = reconcile(plan_a, events, ftp=182)
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


class ManualDuplicateTest(unittest.TestCase):
    """Duplicatas manuais (sem external_id) que repetem um dia do plano: nao
    sae apagadas por bulk-delete (so aceita external_id) e exigem delete por id."""

    def _plan(self):
        return [{"day": "2026-09-21", "external_id": "hermes-plan-2026-09-21"},
                {"day": "2026-09-22", "external_id": "hermes-plan-2026-09-22"}]

    def test_marca_manual_que_duplica_dia_do_plano(self):
        events = [
            {"id": 1, "external_id": None, "start_date_local": "2026-09-21T07:30:00"},
            {"id": 2, "external_id": None, "start_date_local": "2026-09-23T07:30:00"},
        ]
        self.assertEqual(manual_duplicate_ids(self._plan(), events), [1])

    def test_ignora_evento_hermes_ao_gerar_manuais(self):
        events = [
            {"id": 1, "external_id": "hermes-plan-2026-09-21",
             "start_date_local": "2026-09-21T07:30:00"},
        ]
        self.assertEqual(manual_duplicate_ids(self._plan(), events), [])

    def test_respeita_janela_start(self):
        events = [
            {"id": 1, "external_id": None, "start_date_local": "2026-09-21T07:30:00"},
        ]
        # dia 21 fica fora da janela (>= start=22) -> nao e duplicata
        self.assertEqual(
            manual_duplicate_ids(self._plan(), events, start="2026-09-22"), [])


class FthrTest(unittest.TestCase):
    """FTHR (#3): frequencia cardiaca no limiar para prescricao sem medidor
    de potencia (modo FC, %FTHR + RPE)."""

    def test_parse_valido(self):
        self.assertEqual(parse_fthr("182"), 182)
        self.assertEqual(parse_fthr(" 165 "), 165)

    def test_parse_ausente_ou_invalido(self):
        self.assertIsNone(parse_fthr(None))
        self.assertIsNone(parse_fthr(""))
        self.assertIsNone(parse_fthr("abc"))
        self.assertIsNone(parse_fthr("20"))    # fora do intervalo humano
        self.assertIsNone(parse_fthr("300"))

    def test_alvo_em_bpm_por_foco(self):
        self.assertEqual(hr_target_bpm(FOCUS_ZONE2, 182), round(182 * 0.75))
        self.assertEqual(hr_target_bpm(FOCUS_SWEETSPOT, 182), round(182 * 0.88))
        self.assertEqual(hr_target_bpm(FOCUS_THRESHOLD, 182), round(182 * 0.98))
        self.assertEqual(hr_target_bpm(FOCUS_VO2, 182), round(182 * 1.05))

    def test_rpe_por_foco(self):
        self.assertEqual(rpe_for_focus(FOCUS_ZONE2), "3-4")
        self.assertEqual(rpe_for_focus(FOCUS_THRESHOLD), "7-8")
        self.assertEqual(rpe_for_focus("foco-desconhecido"), "5-6")


class HeartRateModeTest(unittest.TestCase):
    """Modo FC (#3): build --no-power carimba hr_mode, o texto usa %FTHR + RPE
    e o evento vai com target HR (enum do Intervals; nao HEART_RATE)."""

    def _fc_plan(self, fthr=182, days=1, start=None):
        start = start or date(2026, 9, 28)  # segunda
        return build_plan([], 2, ftp=182, days=days, start=start,
                          hr_mode=True)

    def test_build_carimba_hr_mode(self):
        plan = self._fc_plan(days=3)
        self.assertTrue(all(w.get("hr_mode") for w in plan),
                        "todos os workouts devem carregar hr_mode")

    def test_sem_hr_mode_nao_carimba(self):
        plan = build_plan([], 2, ftp=182, days=3,
                          start=date(2026, 9, 28))
        self.assertTrue(all("hr_mode" not in w for w in plan))

    def test_texto_fc_usa_fthr_e_rpe_sem_porcento_no_cue(self):
        import re as _re
        plan = self._fc_plan()
        text = "\n".join(workout_text(plan[0], fthr=182).splitlines())
        self.assertIn("FTHR", text)
        self.assertIn("RPE", text)
        self.assertNotIn("FTP", text.replace("FTHR", ""))
        for l in text.splitlines():
            if not l.startswith("- "):
                continue
            cue = " ".join(l[2:].split(" ")[:-2])
            self.assertNotIn("%", cue, f"cue nao pode conter %: {cue!r}")
            self.assertIsNone(_re.search(r"\d+[hms]", cue),
                              f"cue nao pode ter duracao abreviada: {cue!r}")

    def test_evento_fc_vai_com_target_hr(self):
        plan = self._fc_plan()
        payload = event_payload(plan[0], ftp=182, fthr=182)
        self.assertEqual(payload["target"], "HR")
        self.assertIn("FTHR", payload["description"])
        self.assertIn("RPE", payload["description"])

    def test_evento_sem_fthr_continua_power(self):
        plan = self._fc_plan()
        payload = event_payload(plan[0], ftp=182)
        self.assertEqual(payload["target"], "POWER")
        self.assertNotIn("FTHR", payload["description"])

    def test_reconcile_preserva_hr_mode_ao_reescrever(self):
        today = date.today()
        plan = self._fc_plan(days=6, start=today - timedelta(days=4))
        # todos os dias passados: treino perdido -> recuperacao inserida
        plan, missed, info = reconcile(plan, [], ftp=182)
        self.assertTrue(missed)
        self.assertTrue(all(w.get("hr_mode") for w in plan),
                        "recuperacao inserida deve herdar o modo FC")

    def test_texto_em_ingles_fc(self):
        plan = self._fc_plan()
        desc = workout_text(plan[0], fthr=182, lang="en")
        self.assertIn("HR threshold", desc)
        self.assertIn("RPE", desc)
        self.assertNotIn("Agora voce vai entrar", desc)


class AdherenceReportTest(unittest.TestCase):
    TODAY = date(2026, 9, 24)

    def _plan(self, done_days, missed_days, pending_days):
        entries = []
        for day in done_days + missed_days:
            entries.append({"day": day, "name": f"{day} - Treino",
                            "external_id": f"hermes-plan-{day}"})
        for day in pending_days:
            entries.append({"day": day, "name": f"{day} - Treino",
                            "external_id": f"hermes-plan-{day}"})
        return entries

    def _events(self, done_days):
        return [{"external_id": f"hermes-plan-{day}",
                 "paired_activity_id": "555",
                 "start_date_local": f"{day}T10:00:00"}
                for day in done_days]

    def test_tudo_em_dia_passado_classifica(self):
        plan = self._plan(["2026-09-22", "2026-09-23"], ["2026-09-21"], [])
        report = adherence_report(plan, self._events(["2026-09-22",
                                                      "2026-09-23"]),
                                  today=self.TODAY)
        self.assertEqual(report["summary"]["done"], 2)
        self.assertEqual(report["summary"]["missed"], 1)
        self.assertEqual(report["summary"]["pct"], 66.66666666666666)

    def test_dia_futuro_e_pendente(self):
        plan = self._plan([], [], ["2026-09-25"])
        report = adherence_report(plan, [], today=self.TODAY)
        self.assertEqual(report["summary"]["pending"], 1)
        self.assertEqual(report["summary"]["missed"], 0)
        self.assertIsNone(report["summary"]["pct"],
                          "sem treinos ocorridos -> percentual nulo")

    def test_treino_de_hoje_ainda_nao_conta_como_perdido(self):
        # today = 2026-09-24; treino de hoje sem conclusao -> pendente,
        # nunca perdido (so o que ja venceu - dia anterior - e perdido)
        plan = self._plan([], ["2026-09-23"], ["2026-09-24"])
        report = adherence_report(plan, [], today=self.TODAY)
        self.assertEqual(report["summary"]["pending"], 1)
        self.assertEqual(report["summary"]["missed"], 1)  # 23 (ontem) sim
        self.assertEqual(report["summary"]["pct"], 0.0)

    def test_feito_nao_conta_como_perdido(self):
        plan = self._plan(["2026-09-22"], ["2026-09-23"], [])
        report = adherence_report(plan, self._events(["2026-09-22", "x"]),
                                  today=self.TODAY)
        self.assertEqual(report["summary"]["done"], 1)
        self.assertEqual(report["summary"]["missed"], 1)

    def test_agrupa_por_semana_com_week_start(self):
        # 2026-09-21 e 2026-09-22 caem na mesma semana ISO (seg 21/09)
        plan = self._plan(["2026-09-21", "2026-09-22"], [], [])
        report = adherence_report(plan, self._events(["2026-09-21",
                                                      "2026-09-22"]),
                                  today=self.TODAY)
        self.assertEqual(len(report["weeks"]), 1)
        week = report["weeks"][0]
        self.assertEqual(week["week"], "2026-W39")
        self.assertEqual(week["week_start"], "2026-09-21")
        self.assertEqual(week["pct"], 100.0)

    def test_semanas_diferentes_ficam_separadas(self):
        # 2026-09-18 (W38) e 2026-09-23 (W39)
        plan = self._plan(["2026-09-18"], ["2026-09-23"], [])
        report = adherence_report(plan, self._events(["2026-09-18"]),
                                  today=self.TODAY)
        self.assertEqual(len(report["weeks"]), 2)
        self.assertEqual(report["weeks"][0]["week"], "2026-W38")
        self.assertEqual(report["weeks"][0]["pct"], 100.0)
        self.assertEqual(report["weeks"][1]["week"], "2026-W39")
        self.assertEqual(report["weeks"][1]["pct"], 0.0)

    def test_plano_vazio(self):
        report = adherence_report([], [], today=self.TODAY)
        self.assertEqual(report["weeks"], [])
        self.assertEqual(report["summary"]["pct"], None)


class RaceTaperTest(unittest.TestCase):
    """GOAL=race: taper faselatedo (Friel), evento da prova e veredito de TSB."""

    def test_taper_race_tem_fases(self):
        # segunda 2026-09-28 .. +12d (= ate 2026-10-09); prova 2026-10-08 (qui)
        start = date(2026, 9, 28)
        plan = build_plan([], 5, ftp=182, days=15, start=start,
                          goal="race", race_date="2026-10-08")
        by_day = {w["day"]: w for w in plan}
        # D-6 (2026-10-02, sex): unico ultimo estimulo de qualidade
        self.assertIn("Ultimo estimulo (pre-prova)",
                      by_day["2026-10-02"]["name"])
        n = sum(1 for w in plan if "Ultimo estimulo (pre-prova)" in w["name"])
        self.assertEqual(n, 1)
        # D-2/D-1 (2026-10-06/07): spin muito leve (<60% FTP)
        for d in ("2026-10-06", "2026-10-07"):
            self.assertTrue("Spin leve (pre-prova)" in by_day[d]["name"],
                            f"{d} deveria ser spin")
            self.assertLessEqual(by_day[d]["params"]["on_power"], 0.50)
        # D-3 (2026-10-05): recuperacao curta, sem intensidade
        self.assertTrue("Recuperacao (pre-prova)" in by_day["2026-10-05"]["name"])
        self.assertLessEqual(by_day["2026-10-05"]["params"]["on_power"], 0.60)
        # D+1 (2026-10-09, sex): recuperacao pos-prova
        self.assertIn("Recuperacao (pos-prova)",
                      by_day["2026-10-09"]["name"])
        # passa de TAPER_DAYS ou pos-prova: normal, sem marca de taper
        self.assertNotIn("pre-prova", by_day["2026-09-30"]["name"])
        self.assertNotIn("pre-prova", by_day["2026-10-12"]["name"])

    def test_prova_entra_mesmo_fora_da_agenda(self):
        # prova no sabado 2026-10-03 (fora seg-sex): evento garantido
        start = date(2026, 9, 28)
        plan = build_plan([], 0, ftp=182, days=8, start=start,
                          goal="race", race_date="2026-10-03")
        by_day = {w["day"]: w for w in plan}
        self.assertIn("Prova: dia de prova", by_day["2026-10-03"]["name"])
        self.assertEqual(by_day["2026-10-03"]["tss"], 0.0,
                         "prova e marcador: carga real entra pela API")
        # D+1 domingo: descanso natural, nao cria nada
        self.assertNotIn("2026-10-04", by_day)

    def test_sem_race_date_nao_muda_comportamento(self):
        start = date(2026, 9, 28)
        base = build_plan([], 5, ftp=182, days=7, start=start, goal="race")
        self.assertTrue(all("pre-prova" not in w["name"] for w in base))
        self.assertTrue(all("Prova" not in w["name"] for w in base))


class RecoveryBudgetTest(unittest.TestCase):
    """#19: `build` recebe os tetos semanais da rampa de retorno a forma
    (`src.recovery.ramp_schedule`) e orca o plano dentro deles.

    A rampa e um TETO: o plano nunca o fura alem do piso de TSS de um treino
    (cada workout tem duracao minima, entao a janela rolante pode ficar ~um
    treino acima do alvo). SLACK = folga de 2 dias de trabalho (~30 TSS)."""

    SLACK = 30.0

    def test_respeita_teto_de_cada_semana(self):
        ramp = [120.0, 300.0]
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14), recovery_ramp=ramp)
        by_week = {}
        for w in plan:
            day = date.fromisoformat(w["day"])
            wk = (day - date(2026, 9, 14)).days // 7
            by_week[wk] = by_week.get(wk, 0.0) + w["tss"]
        self.assertLessEqual(by_week[0], ramp[0] + self.SLACK,
                             f"semana 1 estourou: {by_week[0]:.1f}")
        self.assertLessEqual(by_week[1], ramp[1] + self.SLACK,
                             f"semana 2 estourou: {by_week[1]:.1f}")
        self.assertGreater(by_week[1], by_week[0],
                           "rampa crescente deveria permitir mais carga na 2a")

    def test_rampa_reduz_carga_abaixo_do_orcamento_padrao(self):
        # orcamento padrao (avg 40) = 266 TSS/sem; natural = 192; rampa 90 forca
        ramp = [90.0]
        plan = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14), recovery_ramp=ramp)
        janela = sum(w["tss"] for w in plan)
        self.assertLessEqual(janela, ramp[0] + self.SLACK,
                             f"rampa menor que orcamento deveria reduzir: {janela:.1f}")
        base = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14))
        self.assertLess(janela, sum(w["tss"] for w in base),
                        "com rampa o plano deveria carregar menos que o padrao")

    def test_rampa_curta_mantem_ultimo_teto(self):
        ramp = [100.0]
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14), recovery_ramp=ramp)
        by_week = {}
        for w in plan:
            day = date.fromisoformat(w["day"])
            wk = (day - date(2026, 9, 14)).days // 7
            by_week[wk] = by_week.get(wk, 0.0) + w["tss"]
        for wk, load in by_week.items():
            self.assertLessEqual(load, ramp[0] + self.SLACK,
                                 f"semana {wk} estourou o ultimo teto: {load:.1f}")
            self.assertGreater(load, 0.0, f"semana {wk} vazia?")


class RaceTsbVerdictTest(unittest.TestCase):
    def test_faixa_alvo(self):
        self.assertEqual(_tsb_race_verdict(-15), "cansado")
        self.assertEqual(_tsb_race_verdict(-10), "ok")
        self.assertEqual(_tsb_race_verdict(5), "ok")
        self.assertEqual(_tsb_race_verdict(20), "ok")
        self.assertEqual(_tsb_race_verdict(25), "acima")


class ZoneIntegrityTest(unittest.TestCase):
    """Invariante de zona (Tabela Z1-Z7; ver docs/EMBASAMENTO-CIENTIFICO.md
    secao 6, que aponta para o documento canonico no vault).

    REGRA: um treino NUNCA entrega menos de %FTP do que o piso da zona que ele
    declara. O `focus` e o nome podem nao mudar enquanto a potencia rebaixada
    entrega outro estímulo - foi exatamente o bug do `_fit_budget`, que
    descia `on_power` ate 0.55 fixo e produzia "Treino de Sweet Spot" com
    potencia de recuperacao (caso real: 2026-10-02, sweetspot @0.55).
    """

    def test_fit_budget_nunca_rebaixa_abaixo_do_piso_da_zona(self):
        from src.plan import _fit_budget
        from src.coach import estimate_tss
        for focus, on_sec, on_pow in [("zone2", 1800, 0.70),
                                      ("sweetspot", 480, 0.88),
                                      ("threshold", 480, 0.98),
                                      ("vo2max", 180, 1.15)]:
            piso = zone_floor(focus)
            self.assertIsNotNone(piso, f"{focus} sem faixa definida")
            params = WorkoutParams(focus=focus, repeats=3, on_sec=on_sec,
                                   off_sec=240, on_power=on_pow, off_power=0.55,
                                   cadence=90, cadence_rest=85)
            tss = estimate_tss(params, 250)
            # budget apertadissimo: forcaria rebaixar a intensidade
            out, _ = _fit_budget(params, tss, [(None, 200)], 210, 250)
            self.assertGreaterEqual(
                out.on_power, piso,
                f"{focus}: on_power {out.on_power} < piso da zona {piso}")
            self.assertEqual(out.focus, focus,
                             "o focus nao pode mudar ao cortar carga")

    def test_reducao_de_carga_preserva_o_nome_do_treino(self):
        # cortar volume (reps/duracao) mantem o nome coerente com a zona
        from src.plan import _fit_budget
        from src.coach import estimate_tss
        params = WorkoutParams(focus="sweetspot", repeats=3, on_sec=480,
                               off_sec=240, on_power=0.88, off_power=0.55,
                               cadence=90, cadence_rest=85)
        out, tss = _fit_budget(params, estimate_tss(params, 250),
                               [(None, 200)], 210, 250)
        self.assertGreaterEqual(out.on_power, zone_floor("sweetspot"))
        self.assertGreaterEqual(tss, 0.0)

    def test_templates_respeitam_a_faixa_da_zona(self):
        # os blocos-base nao podem nascer fora da banda da sua zona
        for focus, bloco in templates().items():
            piso = zone_floor(focus)
            if piso is None:
                continue
            topo = zone_ceiling(focus)
            pot = bloco["on_power"]
            self.assertTrue(
                piso <= pot <= topo,
                f"template {focus} @ {pot} fora da faixa [{piso}, {topo}]")

    def test_plano_gerado_respeita_a_faixa_de_cada_zona(self):
        # build_plan nao pode emitir treino abaixo do piso da zona declarada
        for tsb in (-20, 0, 10, 25):
            for ftp in (182, 250):
                plan = build_plan([], tsb, ftp=ftp, days=21,
                                  start=date(2026, 9, 14))
                for w in plan:
                    piso = zone_floor(w["focus"])
                    if piso is None:
                        continue
                    pot = w["params"]["on_power"]
                    self.assertGreaterEqual(
                        pot, piso,
                        f"{w['day']} {w['focus']} @ {pot} < piso {piso}")

    def test_zona_bands_espelham_a_tabela_do_documento(self):
        # ZONE_BANDS e a versao legivel da "Tabela Cientifica Z1-Z7" do
        # documento canonico no vault (docs/EMBASAMENTO-CIENTIFICO.md secao 6
        # aponta para ele). Se a tabela mudar, este teste falha.
        # ordem e identical a "Tabela Cientifica Z1-Z7" do documento
        esperado = {
            FOCUS_ZONE1_RECOVERY: (0.00, 0.55),    # Z1 Recuperacao  <55%
            FOCUS_ZONE2_ENDURANCE: (0.56, 0.75),   # Z2 Endurance  56-75%
            FOCUS_ZONE3_TEMPO: (0.76, 0.90),       # Z3 Tempo      76-90%
            ZONE_SWEETSPOT: (0.84, 0.97),          # Sweet Spot    84-97%
            FOCUS_ZONE4_LIMIAR: (0.91, 1.05),      # Z4 Limiar     91-105%
            FOCUS_ZONE5_VO2MAX: (1.06, 1.20),      # Z5 VO2max    106-120%
            FOCUS_ZONE6_ANAEROBICA: (1.21, 1.50),  # Z6 Anaerobica 121-150%
        }
        self.assertEqual(ZONE_BANDS, esperado)
        # Z7 e potencia maxima: nao cabe numa faixa de %FTP
        self.assertEqual([z for z in ZONE_BANDS if z.startswith("z7")], [])

    def test_focos_de_prescricao_mapeiam_para_a_zona_canonica(self):
        # 'zone2' e 'endurance' sao a MESMA zona do documento (Z2), nao zonas
        # distintas; 'sweetspot' e categoria de prescricao, nao numero de zona.
        self.assertEqual(focus_zone(FOCUS_ZONE2), FOCUS_ZONE2_ENDURANCE)
        self.assertEqual(focus_zone(FOCUS_ENDURANCE), FOCUS_ZONE2_ENDURANCE)
        self.assertEqual(focus_zone(FOCUS_SWEETSPOT), ZONE_SWEETSPOT)
        self.assertEqual(focus_zone(FOCUS_THRESHOLD), FOCUS_ZONE4_LIMIAR)
        self.assertEqual(focus_zone(FOCUS_VO2), FOCUS_ZONE5_VO2MAX)

    def test_valores_string_dos_focos_nao_mudaram(self):
        # INVARIANTE DE COMPATIBILIDADE: o valor string e persistido em
        # plan.json e publicado no Intervals.icu. Renomear um valor quebraria
        # planos salvos e o calendario -- por isso so as CONSTANTES mudaram.
        self.assertEqual(FOCUS_ZONE2_ENDURANCE, "zone2")
        self.assertEqual(FOCUS_ZONE4_LIMIAR, "threshold")
        self.assertEqual(FOCUS_ZONE5_VO2MAX, "vo2max")
        self.assertEqual(FOCUS_ZONE2, FOCUS_ZONE2_ENDURANCE)
        self.assertEqual(FOCUS_THRESHOLD, FOCUS_ZONE4_LIMIAR)
        self.assertEqual(FOCUS_VO2, FOCUS_ZONE5_VO2MAX)

    def test_z1_recuperacao_nao_e_zona_de_prescricao_do_codigo(self):
        # Z1 (<55%) tem faixa na tabela, mas nao existe foco prescrito: e uma
        # intencao de sessao executada DENTRO da banda Z2 (active recovery).
        self.assertIn(FOCUS_ZONE1_RECOVERY, ZONE_BANDS)
        self.assertNotIn(FOCUS_ZONE1_RECOVERY, FOCUS_ZONE)
        self.assertNotIn(FOCUS_ZONE1_RECOVERY, templates())

    def test_active_recovery_permanece_detectavel_apos_o_corte(self):
        # o corte nao pode transformar um treino de zona em active recovery
        # (que se define por on_power baixo) sem renomear
        from src.plan import _is_active_recovery
        plan = build_plan([], 0, ftp=250, days=14, start=date(2026, 9, 14))
        for w in plan:
            piso = zone_floor(w["focus"])
            if piso is None:
                continue
            if _is_active_recovery(w):
                self.assertLessEqual(w["params"]["on_power"], 0.65,
                                     "active recovery acima do limiar")
                # so Z2 pode ser active recovery
                self.assertEqual(w["focus"], FOCUS_ZONE2)


if __name__ == "__main__":
    unittest.main()
