"""Prototipo #18: treinos de corrida sem medidor de potencia (%LTHR + RPE)."""
import unittest

from src.plan_run import (RUN_FOCUS, event_payload_run, run_text, run_workout)


class RunWorkoutTest(unittest.TestCase):
    def test_focuses_cover_o_mapa_do_ciclismo(self):
        """Os 5 focos do motor (zone2..vo2max) tem preset de corrida."""
        for focus in ("zone2", "endurance", "sweetspot", "threshold", "vo2max"):
            self.assertIn(focus, RUN_FOCUS)

    def test_workout_carimba_sport_run_e_hr_mode(self):
        w = run_workout("threshold", r_lthr=168)
        self.assertEqual(w["params"]["sport"], "run")
        self.assertTrue(w["params"]["hr_mode"])
        self.assertGreater(w["planned_duration"], 0)

    def test_texto_fc_nao_cita_potencia(self):
        t = run_text(run_workout("sweetspot", r_lthr=168))
        self.assertIn("LTHR", t)
        self.assertIn("RPE", t)
        self.assertNotIn("FTP", t)
        self.assertNotIn("watt", t.lower())
        self.assertNotIn("%FTP", t)

    def test_texto_threshold_lista_repeticao(self):
        t = run_text(run_workout("threshold", r_lthr=170))
        series = [ln for ln in t.splitlines()
                  if ln.startswith("- Intervalos Limiar:")]
        self.assertEqual(len(series), 4, "4x cada serie deve ser listada")
        self.assertIn("RPE 9", t)

    def test_dica_de_ritmo_so_com_rftp(self):
        w = run_workout("threshold", r_lthr=170)
        self.assertNotIn("/km", run_text(w))
        self.assertIn("/km", run_text(w, rftp_pace="4:30"))
        self.assertIn("4:30/km", run_text(w, rftp_pace="4:30"),
                      "ritmo-alvo vem do rFTP")

    def test_ritmo_foco_muda_a_dica(self):
        """Tempo corre ~8% mais lento que o rFTP; VO2 ~6% mais rapido."""
        tempo = run_text(run_workout("sweetspot"), rftp_pace="4:30")
        vo2 = run_text(run_workout("vo2max"), rftp_pace="4:30")
        self.assertIn("4:52/km", tempo)
        self.assertIn("4:14/km", vo2)

    def test_evento_run_vai_heart_rate(self):
        w = run_workout("sweetspot", r_lthr=168)
        payload = event_payload_run(w)
        self.assertEqual(payload["type"], "Run")
        self.assertEqual(payload["target"], "HEART_RATE")
        self.assertIn("LTHR", payload["description"])

    def test_fartlek_controla_por_rpe_nao_fc(self):
        """Fartlek: surto de 1' nao alcanca zona de FC — prescreve esforco."""
        w = run_workout("fartlek")
        self.assertEqual(w["params"]["target"], "rpe")
        t = run_text(w, rftp_pace="4:30")
        self.assertIn("ritmo 5-10K", t)
        self.assertIn("RPE 9", t)
        self.assertNotIn("/km", t)

    def test_target_pace_usa_ritmo_como_alvo_primario(self):
        w = run_workout("threshold", r_lthr=170, target="pace")
        t = run_text(w, rftp_pace="4:30")
        self.assertIn("ritmo ~4:30/km", t)
        self.assertIn("LTHR", t, "FC vira ancora da serie")

    def test_pace_sem_rftp_cai_para_hr(self):
        """Sem rFTP configurado, alvo 'pace' nao tem ritmo p/ prescrever."""
        w = run_workout("threshold", r_lthr=170, target="pace")
        t = run_text(w)
        self.assertIn("LTHR", t)
        self.assertNotIn("/km", t)


if __name__ == "__main__":
    unittest.main()