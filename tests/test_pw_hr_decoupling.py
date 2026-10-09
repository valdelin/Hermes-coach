"""HR-2 — Pw:HR observacional, estrutural e local."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from src.activity_stream_cache import ActivityStreamCache
from src.application import Application
from src.provider import ActivityStream, ActivityStreamPoint
from src.pw_hr_decoupling import (CALCULATED, NOT_ELIGIBLE, UNAVAILABLE,
                                  build_pw_hr_decoupling_view,
                                  derive_pw_hr_decoupling,
                                  evaluate_pw_hr_eligibility)


def _stream(points, *, alignment="aligned", captured_at="2026-10-05T12:00:00+00:00"):
    return ActivityStream(
        provider="fake", activity_id="activity-1", points=tuple(points),
        available_fields=("power", "heart_rate"), alignment=alignment,
        time_samples=len(points), power_samples=len(points),
        heart_rate_samples=len(points), captured_at=captured_at)


def _steady_points(*, first_power=200.0, second_power=200.0,
                   first_hr=130.0, second_hr=130.0):
    # 0..120: midpoint 60 pertence deterministamente a primeira metade.
    return [ActivityStreamPoint(float(second),
                                first_power if second <= 60 else second_power,
                                first_hr if second <= 60 else second_hr)
            for second in range(121)]


class PwHrMathTest(unittest.TestCase):
    def test_esforco_constante_tem_decoupling_zero(self):
        view = build_pw_hr_decoupling_view(_stream(_steady_points()))
        self.assertEqual(view.status, CALCULATED)
        self.assertAlmostEqual(view.decoupling_pct, 0.0)
        self.assertEqual(view.physiological_context, "unverified")
        self.assertTrue(view.computable)
        self.assertEqual(view.methodological_context, "unverified")
        self.assertEqual(view.to_dict()["status"], CALCULATED)
        self.assertTrue(view.to_dict()["computable"])
        self.assertEqual(view.to_dict()["methodological_context"], "unverified")

    def test_np_e_calculada_separadamente_em_cada_metade(self):
        view = build_pw_hr_decoupling_view(
            _stream(_steady_points(first_power=200.0, second_power=300.0,
                                   first_hr=100.0, second_hr=100.0)))
        self.assertEqual(view.status, CALCULATED)
        self.assertAlmostEqual(view.first_half.normalized_power, 200.0)
        self.assertAlmostEqual(view.second_half.normalized_power, 300.0)

    def test_fc_maior_na_segunda_metade_tem_sinal_positivo(self):
        view = build_pw_hr_decoupling_view(
            _stream(_steady_points(first_hr=100.0, second_hr=125.0)))
        self.assertEqual(view.status, CALCULATED)
        self.assertAlmostEqual(view.decoupling_pct, 20.0)

    def test_relacao_melhor_na_segunda_metade_tem_sinal_negativo(self):
        view = build_pw_hr_decoupling_view(
            _stream(_steady_points(first_hr=125.0, second_hr=100.0)))
        self.assertEqual(view.status, CALCULATED)
        self.assertAlmostEqual(view.decoupling_pct, -25.0)

    def test_escala_proporcional_mantem_resultado(self):
        first = build_pw_hr_decoupling_view(
            _stream(_steady_points(first_power=200, second_power=240,
                                   first_hr=100, second_hr=120)))
        scaled = build_pw_hr_decoupling_view(
            _stream(_steady_points(first_power=400, second_power=480,
                                   first_hr=200, second_hr=240)))
        self.assertAlmostEqual(first.decoupling_pct, scaled.decoupling_pct)

    def test_split_temporal_usa_midpoint_e_nao_quantidade_de_samples(self):
        points = _steady_points()
        eligibility = evaluate_pw_hr_eligibility(_stream(list(reversed(points))))
        self.assertEqual(eligibility.status, "eligible")
        self.assertEqual(eligibility.first_half[-1].elapsed_seconds, 60.0)
        self.assertEqual(eligibility.second_half[0].elapsed_seconds, 61.0)

    def test_duracao_impar_mantem_metades_temporais_deterministicas(self):
        points = _steady_points()
        points.append(ActivityStreamPoint(121.0, 200.0, 130.0))
        eligibility = evaluate_pw_hr_eligibility(_stream(points))
        self.assertEqual(eligibility.status, "eligible")
        self.assertEqual(len(eligibility.first_half), 61)
        self.assertEqual(len(eligibility.second_half), 61)

    def test_power_zero_e_amostra_valida_quando_a_razao_permanece_definida(self):
        points = _steady_points()
        points[20] = ActivityStreamPoint(20.0, 0.0, 130.0)
        view = build_pw_hr_decoupling_view(_stream(points))
        self.assertEqual(view.status, CALCULATED)

    def test_funcao_pura_nao_muta_entrada_nem_imprime(self):
        points = _steady_points()
        before = tuple(points)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            metric = derive_pw_hr_decoupling(points[:61], points[61:])
        self.assertIsNotNone(metric)
        self.assertEqual(tuple(points), before)
        self.assertEqual(stdout.getvalue(), "")


class PwHrEligibilityTest(unittest.TestCase):
    def test_gap_nao_e_interpolado(self):
        points = _steady_points()
        del points[40]
        view = build_pw_hr_decoupling_view(_stream(points))
        self.assertEqual((view.status, view.reason),
                         (NOT_ELIGIBLE, "non_contiguous_one_second_samples"))
        self.assertFalse(view.computable)
        self.assertEqual(view.methodological_context, "unverified")

    def test_missing_power_ou_hr_nao_vira_zero(self):
        points = _steady_points()
        points[20] = ActivityStreamPoint(20.0, None, 130.0)
        self.assertEqual(build_pw_hr_decoupling_view(_stream(points)).reason,
                         "missing_joint_samples")
        points = _steady_points()
        points[20] = ActivityStreamPoint(20.0, 200.0, None)
        self.assertEqual(build_pw_hr_decoupling_view(_stream(points)).reason,
                         "missing_joint_samples")

    def test_hr_zero_e_preservada_mas_media_zero_e_indefinida(self):
        points = _steady_points(first_hr=0.0, second_hr=130.0)
        view = build_pw_hr_decoupling_view(_stream(points))
        self.assertEqual((view.status, view.reason),
                         (NOT_ELIGIBLE, "zero_mean_heart_rate"))

    def test_duplicata_nao_e_agregada(self):
        points = _steady_points()
        points[61] = ActivityStreamPoint(60.0, 200.0, 130.0)
        self.assertEqual(build_pw_hr_decoupling_view(_stream(points)).reason,
                         "duplicate_elapsed_seconds")

    def test_stream_vazio_ou_nao_alinhado_tem_razao_explicita(self):
        self.assertEqual(build_pw_hr_decoupling_view(_stream([])).reason,
                         "empty_stream")
        self.assertEqual(build_pw_hr_decoupling_view(
            _stream(_steady_points(), alignment="heart_rate_length_mismatch")).reason,
            "stream_not_aligned")


class PwHrApplicationTest(unittest.TestCase):
    def test_query_offline_e_read_only_sobre_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            plan = root / "plan.json"
            snapshot = root / "training_snapshot.json"
            cache = root / "activity_streams.json"
            plan.write_text("[]", encoding="utf-8")
            snapshot.write_text('{"events": []}', encoding="utf-8")
            stream = _stream(_steady_points())
            ActivityStreamCache().with_stream(stream).save(cache)
            before = {path: path.read_bytes() for path in (plan, snapshot, cache)}
            app = Application(
                plan_path=plan, snapshot_path=snapshot,
                activity_stream_cache_path=cache,
                client_factory=lambda: (_ for _ in ()).throw(
                    AssertionError("query local chamou provider")))
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                view = app.get_pw_hr_decoupling(provider="fake", activity_id="activity-1")
            self.assertEqual(view.status, CALCULATED)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual({path: path.read_bytes() for path in before}, before)

    def test_cache_ausente_retorna_unavailable_sem_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = Application(
                plan_path=Path(tmp) / "plan.json",
                activity_stream_cache_path=Path(tmp) / "activity_streams.json",
                client_factory=lambda: (_ for _ in ()).throw(
                    AssertionError("query local chamou provider")))
            view = app.get_pw_hr_decoupling(provider="fake", activity_id="missing")
            self.assertEqual((view.status, view.reason),
                             (UNAVAILABLE, "stream_not_cached"))


if __name__ == "__main__":
    unittest.main()
