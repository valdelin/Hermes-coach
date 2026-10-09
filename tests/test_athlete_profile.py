import unittest

from src.athlete_profile import (AthletePhysiologicalProfile, FtpConfidence,
                                 FtpSource, build_athlete_profile,
                                 ftp_source_from_reference)
from src.ftp_history import FtpReferenceSource
from src.plan import DEFAULT_FTP


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
                         {"user", "ftp20", "ftp60", "ramp", "cp_estimate",
                          "performance_estimate", "confirmed"})
        self.assertEqual({confidence.value for confidence in FtpConfidence},
                         {"low", "medium", "high"})

    def test_builder_sem_dados_preserva_ausencia_em_vez_de_default_ou_estimativa(self):
        profile = build_athlete_profile()
        self.assertIsNone(profile.ftp)
        self.assertIsNone(profile.ftp_source)
        self.assertIsNone(profile.ftp_confidence)
        self.assertIsNone(profile.threshold_hr)
        self.assertIsNone(profile.resting_hr)
        self.assertEqual(profile.training_days, ())
        self.assertIsNone(profile.weekly_training_hours)
        self.assertIsNone(profile.preferred_long_day)
        self.assertIsNone(profile.vo2max)
        self.assertIsNone(profile.critical_power)
        self.assertIsNone(profile.w_prime)
        self.assertIsNone(profile.max_hr)
        self.assertIsNone(profile.training_age)
        self.assertIsNone(profile.hrv_baseline)
        self.assertEqual(profile.cp_test_dates, ())

    def test_ftp_canonico_tem_origem_honesta_e_sem_confianca_inventada(self):
        profile = build_athlete_profile(
            canonical_ftp=182, canonical_source=FtpReferenceSource.USER_ENTERED)
        self.assertEqual(profile.ftp, 182)
        self.assertIs(profile.ftp_source, FtpSource.USER)
        self.assertIsNone(profile.ftp_confidence)

    def test_ftp_canonico_sem_origem_declarada_nao_inventa_autoria(self):
        profile = build_athlete_profile(canonical_ftp=182)
        self.assertEqual(profile.ftp, 182)
        self.assertIs(profile.ftp_source, FtpSource.CONFIRMED)
        self.assertIsNone(profile.ftp_confidence)

    def test_origem_canonica_e_mapeada_sem_confundir_protocolo_com_fonte(self):
        casos = {
            FtpReferenceSource.USER_ENTERED: FtpSource.USER,
            FtpReferenceSource.HERMES_TEST: FtpSource.CONFIRMED,
            FtpReferenceSource.ZWIFT_TEST: FtpSource.CONFIRMED,
            FtpReferenceSource.OTHER_PLATFORM_TEST: FtpSource.CONFIRMED,
            FtpReferenceSource.COACH_DEFINED: FtpSource.CONFIRMED,
        }
        for source, expected in casos.items():
            with self.subTest(source=source):
                profile = build_athlete_profile(
                    canonical_ftp=250, canonical_source=source)
                self.assertIs(profile.ftp_source, expected)
                self.assertIs(ftp_source_from_reference(source), expected)
                self.assertIsNone(profile.ftp_confidence)

    def test_origem_futura_desconhecida_cai_em_confirmado_sem_excecao(self):
        self.assertIs(ftp_source_from_reference("origem_futura"),
                      FtpSource.CONFIRMED)
        self.assertIs(ftp_source_from_reference(
            FtpReferenceSource.ZWIFT_TEST), FtpSource.CONFIRMED)

    def test_default_ftp_operacional_nunca_vira_medicao_fisiologica(self):
        self.assertEqual(DEFAULT_FTP, 182)
        profile = build_athlete_profile(canonical_ftp=None)
        self.assertIsNone(profile.ftp)
        self.assertIsNone(profile.ftp_source)

    def test_contexto_configurado_e_rhr_observado_sao_mapeados(self):
        profile = build_athlete_profile(
            canonical_ftp=182, threshold_hr=172, weekly_training_hours=6.5,
            training_days=(0, 2, 4), preferred_long_day=6, resting_hr=48)
        self.assertEqual(profile.threshold_hr, 172)
        self.assertEqual(profile.weekly_training_hours, 6.5)
        self.assertEqual(profile.training_days, (0, 2, 4))
        self.assertEqual(profile.preferred_long_day, 6)
        self.assertEqual(profile.resting_hr, 48)

    def test_builder_e_deterministico_e_mantem_campos_indisponiveis_none(self):
        kwargs = dict(canonical_ftp=182, threshold_hr=172,
                      weekly_training_hours=6.5, training_days=(0, 2, 4),
                      preferred_long_day=6, resting_hr=48)
        self.assertEqual(build_athlete_profile(**kwargs),
                         build_athlete_profile(**kwargs))
        profile = build_athlete_profile(**kwargs)
        self.assertIsNone(profile.vo2max)
        self.assertIsNone(profile.critical_power)
        self.assertIsNone(profile.w_prime)
        self.assertIsNone(profile.max_hr)
        self.assertIsNone(profile.training_age)


if __name__ == "__main__":
    unittest.main()
