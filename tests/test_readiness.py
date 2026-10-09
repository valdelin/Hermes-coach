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


class LowHrvBaselineContaminationTest(unittest.TestCase):
    """`current` de HRV nao pode participar da media contra a qual e comparado.

    Antes do fix, `_low_hrv` mediava `rows` inteiro — incluindo o proprio valor
    corrente. Uma queda forte baixava a media e portanto subia o threshold,
    mascarando o sinal que a regra de 80% existe para detectar.
    """

    # Queda de ~27% contra o historico anterior. Com a media contaminada o
    # threshold caia para 43.31 e 44 nao disparava `hrv_low`.
    REGRESSAO = [60, 59, 58, 57, 56, 45, 44]

    def _rows(self, series, rhr=50):
        base = date(2026, 9, 1).toordinal()
        out = []
        for i, v in enumerate(series):
            day = date.fromordinal(base + i).isoformat()
            out.append((day, _wellness_day(day, rhr=rhr, hrv=v, sleep_h=8)))
        return out

    def test_regressao_queda_forte_agora_dispara(self):
        """Falha na implementacao antiga: 44 < 54.14*0.80 era False."""
        rows = self._rows(self.REGRESSAO)
        self.assertTrue(readiness._low_hrv(rows))

    def test_valor_corrente_nao_entra_no_proprio_baseline(self):
        """O threshold deve vir do historico, nao de uma media que o inclui."""
        rows = self._rows(self.REGRESSAO)
        base_historico = sum(self.REGRESSAO[:-1]) / len(self.REGRESSAO[:-1])
        self.assertTrue(readiness._low_hrv(rows))
        # o unico threshold que faz `44` disparar e o dos valores anteriores
        self.assertLess(44, base_historico * readiness.HRV_LOW_RATIO)
        # a media contaminada era insuficiente para dispara
        base_contaminada = sum(self.REGRESSAO) / len(self.REGRESSAO)
        self.assertFalse(44 < base_contaminada * readiness.HRV_LOW_RATIO)

    def test_alinhamento_como_rising_rhr(self):
        """`_low_hrv` agora tem a mesma politica de base de `_rising_rhr`."""
        import inspect
        self.assertIn("rows[:-1]", inspect.getsource(readiness._low_hrv))
        self.assertIn("rows[:-1]", inspect.getsource(readiness._rising_rhr))

    def test_caso_normal_nao_dispara(self):
        """baseline ~58, current 55: 55 < 46.40 e False."""
        rows = self._rows([60, 59, 58, 57, 56, 55])
        self.assertFalse(readiness._low_hrv(rows))

    def test_igualdade_nao_dispara(self):
        """Operador `<` preservado: current == threshold nao dispara."""
        base = 50.0
        rows = self._rows([base, base, base, base, base,
                           base * readiness.HRV_LOW_RATIO])
        self.assertAlmostEqual(base * readiness.HRV_LOW_RATIO,
                               rows[-1][1]["hrv"])
        self.assertFalse(readiness._low_hrv(rows))

    def test_sem_historico_nao_dispara(self):
        """0 valores historicos: sem base, sem sinal (nao inventa minimo)."""
        self.assertFalse(readiness._low_hrv(self._rows([44])))

    def test_um_valor_historico_usa_esse_valor_como_base(self):
        """1 valor historico e base valida; 44 contra 60 dispara."""
        rows = self._rows([60, 44])
        self.assertTrue(readiness._low_hrv(rows))

    def test_poucos_historicos_usa_disponiveis(self):
        rows = self._rows([60, 58, 44])
        base = 59.0
        self.assertAlmostEqual(base, sum([60, 58]) / 2)
        self.assertLess(44, base * readiness.HRV_LOW_RATIO)
        self.assertTrue(readiness._low_hrv(rows))

    def test_missing_preservado(self):
        """Ausencia de HRV no dia corrente nao vira zero nem dispara."""
        base = date(2026, 9, 1).toordinal()
        days = [date.fromordinal(base + i).isoformat() for i in range(7)]
        rows = [(d, _wellness_day(d, rhr=50, hrv=60, sleep_h=8))
                for d in days[:-1]]
        rows.append((days[-1], _wellness_day(days[-1], rhr=50, sleep_h=8)))
        self.assertFalse(readiness._low_hrv(rows))

    def test_hrv_sdnn_continua_indo(self):
        """O fallback hrv -> hrvSDNN nao foi tocado pelo fix."""
        base = date(2026, 9, 1).toordinal()
        rows = []
        for i, v in enumerate(self.REGRESSAO):
            day = date.fromordinal(base + i).isoformat()
            rows.append((day, {"id": day, "restingHR": 50,
                               "hrvSDNN": v, "sleepSecs": 8 * 3600}))
        # `hrv` ausente na janela toda: `_last("hrv")` e None e cai para hrvSDNN
        self.assertIsNone(readiness._last("hrv", rows))
        self.assertEqual(readiness._last("hrvSDNN", rows), 44.0)
        self.assertTrue(readiness._low_hrv(rows))

    def test_propaga_para_signals_e_reason(self):
        rows = self._rows(self.REGRESSAO)
        a = readiness.assess_readiness([rec for _, rec in rows])
        self.assertTrue(a.signals["hrv_low"])
        self.assertIn("HRV", a.reason)

    def test_propaga_para_suggest_swap(self):
        rows = self._rows(self.REGRESSAO)
        a = readiness.assess_readiness([rec for _, rec in rows])
        swap, why = readiness.suggest_swap(a)
        self.assertTrue(swap)
        self.assertIn("HRV", why)

    def test_propaga_para_hrv_score_do_assessment(self):
        """O eixo `hrv_score` usa o mesmo `_low_hrv`; flaggeia junto."""
        recs = [rec for _, rec in self._rows(self.REGRESSAO)]
        avaliacao, trace = readiness.assess_readiness_assessment(recs)
        self.assertEqual(avaliacao.hrv_score, readiness.FLAGGED_SCORE)
        self.assertTrue(trace.signals["hrv_low"])

    def test_illness_inalterado_pois_tem_logica_propria(self):
        """`_illness` compara com o valor anterior; nao usa `_low_hrv`."""
        rows = self._rows([60, 59, 58, 57, 56, 45, 44], rhr=50)
        rows[-1] = (rows[-1][0],
                    _wellness_day(rows[-1][0], rhr=63, hrv=44, sleep_h=8))
        rows[-2] = (rows[-2][0],
                    _wellness_day(rows[-2][0], rhr=61, hrv=45, sleep_h=8))
        rows[-3] = (rows[-3][0],
                    _wellness_day(rows[-3][0], rhr=63, hrv=56, sleep_h=8))
        a = readiness.assess_readiness([rec for _, rec in rows])
        # 63 > 61 e 63 > 63? falso: nao ha dois dias estritamente subindo
        self.assertFalse(a.illness)
        self.assertTrue(a.signals["hrv_low"])

    def test_threshold_e_janela_inalterados(self):
        self.assertEqual(readiness.HRV_LOW_RATIO, 0.80)
        self.assertEqual(readiness.RHR_RISE_BPM, 3.0)
        import inspect
        params = inspect.signature(readiness._low_hrv).parameters
        self.assertEqual(params["days"].default, 7)


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
        self.assertEqual(plan[0]["focus"], FOCUS_ZONE2)
        self.assertIn(FOCUS_THRESHOLD, [w["focus"] for w in plan[1:]])

    def test_build_plan_sem_periodization_comportamento_padrao(self):
        plan = build_plan([], tsb=30, days=5, start=date(2026, 9, 28),
                          training_days=(0, 1, 2, 3, 4))
        self.assertEqual(len(plan), 5)
        self.assertIn(plan[0]["focus"], {FOCUS_ZONE2, FOCUS_SWEETSPOT,
                                         FOCUS_THRESHOLD, FOCUS_VO2})


if __name__ == "__main__":
    unittest.main()
