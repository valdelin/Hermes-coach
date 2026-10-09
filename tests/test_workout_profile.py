"""Projecao do treino planejado para o perfil visual do relatorio.

O perfil e uma leitura de ``workout['params']``: nunca interpreta nome,
descricao ou TSS para inventar passos.
"""

import unittest
from datetime import date

from src.plan import build_plan, planned_workout_profile


def _workout(**overrides):
    workout = {
        "day": "2026-10-06",
        "focus": "zone2",
        "planned_duration": 3840,
        "name": "2026-10-06 - Treino de Zona 2",
        "tss": 51.0,
        "intensity_factor": 0.69,
        "ftp_watts": 183,
        "params": {
            "warmup_sec": 600,
            "warmup_power_low": 0.55,
            "warmup_power_high": 0.75,
            "repeats": 2,
            "on_sec": 1140,
            "on_power": 0.75,
            "off_sec": 180,
            "off_power": 0.55,
            "cooldown_sec": 600,
            "cooldown_power_low": 0.70,
            "cooldown_power_high": 0.45,
        },
    }
    workout.update(overrides)
    return workout


class PlannedWorkoutProfileTest(unittest.TestCase):
    def test_build_persiste_ftp_na_sessao_canonica(self):
        plan = build_plan([], 0.0, ftp=183, days=1,
                          start=date(2026, 10, 6))

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0]["ftp_watts"], 183)

    def test_preservacao_de_hoje_carimba_ftp_que_faltava(self):
        """A preservacao verbatim de HOJE e a unica saida de `build_plan` que
        nao constroi a sessao. Uma entrada gravada antes de `ftp_watts` existir
        escapava daqui sem o campo, e o relatorio recusa o perfil (contrato:
        nao inferir watts do `.env`) -- o painel do dia ficava sem grafico."""
        hoje = date.today().isoformat()
        legado = {
            "day": hoje,
            "focus": "sweetspot",
            "planned_duration": 4200,
            "name": f"{hoje} - Treino de Sweet Spot",
            "tss": 56.0,
            "external_id": f"hermes-plan-{hoje}",
            "params": {"focus": "sweetspot"},
        }

        plan = build_plan([], 0.0, ftp=183, days=1, existing=[legado],
                          training_days=tuple(range(7)))
        preservada = next(w for w in plan if w["day"] == hoje)

        self.assertEqual(preservada["ftp_watts"], 183)
        self.assertEqual(preservada["tss"], 56.0)

    def test_preservacao_de_hoje_nao_reescreve_ftp_ja_persistido(self):
        """O carimbo e so para campo ausente: regravar sobrescreveria a
        referencia com a qual o TSS daquela sessao foi de fato estimado."""
        hoje = date.today().isoformat()
        sessao = {
            "day": hoje, "focus": "sweetspot", "planned_duration": 4200,
            "name": f"{hoje} - Treino de Sweet Spot", "tss": 56.0,
            "external_id": f"hermes-plan-{hoje}", "ftp_watts": 165,
            "params": {"focus": "sweetspot"},
        }

        plan = build_plan([], 0.0, ftp=183, days=1, existing=[sessao],
                          training_days=tuple(range(7)))
        preservada = next(w for w in plan if w["day"] == hoje)

        self.assertEqual(preservada["ftp_watts"], 165)

    def test_achata_repeticoes_sem_perder_duracao_ou_alvos(self):
        profile = planned_workout_profile(_workout())

        self.assertTrue(profile["has_structured_blocks"])
        self.assertEqual(profile["duration_seconds"], 3840)
        self.assertEqual(profile["planned_tss"], 51.0)
        self.assertEqual(profile["intensity_factor"], 0.69)
        self.assertEqual(profile["ftp_watts"], 183)
        self.assertEqual(
            [block["kind"] for block in profile["blocks"]],
            ["warmup", "work", "recovery", "work", "recovery", "cooldown"],
        )
        self.assertEqual(
            [(block["start_seconds"], block["end_seconds"])
             for block in profile["blocks"]],
            [(0, 600), (600, 1740), (1740, 1920),
             (1920, 3060), (3060, 3240), (3240, 3840)],
        )
        self.assertEqual(profile["blocks"][1]["label"], "Zona 2 · série 1")
        self.assertEqual(profile["blocks"][3]["label"], "Zona 2 · série 2")

    def test_rampas_e_patamares_derivam_watts_exatos_do_ftp(self):
        profile = planned_workout_profile(_workout())
        warmup, work, recovery, *_rest, cooldown = profile["blocks"]

        self.assertEqual((warmup["start_pct_ftp"], warmup["end_pct_ftp"]),
                         (0.55, 0.75))
        self.assertEqual((warmup["start_watts"], warmup["end_watts"]),
                         (100.7, 137.2))
        self.assertEqual((work["start_watts"], work["end_watts"]),
                         (137.2, 137.2))
        self.assertEqual((recovery["start_watts"], recovery["end_watts"]),
                         (100.7, 100.7))
        self.assertEqual((cooldown["start_pct_ftp"], cooldown["end_pct_ftp"]),
                         (0.70, 0.45))
        self.assertEqual((cooldown["start_watts"], cooldown["end_watts"]),
                         (128.1, 82.4))

    def test_recuperacao_nao_e_criada_quando_off_sec_e_zero(self):
        workout = _workout()
        workout["params"] = {**workout["params"], "repeats": 1,
                             "off_sec": 0}
        profile = planned_workout_profile(workout)

        self.assertEqual([b["kind"] for b in profile["blocks"]],
                         ["warmup", "work", "cooldown"])
        self.assertEqual(profile["duration_seconds"], 2340)

    def test_sessao_sem_blocos_mantem_so_metadados_canonicos(self):
        profile = planned_workout_profile(_workout(params={}))

        self.assertFalse(profile["has_structured_blocks"])
        self.assertEqual(profile["blocks"], [])
        self.assertEqual(profile["duration_seconds"], 3840)
        self.assertEqual(profile["planned_tss"], 51.0)
        self.assertEqual(profile["ftp_watts"], 183)

    def test_plano_legado_sem_ftp_persistido_nao_inventa_watts(self):
        workout = _workout()
        workout.pop("ftp_watts")

        profile = planned_workout_profile(workout)

        self.assertFalse(profile["has_structured_blocks"])
        self.assertEqual(profile["blocks"], [])
        self.assertIsNone(profile["ftp_watts"])

    def test_duracao_fracionaria_nao_e_truncada_para_desenhar_perfil(self):
        workout = _workout()
        workout["params"] = {**workout["params"], "on_sec": 1140.5}

        profile = planned_workout_profile(workout)

        self.assertFalse(profile["has_structured_blocks"])
        self.assertEqual(profile["blocks"], [])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
