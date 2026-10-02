import unittest

from src.critical_power import (CPConfidence, CPProtocol, CriticalPowerProfile,
                                estimate_cp, estimate_cp_profile, estimate_w_prime, work_above_cp,
                                w_prime_balance, w_prime_reconstitution)


class CriticalPowerTest(unittest.TestCase):
    # Esforços sinteticos consistentes com CP 300 W e W' 15 000 J.
    EFFORTS = ((60, 550.0), (180, 383.3), (300, 350.0), (600, 325.0))

    def test_estimativas_exigem_dados_suficientes(self):
        self.assertIsNone(estimate_cp([]))
        self.assertIsNone(estimate_cp([(300, 350.0)]))
        self.assertIsNone(estimate_w_prime([(300, 350.0)]))

    def test_cp_e_w_prime_proximos_do_real(self):
        self.assertAlmostEqual(estimate_cp(self.EFFORTS), 300, delta=5)
        self.assertAlmostEqual(estimate_w_prime(self.EFFORTS), 15000, delta=300)

    def test_perfil_completo_expoe_protocolo_e_confianca(self):
        profile = CriticalPowerProfile(300, 15000, CPProtocol.MULTI_BROKEN,
                                       CPConfidence.HIGH, ("2026-09-01",))
        self.assertTrue(profile.known)
        self.assertEqual(profile.protocol, CPProtocol.MULTI_BROKEN)
        self.assertEqual(profile.test_dates, ("2026-09-01",))

    def test_perfil_sem_marcadores_nao_e_conhecido(self):
        self.assertFalse(CriticalPowerProfile().known)

    def test_trabalho_acima_de_cp_limita_pelo_w_prime(self):
        self.assertEqual(work_above_cp(60, 300, 300, 15000), 0.0)
        self.assertAlmostEqual(work_above_cp(60, 550, 300, 15000), 15000)

    def test_saldo_de_w_prime_nao_fica_negativo(self):
        profile = CriticalPowerProfile(300, 15000)
        self.assertEqual(w_prime_balance(profile, 20000), 0.0)
        self.assertIsNone(w_prime_balance(CriticalPowerProfile(), 100))

    def test_reconstituicao_recupera_e_para_em_zero(self):
        self.assertAlmostEqual(w_prime_reconstitution(1000, 60), 994.0)
        self.assertEqual(w_prime_reconstitution(0, 60), 0.0)
        self.assertEqual(w_prime_reconstitution(1000, 0), 0.0)


class CriticalPowerProfileMetadataTest(unittest.TestCase):
    PERFECT = tuple((t, 300 + 15_000 / t) for t in (60, 180, 300, 600))

    def test_perfil_calcula_cp_w_prime_e_fit_perfeito(self):
        profile = estimate_cp_profile(self.PERFECT, protocol=CPProtocol.STEP,
                                      source="lab_test",
                                      test_dates=("2026-10-02",))
        self.assertAlmostEqual(profile.critical_power, 300.0)
        self.assertAlmostEqual(profile.w_prime, 15_000.0)
        self.assertAlmostEqual(profile.fit_r2, 1.0)
        self.assertAlmostEqual(profile.fit_rmse, 0.0)
        self.assertEqual(profile.source, "lab_test")
        self.assertEqual(profile.model, "linear_1_over_t")
        self.assertEqual(profile.test_dates, ("2026-10-02",))

    def test_fit_com_ruido_registra_erro_em_watts(self):
        noisy = self.PERFECT[:-1] + ((600, 330.0),)
        profile = estimate_cp_profile(noisy)
        self.assertLess(profile.fit_r2, 1.0)
        self.assertGreater(profile.fit_rmse, 0.0)

    def test_dois_pontos_perfeitos_recebem_low(self):
        profile = estimate_cp_profile(self.PERFECT[:2])
        self.assertTrue(profile.known)
        self.assertAlmostEqual(profile.fit_r2, 1.0)
        self.assertAlmostEqual(profile.fit_rmse, 0.0)
        self.assertEqual(profile.cp_confidence, CPConfidence.LOW)
        self.assertEqual(profile.w_prime_confidence, CPConfidence.LOW)

    def test_metadados_de_duracao_sao_objetivos(self):
        profile = estimate_cp_profile(self.PERFECT)
        self.assertEqual(profile.n_efforts, 4)
        self.assertEqual(profile.min_duration_sec, 60)
        self.assertEqual(profile.max_duration_sec, 600)
        self.assertEqual(profile.duration_span_sec, 540)

    def test_campos_de_confianca_sao_estruturalmente_independentes(self):
        profile = CriticalPowerProfile(
            critical_power=300,
            w_prime=15_000,
            cp_confidence=CPConfidence.MEDIUM,
            w_prime_confidence=CPConfidence.LOW,
        )
        self.assertEqual(profile.cp_confidence, CPConfidence.MEDIUM)
        self.assertEqual(profile.w_prime_confidence, CPConfidence.LOW)

    def test_perfil_antigo_mantem_defaults_novos(self):
        profile = CriticalPowerProfile(300, 15_000, CPProtocol.STEP,
                                       CPConfidence.HIGH, ("2026-09-01",))
        self.assertTrue(profile.known)
        self.assertIsNone(profile.source)
        self.assertIsNone(profile.fit_r2)
        self.assertIsNone(profile.cp_confidence)
        self.assertIsNone(profile.w_prime_confidence)
        self.assertIsNone(profile.last_updated)


if __name__ == "__main__":
    unittest.main()
