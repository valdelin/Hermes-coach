import unittest

from src.ftp_estimation import (analyze_ride, best_effort, clean_power,
                                ftp_from_best20, BEST_WINDOW_SEC)

ZERO = 0.0


def steady_ride(window_watts, window_min, warmup_min=5, cooldown_min=5,
                warmup_watts=120, cooldown_watts=120, sample_sec=2.0):
    """Stream sintetico: aquecimento + bloco estavel + volta ao ritmo.

    Amostrado a cada `sample_sec` segundo (padrao 2s). Sirva para construir
    cenarios determinísticos de teste sem depender da data corrente."""
    samples = []
    warmup_n = int(warmup_min * 60 / sample_sec)
    block_n = int(window_min * 60 / sample_sec)
    cool_n = int(cooldown_min * 60 / sample_sec)
    samples.extend([warmup_watts] * warmup_n)
    samples.extend([window_watts] * block_n)
    samples.extend([cooldown_watts] * cool_n)
    return samples


class BestEffortTest(unittest.TestCase):
    def test_melhor_janela_pega_o_bloco_estavel(self):
        power = steady_ride(200, 20)
        best, start, end = best_effort(power, BEST_WINDOW_SEC, sample_sec=2.0)
        self.assertAlmostEqual(best, 200.0, places=3)
        window = power[start:end]
        self.assertEqual(window, [200.0] * len(window))

    def test_stream_curto_devolve_none(self):
        # 5 aquec + 9 bloco + 5 volta = 19 min total < janela de 20 min
        power = steady_ride(200, 9)
        best, _, _ = best_effort(power, BEST_WINDOW_SEC, sample_sec=2.0)
        self.assertIsNone(best)

    def test_vazio_devolve_none(self):
        best, _, _ = best_effort([], BEST_WINDOW_SEC)
        self.assertIsNone(best)


class CleanPowerTest(unittest.TestCase):
    def test_clipa_pico_espurio(self):
        power = [150.0] * 100
        spike_at = 50
        power[spike_at] = 5000.0
        cleaned, removed = clean_power(power)
        self.assertEqual(removed, 1)
        self.assertEqual(cleaned[spike_at], 150.0 * 2.5)

    def test_mediana_zero_nao_limpa(self):
        power = [0.0, 0.0, 500.0, 0.0]
        cleaned, removed = clean_power(power)
        self.assertEqual(removed, 0)
        self.assertEqual(cleaned, power)

    def test_anomalies_da_plataforma_clipam(self):
        power = [150.0] * 10
        power[3] = 600.0
        cleaned, removed = clean_power(power, anomalies=[False, False, False, True] + [False] * 6)
        self.assertEqual(removed, 1)
        self.assertEqual(cleaned[3], 150.0 * 2.5)


class AnalyzeRideTest(unittest.TestCase):
    def test_esforco_estavel_sustenta_ftp(self):
        current_ftp = 182
        power = steady_ride(200, 20)
        est = analyze_ride(power, current_ftp, sample_sec=2.0)
        self.assertTrue(est.quality_ok)
        self.assertTrue(est.suggests_new)
        self.assertEqual(est.proposed_ftp, 190)  # round(0.95 x 200)
        self.assertAlmostEqual(est.diff_ratio, 190 / 182, places=4)
        self.assertEqual(est.reason, "")

    def test_puncheiro_nao_sustenta(self):
        current_ftp = 182
        power = steady_ride(200, 20, sample_sec=2.0)
        for i in range(len(power)):
            if i % 2 == 0:
                power[i] = 400.0
            else:
                power[i] = 100.0
        est = analyze_ride(power, current_ftp, sample_sec=2.0)
        self.assertFalse(est.quality_ok)
        self.assertFalse(est.suggests_new)
        self.assertTrue(est.cv > 0.15)

    def test_apagoes_na_janela_reprovam(self):
        current_ftp = 182
        power = steady_ride(200, 20, sample_sec=2.0)
        # 4 min de costa no meio do bloco estavel
        mid = len(power) // 2
        coast_n = int(4 * 60 / 2.0)
        for i in range(mid, mid + coast_n):
            power[i] = 10.0
        est = analyze_ride(power, current_ftp, sample_sec=2.0)
        self.assertFalse(est.quality_ok)
        self.assertFalse(est.suggests_new)
        self.assertTrue(est.min_ratio < 0.80)

    def test_stream_curto_reprovado(self):
        current_ftp = 182
        power = steady_ride(200, 9)
        est = analyze_ride(power, current_ftp, sample_sec=2.0)
        self.assertFalse(est.quality_ok)
        self.assertFalse(est.suggests_new)
        self.assertIn("curto", est.reason)

    def test_sem_dados_reprovado(self):
        est = analyze_ride([], 182, sample_sec=2.0)
        self.assertFalse(est.quality_ok)
        self.assertFalse(est.suggests_new)
        self.assertIn("sem dados", est.reason)

    def test_diff_abaixo_de_3pc_nao_propoe(self):
        current_ftp = 182
        power = steady_ride(190, 20)  # 0.95 x 190 = 180 -> diff ~0,99
        est = analyze_ride(power, current_ftp, sample_sec=2.0)
        self.assertTrue(est.quality_ok)
        self.assertFalse(est.suggests_new)
        self.assertEqual(est.proposed_ftp, 180)

    def test_diff_acima_de_30pc_trata_como_anomalia(self):
        current_ftp = 182
        power = steady_ride(420, 20)  # 0.95 x 420 = 399 -> diff 2,19
        est = analyze_ride(power, current_ftp, sample_sec=2.0)
        self.assertTrue(est.quality_ok)
        self.assertFalse(est.suggests_new)
        self.assertIn("anomalia", est.reason)

    def test_spike_falso_nao_infla_estimativa(self):
        current_ftp = 182
        power = steady_ride(200, 20, sample_sec=2.0)
        power[len(power) // 2] = 8000.0
        est = analyze_ride(power, current_ftp, sample_sec=2.0)
        self.assertEqual(est.cleaned_outliers, 1)
        self.assertEqual(est.proposed_ftp, 190)  # mesmo resultado do limpo
        self.assertTrue(est.suggests_new)

    def test_deterministico_mesmo_stream_mesmo_resultado(self):
        power = steady_ride(200, 20)
        a = analyze_ride(power, 182, sample_sec=2.0)
        b = analyze_ride(power, 182, sample_sec=2.0)
        self.assertEqual(a, b)


class FtpFromBest20Test(unittest.TestCase):
    def test_conversao_classica(self):
        self.assertEqual(ftp_from_best20(200), 190)
        self.assertEqual(ftp_from_best20(160), 152)
        self.assertEqual(ftp_from_best20(0), 0)


if __name__ == "__main__":
    unittest.main()