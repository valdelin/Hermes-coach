import unittest
from datetime import date

from src.plan import (build_plan, parse_long_day, parse_weekly_hours,
                       parse_min_regular_duration_minutes,
                       parse_active_recovery_days,
                       _place_long_day, _volume_scale, _scale_duration,
                       _enforce_min_regular_duration, estimate_tss,
                       WorkoutParams, FOCUS_ZONE2, FOCUS_SWEETSPOT,
                       FOCUS_THRESHOLD, FOCUS_VO2, ENDURANCE,
                       DEFAULT_TRAINING_DAYS, VOLUME_SCALE_MIN, VOLUME_SCALE_MAX,
                       MIN_REGULAR_DURATION_SEC, weekly_budget)


class ParseWeeklyHoursTest(unittest.TestCase):
    def test_ausente_ou_vazio_retorna_none(self):
        self.assertIsNone(parse_weekly_hours(""))
        self.assertIsNone(parse_weekly_hours(None))

    def test_numero_puro(self):
        self.assertEqual(parse_weekly_hours("5"), 5.0)
        self.assertEqual(parse_weekly_hours("5.5"), 5.5)

    def test_sufixo_h_e_min(self):
        self.assertEqual(parse_weekly_hours("5h"), 5.0)
        self.assertEqual(parse_weekly_hours("5H"), 5.0)
        self.assertEqual(parse_weekly_hours("300min"), 5.0)

    def test_invalido_ou_fora_da_faixa(self):
        self.assertIsNone(parse_weekly_hours("muitas"))
        self.assertIsNone(parse_weekly_hours("0"))
        self.assertIsNone(parse_weekly_hours("-3"))
        self.assertIsNone(parse_weekly_hours("200"))


class ParseMinimumRegularDurationTest(unittest.TestCase):
    def test_ausente_valido_e_invalido(self):
        self.assertIsNone(parse_min_regular_duration_minutes(""))
        self.assertEqual(parse_min_regular_duration_minutes("60"), 3600)
        self.assertIsNone(parse_min_regular_duration_minutes("60.5"))
        self.assertIsNone(parse_min_regular_duration_minutes("0"))


class ActiveRecoveryDaysTest(unittest.TestCase):
    def test_parser_exige_subconjunto_da_agenda(self):
        self.assertEqual(parse_active_recovery_days("ter,qui", (0, 1, 2, 3, 4)),
                         (1, 3))
        with self.assertRaisesRegex(ValueError, "contido"):
            parse_active_recovery_days("ter", (0, 2, 4))

    def test_dias_configurados_geram_z2_e_dias_normais_preservam_template(self):
        plan = build_plan([], 5, ftp=182, days=7, start=date(2026, 9, 14),
                          training_days=(0, 1, 2, 3, 4),
                          active_recovery_days=(1, 3))
        by_weekday = {date.fromisoformat(w["day"]).weekday(): w for w in plan}
        for weekday in (1, 3):
            workout = by_weekday[weekday]
            self.assertEqual(workout["focus"], FOCUS_ZONE2)
            self.assertEqual(workout["params"]["on_power"], 0.60)
            self.assertEqual(workout["planned_duration"], 3600)
            self.assertIn("Recuperacao ativa (Z2)", workout["name"])
        self.assertNotIn("Recuperacao ativa", by_weekday[0]["name"])


class ParseLongDayTest(unittest.TestCase):
    def test_dias_pt_e_en(self):
        self.assertEqual(parse_long_day("dom"), 6)
        self.assertEqual(parse_long_day("SUN"), 6)
        self.assertEqual(parse_long_day("sab"), 5)
        self.assertEqual(parse_long_day("wed"), 2)

    def test_ausente_ou_invalido(self):
        self.assertIsNone(parse_long_day(""))
        self.assertIsNone(parse_long_day(None))
        self.assertIsNone(parse_long_day("feriado"))


class VolumeScaleTest(unittest.TestCase):
    def test_sem_weekly_hours_nao_escala(self):
        weekly = [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2,
                  FOCUS_SWEETSPOT, FOCUS_VO2]
        self.assertIsNone(_volume_scale(weekly, None, DEFAULT_TRAINING_DAYS))
        self.assertIsNone(_volume_scale(weekly, 0, DEFAULT_TRAINING_DAYS))

    def test_menos_horas_reduz_duracoes(self):
        base = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14))  # segunda
        scaled = build_plan([], 0, ftp=182, days=7,
                            start=date(2026, 9, 14), weekly_hours=2)
        for b, s in zip(base, scaled):
            self.assertLessEqual(s["params"]["on_sec"], b["params"]["on_sec"])

    def test_minimo_de_120s_mantido(self):
        plan = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14), weekly_hours=2)
        for w in plan:
            self.assertGreaterEqual(w["params"]["on_sec"], 120)

    def test_mais_horas_aumenta_a_carga_ate_o_teto(self):
        # Mais horas disponiveis aumenta a carga, mas nunca acima do teto
        # semanal (= cap diario x dias de treino). O scale pode elevar um
        # treino enquanto houver folga; quando o teto aperta, o _fit_budget
        # segura. Por isso a invariante e sobre o TOTAL da semana respectar
        # o teto, e nao "todo dia cresce".
        base = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14))
        scaled = build_plan([], 0, ftp=182, days=7,
                            start=date(2026, 9, 14), weekly_hours=8)
        budget = weekly_budget(40.0)  # fallback do avg_load sem eventos
        for b, s in zip(base, scaled):
            self.assertLessEqual(s["params"]["on_sec"], b["params"]["on_sec"] * 1.5)
        # carga total subiu face ao plano base...
        self.assertGreater(sum(w["tss"] for w in scaled),
                           sum(w["tss"] for w in base) - 1)
        # ...mas a semana rolante cabe no teto
        for i, w in enumerate(scaled):
            day = date.fromisoformat(w["day"])
            janela = sum(x["tss"] for x in scaled
                         if 0 <= (day - date.fromisoformat(x["day"])).days < 7)
            self.assertLessEqual(janela, budget + 1)

    def test_horas_acima_do_teto_sao_capadas_pelo_orcamento(self):
        # O teto semanal = cap diario x dias de treino da semana. Pedir mais
        # horas do que o teto comporta NAO pode estourar o orcamento: o
        # _fit_budget reduz a carga ate caber. Com weekly_hours alto demais, o
        # plano escala mas o teto segura (este era o comportamento antes da
        # correcao do teto, que inflava em 7/dias_de_treino).
        plan = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14), weekly_hours=12)
        budget = weekly_budget(40.0)  # fallback do avg_load sem eventos
        for i, w in enumerate(plan):
            day = date.fromisoformat(w["day"])
            janela = sum(x["tss"] for x in plan
                         if 0 <= (day - date.fromisoformat(x["day"])).days < 7)
            self.assertLessEqual(janela, budget + 1)

    def test_tss_acompanha_a_reducao(self):
        base = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14))
        scaled = build_plan([], 0, ftp=182, days=7,
                            start=date(2026, 9, 14), weekly_hours=2)
        self.assertLess(sum(w["tss"] for w in scaled),
                        sum(w["tss"] for w in base))

    def test_scale_duration_aplica_e_respeita_minimo(self):
        p = WorkoutParams(focus=FOCUS_ZONE2, on_sec=1800, repeats=1, off_sec=0)
        out = _scale_duration(p, 0.5)
        self.assertEqual(out.on_sec, 900)
        tiny = WorkoutParams(focus=FOCUS_VO2, on_sec=180, repeats=4, off_sec=180)
        self.assertEqual(_scale_duration(tiny, 0.5).on_sec, 120)
        self.assertIs(_scale_duration(p, None), p)
        self.assertIs(_scale_duration(p, 1.0), p)


class MinimumRegularDurationTest(unittest.TestCase):
    def test_build_aplica_minimo_somente_quando_configurado(self):
        events = [{"start_date_local": date.today().isoformat(),
                   "icu_training_load": 150, "paired_activity_id": 1}]
        base = build_plan(events, 5, ftp=182, days=1,
                          start=date(2026, 10, 12), training_days=(0,))
        configured = build_plan(
            events, 5, ftp=182, days=1, start=date(2026, 10, 12),
            training_days=(0,),
            min_regular_duration_sec=MIN_REGULAR_DURATION_SEC)
        self.assertLess(base[0]["planned_duration"], MIN_REGULAR_DURATION_SEC)
        self.assertEqual(configured[0]["planned_duration"],
                         MIN_REGULAR_DURATION_SEC)

    def test_com_folga_regular_chega_a_sessenta_minutos_sem_mudar_zona(self):
        params = WorkoutParams(focus=FOCUS_VO2, repeats=4, on_sec=180,
                               off_sec=180, on_power=1.15)
        tss = estimate_tss(params, 182)
        out, out_tss = _enforce_min_regular_duration(
            params, tss, [], budget=999, cap=999, ftp=182,
            min_duration_sec=MIN_REGULAR_DURATION_SEC,
            budget_or_readiness_protected=False)
        self.assertEqual(out.warmup_sec + out.repeats *
                         (out.on_sec + out.off_sec) + out.cooldown_sec,
                         MIN_REGULAR_DURATION_SEC)
        self.assertEqual(out.focus, FOCUS_VO2)
        self.assertEqual(out.on_power, 1.15)
        self.assertGreater(out_tss, tss)

    def test_teto_ou_prontidao_preserva_sessao_abaixo_do_minimo(self):
        params = WorkoutParams(focus=FOCUS_SWEETSPOT, repeats=3, on_sec=480,
                               off_sec=240, on_power=0.88)
        tss = estimate_tss(params, 182)
        by_budget, _ = _enforce_min_regular_duration(
            params, tss, [], budget=tss, cap=999, ftp=182,
            min_duration_sec=MIN_REGULAR_DURATION_SEC,
            budget_or_readiness_protected=False)
        by_readiness, _ = _enforce_min_regular_duration(
            params, tss, [], budget=999, cap=999, ftp=182,
            min_duration_sec=MIN_REGULAR_DURATION_SEC,
            budget_or_readiness_protected=True)
        self.assertEqual(by_budget, params)
        self.assertEqual(by_readiness, params)


class LongDayPlacementTest(unittest.TestCase):
    def test_gran_fondo_endurance_cai_no_dia_escolhido(self):
        # agenda seg/qua/dom; LONG_DAY=dom -> endurance no domingo
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14),  # segunda
                          training_days=(0, 2, 6), goal="gran-fondo",
                          long_day=6)
        sundays = [w for w in plan if date.fromisoformat(w["day"]).weekday() == 6]
        self.assertTrue(sundays)
        self.assertTrue(all(w["focus"] == ENDURANCE for w in sundays))

    def test_long_day_fora_da_agenda_usa_dia_proximo(self):
        # agenda seg-sex (sem domingo); LONG_DAY=dom -> endurance em seg
        # (dia mais proximo em distancia circular: 1 dia)
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14), goal="gran-fondo",
                          long_day=6)
        mondays = [w for w in plan if date.fromisoformat(w["day"]).weekday() == 0]
        self.assertTrue(mondays)
        self.assertTrue(all(w["focus"] == ENDURANCE for w in mondays))

    def test_sem_goal_mantem_agenda_e_long_day_move_o_foco_mais_longo(self):
        # agenda seg/qua/dom; LONG_DAY=dom -> Sweet Spot (foco mais longo do
        # template padrao tsb=0) cai no domingo
        plan = build_plan([], 0, ftp=182, days=14,
                          start=date(2026, 9, 14), training_days=(0, 2, 6),
                          long_day=6)
        sunday = [w for w in plan if date.fromisoformat(w["day"]).weekday() == 6]
        self.assertEqual(len(sunday), 2)  # 2 domingos na janela de 14 dias
        self.assertTrue(all(w["focus"] == FOCUS_SWEETSPOT for w in sunday))

    def test_sem_long_day_nada_muda(self):
        a = build_plan([], 0, ftp=182, days=7, start=date(2026, 9, 14))
        b = build_plan([], 0, ftp=182, days=7, start=date(2026, 9, 14),
                       long_day=None, weekly_hours=None)
        self.assertEqual(
            [w["focus"] for w in a],
            [w["focus"] for w in b])
        self.assertEqual(
            [w["params"]["on_sec"] for w in a],
            [w["params"]["on_sec"] for w in b])

    def test_place_long_day_sem_validacao(self):
        weekly = [FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_ZONE2,
                  FOCUS_SWEETSPOT, ENDURANCE]
        self.assertEqual(_place_long_day(weekly, None, (0, 1, 2)), weekly)
        self.assertEqual(_place_long_day(weekly, 6, ()), weekly)


class PreserveTodayWithAvailabilityTest(unittest.TestCase):
    """BUG #7: o caminho que preserva o treino de hoje nao pode descartar
    WEEKLY_HOURS/LONG_DAY nos dias futuros (plan.py:373-376)."""

    def _existing(self):
        today = date.today()
        if today.weekday() >= 5:
            self.skipTest("hoje e fim de semana")
        return [{"day": today.isoformat(), "focus": FOCUS_ZONE2,
                 "planned_duration": 2400,
                 "name": f"{today} - Recuperacao (plano ajustado)",
                 "params": {"on_sec": 1200}, "tss": 14.0,
                 "external_id": f"hermes-plan-{today}"}]

    def test_preserva_hoje_e_aplica_weekly_hours_nos_dias_futuros(self):
        existing = self._existing()
        base = build_plan([], -7, ftp=182, days=5, existing=existing)
        scaled = build_plan([], -7, ftp=182, days=5, existing=existing,
                            weekly_hours=2)
        # treino de hoje preservado nunca e escalado
        self.assertEqual(scaled[0]["params"]["on_sec"], 1200)
        # dias futuros DEVEM ser escalados (regressao: antes ficavam iguais)
        self.assertEqual(len(base), len(scaled))
        for b, s in zip(base[1:], scaled[1:]):
            self.assertLessEqual(s["params"]["on_sec"], b["params"]["on_sec"])
        self.assertLess(sum(w["tss"] for w in scaled[1:]),
                        sum(w["tss"] for w in base[1:]))

    def test_preserva_hoje_e_aplica_long_day_nos_dias_futuros(self):
        existing = self._existing()
        base = build_plan([], 0, ftp=182, days=14, goal="gran-fondo",
                          existing=existing)
        rotated = build_plan([], 0, ftp=182, days=14, goal="gran-fondo",
                             existing=existing, long_day=6)  # domingo
        self.assertEqual(rotated[0]["day"], existing[0]["day"])
        # agenda seg-sex + LONG_DAY=dom -> endurance cai na segunda
        # (dia de treino mais proximo). Antes da correcao, o LONG_DAY era
        # descartado e a segunda ficava com o foco do template (ZONE2).
        mondays = [w for w in rotated[1:]
                   if date.fromisoformat(w["day"]).weekday() == 0]
        self.assertTrue(mondays, "precisa haver segunda no horizonte")
        self.assertTrue(all(w["focus"] == ENDURANCE for w in mondays),
                        "LONG_DAY nao foi aplicado nos dias futuros")
        self.assertNotEqual([w["focus"] for w in base[1:]],
                            [w["focus"] for w in rotated[1:]])


if __name__ == "__main__":
    unittest.main()
