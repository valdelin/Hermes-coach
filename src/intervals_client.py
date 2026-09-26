import time

import requests


# Falhas transitorias que valem retry com backoff: erros de rede/timeout e
# respostas HTTP 429 (rate limit) / 5xx (servico instavel). Erros de cliente
# (4xx) nao recebem retry — falham imediatamente.
RETRIES = 3
BACKOFF = 0.5  # segundos; dobra a cada tentativa (0.5, 1.0, 2.0)
RETRY_STATUS = {429, 500, 502, 503, 504}


class IntervalsApiError(requests.exceptions.RequestException):
    """Falha de comunicacao com o Intervals.icu apos tentativas de retry.

    Mensagem amigavel para o usuario (rede instavel, servico fora, credenciais
    invalidas) em vez de traceback cru de `requests`.
    """


class IntervalsClient:
    BASE = "https://intervals.icu/api/v1/athlete"
    API_ROOT = "https://intervals.icu/api/v1"

    def __init__(self, athlete_id, api_key, session=None, sleep=time.sleep):
        self.base = f"{self.BASE}/{athlete_id}"
        self.auth = ("API_KEY", api_key)
        self.session = session or requests.Session()
        self._sleep = sleep  # injetavel nos testes (evita espera real)

    def _request(self, method, url, params=None, json=None):
        """Executa uma chamada com retry/backoff para falhas transitorias.

        Retorna a `requests.Response` de sucesso (2xx/3xx). Falhas transitorias
        (rede/timeout/429/5xx) tentam `RETRIES` vezes; ao esgotar, levanta
        `IntervalsApiError` com mensagem amigavel. 4xx (exceto 429) falham
        imediatamente via `raise_for_status()`.
        """
        attempts = []
        for attempt in range(RETRIES):
            try:
                resp = self.session.request(
                    method, url, params=params, json=json,
                    auth=self.auth, timeout=30,
                )
            except (requests.exceptions.ConnectionError,
                    requests.exceptions.Timeout) as exc:
                attempts.append(type(exc).__name__)
                if attempt < RETRIES - 1:
                    self._sleep(BACKOFF * (2 ** attempt))
                    continue
                raise IntervalsApiError(
                    "nao foi possivel falar com o Intervals.icu apos "
                    f"{RETRIES} tentativas ({'; '.join(attempts)}). "
                    "Verifique a conexao e tente de novo."
                ) from exc

            if resp.status_code in RETRY_STATUS:
                attempts.append(f"HTTP {resp.status_code}")
                if attempt < RETRIES - 1:
                    self._sleep(BACKOFF * (2 ** attempt))
                    continue
                raise IntervalsApiError(
                    "o Intervals.icu respondeu "
                    f"HTTP {resp.status_code} apos {RETRIES} tentativas. "
                    "O servico pode estar instavel; tente de novo mais tarde."
                )

            if resp.status_code in (401, 403):
                raise IntervalsApiError(
                    "credenciais invalidas (HTTP "
                    f"{resp.status_code}) — confira INTERVALS_API_KEY "
                    "e INTERVALS_ATHLETE_ID no .env"
                )

            resp.raise_for_status()
            return resp

        # Inalcancavel: o loop sempre retorna ou levanta.
        raise IntervalsApiError("falha desconhecida na comunicacao com o Intervals.icu")

    def events(self, **params):
        return self._get("/events", params)

    def wellness(self, **params):
        return self._get("/wellness", params)

    def create_events(self, payloads, upsert=True):
        resp = self._request(
            "POST",
            f"{self.base}/events/bulk",
            params={"upsert": "true" if upsert else "false"},
            json=payloads,
        )
        return resp.status_code, resp.json()

    def delete_events(self, external_ids):
        resp = self._request(
            "PUT",
            f"{self.base}/events/bulk-delete",
            json=[{"external_id": eid} for eid in external_ids],
        )
        return resp.status_code, resp.json()

    def _get(self, path, params):
        resp = self._request("GET", f"{self.base}{path}", params=params or None)
        return resp.json()

    def activity(self, activity_id):
        """Detalhe de uma atividade: GET /api/v1/activity/{id} (fora do escopo
        do atleta). Usado pelo ftp-scan para avaliar treinos fora do plano."""
        resp = self._request(
            "GET", f"{self.API_ROOT}/activity/{activity_id}"
        )
        return resp.json()

    def activity_streams(self, activity_id, types=("watts", "time")):
        """Streams de uma atividade: GET /api/v1/activity/{id}/streams.json.
        Retorna dict {type: data} (ex.: {"watts": [...], "time": [...]})."""
        resp = self._request(
            "GET",
            f"{self.API_ROOT}/activity/{activity_id}/streams.json",
            params={"types": ",".join(types)},
        )
        streams = resp.json()
        if isinstance(streams, list):
            return {s["type"]: (s.get("data") or []) for s in streams}
        return streams or {}

    def sport_settings(self):
        """Configuracoes por esporte do atleta: GET /athlete/{id}/sport-settings."""
        return self._get("/sport-settings", {})

    def put_sport_settings(self, sport_settings_id, payload):
        """PUT /athlete/{id}/sport-settings/{id} (ex.: atualizar indoor_ftp)."""
        resp = self._request(
            "PUT",
            f"{self.base}/sport-settings/{sport_settings_id}",
            json=payload,
        )
        return resp.status_code, resp.json()