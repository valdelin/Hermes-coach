import unittest
from unittest import mock

import requests

from src.intervals_client import (IntervalsClient, IntervalsApiError,
                                  RETRIES, RETRY_STATUS)


class _FakeResponse:
    """Resposta fake com o contrato minimo de `requests.Response`."""

    def __init__(self, status_code=200, payload=None, exc=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self._exc = exc

    def raise_for_status(self):
        if self._exc is not None:
            raise self._exc
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeSession:
    """Session fake: entrega respostas (ou excecoes) em fila, registra chamadas."""

    def __init__(self, responses):
        self._queue = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        item = self._queue.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _client(session):
    return IntervalsClient("123", "sekret", session=session,
                           sleep=lambda _s: None)


class IntervalsClientRetryTest(unittest.TestCase):
    def test_sucesso_sem_retry(self):
        session = _FakeSession([_FakeResponse(200, {"ok": True})])
        client = _client(session)
        self.assertEqual(client.events(oldest="2026-09-01"), {"ok": True})
        self.assertEqual(len(session.calls), 1)

    def test_connection_error_retry_depois_sucesso(self):
        session = _FakeSession([
            requests.exceptions.ConnectionError("boom"),
            _FakeResponse(200, {"ok": True}),
        ])
        client = _client(session)
        self.assertEqual(client.events(), {"ok": True})
        self.assertEqual(len(session.calls), 2)

    def test_timeout_retry_depois_sucesso(self):
        session = _FakeSession([
            requests.exceptions.Timeout("slow"),
            _FakeResponse(200, {"ok": True}),
        ])
        client = _client(session)
        self.assertEqual(client.wellness(), {"ok": True})
        self.assertEqual(len(session.calls), 2)

    def test_http_500_retry_depois_sucesso(self):
        session = _FakeSession([
            _FakeResponse(500, {"e": "boom"}),
            _FakeResponse(200, {"ok": True}),
        ])
        client = _client(session)
        self.assertEqual(client.events(), {"ok": True})
        self.assertEqual(len(session.calls), 2)

    def test_429_retry_depois_sucesso(self):
        session = _FakeSession([
            _FakeResponse(429, {"e": "rate"}),
            _FakeResponse(200, {"ok": True}),
        ])
        client = _client(session)
        self.assertEqual(client.events(), {"ok": True})
        self.assertEqual(len(session.calls), 2)

    def test_esgota_retries_connection_error_lanca_api_error(self):
        session = _FakeSession([
            requests.exceptions.ConnectionError("boom")] * RETRIES)
        client = _client(session)
        with self.assertRaises(IntervalsApiError) as ctx:
            client.events()
        self.assertIn("nao foi possivel falar com o Intervals.icu", str(ctx.exception))
        self.assertEqual(len(session.calls), RETRIES)

    def test_esgota_retries_http_500_lanca_api_error(self):
        session = _FakeSession([_FakeResponse(500)] * RETRIES)
        client = _client(session)
        with self.assertRaises(IntervalsApiError) as ctx:
            client.events()
        self.assertIn("HTTP 500", str(ctx.exception))
        self.assertEqual(len(session.calls), RETRIES)

    def test_401_falha_imediata_com_mensagem(self):
        session = _FakeSession([_FakeResponse(401)])
        client = _client(session)
        with self.assertRaises(IntervalsApiError) as ctx:
            client.events()
        self.assertIn("credenciais invalidas", str(ctx.exception))
        self.assertEqual(len(session.calls), 1)

    def test_404_falha_imediata_sem_retry(self):
        session = _FakeSession([_FakeResponse(404)])
        client = _client(session)
        with self.assertRaises(requests.exceptions.HTTPError):
            client.events()
        self.assertEqual(len(session.calls), 1)

    def test_backoff_exponencial(self):
        sleeps = []
        session = _FakeSession([
            requests.exceptions.ConnectionError("a"),
            requests.exceptions.ConnectionError("b"),
            _FakeResponse(200, {"ok": True}),
        ])
        client = IntervalsClient("123", "sekret", session=session,
                                 sleep=sleeps.append)
        self.assertEqual(client.events(), {"ok": True})
        self.assertEqual(sleeps, [0.5, 1.0])

    def test_create_events_envia_bulk_e_retorna_status(self):
        session = _FakeSession([_FakeResponse(200, {"ids": [1]})])
        client = _client(session)
        status, body = client.create_events([{"name": "x"}])
        self.assertEqual(status, 200)
        self.assertEqual(body, {"ids": [1]})
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "POST")
        self.assertIn("/events/bulk", url)
        self.assertEqual(kwargs["json"], [{"name": "x"}])
        self.assertEqual(kwargs["params"], {"upsert": "true"})

    def test_delete_events(self):
        session = _FakeSession([_FakeResponse(200, {"deleted": 1})])
        client = _client(session)
        status, body = client.delete_events(["a", "b"])
        self.assertEqual(status, 200)
        method, url, kwargs = session.calls[0]
        self.assertEqual(method, "PUT")
        self.assertEqual(kwargs["json"], [{"external_id": "a"}, {"external_id": "b"}])

    def test_delete_event_por_id_numerico(self):
        # Eventos manuais (sem external_id) so podem ser apagados por id.
        session = _FakeSession([_FakeResponse(200, {})])
        client = _client(session)
        status = client.delete_event(136554084)
        self.assertEqual(status, 200)
        method, url, _ = session.calls[0]
        self.assertEqual(method, "DELETE")
        self.assertIn("/events/136554084", url)

    def test_activity_streams_achata_lista(self):
        session = _FakeSession([
            _FakeResponse(200, [{"type": "watts", "data": [1, 2]},
                                {"type": "time", "data": [3, 4]}]),
        ])
        client = _client(session)
        self.assertEqual(client.activity_streams("i1"),
                         {"watts": [1, 2], "time": [3, 4]})


class IntervalsApiErrorTest(unittest.TestCase):
    def test_e_subclasse_de_request_exception(self):
        self.assertTrue(issubclass(IntervalsApiError,
                                   requests.exceptions.RequestException))

    def test_retry_status_tem_429_e_5xx(self):
        self.assertEqual(RETRY_STATUS, {429, 500, 502, 503, 504})


if __name__ == "__main__":
    unittest.main()