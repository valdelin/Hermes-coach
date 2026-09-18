import unittest
from datetime import date

from src.impulse_response import ImpulseResponseEngine, daily_tss_series


class CalculateTssTest(unittest.TestCase):
    def test_exemplo_60min_95pct(self):
        # Exemplo do doc de arquitetura: 60 min a 95% do limiar (threshold=1.0)
        engine = ImpulseResponseEngine()
        self.assertAlmostEqual(engine.calculate_tss(3600, 0.95, 1.0), 90.25)

    def test_potencia_em_watts(self):
        engine = ImpulseResponseEngine()
        # 1h a 160W com FTP 182W -> IF = 160/182 = 0.8791
        # TSS = IF^2 * 1h * 100 = 77.29 (round de 77.2853)
        self.assertAlmostEqual(engine.calculate_tss(3600, 160, 182), 77.29, places=2)

    def test_exemplo_do_plano(self):
        # 20 min a 60% do FTP (recuperacao de ontem no plan.json)
        engine = ImpulseResponseEngine()
        self.assertAlmostEqual(engine.calculate_tss(1200, 0.6, 1.0), 12.0)

    def test_threshold_invalido(self):
        engine = ImpulseResponseEngine()
        self.assertEqual(engine.calculate_tss(3600, 200, 0), 0.0)
        self.assertEqual(engine.calculate_tss(3600, 200, -1), 0.0)

    def test_intensidade_zero(self):
        engine = ImpulseResponseEngine()
        self.assertEqual(engine.calculate_tss(3600, 0, 200), 0.0)


class ComputeMetricsTest(unittest.TestCase):
    def test_historico_vazio(self):
        m = ImpulseResponseEngine().compute_metrics([])
        self.assertEqual(m["ctl_fitness"], 0.0)
        self.assertEqual(m["atl_fatigue"], 0.0)
        self.assertEqual(m["tsb_form"], 0.0)

    def test_um_dia(self):
        engine = ImpulseResponseEngine()
        m = engine.compute_metrics([42])
        # ctl = 42*(1-exp(-1/42)) ~= 0.99; atl = 42*(1-exp(-1/7)) ~= 5.59
        self.assertAlmostEqual(m["ctl_fitness"], 1.0, places=1)
        self.assertAlmostEqual(m["atl_fatigue"], 5.6, places=1)
        self.assertAlmostEqual(m["tsb_form"], -4.6, places=1)

    def test_serie_constante_converge(self):
        engine = ImpulseResponseEngine()
        m = engine.compute_metrics([100] * 500)
        self.assertAlmostEqual(m["ctl_fitness"], 100.0, delta=0.5)
        self.assertAlmostEqual(m["atl_fatigue"], 100.0, delta=0.5)
        self.assertAlmostEqual(m["tsb_form"], 0.0, delta=1.0)

    def test_tsb_eh_ctl_menos_atl(self):
        # Exemplo do doc de arquitetura (14 dias)
        series = [45, 60, 0, 80, 50, 90, 0, 40, 70, 0, 85, 60, 100, 0]
        m = ImpulseResponseEngine().compute_metrics(series)
        self.assertAlmostEqual(m["tsb_form"], m["ctl_fitness"] - m["atl_fatigue"],
                               delta=0.2)
        # historico recente de treino -> ATL > CTL (TSB negativo)
        self.assertLess(m["tsb_form"], 0)

    def test_constantes_personalizadas(self):
        engine = ImpulseResponseEngine(ctl_time_constant=10, atl_time_constant=3)
        m = engine.compute_metrics([100] * 200)
        self.assertAlmostEqual(m["ctl_fitness"], 100.0, delta=0.5)
        self.assertAlmostEqual(m["atl_fatigue"], 100.0, delta=0.5)

    def test_valores_iniciais_projecao(self):
        # Partindo de um estado atual, aplicar carga futura atualiza o TSB
        engine = ImpulseResponseEngine()
        m = engine.compute_metrics([40, 40, 40], initial_ctl=17.4, initial_atl=16.5)
        self.assertGreater(m["ctl_fitness"], 17.4)
        self.assertGreater(m["atl_fatigue"], 16.5)
        self.assertNotAlmostEqual(m["tsb_form"], 17.4 - 16.5, places=1)


class DailyTssSeriesTest(unittest.TestCase):
    def test_agrega_por_dia_e_ordena(self):
        events = [
            {"start_date_local": "2026-09-01T07:00:00", "icu_training_load": "40"},
            {"start_date_local": "2026-09-01T18:00:00", "tss": "20"},
            {"start_date_local": "2026-09-03T07:00:00", "tss": "50"},
            {"start_date_local": "2026-09-02T07:00:00", "icu_training_load": "30"},
            {"no-load": True},
        ]
        series = daily_tss_series(events, window_days=60, today=date(2026, 9, 10))
        self.assertEqual(series, [60.0, 30.0, 50.0])

    def test_respeita_janela(self):
        events = [
            {"start_date_local": "2026-06-01T07:00:00", "tss": "99"},  # fora (30d)
            {"start_date_local": "2026-09-01T07:00:00", "tss": "50"},
            {"start_date_local": "2026-09-12T07:00:00", "tss": "70"},  # futuro/hoje+2
        ]
        series = daily_tss_series(events, window_days=30, today=date(2026, 9, 10))
        self.assertEqual(series, [50.0])

    def test_desconsidera_sem_carga(self):
        events = [
            {"start_date_local": "2026-09-01T07:00:00"},
            {"start_date_local": "2026-09-02T07:00:00", "icu_training_load": None},
            {"day": "2026-09-03", "tss": "0"},
        ]
        series = daily_tss_series(events, window_days=60, today=date(2026, 9, 10))
        self.assertEqual(series, [])


if __name__ == "__main__":
    unittest.main()