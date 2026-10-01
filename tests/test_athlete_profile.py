import unittest

from src.athlete_profile import AthletePhysiologicalProfile, FtpConfidence, FtpSource


class AthleteProfileTest(unittest.TestCase):
    def test_atleta_apenas_com_ftp_e_preservado(self):
        profile = AthletePhysiologicalProfile(ftp=250, ftp_source=FtpSource.USER,
                                              ftp_confidence=FtpConfidence.HIGH)
        self.assertEqual(profile.ftp, 250)
        self.assertIsNone(profile.critical_power)
        self.assertIsNone(profile.w_prime)
        self.assertIsNone(profile.vo2max)

    def test_fontes_e_confiancas_sao_explicitas(self):
        self.assertEqual({source.value for source in FtpSource},
                         {"user", "ftp20", "ftp60", "ramp", "cp_estimate", "performance_estimate"})
        self.assertEqual({confidence.value for confidence in FtpConfidence},
                         {"low", "medium", "high"})


if __name__ == "__main__":
    unittest.main()
