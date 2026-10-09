#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""HR-4 — sinais de wellness observados (sono, stress, readiness do provider).

Cobre o contrato de leitura de `ui_state.ObservedWellnessView`:
- campos reais vs `unsupported_field` (§3, §41);
- unidade de sono em segundos, sem converter score<->horas (§5, §6);
- escala/direcao desconhecidas declaradas, nunca inferidas (§7, §8, §9);
- `provider_readiness` separado de readiness do Hermes (§12);
- baseline/delta/delta_pct/sample_count, com `delta_pct=None` se baseline 0 (§16, §36);
- missing != zero, rejeicao de bool/NaN/inf/string/negativo (§19, §20);
- stale ainda expoe valor e baseline (§21);
- offline: 0 provider calls, 0 writes, 0 stdout (§22, §23, §38);
- readiness nao muda (§25, §29, §39).
"""
from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import MappingProxyType

from src import ui_state as U

DAY = date(2026, 10, 1)


def _snap(records, *, provider="intervals.icu",
          captured_at="2026-10-01T06:00:00", freshness=None):
    """SnapshotView local com wellness canonico; nunca toca provider."""
    return U.SnapshotView(
        provider=provider, captured_at=captured_at,
        freshness=freshness,
        wellness=tuple(MappingProxyType(dict(r)) for r in records),
        events=(), activities=())


def _day(offset, **fields):
    base = {"day": (DAY - timedelta(days=offset)).isoformat()}
    base.update(fields)
    return base


def _wellness_window(**today_fields):
    """4 dias com os quatro campos existentes, variando so o dia corrente."""
    return [
        _day(3, sleep_secs=26000, sleep_score=70, stress=180, readiness=70),
        _day(2, sleep_secs=27000, sleep_score=72, stress=175, readiness=72),
        _day(1, sleep_secs=28000, sleep_score=74, stress=170, readiness=74),
        _day(0, **today_fields),
    ]


def _metric(view, concept):
    return getattr(view, concept)


# ---------------------------------------------------------------------------
# Contrato: inventario e unsupported_field
# ---------------------------------------------------------------------------

class InventoryTest(unittest.TestCase):
    """§3 — o inventario expoe os 7 conceitos, mesmo os que nao existem."""

    CONCEPTS = ("sleep_duration", "sleep_score", "stress", "soreness",
                "motivation", "fatigue", "provider_readiness")

    def test_inventario_tem_os_sete_conceitos(self):
        self.assertEqual(
            tuple(spec.concept for spec in U.WELLNESS_METRIC_SPECS),
            self.CONCEPTS)

    def test_view_expoe_todos_os_conceitos(self):
        view = U.build_observed_wellness_view(_snap([]), today=DAY)
        self.assertEqual(tuple(m.concept for m in view.metrics), self.CONCEPTS)

    def test_campos_reais_sao_os_canonicos_do_boundary(self):
        esperado = {
            "sleep_duration": "sleep_secs",
            "sleep_score": "sleep_score",
            "stress": "stress",
            "provider_readiness": "readiness",
        }
        for spec in U.WELLNESS_METRIC_SPECS:
            if spec.concept in esperado:
                self.assertEqual(spec.field, esperado[spec.concept])

    def test_conceitos_sem_chave_no_provider(self):
        sem_campo = {spec.concept for spec in U.WELLNESS_METRIC_SPECS
                     if spec.field is None}
        self.assertEqual(sem_campo, {"soreness", "motivation", "fatigue"})

    def test_nao_existe_alias_inventado_no_boundary(self):
        # §41: o boundary nao registra soreness/motivation/fatigue, nem
        # mapeia nome parecido (`muscle_soreness` etc.).
        from src.provider_fields import ALL_FIELDS
        for nome in ("soreness", "motivation", "fatigue",
                     "muscle_soreness", "sore", "motivation_score"):
            self.assertNotIn(nome, ALL_FIELDS)


class UnsupportedFieldTest(unittest.TestCase):
    """§33, §41 — sem soreness/motivation/fatigue, o contrato declara a lacuna."""

    def test_unsupported_mesmo_com_historico_presente(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=27000, sleep_score=72,
                                   stress=175, readiness=71)), today=DAY)
        for conceito in ("soreness", "motivation", "fatigue"):
            metric = _metric(view, conceito)
            self.assertEqual(metric.status, U.WELLNESS_STATUS_UNSUPPORTED)
            self.assertIsNone(metric.field)
            self.assertIsNone(metric.current)

    def test_unsupported_nao_e_affected_por_registro_sem_chave(self):
        """Um `soreness` no registro cru nao pode virar sinal observado."""
        records = _wellness_window(sleep_secs=27000, sleep_score=72,
                                   stress=175, readiness=71)
        records[-1] = dict(records[-1], soreness=3, motivation=4, fatigue=5)
        view = U.build_observed_wellness_view(_snap(records), today=DAY)
        self.assertEqual(set(view.unsupported),
                         {"soreness", "motivation", "fatigue"})
        self.assertIsNone(_metric(view, "soreness").current)

    def test_unsupported_lista_exposta(self):
        view = U.build_observed_wellness_view(_snap([]), today=DAY)
        self.assertEqual(set(view.unsupported),
                         {"soreness", "motivation", "fatigue"})
        self.assertEqual(view.to_dict()["unsupported"],
                         ["soreness", "motivation", "fatigue"])


# ---------------------------------------------------------------------------
# Ausencia de dado
# ---------------------------------------------------------------------------

class MissingDataTest(unittest.TestCase):
    """§33, §34 — ausencia de wellness, de sleep, ou parcial."""

    def test_sem_snapshot(self):
        view = U.build_observed_wellness_view(None, today=DAY)
        self.assertEqual(view.target_day, DAY.isoformat())
        self.assertIsNone(view.reference_day)
        self.assertFalse(view.available)

    def test_sem_wellness(self):
        view = U.build_observed_wellness_view(_snap([]), today=DAY)
        self.assertFalse(view.available)
        self.assertIsNone(view.reference_day)
        for metric in view.metrics:
            self.assertIsNone(metric.current)
            self.assertNotEqual(metric.current, 0)

    def test_sem_sleep(self):
        view = U.build_observed_wellness_view(
            _snap([_day(1, stress=180), _day(0, stress=175)]), today=DAY)
        self.assertTrue(view.available)
        self.assertEqual(_metric(view, "sleep_duration").status,
                         U.WELLNESS_STATUS_MISSING_CURRENT)
        self.assertIsNone(_metric(view, "sleep_duration").current)
        self.assertEqual(_metric(view, "stress").status,
                         U.WELLNESS_STATUS_OBSERVED)

    def test_so_sleep(self):
        view = U.build_observed_wellness_view(
            _snap([_day(1, sleep_secs=27000), _day(0, sleep_secs=27000)]),
            today=DAY)
        self.assertTrue(view.available)
        self.assertEqual(_metric(view, "sleep_duration").status,
                         U.WELLNESS_STATUS_OBSERVED)
        self.assertIsNone(_metric(view, "stress").current)
        self.assertEqual(_metric(view, "stress").status,
                         U.WELLNESS_STATUS_MISSING_CURRENT)

    def test_so_stress(self):
        view = U.build_observed_wellness_view(
            _snap([_day(1, stress=180), _day(0, stress=175)]), today=DAY)
        self.assertEqual(_metric(view, "stress").status,
                         U.WELLNESS_STATUS_OBSERVED)
        self.assertIsNone(_metric(view, "sleep_duration").current)

    def test_so_provider_readiness(self):
        view = U.build_observed_wellness_view(
            _snap([_day(1, readiness=70), _day(0, readiness=55)]), today=DAY)
        self.assertTrue(view.available)
        self.assertEqual(_metric(view, "provider_readiness").status,
                         U.WELLNESS_STATUS_OBSERVED)
        self.assertEqual(_metric(view, "provider_readiness").current, 55.0)
        self.assertEqual(_metric(view, "sleep_duration").status,
                         U.WELLNESS_STATUS_MISSING_CURRENT)

    def test_missing_nunca_vira_zero(self):
        """§19 — ausencia e `None`, nunca 0 nem string vazia."""
        view = U.build_observed_wellness_view(_snap([_day(0, hrv=60)]), today=DAY)
        dicionario = view.to_dict()
        for entrada in dicionario["metrics"]:
            self.assertNotEqual(entrada["current"], 0)
            if entrada["status"] != U.WELLNESS_STATUS_OBSERVED:
                self.assertIsNone(entrada["current"])

    def test_valor_de_dia_anterior_nao_vira_current(self):
        view = U.build_observed_wellness_view(
            _snap([_day(5, sleep_secs=27000)]), today=DAY)
        # referencia e o ultimo dia com wellness; o valor e dele, nao de hoje.
        self.assertEqual(view.reference_day, (DAY - timedelta(days=5)).isoformat())
        self.assertEqual(_metric(view, "sleep_duration").current, 27000.0)


# ---------------------------------------------------------------------------
# Sono: unidade e nao-equivalencia
# ---------------------------------------------------------------------------

class SleepUnitTest(unittest.TestCase):
    """§5, §6 — segundos confirmados; score nunca vira horas e vice-versa."""

    def test_duracao_em_segundos(self):
        spec = next(s for s in U.WELLNESS_METRIC_SPECS
                    if s.concept == "sleep_duration")
        self.assertEqual(spec.unit, "seconds")
        self.assertEqual(spec.field, "sleep_secs")

    def test_valor_preservado_em_segundos(self):
        view = U.build_observed_wellness_view(
            _snap([_day(0, sleep_secs=27000)]), today=DAY)
        self.assertEqual(_metric(view, "sleep_duration").current, 27000.0)

    def test_score_nao_e_convertido_para_horas(self):
        view = U.build_observed_wellness_view(
            _snap([_day(0, sleep_score=72)]), today=DAY)
        self.assertEqual(_metric(view, "sleep_score").current, 72.0)
        self.assertEqual(_metric(view, "sleep_score").unit, "points")
        self.assertIsNone(_metric(view, "sleep_duration").current)

    def test_horas_nao_sao_convertidas_para_score(self):
        view = U.build_observed_wellness_view(
            _snap([_day(0, sleep_secs=27000)]), today=DAY)
        self.assertIsNone(_metric(view, "sleep_score").current)
        self.assertEqual(_metric(view, "sleep_score").status,
                         U.WELLNESS_STATUS_MISSING_CURRENT)

    def test_sleep_e_sleep_score_sao_campos_distintos(self):
        view = U.build_observed_wellness_view(
            _snap([_day(0, sleep_secs=27000, sleep_score=72)]), today=DAY)
        self.assertEqual(_metric(view, "sleep_duration").current, 27000.0)
        self.assertEqual(_metric(view, "sleep_score").current, 72.0)


# ---------------------------------------------------------------------------
# Escala e direcao desconhecidas
# ---------------------------------------------------------------------------

class UnknownScaleTest(unittest.TestCase):
    """§7, §8, §9 — escala sem contrato vira `unknown`, nunca assumida."""

    def test_stress_sem_unidade_documentada(self):
        view = U.build_observed_wellness_view(_snap([_day(0, stress=175)]),
                                              today=DAY)
        self.assertEqual(_metric(view, "stress").current, 175.0)
        self.assertEqual(_metric(view, "stress").unit,
                         U.WELLNESS_SCALE_UNKNOWN)

    def test_stress_escala_desconhecida(self):
        view = U.build_observed_wellness_view(_snap([_day(0, stress=175)]),
                                              today=DAY)
        self.assertEqual(_metric(view, "stress").scale,
                         U.WELLNESS_SCALE_UNKNOWN)

    def test_nenhuma_metrica_declara_direcao(self):
        """§8, §9, §18 — nao ha rotulo high-is-good/high-is-bad em HR-4."""
        for spec in U.WELLNESS_METRIC_SPECS:
            self.assertFalse(hasattr(spec, "direction"))
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=27000, sleep_score=72,
                                   stress=175, readiness=71)), today=DAY)
        for metric in view.metrics:
            self.assertFalse(hasattr(metric, "direction"))

    def test_nenhum_rotulo_de_julgamento(self):
        """§18 — sem good/bad/danger/overreaching nos valores."""
        proibidos = ("good", "bad", "danger", "overreaching", "ruim", "bom")
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=27000, sleep_score=72,
                                   stress=175, readiness=71)), today=DAY)
        for metric in view.metrics:
            for atributo in ("status", "scale", "unit", "source", "concept"):
                valor = str(getattr(metric, atributo)).lower()
                for termo in proibidos:
                    self.assertNotIn(termo, valor)


# ---------------------------------------------------------------------------
# Provider readiness vs readiness do Hermes
# ---------------------------------------------------------------------------

class ProviderReadinessTest(unittest.TestCase):
    """§12 — o score do provider nao se confunde com o readiness do Hermes."""

    def test_campo_chama_provider_readiness(self):
        self.assertIn("provider_readiness", U.ObservedWellnessView.__dataclass_fields__)

    def test_view_nao_expoe_readiness_do_hermes(self):
        exposto = set(U.ObservedWellnessView.__dataclass_fields__)
        exposto |= {n for n in dir(U.ObservedWellnessView)
                    if not n.startswith("_")}
        for proibido in ("readiness", "readiness_score", "readiness_view",
                         "heuristic_level", "heuristic_score",
                         "heuristic_confidence", "illness_alert",
                         "composite_low", "readiness_action", "action"):
            self.assertNotIn(proibido, exposto)

    def test_provider_readiness_nao_recebe_baseline(self):
        """Composto do provider: media entre dias pode misturar versoes."""
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=27000, sleep_score=72,
                                   stress=175, readiness=71)), today=DAY)
        metric = _metric(view, "provider_readiness")
        self.assertEqual(metric.current, 71.0)
        self.assertIsNone(metric.baseline)
        self.assertIsNone(metric.delta)
        self.assertIsNone(metric.delta_pct)
        self.assertEqual(metric.sample_count, 4)

    def test_outros_campos_tem_baseline(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=27000, sleep_score=72,
                                   stress=175, readiness=71)), today=DAY)
        for conceito in ("sleep_duration", "sleep_score", "stress"):
            self.assertIsNotNone(_metric(view, conceito).baseline, conceito)


# ---------------------------------------------------------------------------
# Baseline, delta, sample_count
# ---------------------------------------------------------------------------

class BaselineTest(unittest.TestCase):
    """§16, §18, §36 — baseline, delta, delta_pct e n."""

    def test_baseline_sleep_duration(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000)), today=DAY)
        metric = _metric(view, "sleep_duration")
        self.assertEqual(metric.current, 24000.0)
        self.assertEqual(metric.baseline, (26000 + 27000 + 28000 + 24000) / 4)
        self.assertEqual(metric.sample_count, 4)

    def test_delta_e_delta_pct(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000)), today=DAY)
        metric = _metric(view, "sleep_duration")
        self.assertEqual(metric.delta, 24000.0 - metric.baseline)
        self.assertAlmostEqual(
            metric.delta_pct,
            (24000.0 - metric.baseline) / metric.baseline * 100.0)

    def test_baseline_stress_e_sleep_score(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190)), today=DAY)
        self.assertAlmostEqual(_metric(view, "sleep_score").baseline,
                               (70 + 72 + 74 + 61) / 4)
        self.assertAlmostEqual(_metric(view, "stress").baseline,
                               (180 + 175 + 170 + 190) / 4)

    def test_delta_pct_none_quando_baseline_zero(self):
        """§36 — divisao por zero nao e feita e o sinal nao vira 0%.

        A janela e inclusiva e termina em `reference_day`,entao `baseline == 0`
        so acontece quando todos os valores observados na janela sao zero.
        """
        records = [_day(3, stress=0), _day(2, stress=0),
                   _day(1, stress=0), _day(0, stress=0)]
        view = U.build_observed_wellness_view(_snap(records), today=DAY)
        metric = _metric(view, "stress")
        self.assertEqual(metric.current, 0.0)
        self.assertEqual(metric.baseline, 0.0)
        self.assertEqual(metric.delta, 0.0)
        self.assertIsNone(metric.delta_pct)

    def test_baseline_zero_com_current_zero(self):
        records = [_day(1, stress=0), _day(0, stress=0)]
        view = U.build_observed_wellness_view(_snap(records), today=DAY)
        metric = _metric(view, "stress")
        self.assertEqual(metric.current, 0.0)
        self.assertEqual(metric.baseline, 0.0)
        self.assertEqual(metric.delta, 0.0)
        self.assertIsNone(metric.delta_pct)

    def test_zero_e_observacao_valida(self):
        """§20 — zero sobrevive onde e semanticamente possivel."""
        view = U.build_observed_wellness_view(
            _snap([_day(0, sleep_secs=0)]), today=DAY)
        metric = _metric(view, "sleep_duration")
        self.assertEqual(metric.current, 0.0)
        self.assertEqual(metric.status, U.WELLNESS_STATUS_OBSERVED)

    def test_baseline_com_uma_so_observacao_nao_fala_de_tendencia(self):
        """n=1: media == current, entao delta nao pode ser 0.0 (tautologia)."""
        view = U.build_observed_wellness_view(_snap([_day(0, sleep_secs=27000)]),
                                              today=DAY)
        metric = _metric(view, "sleep_duration")
        self.assertEqual(metric.current, 27000.0)
        self.assertEqual(metric.baseline, 27000.0)
        self.assertEqual(metric.sample_count, 1)
        self.assertIsNone(metric.delta)
        self.assertIsNone(metric.delta_pct)
        self.assertEqual(metric.status, U.WELLNESS_STATUS_OBSERVED)

    def test_baseline_none_quando_nao_ha_observacao_na_janela(self):
        view = U.build_observed_wellness_view(
            _snap([_day(0, hrv=60)]), today=DAY)
        metric = _metric(view, "sleep_duration")
        self.assertIsNone(metric.baseline)
        self.assertEqual(metric.sample_count, 0)
        self.assertIsNone(metric.delta)

    def test_janela_inclusiva_respeitada(self):
        """§17 — a janela conta `window_days` dias, terminando em reference."""
        records = [_day(offset, sleep_secs=1000 * (offset + 1))
                   for offset in range(3, -1, -1)]
        dentro = U.build_observed_wellness_view(
            _snap(records), today=DAY, window_days=4)
        self.assertEqual(_metric(dentro, "sleep_duration").sample_count, 4)
        fora = U.build_observed_wellness_view(
            _snap(records), today=DAY, window_days=2)
        # `_day(3..0)` grava 4000,3000,2000,1000; janela 2 cobre offsets 1 e 0
        # -> 2000 e 1000. Offsets 3 e 2 ficam fora.
        self.assertEqual(_metric(fora, "sleep_duration").sample_count, 2)
        self.assertAlmostEqual(
            _metric(fora, "sleep_duration").baseline, (2000 + 1000) / 2)

    def test_window_days_invalido(self):
        for valor in (0, -1, True, 3.5, "7"):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    U.build_observed_wellness_view(_snap([]), today=DAY,
                                                  window_days=valor)

    def test_dia_repetido_usa_ultimo_registro(self):
        records = [_day(1, sleep_secs=27000), _day(1, sleep_secs=28000),
                   _day(0, sleep_secs=27000)]
        view = U.build_observed_wellness_view(_snap(records), today=DAY)
        self.assertEqual(_metric(view, "sleep_duration").sample_count, 2)
        self.assertAlmostEqual(_metric(view, "sleep_duration").baseline,
                               (28000 + 27000) / 2)

    def test_gap_nao_e_preenchido(self):
        # dia 9 esta fora da janela de 7; dia 0 e a referencia.
        records = [_day(9, sleep_secs=27000), _day(0, sleep_secs=25000)]
        view = U.build_observed_wellness_view(_snap(records), today=DAY)
        metric = _metric(view, "sleep_duration")
        self.assertEqual(metric.sample_count, 1)
        self.assertEqual(metric.baseline, 25000.0)


# ---------------------------------------------------------------------------
# Sanidade numerica (§20)
# ---------------------------------------------------------------------------

class InvalidValueTest(unittest.TestCase):
    """§20, §35 — bool, NaN, inf, string e negativo."""

    INVALIDOS = (True, False, float("nan"), float("inf"), float("-inf"),
                 "abc", "", "   ", None, [], {}, object())

    def test_valores_invalidos_viram_none(self):
        for valor in self.INVALIDOS:
            with self.subTest(valor=repr(valor)):
                self.assertIsNone(
                    U._wellness_number(valor, allow_zero=True))

    def test_negativo_rejeitado(self):
        self.assertIsNone(U._wellness_number(-1.0, allow_zero=True))
        self.assertIsNone(U._wellness_number("-1", allow_zero=True))

    def test_numerico_valido_aceito(self):
        for valor in (27000, 27000.5, "27000", " 27000 ", 0.0, 1e-4):
            with self.subTest(valor=valor):
                self.assertIsNotNone(U._wellness_number(valor, allow_zero=True))

    def test_zero_respeita_allow_zero(self):
        self.assertEqual(U._wellness_number(0.0, allow_zero=True), 0.0)
        self.assertIsNone(U._wellness_number(0.0, allow_zero=False))

    def test_invalido_nao_contamina_serie(self):
        records = [_day(3, stress=180), _day(2, stress=True),
                   _day(1, stress="abc"), _day(0, stress=175)]
        view = U.build_observed_wellness_view(_snap(records), today=DAY)
        metric = _metric(view, "stress")
        self.assertEqual(metric.sample_count, 2)
        self.assertEqual(metric.baseline, (180 + 175) / 2)

    def test_invalido_no_dia_de_referencia_nao_vira_current(self):
        records = [_day(1, stress=180), _day(0, stress=float("nan"))]
        view = U.build_observed_wellness_view(_snap(records), today=DAY)
        metric = _metric(view, "stress")
        self.assertIsNone(metric.current)
        self.assertEqual(metric.status, U.WELLNESS_STATUS_MISSING_CURRENT)


# ---------------------------------------------------------------------------
# Freshness (§21, §37)
# ---------------------------------------------------------------------------

class StaleTest(unittest.TestCase):
    """§21, §37 — stale e provenance: expoe valor, nunca apaga."""

    STALE = U.FreshnessView(status="stale", provider="intervals.icu",
                             synced_at="2026-09-28T06:00:00",
                             stale_after_hours=24.0, age_seconds=259200.0)

    def test_stale_expoe_current_e_baseline(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190), freshness=self.STALE),
            today=DAY)
        metric = _metric(view, "sleep_duration")
        self.assertEqual(metric.current, 24000.0)
        self.assertIsNotNone(metric.baseline)
        self.assertNotEqual(metric.sample_count, 0)

    def test_freshness_continua_visivel(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190), freshness=self.STALE),
            today=DAY)
        self.assertIsNotNone(view.freshness)
        self.assertEqual(view.freshness.status, "stale")
        self.assertEqual(view.to_dict()["freshness"]["status"], "stale")

    def test_stale_nao_muda_status_do_metrica(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190), freshness=self.STALE),
            today=DAY)
        self.assertEqual(_metric(view, "sleep_duration").status,
                         U.WELLNESS_STATUS_OBSERVED)

    def test_captured_at_e_provider_expostos(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190)), today=DAY)
        self.assertEqual(view.captured_at, "2026-10-01T06:00:00")
        self.assertEqual(view.provider, "intervals.icu")


# ---------------------------------------------------------------------------
# Determinismo temporal (§24)
# ---------------------------------------------------------------------------

class DeterminismTest(unittest.TestCase):
    """§24 — nenhum `date.today()`/`datetime.now()` escondido."""

    def test_build_aceita_today_explicito(self):
        primeiro = U.build_observed_wellness_view(
            _snap([_day(3, sleep_secs=26000)]), today=DAY)
        segundo = U.build_observed_wellness_view(
            _snap([_day(3, sleep_secs=26000)]), today=DAY)
        self.assertEqual(primeiro.to_dict(), segundo.to_dict())

    def test_target_day_vem_do_argumento(self):
        outro = date(2030, 1, 1)
        view = U.build_observed_wellness_view(_snap([]), today=outro)
        self.assertEqual(view.target_day, "2030-01-01")

    def test_funcao_nao_chama_relogio(self):
        # `co_names` olha o bytecode: o docstring cita `date.today()` para
        # documentar que ele nao e chamado, entao nao serve como evidencia.
        codigo = U.build_observed_wellness_view.__code__
        nomes = set(codigo.co_names)
        for proibido in ("today_now", "now", "time", "time_ns"):
            self.assertNotIn(proibido, nomes)
        for co in codigo.co_consts:
            if hasattr(co, "co_names"):
                self.assertNotIn("today_now", set(co.co_names))


# ---------------------------------------------------------------------------
# Offline / local only (§22, §23, §38)
# ---------------------------------------------------------------------------

class OfflineTest(unittest.TestCase):
    """§38 — 0 provider calls, 0 writes, 0 stdout."""

    def test_build_nao_chama_provider(self):
        class ProviderQuebrado:
            def __getattr__(self, nome):
                raise AssertionError(f"acesso a provider: {nome}")

        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190)), today=DAY)
        self.assertTrue(view.available)
        self.assertIsInstance(ProviderQuebrado(), ProviderQuebrado)

    def test_build_nao_imprime(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            U.build_observed_wellness_view(
                _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                       stress=190)), today=DAY)
        self.assertEqual(buffer.getvalue(), "")

    def test_build_nao_escreve_arquivo(self):
        import inspect
        for nome in ("build_observed_wellness_view", "_wellness_series",
                     "_wellness_baseline"):
            fonte = inspect.getsource(getattr(U, nome))
            for proibido in ("open(", "write", "Path(", "mkdir"):
                self.assertNotIn(proibido, fonte, f"{nome}::{proibido}")

    def test_view_e_imutavel(self):
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190)), today=DAY)
        with self.assertRaises(Exception):
            view.target_day = "2099-01-01"
        with self.assertRaises(Exception):
            view.sleep_duration.current = 0.0

    def test_to_dict_e_json_serializavel(self):
        import json
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=24000, sleep_score=61,
                                   stress=190)), today=DAY)
        json.dumps(view.to_dict())

    def test_view_le_chaves_canonicas_do_snapshot(self):
        """O snapshot persiste canonico (`snapshot.py`); o View le isso.

        O nome legado pode existir em `source` como texto de proveniencia, mas
        `field` e sempre canonico."""
        registro = {"day": "2026-10-01", "sleep_secs": 27000,
                    "sleep_score": 72, "stress": 175, "readiness": 70}
        view = U.build_observed_wellness_view(_snap([registro]), today=DAY)
        self.assertEqual(_metric(view, "sleep_duration").current, 27000.0)
        self.assertEqual(_metric(view, "sleep_score").current, 72.0)
        for metric in view.metrics:
            if metric.field is not None:
                self.assertNotIn("Secs", metric.field)
                self.assertNotIn("Score", metric.field)
            self.assertIn(metric.field,
                          {spec.field for spec in U.WELLNESS_METRIC_SPECS
                           if spec.field is not None} | {None})


# ---------------------------------------------------------------------------
# Guardrails (§27, §28, §29, §30, §31, §32, §25)
# ---------------------------------------------------------------------------

class GuardrailTest(unittest.TestCase):
    """Nenhum score composto, advisory, policy ou prescricao em HR-4."""

    def test_view_nao_expoe_score_composto(self):
        campos = set(U.ObservedWellnessView.__dataclass_fields__)
        for proibido in ("wellness_score", "overall_wellness", "score",
                         "level", "classification", "status_geral"):
            self.assertNotIn(proibido, campos)
        for proibido in ("score", "level", "action", "advice"):
            self.assertNotIn(proibido, U.WellnessMetricView.__dataclass_fields__)

    def test_view_nao_expoe_readiness_action(self):
        texto = (U.ObservedWellnessView.__doc__ or "") + (
            U.WellnessMetricView.__doc__ or "")
        codigo = U.build_observed_wellness_view.__code__.co_names
        self.assertNotIn("ReadinessAction", codigo)
        self.assertNotIn("readiness_decision", codigo)

    def test_view_nao_combina_sinais(self):
        """§28 — sem logica tipo `poor_sleep + high_stress -> yellow`."""
        codigo = U.build_observed_wellness_view.__code__.co_names
        for proibido in ("_wellness_level", "combine", "aggregate",
                         "overall", "flag", "verdict"):
            self.assertNotIn(proibido, codigo)
        # tres sinais em extremos opostos continuam sendo tres numeros.
        view = U.build_observed_wellness_view(
            _snap(_wellness_window(sleep_secs=0, sleep_score=0, stress=99999)),
            today=DAY)
        self.assertEqual(_metric(view, "sleep_duration").current, 0.0)
        self.assertEqual(_metric(view, "stress").current, 99999.0)
        dicionario = view.to_dict()
        for proibido in ("level", "verdict", "combined", "flags"):
            self.assertNotIn(proibido, dicionario)
        # status por metrica e sempre um dos tres do contrato, nada mais.
        permitidos = {U.WELLNESS_STATUS_OBSERVED,
                      U.WELLNESS_STATUS_MISSING_CURRENT,
                      U.WELLNESS_STATUS_UNSUPPORTED}
        for metric in view.metrics:
            self.assertIn(metric.status, permitidos)

    def test_nao_cria_thresholds_novos(self):
        """§26 — os limiares existentes ficam so em `readiness.py`."""
        from src import readiness
        fonte = (U.ObservedWellnessView.__doc__ or "") + (
            U.WELLNESS_METRIC_SPECS.__class__.__name__ or "")
        self.assertEqual(readiness.SLEEP_SHORT_HOURS, 6.0)
        self.assertEqual(readiness.SLEEP_BELOW_AVG_HOURS, 2.0)
        self.assertEqual(readiness.READINESS_LOW, 60)
        codigo = U.build_observed_wellness_view.__code__.co_names
        for limiar in ("SLEEP_SHORT_HOURS", "SLEEP_BELOW_AVG_HOURS",
                       "READINESS_LOW", "HRV_LOW_RATIO"):
            self.assertNotIn(limiar, codigo)

    def test_nao_funde_com_hr3(self):
        """§31 — HRV/RHR continuam só em HeartRateTrendView."""
        campos = set(U.ObservedWellnessView.__dataclass_fields__)
        self.assertNotIn("hrv", campos)
        self.assertNotIn("rhr", campos)
        self.assertNotIn("hrv_trend", campos)

    def test_nao_funde_com_pmc_ou_form(self):
        """§32 — sem form_pct/CTL ramp/PMC nesta View."""
        campos = set(U.ObservedWellnessView.__dataclass_fields__)
        for proibido in ("form_pct", "ctl_ramp", "pmc", "ctl", "atl", "tsb"):
            self.assertNotIn(proibido, campos)

    def test_nao_toca_prescription(self):
        """§30 — HR-4 nao referencia o fluxo prescritivo."""
        codigo = U.build_observed_wellness_view.__code__.co_names
        for proibido in ("recovery_workout", "suggest_swap", "apply",
                         "postpone", "cancel", "deload"):
            self.assertNotIn(proibido, codigo)


# ---------------------------------------------------------------------------
# Read-only: HR-4 nao muda readiness (§25, §29, §39)
# ---------------------------------------------------------------------------

class ReadinessUnchangedTest(unittest.TestCase):
    """§29, §39 — readiness produz exatamente o mesmo antes e depois."""

    REGISTROS = [
        {"id": "2026-09-27", "restingHR": 48, "hrv": 62.0, "hrvSDNN": 55.0,
         "sleepSecs": 6 * 3600, "readiness": 80},
        {"id": "2026-09-28", "restingHR": 48, "hrv": 60.0, "hrvSDNN": 54.0,
         "sleepSecs": 7 * 3600, "readiness": 75},
        {"id": "2026-09-29", "restingHR": 49, "hrv": 58.0, "hrvSDNN": 52.0,
         "sleepSecs": 5 * 3600, "readiness": 55},
        {"id": "2026-09-30", "restingHR": 50, "hrv": 50.0, "hrvSDNN": 48.0,
         "sleepSecs": 5 * 3600, "readiness": 40},
    ]

    def _assessment(self):
        from src import readiness
        return readiness.assess_readiness_assessment(self.REGISTROS,
                                                     today=date(2026, 9, 30))

    def test_resultado_esperado_preservado(self):
        from src.readiness_assessment import ReadinessLevel
        assessment, trace = self._assessment()
        self.assertEqual(assessment.level(), ReadinessLevel.YELLOW)
        self.assertEqual(trace.signals.get("sleep_short"), True)
        # `composite_low` mora no trace (o sinal correspondente e
        # `readiness_low`, dentro de `signals`).
        self.assertEqual(trace.signals.get("readiness_low"), True)
        self.assertEqual(trace.composite_low, True)

    def test_resultado_inalterado_apos_rodar_hr4(self):
        antes_assessment, antes_trace = self._assessment()
        antes = (antes_assessment.level(), antes_assessment.overall_readiness,
                 dict(antes_trace.signals))
        U.build_observed_wellness_view(_snap(self.REGISTROS),
                                       today=date(2026, 9, 30))
        depois_assessment, depois_trace = self._assessment()
        depois = (depois_assessment.level(),
                  depois_assessment.overall_readiness,
                  dict(depois_trace.signals))
        self.assertEqual(antes, depois)

    def test_thresholds_readiness_intactos(self):
        from src import readiness
        self.assertEqual(readiness.SLEEP_SHORT_HOURS, 6.0)
        self.assertEqual(readiness.SLEEP_BELOW_AVG_HOURS, 2.0)
        self.assertEqual(readiness.READINESS_LOW, 60)
        self.assertEqual(readiness.HRV_LOW_RATIO, 0.80)
        self.assertEqual(readiness.RHR_RISE_BPM, 3.0)

    def test_readiness_view_inalterada(self):
        import json
        from src import snapshot as snapshot_module

        def readiness_json():
            bruto = snapshot_module.TrainingSnapshot.from_dict({
                "events": [], "wellness": self.REGISTROS, "activities": [],
                "captured_at": "2026-09-30T12:00:00",
                "provider": "intervals.icu",
            })
            visao = U.build_snapshot_view(
                bruto, now=datetime(2026, 9, 30, 12, tzinfo=timezone.utc))
            return json.dumps(
                U.build_readiness_view(visao, today=date(2026, 9, 30)).to_dict(),
                sort_keys=True)

        antes = readiness_json()
        U.build_observed_wellness_view(_snap(self.REGISTROS),
                                       today=date(2026, 9, 30))
        self.assertEqual(antes, readiness_json())


if __name__ == "__main__":
    unittest.main()
