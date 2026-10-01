import unittest
from dataclasses import FrozenInstanceError

from src.coach import (FOCUS_ENDURANCE, FOCUS_SWEETSPOT, FOCUS_THRESHOLD,
                       FOCUS_ZONE2_ENDURANCE, FOCUS_ZONE4_LIMIAR, ZONE_BANDS)
from src.zone_intent import (ENDURANCE, SWEET_SPOT, THRESHOLD, AmbiguousIntensity,
                             DoseShape, ZoneLever, aliases,
                             band_overlap, classify, describes_intent,
                             describes_dose, distinguishes, families_at)

FAMILIES = (ENDURANCE, SWEET_SPOT, THRESHOLD)


class ZoneIntentTest(unittest.TestCase):
    def test_cada_familia_tem_intencao_e_dose_distintas(self):
        intents = [profile.intent for profile in FAMILIES]
        doses = [profile.dose for profile in FAMILIES]
        self.assertEqual(len(set(intents)), len(FAMILIES))
        self.assertEqual(len(set(doses)), len(FAMILIES))

    def test_intencao_e_dose_dependem_do_foco_e_nao_da_potencia(self):
        # Mesma potencia, familias distintas: a intencao declarada decide.
        for fraction in (0.91, 0.94, 0.97):
            self.assertEqual(len(families_at(fraction)), 2)
            for profile in (SWEET_SPOT, THRESHOLD):
                self.assertTrue(describes_intent(profile.focus, fraction))
                self.assertTrue(describes_dose(profile.focus, fraction))
        self.assertNotEqual(describes_intent(SWEET_SPOT.focus, 0.94),
                            describes_intent(THRESHOLD.focus, 0.94))
        self.assertNotEqual(describes_dose(SWEET_SPOT.focus, 0.94),
                            describes_dose(THRESHOLD.focus, 0.94))

    def test_classify_recusa_adivinhar_na_sobreposicao(self):
        for fraction in (0.91, 0.94, 0.97):
            with self.assertRaises(AmbiguousIntensity):
                classify(fraction)
        self.assertEqual(classify(0.65).focus, ENDURANCE.focus)

    def test_sobreposicao_sweetspot_threshold_e_real(self):
        self.assertEqual(band_overlap(SWEET_SPOT.focus, THRESHOLD.focus),
                         (0.91, 0.97))
        self.assertIsNone(band_overlap(ENDURANCE.focus, SWEET_SPOT.focus))

    def test_z2_e_continuo_sem_intervalos_artificiais(self):
        self.assertIs(ENDURANCE.dose_shape, DoseShape.CONTINUOUS)
        self.assertNotIn(ZoneLever.REPETITIONS, ENDURANCE.levers)
        self.assertIn("intervalos artificiais", ENDURANCE.not_claim)

    def test_sweetspot_progride_em_volume_e_duracao(self):
        self.assertEqual(set(SWEET_SPOT.levers),
                         {ZoneLever.DURATION, ZoneLever.TOTAL_VOLUME})
        self.assertIn("nao zona fisiologica universal", SWEET_SPOT.not_claim)

    def test_threshold_progride_em_duracao_repeticoes_e_recuperacao(self):
        self.assertEqual(set(THRESHOLD.levers),
                         {ZoneLever.DURATION, ZoneLever.REPETITIONS,
                          ZoneLever.RECOVERY})
        self.assertIn("95% FTP = MLSS", THRESHOLD.not_claim)

    def test_ressalvas_proibem_exatamente_as_equivalencias_do_prompt(self):
        self.assertIn("limiar fisiologico", SWEET_SPOT.not_claim)
        self.assertIn("95% FTP = MLSS", THRESHOLD.not_claim)
        for profile in FAMILIES:
            self.assertTrue(profile.not_claim.strip())
            self.assertTrue(profile.criterion.strip())

    def test_bandas_vem_do_invariante_e_nao_sao_redefinidas(self):
        for profile in FAMILIES:
            self.assertEqual(profile.band, ZONE_BANDS[profile.focus])
        self.assertEqual(ENDURANCE.band, (0.56, 0.75))
        self.assertEqual(SWEET_SPOT.band, (0.84, 0.97))
        self.assertEqual(THRESHOLD.band, (0.91, 1.05))

    def test_distinguishes_reporta_os_eixos_de_divergencia(self):
        divergent = distinguishes(SWEET_SPOT.focus, THRESHOLD.focus)
        self.assertEqual(set(divergent),
                         {"intent", "dose", "levers", "not_claim"})
        endurance_vs_sweetspot = distinguishes(ENDURANCE.focus, SWEET_SPOT.focus)
        self.assertIn("dose_shape", endurance_vs_sweetspot)

    def test_aliases_legados_resolvem_para_o_mesmo_perfil(self):
        resolved = aliases()
        self.assertEqual(set(resolved[ENDURANCE.focus]),
                         {FOCUS_ZONE2_ENDURANCE, FOCUS_ENDURANCE})
        self.assertIn(SWEET_SPOT.focus, resolved)
        self.assertIn(THRESHOLD.focus, resolved)
        self.assertEqual(len(resolved), len(FAMILIES))

    def test_foco_sem_perfil_falha_explicitamente(self):
        with self.assertRaises(KeyError):
            describes_intent("z7_sprint", 1.10)

    def test_potencia_fora_de_qualquer_familia_falha(self):
        self.assertEqual(families_at(0.30), ())
        with self.assertRaises(KeyError):
            classify(0.30)

    def test_perfil_e_imutavel(self):
        with self.assertRaises(FrozenInstanceError):
            SWEET_SPOT.intent = "outra coisa"


if __name__ == "__main__":
    unittest.main()
