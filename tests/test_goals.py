import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from src.plan import (GOALS, GOAL_LABELS, GOAL_TEMPLATES, GOAL_BUDGET_SCALE,
                      TAPER_DAYS, build_plan, load_plan, load_plan_meta,
                      parse_goal, save_plan, weekly_template,
                      FOCUS_ZONE2, FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2,
                      ENDURANCE)


class ParseGoalTest(unittest.TestCase):
    def test_catalogo_tem_os_7_tipos(self):
        self.assertEqual(
            GOALS,
            ("back-to-fitness", "ftp-builder", "gran-fondo", "time-trial",
             "climbing", "active-off-season", "race"))

    def test_parse_valido(self):
        for g in GOALS:
            self.assertEqual(parse_goal(g), g)
            self.assertEqual(parse_goal(g.upper()), g)

    def test_parse_underscore_aceito(self):
        self.assertEqual(parse_goal("back_to_fitness"), "back-to-fitness")

    def test_parse_ausente_ou_invalido_retorna_none(self):
        self.assertIsNone(parse_goal(""))
        self.assertIsNone(parse_goal(None))
        self.assertIsNone(parse_goal("nao-existe"))
        self.assertIsNone(parse_goal("maratona"))

    def test_todos_os_tipos_tem_template_e_escala(self):
        for g in GOALS:
            self.assertIn(g, GOAL_TEMPLATES, f"{g} sem template")
            self.assertIn(g, GOAL_BUDGET_SCALE, f"{g} sem budget_scale")
            self.assertIn(g, GOAL_LABELS, f"{g} sem label")


class GoalWeeklyTemplateTest(unittest.TestCase):
    def test_sem_goal_mantem_template_atual(self):
        self.assertEqual(weekly_template(-20), weekly_template(-20, None))

    def test_active_off_season_nunca_usa_vo2(self):
        for tsb in (-30, -10, 0, 3, 10, 30):
            t = weekly_template(tsb, "active-off-season")
            self.assertNotIn(FOCUS_VO2, t, f"off-season com VO2 em tsb {tsb}")

    def test_back_to_fitness_comeca_leve(self):
        t = weekly_template(-20, "back-to-fitness")
        self.assertEqual(t, [FOCUS_ZONE2, FOCUS_ZONE2, FOCUS_ZONE2,
                             FOCUS_ZONE2, FOCUS_SWEETSPOT])

    def test_gran_fondo_tem_endurance_no_fim_de_semana(self):
        # posicao 4 da semana = dia longo (sexta na agenda-padrao)
        t = weekly_template(0, "gran-fondo")
        self.assertEqual(t[4], ENDURANCE)

    def test_time_trial_enfatiza_limiar_no_tsb_alto(self):
        t = weekly_template(10, "time-trial")
        self.assertGreater(t.count(FOCUS_THRESHOLD), 2)


class GoalBuildTest(unittest.TestCase):
    START = date(2026, 9, 14)  # segunda-feira (agenda seg-sex)

    def test_back_to_fitness_mais_leve_que_ftp_builder(self):
        b = build_plan([], 2, ftp=182, days=14, start=self.START,
                       goal="back-to-fitness")
        f = build_plan([], 2, ftp=182, days=14, start=self.START,
                       goal="ftp-builder")
        self.assertLess(sum(w["tss"] for w in b),
                        sum(w["tss"] for w in f),
                        "back-to-fitness deve ter carga total menor")

    def test_off_season_mais_leve_que_race(self):
        o = build_plan([], 2, ftp=182, days=14, start=self.START,
                       goal="active-off-season")
        r = build_plan([], 2, ftp=182, days=14, start=self.START,
                       goal="race", race_date="2026-12-01")
        self.assertLess(sum(w["tss"] for w in o),
                        sum(w["tss"] for w in r),
                        "off-season deve ser bem mais leve que race")

    def test_gran_fondo_inclui_dia_endurance(self):
        plan = build_plan([], 2, ftp=182, days=14, start=self.START,
                          goal="gran-fondo")
        focos = {w["focus"] for w in plan}
        self.assertIn(ENDURANCE, focos,
                      "gran-fondo deve ter treino de endurance longo")

    def test_goal_invalido_usa_comportamento_padrao(self):
        base = build_plan([], 2, ftp=182, days=7, start=self.START)
        same = build_plan([], 2, ftp=182, days=7, start=self.START,
                          goal=None)
        self.assertEqual(base, same)


class RaceTaperTest(unittest.TestCase):
    START = date(2026, 10, 5)  # segunda-feira

    def test_race_sem_race_date_mantem_template(self):
        plan = build_plan([], 5, ftp=182, days=7, start=self.START,
                          goal="race", race_date=None)
        self.assertTrue(plan)
        self.assertFalse(any("Taper" in w["name"] for w in plan),
                         "sem RACE_DATE nao ha tapper")

    def test_race_com_prova_proxima_aplica_tapper(self):
        race_date = "2026-10-16"  # sexta-feira, 2 semanas apos o start
        plan = build_plan([], 0, ftp=182, days=14, start=self.START,
                          goal="race", race_date=race_date)
        tapers = [w for w in plan if "Taper" in w["name"]]
        self.assertTrue(tapers, "deve haver dias de tapper antes da prova")
        for w in tapers:
            self.assertEqual(w["focus"], FOCUS_ZONE2,
                             "tapper e recuperacao leve (zona 2)")
            self.assertLess(w["tss"], 30,
                            f"tapper leve: TSS {w['tss']:.0f}")

    def test_tapper_so_dentro_da_janela(self):
        # prova longe: nenhum treino na janela de 14 dias vira tapper
        plan = build_plan([], 0, ftp=182, days=14, start=self.START,
                          goal="race", race_date="2027-01-15")
        self.assertFalse(any("Taper" in w["name"] for w in plan),
                         "prova longe nao pode gerar tapper agora")


class GoalVarietyTest(unittest.TestCase):
    def test_com_goal_estruturas_variam_por_foco(self):
        START = date(2026, 9, 14)
        plan = build_plan([], 5, ftp=182, days=14, start=START,
                          goal="ftp-builder")
        by_focus = {}
        for w in plan:
            by_focus.setdefault(w["focus"], []).append(w)
        ss = by_focus.get(FOCUS_SWEETSPOT, [])
        th = by_focus.get(FOCUS_THRESHOLD, [])
        for name, group in (("sweet spot", ss), ("limiar", th)):
            if len(group) < 2:
                continue
            structs = {(w["params"]["repeats"], w["params"]["on_sec"],
                        w["params"]["on_power"]) for w in group}
            self.assertGreater(len(structs), 1,
                               f"{name} deveria alternar formatos com GOAL")

    def test_sem_goal_mantem_mesma_estrutura(self):
        START = date(2026, 9, 14)
        plan = build_plan([], 5, ftp=182, days=14, start=START)  # sem GOAL
        by_focus = {}
        for w in plan:
            by_focus.setdefault(w["focus"], []).append(w)
        ss = by_focus.get(FOCUS_SWEETSPOT, [])
        if len(ss) >= 2:
            structs = {(w["params"]["repeats"], w["params"]["on_sec"]) for w in ss}
            self.assertEqual(len(structs), 1,
                             "sem GOAL o template atual nao deve variar")


class PlanMetaTest(unittest.TestCase):
    def _sample_plan(self):
        return build_plan([], 0, ftp=182, days=2, goal="ftp-builder",
                          start=date(2026, 9, 14))

    def test_save_load_com_meta(self):
        plan = self._sample_plan()
        with tempfile.TemporaryDirectory() as t:
            path = str(Path(t) / "plan.json")
            save_plan(plan, path, goal="ftp-builder", race_date=None)
            self.assertEqual(load_plan(path), plan,
                             "load_plan deve continuar devolvendo a lista")
            self.assertEqual(load_plan_meta(path),
                             {"goal": "ftp-builder", "race_date": None})

    def test_save_load_formato_antigo(self):
        plan = self._sample_plan()
        with tempfile.TemporaryDirectory() as t:
            path = str(Path(t) / "plan.json")
            save_plan(plan, path)  # sem GOAL -> lista pura
            self.assertEqual(load_plan(path), plan)
            self.assertEqual(load_plan_meta(path),
                             {"goal": None, "race_date": None})

    def test_load_meta_arquivo_inexistente(self):
        with tempfile.TemporaryDirectory() as t:
            path = str(Path(t) / "nada.json")
            self.assertEqual(load_plan_meta(path),
                             {"goal": None, "race_date": None})


class PromptRaceDateTest(unittest.TestCase):
    """GOAL=race: o fluxo SEMPRE pergunta a data alvo antes de montar o plano
    (nunca assume default nem deixa em branco)."""

    def _import_training_plan(self):
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
        import training_plan
        return training_plan

    def test_pergunta_e_salva_race_date(self):
        from unittest import mock
        tp = self._import_training_plan()
        saved = []
        with mock.patch("builtins.input", return_value="2027-03-15"), \
             mock.patch.object(tp, "_env_set", side_effect=lambda k, v: saved.append((k, v))):
            result = tp.prompt_race_date()
        self.assertEqual(result, "2027-03-15")
        self.assertEqual(saved, [("RACE_DATE", "2027-03-15")],
                         "data alvo precisa ser salva no .env")

    def test_recusa_data_invalida_e_passada(self):
        from unittest import mock
        tp = self._import_training_plan()
        saved = []
        with mock.patch("builtins.input",
                        side_effect=["2026-01-01", "nao-e-data", "2027-06-10"]), \
             mock.patch.object(tp, "_env_set", side_effect=lambda k, v: saved.append((k, v))):
            result = tp.prompt_race_date()
        self.assertEqual(result, "2027-06-10")
        self.assertEqual(saved, [("RACE_DATE", "2027-06-10")],
                         "so salva depois de uma data futura valida")


if __name__ == "__main__":
    unittest.main()