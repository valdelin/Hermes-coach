"""Testes da camada de deteccao de candidatos a FTP (#6). Sem rede: todos os
insumos sao locais (eventos/streams sinteticos)."""
import unittest

from src import ftp_scan
from src.ftp_scan import (best_candidate, can_estimate_ftp, extra_activities,
                          estimate_ride, ride_settings, sample_rate,
                          sanitize_ride_payload, skip_reason)


def steady_power(watts, minutes=50, sample_sec=1.0):
    """Stream de watts estavel por `minutes` minutos."""
    return [watts] * int(minutes * 60 / sample_sec)


def sample_activity(**over):
    """Detalhe de atividade sintetica (padroes: VirtualRide UPLOAD com watts)."""
    base = {
        "source": "UPLOAD", "type": "VirtualRide",
        "moving_time": 50 * 60, "device_watts": True,
        "stream_types": ["time", "watts"],
        "icu_weighted_avg_watts": 190, "icu_pm_ftp": 187,
    }
    base.update(over)
    return base


class ExtraActivitiesTest(unittest.TestCase):
    def test_so_eventos_pareados_fora_do_plano(self):
        events = [
            {"external_id": "hermes-plan-2026-09-18",
             "paired_activity_id": "i1", "start_date_local": "2026-09-18T19:00:00",
             "name": "Treino do plano"},
            {"external_id": "zwift-abc", "paired_activity_id": "i2",
             "start_date_local": "2026-09-20T10:00:00", "name": "Pedal solto"},
            {"external_id": "hermes-plan-2026-09-21", "paired_activity_id": None,
             "start_date_local": "2026-09-21T18:00:00", "name": "Sem atividade"},
        ]
        extras = extra_activities(events)
        self.assertEqual(len(extras), 1)
        self.assertEqual(extras[0]["activity_id"], "i2")
        self.assertEqual(extras[0]["day"], "2026-09-20")
        self.assertEqual(extras[0]["name"], "Pedal solto")

    def test_sem_pareados_devolve_vazio(self):
        self.assertEqual(extra_activities([]), [])
        self.assertEqual(
            extra_activities([{"external_id": "hermes-plan-x",
                               "paired_activity_id": None}]),
            [])


class CanEstimateFtpTest(unittest.TestCase):
    FTP = 182

    def test_ride_valida_passa(self):
        self.assertTrue(can_estimate_ftp(sample_activity(), self.FTP))
        self.assertIsNone(skip_reason(sample_activity(), self.FTP))

    def test_manual_reprovado(self):
        a = sample_activity(source="MANUAL")
        self.assertFalse(can_estimate_ftp(a, self.FTP))
        self.assertIn("manual", skip_reason(a, self.FTP))

    def test_curta_reprovada(self):
        a = sample_activity(moving_time=30 * 60)
        self.assertFalse(can_estimate_ftp(a, self.FTP))
        self.assertIn("curta", skip_reason(a, self.FTP))

    def test_sem_potencia_reprovada(self):
        a = sample_activity(stream_types=["time"], device_watts=False,
                            icu_weighted_avg_watts=None)
        self.assertFalse(can_estimate_ftp(a, self.FTP))
        self.assertIn("sem potencia", skip_reason(a, self.FTP))

    def test_intensidade_baixa_reprovada(self):
        a = sample_activity(icu_weighted_avg_watts=100)
        self.assertFalse(can_estimate_ftp(a, self.FTP))
        self.assertIn("intensidade baixa", skip_reason(a, self.FTP))


class SampleRateTest(unittest.TestCase):
    def test_stream_de_1s(self):
        self.assertEqual(sample_rate(list(range(100))), 1.0)

    def test_stream_de_2s(self):
        time = [i * 2 for i in range(100)]
        self.assertEqual(sample_rate(time), 2.0)

    def test_sem_tempo_assume_1s(self):
        self.assertEqual(sample_rate([]), 1.0)

    def test_intervalos_irregulares_usam_mediana(self):
        time = [0, 1, 2, 3, 30, 31, 32]  # 1s com um gap de 27s
        self.assertEqual(sample_rate(time), 1.0)


class EstimateRideTest(unittest.TestCase):
    def test_esforco_estavel_sustenta_ftp(self):
        power = steady_power(200, 50)
        rec = estimate_ride("i1", "2026-09-18", "Pedal", sample_activity(),
                            power, list(range(len(power))), 182)
        self.assertTrue(rec["quality_ok"])
        self.assertTrue(rec["suggests_new"])
        self.assertEqual(rec["proposed_ftp"], 190)  # round(0.95 x 200)
        self.assertEqual(rec["intervals_ftp"], 187)
        self.assertFalse(rec["applied"])

    def test_sem_stream_reprovado(self):
        rec = estimate_ride("i1", "2026-09-18", "Pedal", sample_activity(),
                            [], [], 182)
        self.assertFalse(rec["quality_ok"])
        self.assertFalse(rec["suggests_new"])
        self.assertIn("sem dados", rec["reason"])


class BestCandidateTest(unittest.TestCase):
    def test_mais_recente_ganha(self):
        cands = [
            {"day": "2026-09-10", "proposed_ftp": 195},
            {"day": "2026-09-18", "proposed_ftp": 190},
        ]
        self.assertEqual(best_candidate(cands)["proposed_ftp"], 190)

    def test_empate_por_mesmo_dia_maior_proposto(self):
        cands = [
            {"day": "2026-09-18", "proposed_ftp": 190},
            {"day": "2026-09-18", "proposed_ftp": 195},
        ]
        self.assertEqual(best_candidate(cands)["proposed_ftp"], 195)


class RideSettingsTest(unittest.TestCase):
    def test_acha_entrada_de_bicicleta(self):
        settings = [
            {"id": 1, "types": ["Run"], "ftp": 200},
            {"id": 31898, "types": ["Ride", "VirtualRide"], "indoor_ftp": 182},
        ]
        ride = ride_settings(settings)
        self.assertEqual(ride["id"], 31898)

    def test_ausente_devolve_none(self):
        self.assertIsNone(ride_settings([{"id": 1, "types": ["Run"]}]))

    def test_payload_sem_created_updated_e_com_novo_ftp(self):
        settings = {"id": 31898, "types": ["Ride"], "indoor_ftp": 182,
                    "ftp": 183, "created": "x", "updated": "y"}
        payload = sanitize_ride_payload(settings, 190)
        self.assertEqual(payload["indoor_ftp"], 190)
        self.assertNotIn("created", payload)
        self.assertNotIn("updated", payload)
        self.assertEqual(payload["ftp"], 183)


if __name__ == "__main__":
    unittest.main()