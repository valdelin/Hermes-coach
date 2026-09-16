import requests


class IntervalsClient:
    BASE = "https://intervals.icu/api/v1/athlete"

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