# Hermes Coach - IntervalsAdapter (UI-3)
#
# Unico ponto que conhece os detalhes da API do Intervals.icu: nomes de campo
# (`icu_*`, `paired_activity_id`, `external_id`), shapes e semantica de erro HTTP.
# A Application consome os contratos de `provider.py`; trocar de plataforma
# significa escrever outro adapter, nao tocar em casos de uso/dominio.
#
from __future__ import annotations

import math
from dataclasses import replace
from typing import Any, Dict, List, Optional

import requests

try:
    from .provider import (ActivitySnapshot, ActivityStream, ActivityStreamPoint,
                           ProviderAuthError, ProviderCapability,
                           ProviderError, ProviderOperationError,
                           ProviderUnavailable, TrainingEvent, WellnessSnapshot)
    from .intervals_client import IntervalsApiError
except ImportError:  # execucao como script solto
    from provider import (ActivitySnapshot, ActivityStream, ActivityStreamPoint,
                          ProviderAuthError,
                          ProviderCapability, ProviderError,
                          ProviderOperationError, ProviderUnavailable,
                          TrainingEvent, WellnessSnapshot)
    from intervals_client import IntervalsApiError


DEFAULT_CAPABILITIES = frozenset({
    ProviderCapability.READ_EVENTS,
    ProviderCapability.READ_WELLNESS,
    ProviderCapability.READ_ACTIVITIES,
    ProviderCapability.WRITE_WORKOUTS,
    ProviderCapability.UPDATE_WORKOUTS,
    ProviderCapability.DELETE_WORKOUTS,
    ProviderCapability.COMPLETION_LINKS,
    ProviderCapability.READ_ACTIVITY_STREAMS,
    ProviderCapability.READ_HEART_RATE_STREAM,
})


# ---------------------------------------------------------------------------
# Traducao Intervals bruto -> records normalizados
# ---------------------------------------------------------------------------
# Unico lugar que conhece os nomes `icu_*`/`restingHR`/`paired_activity_id`.
# Os DTOs em `provider.py` sao agnosticos de provider.

def _training_event(raw: Dict[str, Any]) -> TrainingEvent:
    raw = dict(raw or {})
    return TrainingEvent(raw=raw, normalized={
        "provider_event_id": raw.get("id") or raw.get("uid"),
        "start_date": raw.get("start_date_local") or raw.get("start_time_local"),
        "category": raw.get("category"),
        "type": raw.get("type"),
        "name": raw.get("name"),
        "training_load": raw.get("icu_training_load"),
        "tss": raw.get("tss"),
        "ctl": raw.get("icu_ctl"),
        "atl": raw.get("icu_atl"),
        "tsb": raw.get("icu_tsb"),
        "ftp": raw.get("icu_ftp"),
        "external_id": raw.get("external_id"),
        "paired_activity_id": raw.get("paired_activity_id"),
        "activity_id": raw.get("activity_id"),
        "distance": raw.get("distance"),
        "moving_time": raw.get("moving_time"),
        "elapsed_time": raw.get("elapsed_time"),
    })


def _wellness_snapshot(raw: Dict[str, Any]) -> WellnessSnapshot:
    raw = dict(raw or {})
    return WellnessSnapshot(raw=raw, normalized={
        "day": raw.get("id") or raw.get("date"),
        "resting_hr": raw.get("restingHR"),
        "hrv": raw.get("hrv"),
        "hrv_sdnn": raw.get("hrvSDNN"),
        "sleep_secs": raw.get("sleepSecs"),
        "steps": raw.get("steps"),
        "stress": raw.get("stress"),
        "weight": raw.get("weight"),
    })


def _activity_snapshot(raw: Dict[str, Any]) -> ActivitySnapshot:
    raw = dict(raw or {})
    start = raw.get("start_date_local") or raw.get("start_date") or ""
    return ActivitySnapshot(raw=raw, normalized={
        "provider_activity_id": raw.get("id"),
        "day": start[:10] or None,
        "name": raw.get("name"),
        "type": raw.get("type"),
        "training_load": raw.get("icu_training_load") or raw.get("tss"),
        "moving_time": raw.get("moving_time"),
        "elapsed_time": raw.get("elapsed_time"),
        "distance": raw.get("distance"),
        "elevation_gain": raw.get("total_elevation_gain"),
        "avg_power": raw.get("icu_average_watts") or raw.get("average_power"),
        "np": raw.get("icu_weighted_avg_watts"),
        "avg_hr": raw.get("average_heartrate"),
    })


def _number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _activity_stream(raw: Any, activity_id: Any) -> ActivityStream:
    """Traduz somente streams cujo formato esta confirmado neste projeto.

    Intervals usa arrays `time`, `watts` e `heartrate` no endpoint. A chave de
    FC e confirmada por STREAM-2B: tres VirtualRides reais retornaram arrays de
    mesmo comprimento, com `time` monotono de 0 ate moving_time e media de HR
    coerente com `average_heartrate`. `time` representa offset em segundos desde
    o inicio; nenhum timestamp absoluto e fabricado. `fixed_heartrate` e uma
    variante do provider, nao um alias silencioso, e nao e usada aqui.
    """
    streams = raw if isinstance(raw, dict) else {}
    times = streams.get("time")
    watts = streams.get("watts")
    heart_rates = streams.get("heartrate")
    times = list(times) if isinstance(times, list) else []
    watts = list(watts) if isinstance(watts, list) else []
    has_heart_rates = isinstance(heart_rates, list)
    heart_rates = list(heart_rates) if has_heart_rates else []
    fields = tuple(name for name, values in (
        ("power", streams.get("watts")),
        ("heart_rate", streams.get("heartrate")),
    ) if isinstance(values, list))
    if not times and not watts and not heart_rates:
        alignment = "empty"
        points = ()
    elif not times:
        alignment = "missing_time"
        points = ()
    elif len(times) != len(watts):
        alignment = "length_mismatch"
        points = ()
    elif has_heart_rates and len(times) != len(heart_rates):
        alignment = "heart_rate_length_mismatch"
        points = ()
    else:
        values = [(_number(time), _number(power),
                   _number(heart_rates[index]) if has_heart_rates else None,
                   index)
                  for index, (time, power) in enumerate(zip(times, watts))]
        alignment = "aligned" if all(time is not None for time, _, _, _ in values) \
            else "invalid_time"
        # Mesmo timestamp preserva a ordem recebida; nenhum sample e agregado.
        if alignment == "aligned":
            values.sort(key=lambda item: (item[0], item[3]))
        points = tuple(ActivityStreamPoint(
            elapsed_seconds=time, power=power, heart_rate=heart_rate)
            for time, power, heart_rate, _ in values)
    return ActivityStream(provider="intervals", activity_id=str(activity_id),
                          points=points, available_fields=fields,
                          alignment=alignment, time_samples=len(times),
                          power_samples=len(watts),
                          heart_rate_samples=(len(heart_rates)
                                              if has_heart_rates else None))


class IntervalsAdapter:
    """Adapter concreto do provider Intervals.icu.

    Implementa os contratos de leitura (`TrainingMetricsProvider`,
    `ActivityProvider`) e escrita (`WorkoutSyncProvider`) traduzindo respostas
    brutas em records normalizados e erros HTTP em `ProviderError`.
    """

    provider_name = "intervals"

    def __init__(self, client: Any,
                 capabilities: Optional[frozenset] = None) -> None:
        self._client = client
        self.capabilities = frozenset(capabilities or DEFAULT_CAPABILITIES)

    # -- error boundary --------------------------------------------------
    @staticmethod
    def _translate(exc: Exception) -> ProviderError:
        status = getattr(exc, "status", None)
        if status in (401, 403):
            return ProviderAuthError(str(exc))
        if status is None or status in (429, 500, 502, 503, 504):
            return ProviderUnavailable(str(exc))
        return ProviderOperationError(str(exc))

    def _call(self, fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except IntervalsApiError as exc:
            raise self._translate(exc) from exc
        except requests.exceptions.RequestException as exc:
            raise ProviderOperationError(str(exc)) from exc

    # -- reads -----------------------------------------------------------
    def events(self, oldest: Optional[str] = None,
               newest: Optional[str] = None) -> List[TrainingEvent]:
        raw = self._call(self._client.events, oldest=oldest, newest=newest)
        return [_training_event(e) for e in (raw or [])]

    def wellness(self, oldest: Optional[str] = None,
                 newest: Optional[str] = None) -> List[WellnessSnapshot]:
        raw = self._call(self._client.wellness, oldest=oldest, newest=newest)
        return [_wellness_snapshot(w) for w in (raw or [])]

    def activity(self, activity_id: Any) -> ActivitySnapshot:
        raw = self._call(self._client.activity, activity_id)
        return _activity_snapshot(raw)

    def activity_stream(self, activity_id: Any) -> ActivityStream:
        """Busca e normaliza a serie temporal confirmada do Intervals."""
        raw = self._call(self._client.activity_streams, activity_id,
                         types=("time", "watts", "heartrate"))
        return _activity_stream(raw, activity_id)

    # -- writes ----------------------------------------------------------
    def create_events(self, payloads: List[Dict[str, Any]], upsert: bool = True):
        # `upsert=True` e o default do client; so repassamos quando explicito
        # para nao quebrar fakes que nao aceitam o kwarg.
        if upsert is True:
            return self._call(self._client.create_events, payloads)
        return self._call(self._client.create_events, payloads, upsert=upsert)

    def delete_events(self, external_ids: List[str]):
        return self._call(self._client.delete_events, external_ids)

    def delete_event(self, event_id: Any):
        return self._call(self._client.delete_event, event_id)

    # -- provider-specific utilities (ftp-scan diagnostics) --------------
    def activity_streams(self, activity_id: Any, types=("watts", "time")):
        return self._call(self._client.activity_streams, activity_id, types=types)

    def sport_settings(self):
        return self._call(self._client.sport_settings)

    def put_sport_settings(self, sport_settings_id: Any, payload: Dict[str, Any]):
        return self._call(self._client.put_sport_settings, sport_settings_id,
                          payload)
