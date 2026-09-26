import unittest
from datetime import date

from src import readiness
from src.plan import (PERIODIZATIONS, PERIODIZATION_TEMPLATES,
                      PERIODIZATION_LABELS, parse_periodization,
                      weekly_template, build_plan, FOCUS_ZONE2,
                      FOCUS_SWEETSPOT, FOCUS_THRESHOLD, FOCUS_VO2)


def _wellness_day(day, rhr=None, hrv=None, sleep_h=None, readiness_v=None):
    rec = {"id": day}
    if rhr is not None:
        rec["restingHR"] = rhr
    if hrv is not None:
        rec["hrv"] = hrv
    if sleep_h is not None:
        rec["sleepSecs"] = int(sleep_h * 3600)
    if readiness_v is not None:
        rec["readiness"] = readiness_v
    return rec


class AssessReadinessTest(unittest.TestCase):
    def test_sem_dados_has_data_false(self):
        a = readiness.assess_readiness([])
        self.assertFalse(a.has_data)
        self.assertFalse(a.illness)

    def test_sinais_normais(self):
        days = [date.fromordinal(date(2026, 9, 1).toordinal() + i).isoformat()
                for i in range(7)]
        rows = [_wellness_day(d, rhr=50, hrv=70, sleep_h=8) for d in days]
        a = readiness.assess_readiness(rows)
        self.assertTrue(a.has_data)
        self.assertFalse(any(a.signals.values()))
        self.assertFalse(a.illness)

    def test_rhr_subindo_sinal(self):
        days = [date.fromordinal(date(2026, 9, 1).toordinal() + i).isoformat()
                for i in range(7)]
        rows = [_wellness_day(d, rhr=50, hrv=70, sleep_h=8) for d in days]
        rows[-1] = _wellness_day(days[-1], rhr=58, hrv=70, sleep_h=8)
        a = readiness.assess_readiness(rows)
        self.assertTrue(a.signals["rhr_rising"])

    def test_hrv_baixo_sinal(self):
        days = [date.fromordinal(date(2026, 9, 1).toordinal() + i).isoformat()
                for i in range(7)]
        rows = [_wellness_day(d, rhr=50, hrv=70, sleep_h=8) for d in days]
        rows[-1] = _wellness_day(days[-1], rhr=50, hrv=40, sleep_h=8)
        a = readiness.assess_readiness(rows)
        self.assertTrue(a.signals["hrv_low"])

    def test_sono_curto_sinal(self):
        days = [date.fromordinal(date(2026, 9, 1).toordinal() + i).isoformat()
                for i in range(7)]
        rows = [_wellness_day(d, rhr=50, hrv=70, sleep_h=8) for d in days]
        rows[-1] = _wellness_day(days[-1], rhr=50, hrv=70, sleep_h=5)
        a = readiness.assess_readiness(rows)
        self.assertTrue(a.signals["sleep_short"])

    def test_doenca_rhr_2_noites_hrv_caindo(self):
        days = [date.fromordinal(date(2026, 9, 1).toordinal() + i).isoformat()
                for i in range(5)]
        rows = [_wellness_day(d, rhr=50, hrv=70, sleep_h=8) for d in days[:2]]
        rows.append(_wellness_day(days[2], rhr=56, hrv=70, sleep_h=8))
        rows.append(_wellness_day(days[3], rhr=61, hrv=66, sleep_h=8))
        rows.append(_wellness_day(days[4], rhr=63, hrv=55, sleep_h=8))
        a = readiness.assess_readiness(rows)
        self.assertTrue(a.illness)


class RecoveryWorkoutTest(unittest.TestCase):
    def test_formato_plan_json(self):
        w = readiness.recovery_workout("2026-09-26", ftp=200)
        self.assertEqual(w["day"], "2026-09-26")
        self.assertEqual(w["focus"], "zone2")
        self.assertIn("Zona 2", w["name"])
        self.assertEqual(w["external_id"], "hermes-plan-2026-09-26")
        self.assertIn("params", w)
        self.assertGreater(w["tss"], 0)
        self.assertGreater(w["planned_duration"], 0)

    def test_troca_e_leve(self):
        w = readiness.recovery_workout("2026-09-26", ftp=200)
        self.assertEqual(w["params"]["repeats"], 1)
        self.assertLessEqual(w["tss"], 40)


class SuggestSwapTest(unittest.TestCase):
    def test_sem_dados_nao_sugere(self):
        a = readiness.Readiness({}, False, "sem dados", has_data=False)
        swap, _ = readiness.suggest_swap(a)
        self.assertFalse(swap)

    def test_sinais_normais_nao_sugere(self):
        a = readiness.Readiness({"rhr_rising": False, "hrv_low": False,
                                 "sleep_short": False, "readiness_low": False},
                                False, "normal", has_data=True)
        swap, _ = readiness.suggest_swap(a)
        self.assertFalse(swap)

    def test_doenca_sugere(self):
        a = readiness.Readiness({"rhr_rising": True, "hrv_low": True,
                                 "sleep_short": False, "readiness_low": False},
                                True, "alerta", has_data=True)
        swap, why = readiness.suggest_swap(a)
        self.assertTrue(swap)
        self.assertIn("doenca", why)

    def test_limiar_com_rhr_alto_sugere(self):
        a = readiness.Readiness({"rhr_rising": True, "hrv_low": False,
                                 "sleep_short": False, "readiness_low": False},
                                False, "RHR acima", has_data=True)
        planned = {"focus": "threshold"}
        swap, why = readiness.suggest_swap(a, planned)
        self.assertTrue(swap)
        self.assertIn("threshold", why)

    def test_zone2_com_sinal_leve_nao_sugere(self):
        a = readiness.Readiness({"rhr_rising": False, "hrv_low": False,
                                 "sleep_short": True, "readiness_low": False},
                                False, "sono curto", has_data=True)
        planned = {"focus": "zone2"}
        swap, _ = readiness.suggest_swap(a, planned)
        self.assertFalse(swap)


class CoachAlertPayloadTest(unittest.TestCase):
    def test_payload_contem_dados(self):
        a = readiness.Readiness({"rhr_rising": True, "hrv_low": True},
                                True, "alerta doenca", has_data=True)
        payload = readiness.coach_alert_payload("123", a, "2026-09-26")
        self.assertEqual(payload["atleta"], "123")
        self.assertEqual(payload["dia"], "2026-09-26")
        self.assertEqual(payload["tipo"], "alerta-doenca")
        self.assertIn("mensagem", payload)
        self.assertTrue(payload["sinais"]["rhr_rising"])


class ParsePeriodizationTest(unittest.TestCase):
    def test_catalogo_tem_5_modelos(self):
        self.assertEqual(PERIODIZATIONS,
                         ("polarized", "pyramidal", "undulating", "linear",
                          "block"))

    def test_parse_valido(self):
        for p in PERIODIZATIONS:
            self.assertEqual(parse_periodization(p), p)
            self.assertEqual(parse_periodization(p.upper()), p)

    def test_parse_underscore_aceito(self):
        self.assertEqual(parse_periodization("pyramidal"), "pyramidal")

    def test_parse_ausente_ou_invalido(self):
        self.assertIsNone(parse_periodization(""))
        self.assertIsNone(parse_periodization(None))
        self.assertIsNone(parse_periodization("nao-existe"))
        self.assertIsNone(parse_periodization("threshold"))

    def test_todos_os_modelos_tem_template_e_label(self):
        for p in PERIODIZATIONS:
            self.assertIn(p, PERIODIZATION_TEMPLATES)
            self.assertIn(p, PERIODIZATION_LABELS)


class PeriodizationWeeklyTemplateTest(unittest.TestCase):
    def test_sem_periodizacao_mantem_atual(self):
        self.assertEqual(weekly_template(-20, None),
                         weekly_template(-20, None, None))

    def test_polarized_tem_vo2_mas_pouco_sweet_spot(self):
        t = weekly_template(0, None, "polarized")
        self.assertIn(FOCUS_VO2, t)
        self.assertNotIn(FOCUS_SWEETSPOT, t)

    def test_block_tsb_baixo_tudo_zone2(self):
        t = weekly_template(-30, None, "block")
        self.assertEqual(set(t), {FOCUS_ZONE2})

    def test_block_tsb_alto_tem_qualidade(self):
        t = weekly_template(30, None, "block")
        self.assertIn(FOCUS_THRESHOLD, t)
        self.assertIn(FOCUS_VO2, t)

    def test_pyramidal_tem_base_zone2(self):
        t = weekly_template(-30, None, "pyramidal")
        self.assertIn(FOCUS_ZONE2, t)


class BuildPlanPeriodizationTest(unittest.TestCase):
    def test_build_plan_aceita_periodization(self):
        plan = build_plan([], tsb=-30, days=5, start=date(2026, 9, 28),
                          training_days=(0, 1, 2, 3, 4),
                          periodization="block", goal=None)
        self.assertEqual(len(plan), 5)
        for w in plan:
            self.assertEqual(w["focus"], FOCUS_ZONE2)

    def test_build_plan_sem_periodization_comportamento_padrao(self):
        plan = build_plan([], tsb=30, days=5, start=date(2026, 9, 28),
                          training_days=(0, 1, 2, 3, 4))
        self.assertEqual(len(plan), 5)
        self.assertIn(plan[0]["focus"], {FOCUS_ZONE2, FOCUS_SWEETSPOT,
                                         FOCUS_THRESHOLD, FOCUS_VO2})


if __name__ == "__main__":
    unittest.main()