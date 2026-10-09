"""STREAM-1 — boundary temporal normalizado e cache local, sem rede."""
import contextlib
import io
import json
import tempfile
import tokenize
import unittest
from datetime import datetime, timezone
from pathlib import Path

from src.activity_stream_cache import ActivityStreamCache
from src.application import Application
from src.intervals_adapter import DEFAULT_CAPABILITIES, IntervalsAdapter
from src.provider import (ActivityStream, ActivityStreamPoint, ProviderCapability,
                          ProviderOperationError)

T0 = datetime(2026, 10, 5, 12, 0, tzinfo=timezone.utc)
FIXTURE = Path(__file__).parent / "fixtures" / "activity_streams_time_watts_heartrate.json"


def _code_only(path):
    source = Path(path).read_text(encoding="utf-8")
    return " ".join(
        token.string
        for token in tokenize.generate_tokens(io.StringIO(source).readline)
        if token.type not in (tokenize.COMMENT, tokenize.STRING))


class _RawStreamsClient:
    def __init__(self, streams=None, error=None):
        self.streams = streams if streams is not None else {}
        self.error = error
        self.calls = []

    def activity_streams(self, activity_id, types=("watts", "time")):
        self.calls.append((activity_id, types))
        if self.error is not None:
            raise self.error
        return self.streams


class _NormalizedStreamProvider:
    provider_name = "fake"
    capabilities = frozenset({ProviderCapability.READ_ACTIVITY_STREAMS})

    def __init__(self, stream):
        self.stream = stream
        self.calls = []

    def activity_stream(self, activity_id):
        self.calls.append(activity_id)
        return self.stream


class DtoTest(unittest.TestCase):
    def test_frozen_serializa_none_zero_e_float(self):
        stream = ActivityStream(
            provider="intervals", activity_id="a1",
            points=(ActivityStreamPoint(0.0, power=0.0),
                    ActivityStreamPoint(1.5, power=None)),
            available_fields=("power",), alignment="aligned",
            time_samples=2, power_samples=2)
        payload = stream.to_dict()
        self.assertEqual(payload["points"][0]["power"], 0.0)
        self.assertIsNone(payload["points"][1]["power"])
        self.assertEqual(ActivityStream.from_dict(payload), stream)
        with self.assertRaises(Exception):
            stream.points = ()


class AdapterTest(unittest.TestCase):
    def test_capability_de_streams_confirmados(self):
        self.assertIn(ProviderCapability.READ_ACTIVITY_STREAMS,
                      DEFAULT_CAPABILITIES)
        self.assertIn(ProviderCapability.READ_HEART_RATE_STREAM,
                      DEFAULT_CAPABILITIES)

    def test_fixture_real_sanitizada_normaliza_hr_e_preserva_associacao(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        raw = {stream["type"]: stream["data"] for stream in fixture["response"]}
        stream = IntervalsAdapter(_RawStreamsClient(raw)).activity_stream("sanitized")
        self.assertEqual(stream.alignment, "aligned")
        self.assertEqual(stream.available_fields, ("power", "heart_rate"))
        self.assertEqual(stream.heart_rate_samples, 7)
        self.assertEqual(
            [(point.elapsed_seconds, point.power, point.heart_rate)
             for point in stream.points],
            [(0.0, 29.0, 67.0), (1.0, 33.0, 67.0), (2.0, 59.0, 68.0),
             (612.0, 109.0, 132.0), (1224.0, 109.0, 133.0),
             (1836.0, 104.0, 134.0), (2447.0, 2.0, 126.0)])

    def test_hr_mismatch_nao_trunca_nem_emite_pontos(self):
        stream = IntervalsAdapter(_RawStreamsClient({
            "time": [0, 1], "watts": [100, 101], "heartrate": [130],
        })).activity_stream("a1")
        self.assertEqual(stream.alignment, "heart_rate_length_mismatch")
        self.assertEqual(stream.points, ())
        self.assertEqual(stream.heart_rate_samples, 1)

    def test_hr_invalida_e_zero_sao_preservados_estruturalmente(self):
        stream = IntervalsAdapter(_RawStreamsClient({
            "time": [0, 1, 2], "watts": [100, 101, 102],
            "heartrate": [0, None, "130"],
        })).activity_stream("a1")
        self.assertEqual([point.heart_rate for point in stream.points],
                         [0.0, None, None])

    def test_time_watts_viram_pontos_ordenados_sem_agregar_duplicatas(self):
        client = _RawStreamsClient({
            "time": [60, 0, 60], "watts": [210, 0, 220],
        })
        stream = IntervalsAdapter(client).activity_stream("a1")
        self.assertEqual(client.calls,
                         [("a1", ("time", "watts", "heartrate"))])
        self.assertEqual(stream.provider, "intervals")
        self.assertEqual(stream.available_fields, ("power",))
        self.assertEqual(stream.alignment, "aligned")
        self.assertEqual([(p.elapsed_seconds, p.power) for p in stream.points],
                         [(0.0, 0.0), (60.0, 210.0), (60.0, 220.0)])
        self.assertTrue(all(point.heart_rate is None for point in stream.points))

    def test_none_e_numeros_invalidos_nao_viram_zero(self):
        stream = IntervalsAdapter(_RawStreamsClient({
            "time": [0, None, 2], "watts": [0, "200", float("nan")],
        })).activity_stream("a1")
        self.assertEqual(stream.alignment, "invalid_time")
        self.assertEqual([(p.elapsed_seconds, p.power) for p in stream.points],
                         [(0.0, 0.0), (None, None), (2.0, None)])

    def test_arrays_de_tamanho_diferente_nao_sao_alinhados(self):
        stream = IntervalsAdapter(_RawStreamsClient({
            "time": [0, 1, 2], "watts": [100, 101],
        })).activity_stream("a1")
        self.assertEqual(stream.alignment, "length_mismatch")
        self.assertEqual(stream.time_samples, 3)
        self.assertEqual(stream.power_samples, 2)
        self.assertEqual(stream.points, ())

    def test_time_ou_stream_vazios_tem_diagnostico_explicito(self):
        missing_time = IntervalsAdapter(_RawStreamsClient({"watts": [100]})) \
            .activity_stream("a1")
        empty = IntervalsAdapter(_RawStreamsClient({"time": [], "watts": []})) \
            .activity_stream("a1")
        self.assertEqual(missing_time.alignment, "missing_time")
        self.assertEqual(empty.alignment, "empty")

    def test_erro_do_cliente_usa_taxonomia_do_provider(self):
        from src.intervals_client import IntervalsApiError

        with self.assertRaises(ProviderOperationError):
            IntervalsAdapter(_RawStreamsClient(error=IntervalsApiError("bad", 400))) \
                .activity_stream("a1")


class CacheTest(unittest.TestCase):
    def _stream(self, provider="intervals", activity_id="a1", heart_rate=None):
        return ActivityStream(
            provider=provider, activity_id=activity_id,
            points=(ActivityStreamPoint(0.0, 0.0, heart_rate),),
            available_fields=(("power", "heart_rate") if heart_rate is not None
                              else ("power",)), alignment="aligned",
            time_samples=1, power_samples=1,
            heart_rate_samples=1 if heart_rate is not None else None,
            captured_at=T0.isoformat())

    def test_save_reload_e_chave_provider_activity(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "activity_streams.json"
            cache = ActivityStreamCache().with_stream(self._stream()) \
                .with_stream(self._stream(provider="other"))
            cache.save(path)
            loaded = ActivityStreamCache.load(path)
            self.assertEqual(loaded.get(provider="intervals", activity_id="a1"),
                             self._stream())
            self.assertEqual(loaded.get(provider="other", activity_id="a1"),
                             self._stream(provider="other"))

    def test_cache_ausente_ou_corrompido_e_vazio(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "activity_streams.json"
            self.assertEqual(ActivityStreamCache.load(path).streams, {})
            path.write_text('{"streams": {"bad": {"time_samples": "x"}}}',
                            encoding="utf-8")
            self.assertEqual(ActivityStreamCache.load(path).streams, {})

    def test_cache_legado_sem_hr_carrega_com_none(self):
        legacy = {
            "provider": "intervals", "activity_id": "a1",
            "points": [{"elapsed_seconds": 0.0, "power": 100.0}],
            "available_fields": ["power"], "alignment": "aligned",
            "time_samples": 1, "power_samples": 1,
        }
        loaded = ActivityStream.from_dict(legacy)
        self.assertIsNone(loaded.points[0].heart_rate)
        self.assertIsNone(loaded.heart_rate_samples)

    def test_cache_preserva_hr_normalizada(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "activity_streams.json"
            expected = self._stream(heart_rate=132.0)
            ActivityStreamCache().with_stream(expected).save(path)
            actual = ActivityStreamCache.load(path).get(
                provider="intervals", activity_id="a1")
            self.assertEqual(actual, expected)


class ApplicationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.plan = root / "plan.json"
        self.snapshot = root / "training_snapshot.json"
        self.cache = root / "activity_streams.json"
        self.stream = ActivityStream(
            provider="fake", activity_id="a1",
            points=(ActivityStreamPoint(0.0, 200.0, 130.0),),
            available_fields=("power", "heart_rate"), alignment="aligned",
            time_samples=1, power_samples=1, heart_rate_samples=1)

    def tearDown(self):
        self.tmp.cleanup()

    def test_fetch_remoto_explicito_persiste_e_query_local_nao_chama_provider(self):
        provider = _NormalizedStreamProvider(self.stream)
        app = Application(plan_path=self.plan, snapshot_path=self.snapshot,
                          activity_stream_cache_path=self.cache,
                          client_factory=lambda: provider)
        fetched = app.fetch_activity_stream("a1", now=T0)
        self.assertEqual(provider.calls, ["a1"])
        self.assertEqual(fetched.captured_at, T0.isoformat())

        offline = Application(plan_path=self.plan, snapshot_path=self.snapshot,
                              activity_stream_cache_path=self.cache,
                              client_factory=lambda: (_ for _ in ()).throw(
                                  AssertionError("leitura local chamou provider")))
        self.assertEqual(offline.get_cached_activity_stream(
            provider="fake", activity_id="a1"), fetched)
        self.assertEqual(fetched.points[0].heart_rate, 130.0)

    def test_fetch_nao_toca_plano_ou_snapshot_nem_imprime(self):
        provider = _NormalizedStreamProvider(self.stream)
        self.plan.write_text("[]", encoding="utf-8")
        self.snapshot.write_text('{"events": []}', encoding="utf-8")
        plan_before = self.plan.read_text(encoding="utf-8")
        snapshot_before = self.snapshot.read_text(encoding="utf-8")
        app = Application(plan_path=self.plan, snapshot_path=self.snapshot,
                          activity_stream_cache_path=self.cache,
                          client_factory=lambda: provider)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            app.fetch_activity_stream("a1", now=T0)
        self.assertEqual(stdout.getvalue(), "")
        self.assertEqual(self.plan.read_text(encoding="utf-8"), plan_before)
        self.assertEqual(self.snapshot.read_text(encoding="utf-8"), snapshot_before)

    def test_provider_legado_sem_declaracao_de_capabilities_usa_protocolo(self):
        provider = _NormalizedStreamProvider(self.stream)
        provider.capabilities = frozenset()
        app = Application(plan_path=self.plan, activity_stream_cache_path=self.cache,
                          client_factory=lambda: provider)
        # Sem declaracao de capabilities, o protocolo e suficiente para fakes
        # legados; nao ha suposicao baseada no nome do provider.
        self.assertEqual(app.fetch_activity_stream("a1", now=T0).activity_id, "a1")

    def test_provider_que_declara_capabilities_sem_streams_e_rejeitado(self):
        provider = _NormalizedStreamProvider(self.stream)
        provider.capabilities = frozenset({ProviderCapability.READ_EVENTS})
        app = Application(plan_path=self.plan, activity_stream_cache_path=self.cache,
                          client_factory=lambda: provider)
        with self.assertRaises(ProviderOperationError):
            app.fetch_activity_stream("a1", now=T0)
        self.assertEqual(provider.calls, [])


class BoundaryTest(unittest.TestCase):
    def test_application_nao_conhece_nomes_crus_do_intervals(self):
        from src import application

        code = _code_only(application.__file__)
        for raw_name in ("watts", "heartrate", "icu_"):
            self.assertNotIn(raw_name, code)

    def test_cache_e_dto_nao_calculam_decoupling(self):
        from src import activity_stream_cache, provider

        for module in (activity_stream_cache, provider):
            code = _code_only(module.__file__).lower()
            for prohibited in ("decoupling", "pw_hr", "first_half"):
                self.assertNotIn(prohibited, code)


if __name__ == "__main__":
    unittest.main()
