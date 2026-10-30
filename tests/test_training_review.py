"""Projeções factuais compartilhadas da revisão de treino na TUI."""

import unittest
from datetime import date

from src.coach import FOCUS_ZONE1_RECOVERY, FOCUS_ZONE2_ENDURANCE, ZONE_SWEETSPOT
from src.ui.training_review import (
    day_comparison,
    planned_workout_summary,
    week_summary,
    zone_seconds_for_plan,
    zone_seconds_for_stream,
)


PLANNED = {
    "day": "2026-11-02",
    "focus": "sweetspot",
    "planned_duration": 3600,
    "tss": 55,
    "params": {
        "warmup_sec": 600,
        "repeats": 2,
        "on_sec": 720,
        "off_sec": 180,
        "on_power": 0.90,
        "off_power": 0.55,
        "cooldown_sec": 600,
    },
}


class PlannedWorkoutSummaryTest(unittest.TestCase):
    def test_expoe_blocos_existentes_e_zonas_do_plano(self):
        summary = planned_workout_summary(PLANNED)

        self.assertEqual(summary.focus, "sweetspot")
        self.assertEqual(summary.duration_seconds, 3600)
        self.assertEqual(summary.tss, 55.0)
        self.assertEqual(
            [(block.label, block.duration_seconds, block.repetitions) for block in summary.blocks],
            [("Aquecimento", 600, 1), ("Trabalho", 720, 2),
             ("Recuperação", 180, 1), ("Desaquecimento", 600, 1)],
        )
        self.assertEqual(summary.zone_seconds[ZONE_SWEETSPOT], 1440.0)
        self.assertEqual(summary.zone_seconds[FOCUS_ZONE1_RECOVERY], 1380.0)

    def test_omite_apenas_blocos_sem_parametro(self):
        summary = planned_workout_summary({"focus": "zone2", "params": {"on_sec": 1800}})

        self.assertEqual([block.label for block in summary.blocks], ["Trabalho"])
        self.assertIsNone(summary.duration_seconds)
        self.assertIsNone(summary.tss)


class DayComparisonTest(unittest.TestCase):
    def test_compara_duracao_tss_e_potencias_reais(self):
        comparison = day_comparison(
            PLANNED,
            {"duration": 3300, "tss": 48, "average_watts": 180,
             "normalized_power": 195},
        )

        self.assertEqual(comparison.duration_delta_seconds, -300)
        self.assertEqual(comparison.tss_delta, -7.0)
        self.assertEqual(comparison.average_watts, 180.0)
        self.assertEqual(comparison.normalized_power, 195.0)

    def test_preserva_metrica_real_ausente_como_none(self):
        comparison = day_comparison(PLANNED, {"duration": "inválido", "tss": None})

        self.assertIsNone(comparison.actual_duration_seconds)
        self.assertIsNone(comparison.duration_delta_seconds)
        self.assertIsNone(comparison.actual_tss)
        self.assertIsNone(comparison.tss_delta)
        self.assertIsNone(comparison.average_watts)
        self.assertIsNone(comparison.normalized_power)


class ZoneSecondsTest(unittest.TestCase):
    def test_soma_zonas_planejadas_sem_estimar_segmento_ausente(self):
        zones = zone_seconds_for_plan(PLANNED)

        self.assertEqual(zones[FOCUS_ZONE1_RECOVERY], 1380.0)
        self.assertEqual(zones[ZONE_SWEETSPOT], 1440.0)
        self.assertNotIn(FOCUS_ZONE2_ENDURANCE, zones)

    def test_calcula_zonas_reais_com_duracao_dos_pontos(self):
        zones = zone_seconds_for_stream([(0, 100), (60, 180), (120, 180)], ftp=200)

        self.assertEqual(zones[FOCUS_ZONE1_RECOVERY], 60.0)
        self.assertEqual(zones[ZONE_SWEETSPOT], 120.0)

    def test_sem_ftp_valido_nao_produz_zonas_reais(self):
        self.assertIsNone(zone_seconds_for_stream([(0, 100), (60, 180)], ftp=None))
        self.assertIsNone(zone_seconds_for_stream([(0, 100), (60, 180)], ftp=0))


class WeekSummaryTest(unittest.TestCase):
    def test_classifica_status_e_soma_totais_da_semana(self):
        entries = {
            "2026-11-02": {"planned": PLANNED, "done": {"duration": 3300, "tss": 48}},
            "2026-11-03": {"planned": {"planned_duration": 1800, "tss": 20}},
            "2026-11-04": {"planned": {"planned_duration": 2400, "tss": 30}},
            "2026-11-05": {"done": {"duration": 1200, "tss": 15}},
        }

        summary = week_summary(entries, date(2026, 11, 2), today=date(2026, 11, 3))

        self.assertEqual(summary.planned_duration_seconds, 7800)
        self.assertEqual(summary.actual_duration_seconds, 4500)
        self.assertEqual(summary.planned_tss, 105.0)
        self.assertEqual(summary.actual_tss, 63.0)
        self.assertEqual((summary.completed, summary.missed, summary.pending, summary.extra), (1, 0, 2, 1))

    def test_ignora_valores_invalidos_como_carga_positiva(self):
        summary = week_summary(
            {"2026-11-02": {"planned": {"planned_duration": "x", "tss": -1},
                            "done": {"duration": 0, "tss": "x"}}},
            date(2026, 11, 2), today=date(2026, 11, 2),
        )

        self.assertEqual(summary.planned_duration_seconds, 0)
        self.assertEqual(summary.actual_duration_seconds, 0)
        self.assertEqual(summary.planned_tss, 0.0)
        self.assertEqual(summary.actual_tss, 0.0)

    def test_sem_streams_declara_zona_real_indisponivel(self):
        summary = week_summary({"2026-11-02": {"planned": PLANNED}},
                               date(2026, 11, 2), today=date(2026, 11, 2))

        self.assertIsNone(summary.actual_zone_seconds)
        self.assertEqual(summary.planned_zone_seconds[ZONE_SWEETSPOT], 1440.0)

    def test_agrega_zonas_reais_quando_fornecidas(self):
        summary = week_summary(
            {"2026-11-02": {"done": {"duration": 120, "tss": 2}}},
            date(2026, 11, 2), today=date(2026, 11, 2),
            actual_zone_seconds={"2026-11-02": {FOCUS_ZONE2_ENDURANCE: 120.0}},
        )

        self.assertEqual(summary.actual_zone_seconds, {FOCUS_ZONE2_ENDURANCE: 120.0})


if __name__ == "__main__":
    unittest.main()
