import unittest

from src.critical_power import (CPConfidence, CPProtocol, CriticalPowerProfile,
                                estimate_cp, estimate_w_prime, work_above_cp,
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


if __name__ == "__main__":
    unittest.main()
