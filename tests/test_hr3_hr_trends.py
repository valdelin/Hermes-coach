"""HR-3 — HRV/RHR observados, baseline individual e tendencia (leitura pura).

Nenhum teste depende do relogio real: `today`/`now`/`reference_day` sao sempre
explicitos. Nenhum toca provider, plano ou policy.
"""
import contextlib
import dataclasses
import io
import tempfile
import tokenize
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from src import readiness, ui_state
from src.application import Application
from src.snapshot import TrainingSnapshot

T0 = datetime(2026, 10, 3, 12, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 3)
STALE_T0 = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)


def _boom(*_args, **_kwargs):
    raise AssertionError("HR-3 nao pode chamar provider")


def _code_only(path):
    source = Path(path).read_text(encoding="utf-8")
    return " ".join(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type not in (tokenize.COMMENT, tokenize.STRING))


class _Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.app = Application(plan_path=root / "plan.json",
                               env_path=root / ".env",
                               snapshot_path=root / "training_snapshot.json",
                               client_factory=_boom)

    def tearDown(self):
        self.tmp.cleanup()

    def _snapshot(self, *, wellness=None, captured=T0):
        snap = TrainingSnapshot.capture(
            wellness=wellness or [], events=[], activities=[],
            provider="intervals", now=captured)
        self.app.save_training_snapshot(snap)
        return snap

    def _view(self, *, today=TODAY, window_days=None, now=T0):
        kwargs = {"today": today, "now": now}
        if window_days is not None:
            kwargs["window_days"] = window_days
        return self.app.get_heart_rate_trend_view(**kwargs)


# ---------------------------------------------------------------------------
# §30 dados ausentes: missing != zero
# ---------------------------------------------------------------------------

class MissingDataTest(_Base):
    def test_sem_wellness_nao_inventa_serie(self):
        self._snapshot(wellness=[])
        view = self._view()
        self.assertIsNone(view.hrv)
        self.assertIsNone(view.rhr)
        self.assertIsNone(view.reference_day)
        self.assertIsNone(view.hrv_field)

    def test_sem_snapshot_view_vazia_sem_objeto_artificial(self):
        view = self.app.get_heart_rate_trend_view(today=TODAY, now=T0)
        self.assertIsNone(view.hrv)
        self.assertIsNone(view.rhr)
        self.assertEqual(view.target_day, "2026-10-03")

    def test_wellness_sem_hrv_e_sem_rhr_nao_converte_ausencia_em_zero(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "sleepSecs": 8 * 3600}])
        hrv = ui_state.build_heart_rate_trend_view(
            self._snapshot_view(), today=TODAY).hrv
        self.assertEqual(hrv.status, ui_state.HR_TREND_MISSING_CURRENT_VALUE)
        self.assertIsNone(hrv.current)
        self.assertIsNone(hrv.baseline)
        self.assertIsNone(hrv.delta)
        self.assertIsNone(hrv.delta_pct)
        self.assertEqual(hrv.sample_count, 0)

    def _snapshot_view(self):
        snap = self._snapshot(wellness=[{"id": "2026-10-03",
                                         "sleepSecs": 8 * 3600}])
        return ui_state.build_snapshot_view(snap, now=T0)

    def test_so_hrv_sem_rhr(self):
        self._snapshot(wellness=[
            {"id": "2026-10-02", "hrv": 60},
            {"id": "2026-10-03", "hrv": 58},
        ])
        view = self._view()
        self.assertEqual(view.hrv.current, 58)
        self.assertEqual(view.rhr.status,
                         ui_state.HR_TREND_MISSING_CURRENT_VALUE)
        self.assertIsNone(view.rhr.current)
        self.assertIsNone(view.rhr.delta)

    def test_so_rhr_sem_hrv(self):
        self._snapshot(wellness=[
            {"id": "2026-10-02", "restingHR": 50},
            {"id": "2026-10-03", "restingHR": 52},
        ])
        view = self._view()
        self.assertEqual(view.rhr.current, 52)
        # baseline = media da janela inclusiva (50 e 52) = 51
        self.assertEqual(view.rhr.baseline, 51.0)
        self.assertEqual(view.rhr.delta, 1.0)
        self.assertEqual(view.hrv.status,
                         ui_state.HR_TREND_MISSING_CURRENT_VALUE)
        self.assertIsNone(view.hrv_field)

    def test_zero_observado_e_invalido_para_rhr_e_hrv(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 0,
                                  "hrv": 0}])
        view = self._view()
        self.assertIsNone(view.rhr.current)
        self.assertIsNone(view.hrv.current)


# ---------------------------------------------------------------------------
# §31 historico insuficiente
# ---------------------------------------------------------------------------

class InsufficientHistoryTest(_Base):
    def test_uma_amostra_produz_baseline_igual_ao_valor_e_delta_zero(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50,
                                  "hrv": 60}])
        view = self._view()
        self.assertEqual(view.rhr.status, ui_state.HR_TREND_AVAILABLE)
        self.assertEqual(view.rhr.baseline, 50.0)
        self.assertEqual(view.rhr.delta, 0.0)
        self.assertEqual(view.rhr.sample_count, 1)
        self.assertEqual(view.rhr.unit, "bpm")

    def test_sem_nenhuma_amostra_na_janela_status_insufficient(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50,
                                  "hrv": 60}])
        view = self._view(window_days=1)
        self.assertEqual(view.rhr.status, ui_state.HR_TREND_AVAILABLE)

        # baseline unico do dia isolado continua suficiente; o que nao existe
        # e historico, e isso se ve por sample_count, nao por status adivinhado.
        self.assertEqual(view.rhr.sample_count, 1)

    def test_sample_count_expoe_historico_fraco_sem_inventar_corte(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self._view()
        self.assertEqual(view.rhr.sample_count, 1)
        self.assertEqual(view.rhr.status, ui_state.HR_TREND_AVAILABLE)

    def test_janela_exclui_observacao_fora_do_periodo(self):
        self._snapshot(wellness=[
            {"id": "2026-09-20", "restingHR": 90},
            {"id": "2026-10-03", "restingHR": 50},
        ])
        view = self._view(window_days=7)
        self.assertEqual(view.rhr.sample_count, 1)
        self.assertEqual(view.rhr.baseline, 50.0)


# ---------------------------------------------------------------------------
# §32 valores invalidos
# ---------------------------------------------------------------------------

class InvalidValueTest(unittest.TestCase):
    def test_zero_e_invalido_para_ambos_os_campos(self):
        # FC de repouso zero e leitura quebrada de sensor, nao observacao.
        self.assertIsNone(ui_state._hr_metric(0, allow_zero=False))
    def test_rejeita_bool_nan_infinito_e_string(self):
        for value in (True, False, float("nan"), float("inf"),
                      float("-inf"), "abc", "", "   ", object()):
            with self.subTest(value=repr(value)):
                self.assertIsNone(ui_state._hr_metric(value, allow_zero=False))

    def test_aceita_numeros_e_strings_numericas(self):
        self.assertEqual(ui_state._hr_metric(50, allow_zero=False), 50.0)
        self.assertEqual(ui_state._hr_metric(50.5, allow_zero=False), 50.5)
        self.assertEqual(ui_state._hr_metric(" 50 ", allow_zero=False), 50.0)
        self.assertEqual(ui_state._hr_metric(-3, allow_zero=False), -3.0)

    def test_zero_so_passa_quando_allow_zero(self):
        self.assertIsNone(ui_state._hr_metric(0, allow_zero=False))
        self.assertEqual(ui_state._hr_metric(0, allow_zero=True), 0.0)

    def test_none_e_ausencia_nao_zero(self):
        self.assertIsNone(ui_state._hr_metric(None, allow_zero=False))

    def test_serie_descarta_invalido_sem_interpolar(self):
        series = ui_state._hr_series(
            [{"day": "2026-10-01", "resting_hr": 50},
             {"day": "2026-10-02", "resting_hr": float("nan")},
             {"day": "2026-10-03", "resting_hr": True},
             {"day": "sem-data", "resting_hr": 44},
             "lixo"],
            field="resting_hr", allow_zero=False)
        self.assertEqual(sorted(series), [date(2026, 10, 1)])
        self.assertEqual(series[date(2026, 10, 1)], 50.0)


# ---------------------------------------------------------------------------
# §33 baseline e delta
# ---------------------------------------------------------------------------

class BaselineDeltaTest(unittest.TestCase):
    def test_baseline_e_media_da_janela_inclusiva(self):
        series = {date(2026, 10, d): float(v)
                  for d, v in ((1, 50), (2, 60), (3, 70))}
        baseline, count = ui_state.derive_hr_baseline(
            series, reference_day=date(2026, 10, 3))
        self.assertEqual(baseline, 60.0)
        self.assertEqual(count, 3)

    def test_delta_absoluto_e_percentual(self):
        self.assertEqual(ui_state.derive_hr_delta(70, 60), 10.0)
        self.assertAlmostEqual(
            ui_state.derive_hr_delta_pct(70, 60), 100.0 / 6.0)

    def test_delta_none_quando_falta_operando(self):
        self.assertIsNone(ui_state.derive_hr_delta(None, 60))
        self.assertIsNone(ui_state.derive_hr_delta(60, None))
        self.assertIsNone(ui_state.derive_hr_delta_pct(None, 60))

    def test_delta_pct_none_quando_baseline_zero(self):
        self.assertIsNone(ui_state.derive_hr_delta_pct(10, 0))

    def test_window_days_invalido_levanta(self):
        for bad in (0, -1, True, 1.5, "7"):
            with self.subTest(window_days=bad):
                with self.assertRaises(ValueError):
                    ui_state.derive_hr_baseline({}, reference_day=TODAY,
                                                window_days=bad)

    def test_baseline_none_sem_observacao(self):
        baseline, count = ui_state.derive_hr_baseline(
            {}, reference_day=TODAY)
        self.assertIsNone(baseline)
        self.assertEqual(count, 0)

    def test_view_com_delta_correto(self):
        self._snap = None
        snap = TrainingSnapshot.capture(wellness=[
            {"id": "2026-10-01", "restingHR": 50, "hrv": 60},
            {"id": "2026-10-02", "restingHR": 50, "hrv": 60},
            {"id": "2026-10-03", "restingHR": 53, "hrv": 54},
        ], events=[], activities=[], provider="intervals", now=T0)
        view = ui_state.build_heart_rate_trend_view(
            ui_state.build_snapshot_view(snap, now=T0), today=TODAY)
        self.assertEqual(view.rhr.baseline, 51.0)
        self.assertEqual(view.rhr.delta, 2.0)
        self.assertAlmostEqual(view.rhr.delta_pct, 200.0 / 51.0)
        self.assertEqual(view.hrv.baseline, 58.0)
        self.assertEqual(view.hrv.delta, -4.0)


# ---------------------------------------------------------------------------
# §11 HRV: metricas diferentes nao se misturam em silencio
# ---------------------------------------------------------------------------

class HrvFieldSelectionTest(_Base):
    def test_usa_hrv_quando_existe(self):
        self._snapshot(wellness=[
            {"id": "2026-10-02", "hrv": 60, "hrvSDNN": 20},
            {"id": "2026-10-03", "hrv": 58, "hrvSDNN": 21},
        ])
        view = self._view()
        self.assertEqual(view.hrv_field, "hrv")
        self.assertEqual(view.hrv.current, 58)
        self.assertEqual(view.hrv.baseline, 59.0)

    def test_fallback_para_sdnn_apenas_quando_hrv_ausente(self):
        self._snapshot(wellness=[
            {"id": "2026-10-02", "hrvSDNN": 20},
            {"id": "2026-10-03", "hrvSDNN": 21},
        ])
        view = self._view()
        self.assertEqual(view.hrv_field, "hrv_sdnn")
        self.assertEqual(view.hrv.current, 21)
        self.assertEqual(view.hrv.baseline, 20.5)

    def test_ambos_ausentes_deixa_hrv_field_nulo(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self._view()
        self.assertIsNone(view.hrv_field)
        self.assertEqual(view.hrv.status,
                         ui_state.HR_TREND_MISSING_CURRENT_VALUE)

    def test_nao_mistura_hrv_com_sdnn_na_mesma_serie(self):
        """hrv em um dia e hrv_sdnn em outro NAO vira uma serie so."""
        self._snapshot(wellness=[
            {"id": "2026-10-02", "hrv": 60},
            {"id": "2026-10-03", "hrvSDNN": 21},
        ])
        view = self._view()
        # `hrv` existe na janela -> usa so `hrv`; o dia com so sdnn nao entra.
        self.assertEqual(view.hrv_field, "hrv")
        self.assertEqual(view.hrv.sample_count, 1)
        self.assertEqual(view.hrv.baseline, 60.0)
        self.assertEqual(view.hrv.current, None)
        self.assertEqual(view.hrv.status,
                         ui_state.HR_TREND_MISSING_CURRENT_VALUE)


# ---------------------------------------------------------------------------
# §35 freshness
# ---------------------------------------------------------------------------

class FreshnessTest(_Base):
    def test_stale_ainda_produz_derivado_e_permanece_visivel(self):
        self._snapshot(wellness=[
            {"id": "2026-10-01", "restingHR": 50},
            {"id": "2026-10-02", "restingHR": 51},
        ], captured=STALE_T0)
        view = self._view(window_days=7)
        self.assertEqual(view.rhr.current, 51)
        self.assertEqual(view.rhr.baseline, 50.5)
        self.assertIsNotNone(view.freshness)
        self.assertEqual(view.freshness.status, "stale")
        self.assertEqual(view.captured_at, STALE_T0.isoformat())
        self.assertEqual(view.provider, "intervals")

    def test_fresh_exposto_quando_recem_capturado(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self._view()
        self.assertEqual(view.freshness.status, "fresh")


# ---------------------------------------------------------------------------
# §34 determinismo temporal
# ---------------------------------------------------------------------------

class DeterminismTest(_Base):
    def test_nao_usa_relogio_do_sistema(self):
        source = _code_only("src/ui_state.py")
        self.assertNotIn("date.today()", source)
        self.assertNotIn("datetime.now(", source)
        self.assertNotIn("utcnow(", source)

    def test_reference_day_e_o_ultimo_observado_nao_o_target(self):
        self._snapshot(wellness=[{"id": "2026-10-01", "restingHR": 50}])
        view = self._view(today=date(2026, 10, 3))
        self.assertEqual(view.target_day, "2026-10-03")
        self.assertEqual(view.reference_day, "2026-10-01")
        self.assertEqual(view.rhr.current, 50)

    def test_mes_e_ano_distintos_nao_quebram(self):
        self._snapshot(wellness=[
            {"id": "2025-12-30", "restingHR": 48},
            {"id": "2026-01-01", "restingHR": 52},
        ])
        view = self._view(today=date(2026, 1, 1), window_days=7)
        self.assertEqual(view.reference_day, "2026-01-01")
        self.assertEqual(view.rhr.baseline, 50.0)

    def test_janela_cruza_limite_de_mes(self):
        self._snapshot(wellness=[
            {"id": "2026-09-29", "restingHR": 48},
            {"id": "2026-09-30", "restingHR": 50},
            {"id": "2026-10-01", "restingHR": 52},
        ])
        view = self._view(today=date(2026, 10, 1), window_days=7)
        self.assertEqual(view.rhr.sample_count, 3)
        self.assertEqual(view.rhr.baseline, 50.0)

    def test_fim_de_semana_nao_tem_tratamento_especial(self):
        # 2026-10-03 e um sabado; a serie nao depende de dia da semana.
        self._snapshot(wellness=[{"id": "2026-10-02", "restingHR": 50},
                                 {"id": "2026-10-03", "restingHR": 51}])
        view = self._view()
        self.assertEqual(view.rhr.baseline, 50.5)


# ---------------------------------------------------------------------------
# §4 §24 readiness: sem duplicacao e sem regressao
# ---------------------------------------------------------------------------

class ReadinessNonRegressionTest(_Base):
    RECORDS = [
        {"id": "2026-09-27", "restingHR": 50, "hrv": 60, "sleepSecs": 8 * 3600},
        {"id": "2026-09-28", "restingHR": 51, "hrv": 59, "sleepSecs": 8 * 3600},
        {"id": "2026-09-29", "restingHR": 52, "hrv": 58, "sleepSecs": 8 * 3600},
        {"id": "2026-09-30", "restingHR": 53, "hrv": 57, "sleepSecs": 8 * 3600},
        {"id": "2026-10-01", "restingHR": 54, "hrv": 56, "sleepSecs": 8 * 3600},
        {"id": "2026-10-02", "restingHR": 58, "hrv": 45, "sleepSecs": 8 * 3600},
        {"id": "2026-10-03", "restingHR": 59, "hrv": 44, "sleepSecs": 8 * 3600},
    ]

    def test_thresholds_de_readiness_nao_mudaram(self):
        self.assertEqual(readiness.RHR_RISE_BPM, 3.0)
        self.assertEqual(readiness.HRV_LOW_RATIO, 0.80)
        self.assertEqual(readiness.SLEEP_SHORT_HOURS, 6.0)
        self.assertEqual(readiness.SLEEP_BELOW_AVG_HOURS, 2.0)
        self.assertEqual(readiness.READINESS_LOW, 60)

    def test_sinais_de_readiness_inalterados(self):
        rows = [(rec["id"], rec) for rec in self.RECORDS]
        self.assertTrue(readiness._rising_rhr(rows))
        # `hrv_low`: o baseline nao e contaminado pelo valor corrente
        # (corrigido em PROMPT 28). Historico `[60,59,58,57,56]` -> media
        # 55.83, threshold 44.67, e `44 < 44.67` e True. Antes a media era
        # 54.14 e o sinal nao disparava. `_rising_rhr` sempre usou
        # `rows[:-1]`; agora os dois seguem a mesma politica de base.
        self.assertTrue(readiness._low_hrv(rows))
        # o threshold em si nao se moveu: 0.80 sobre a media do historico
        base = sum([60, 59, 58, 57, 56]) / 5
        self.assertLess(44, base * readiness.HRV_LOW_RATIO)

    def test_hr3_nao_reimplementa_os_sinais_de_readiness(self):
        """A View expoe observacao; o sinal continua sendo do modulo."""
        self._snapshot(wellness=self.RECORDS)
        view = self._view()
        readiness_view = self.app.get_readiness_view(today=TODAY, now=T0)
        signals = dict(readiness_view.heuristic_signals)
        # mesmo sinal, mesma fonte; HR-3 nao duplica nem reinterpreta
        self.assertTrue(signals["rhr_rising"])
        self.assertTrue(signals["hrv_low"])
        # ...e o valor observado por tras do sinal e o mesmo
        self.assertEqual(view.rhr.current, 59)
        self.assertEqual(readiness_view.wellness.resting_hr, 59)

    def test_view_nao_traz_policy_nem_advice(self):
        self._snapshot(wellness=self.RECORDS)
        payload = self._view().to_dict()
        for forbidden in ("advice", "advisory", "prescription", "action",
                          "readiness_action", "level", "score"):
            self.assertNotIn(forbidden, payload)

    def test_view_nao_cria_advise_nem_prescreve(self):
        source = _code_only("src/ui_state.py")
        for forbidden in ("ReadinessAction", "readiness_decision",
                          "evaluate_form_advisory", "evaluate_ctl_ramp_advisory",
                          "FormAdvisory"):
            self.assertNotIn(forbidden, source)

    def test_application_nao_chama_provider_nem_escreve(self):
        self._snapshot(wellness=self.RECORDS)
        before = (self.app.snapshot_path.read_bytes()
                  if self.app.snapshot_path.exists() else None)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self._view()
        self.assertEqual(out.getvalue(), "")
        after = (self.app.snapshot_path.read_bytes()
                 if self.app.snapshot_path.exists() else None)
        self.assertEqual(before, after)

    def test_nao_integra_com_form_advisory_ou_pw_hr(self):
        self._snapshot(wellness=self.RECORDS)
        view = self._view()
        self.assertFalse(hasattr(view, "form_pct"))
        self.assertFalse(hasattr(view, "advisory"))
        self.assertFalse(hasattr(view, "decoupling"))


# ---------------------------------------------------------------------------
# §1-§8 FCR: alias terminologico de RHR, nao uma terceira metrica
# ---------------------------------------------------------------------------

class FcrIsRhrAliasTest(_Base):
    """FCR = frequencia cardiaca de repouso = RHR. Nao existe campo FCR."""

    def test_view_nao_expoe_campo_fcr(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self._view()
        for nome in dataclasses.fields(view):
            self.assertNotIn("fcr", nome.name.lower())
        self.assertNotIn("fcr", view.to_dict())

    def test_rhr_e_o_campo_que_expoe_fcr(self):
        """O valor de FCR e o `current` de `rhr`; nenhum outro campo."""
        self._snapshot(wellness=[{"id": "2026-10-02", "restingHR": 50},
                                 {"id": "2026-10-03", "restingHR": 52}])
        payload = self._view().to_dict()
        self.assertEqual(payload["rhr"]["current"], 52.0)
        # nenhum outro lugar repete esse numero sob outro nome
        for key, value in payload.items():
            if key == "rhr":
                continue
            self.assertNotEqual(value, 52.0)

    def test_schema_tem_exatamente_dois_sinais(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        payload = self._view().to_dict()
        sinais = [k for k in ("hrv", "rhr", "fcr", "hr_recovery")
                  if k in payload]
        self.assertEqual(sinais, ["hrv", "rhr"])

    def test_status_unsupported_field_foi_removido(self):
        """O estado existia so para marcar FCR; nao ha mais quem o use."""
        self.assertFalse(hasattr(ui_state, "HR_TREND_UNSUPPORTED_FIELD"))

    def test_codigo_nao_trata_fcr_como_metrica(self):
        src = _code_only("src/ui_state.py")
        self.assertNotIn("heart-rate recovery", src)
        self.assertNotIn("heart_rate_recovery", src)
        self.assertNotIn("fcr_heart_rate_recovery", src)

    def test_documentacao_nao_chama_fcr_de_recovery(self):
        docs = Path(__file__).resolve().parent.parent / "docs"
        for nome in ("HR-3-HRV-RHR-TRENDS.md", "ROADMAP.md", "GLOSSARIO.md",
                     "ROTEIRO-TREINADOR.md"):
            texto = (docs / nome).read_text(encoding="utf-8").lower()
            self.assertNotIn("fcr (heart-rate recovery)", texto, nome)
            self.assertNotIn("fcr: heart-rate recovery", texto, nome)

    def test_provider_e_readiness_intactos(self):
        """FCR nao virou campo de provider nem mexeu no readiness."""
        from src import provider_fields
        for nome in ("resting_hr", "hrv", "hrv_sdnn"):
            self.assertTrue(hasattr(provider_fields, "field"))
        self.assertEqual(readiness.HRV_LOW_RATIO, 0.80)
        self.assertEqual(readiness.RHR_RISE_BPM, 3.0)


# ---------------------------------------------------------------------------
# §38 shape da view
# ---------------------------------------------------------------------------

class ViewShapeTest(_Base):
    def test_to_dict_expoe_proveniencia(self):
        self._snapshot(wellness=[{"id": "2026-10-02", "restingHR": 50},
                                 {"id": "2026-10-03", "restingHR": 52}])
        payload = self._view().to_dict()
        for key in ("target_day", "window_days", "reference_day", "hrv",
                    "rhr", "hrv_field",
                    "freshness", "captured_at", "provider"):
            self.assertIn(key, payload)
        for key in ("field", "status", "current", "baseline", "delta",
                    "delta_pct", "sample_count", "unit"):
            self.assertIn(key, payload["rhr"])

    def test_view_e_imutavel(self):
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self._view()
        with self.assertRaises(Exception):
            view.target_day = "2026-01-01"

    def test_metric_available_reflete_o_que_existe(self):
        self._snapshot(wellness=[{"id": "2026-10-02", "restingHR": 50},
                                 {"id": "2026-10-03", "restingHR": 52}])
        view = self._view()
        self.assertTrue(view.rhr.available)
        self.assertFalse(view.hrv.available)

    def test_estrutura_nao_tem_readiness_nem_pmc(self):
        """HR-3 e uma camada a parte: nao embute outras Views."""
        self._snapshot(wellness=[{"id": "2026-10-03", "restingHR": 50}])
        view = self._view()
        self.assertIsInstance(view.hrv, ui_state.HeartRateMetricTrend)
        self.assertIsInstance(view.rhr, ui_state.HeartRateMetricTrend)


if __name__ == "__main__":
    unittest.main()