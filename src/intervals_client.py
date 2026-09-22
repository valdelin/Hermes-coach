import requests


class IntervalsClient:
    BASE = "https://intervals.icu/api/v1/athlete"
    API_ROOT = "https://intervals.icu/api/v1"

    def __init__(self, athlete_id, api_key, session=None):
        self.base = f"{self.BASE}/{athlete_id}"
        self.auth = ("API_KEY", api_key)
        self.session = session or requests.Session()

    def events(self, **params):
        return self._get("/events", params)

    def wellness(self, **params):
        return self._get("/wellness", params)

    def create_events(self, payloads, upsert=True):
        resp = self.session.post(
            f"{self.base}/events/bulk",
            params={"upsert": "true" if upsert else "false"},
            json=payloads,
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.status_code, resp.json()

    def delete_events(self, external_ids):
        resp = self.session.put(
            f"{self.base}/events/bulk-delete",
            json=[{"external_id": eid} for eid in external_ids],
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.status_code, resp.json()

    def _get(self, path, params):
        resp = self.session.get(
            f"{self.base}{path}",
            params=params or None,
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def activity(self, activity_id):
        """Detalhe de uma atividade: GET /api/v1/activity/{id} (fora do escopo
        do atleta). Usado pelo ftp-scan para avaliar treinos fora do plano."""
        resp = self.session.get(
            f"{self.API_ROOT}/activity/{activity_id}",
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def activity_streams(self, activity_id, types=("watts", "time")):
        """Streams de uma atividade: GET /api/v1/activity/{id}/streams.json.
        Retorna dict {type: data} (ex.: {"watts": [...], "time": [...]})."""
        resp = self.session.get(
            f"{self.API_ROOT}/activity/{activity_id}/streams.json",
            params={"types": ",".join(types)},
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        streams = resp.json()
        if isinstance(streams, list):
            return {s["type"]: (s.get("data") or []) for s in streams}
        return streams or {}

    def sport_settings(self):
        """Configuracoes por esporte do atleta: GET /athlete/{id}/sport-settings."""
        return self._get("/sport-settings", {})

    def put_sport_settings(self, sport_settings_id, payload):
        """PUT /athlete/{id}/sport-settings/{id} (ex.: atualizar indoor_ftp)."""
        resp = self.session.put(
            f"{self.base}/sport-settings/{sport_settings_id}",
            json=payload,
            auth=self.auth,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.status_code, resp.json()