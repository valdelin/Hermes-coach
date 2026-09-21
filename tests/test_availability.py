import unittest
from datetime import date

from src.plan import (build_plan, parse_long_day, parse_weekly_hours,
                      _place_long_day, _volume_scale, _scale_duration,
                      WorkoutParams, FOCUS_ZONE2, FOCUS_SWEETSPOT,
                      FOCUS_THRESHOLD, FOCUS_VO2, ENDURANCE,
                      DEFAULT_TRAINING_DAYS, VOLUME_SCALE_MIN, VOLUME_SCALE_MAX)


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

    def test_mais_horas_aumenta_ate_o_teto(self):
        base = build_plan([], 0, ftp=182, days=7,
                          start=date(2026, 9, 14))
        scaled = build_plan([], 0, ftp=182, days=7,
                            start=date(2026, 9, 14), weekly_hours=12)
        for b, s in zip(base, scaled):
            self.assertLessEqual(s["params"]["on_sec"], b["params"]["on_sec"] * 1.5)
            self.assertGreaterEqual(s["params"]["on_sec"], b["params"]["on_sec"])

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


if __name__ == "__main__":
    unittest.main()