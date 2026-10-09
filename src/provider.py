# Hermes Coach - Provider boundary (UI-3)
#
# Contratos, capabilities, records normalizados e taxonomia de erro para
# plataformas externas de treino. O provider concreto (Intervals.icu) vive
# atras destes contratos; Application/dominio nao devem depender de shapes
# especificos do provider. Details `icu_*` ficam no adapter.
#
from __future__ import annotations

from collections.abc import Mapping
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Optional, Protocol, Tuple, runtime_checkable

_MISSING = object()


class ProviderCapability(str, Enum):
    """O que um provider sabe fazer, consultavel sem `if provider_name == ...`."""

    READ_EVENTS = "read_events"
    READ_WELLNESS = "read_wellness"
    READ_ACTIVITIES = "read_activities"
    WRITE_WORKOUTS = "write_workouts"
    UPDATE_WORKOUTS = "update_workouts"
    DELETE_WORKOUTS = "delete_workouts"
    COMPLETION_LINKS = "completion_links"
    READ_ACTIVITY_STREAMS = "read_activity_streams"
    READ_HEART_RATE_STREAM = "read_heart_rate_stream"


class ProviderError(Exception):
    """Base de falhas do boundary de provider (sem vazar HTTP/`requests`)."""


class ProviderUnavailable(ProviderError):
    """Falha transitoria: rede/timeout/rate-limit/servico instavel."""


class ProviderAuthError(ProviderError):
    """Credenciais rejeitadas pelo provider."""


class ProviderOperationError(ProviderError):
    """Qualquer outra falha do provider ou do protocolo."""


class NormalizedRecord(Mapping):
    """Visao de leitura sobre um payload do provider + acessores normalizados.

    Item access devolve o payload ORIGINAL do provider quando a chave existe
    nele (`record["external_id"]`, `dict(record)`), preservando o comportamento
    dos consumidores legados durante a transicao. Chaves so normalizadas
    (`record.get("ctl")`) resolvem pelo valor normalizado, e os campos tambem
    sao expostos como atributos (`record.ctl`). Codigo novo deve preferir
    atributos ou `normalized()`.
    """

    def __init__(self, raw: Optional[Dict[str, Any]] = None,
                 normalized: Optional[Dict[str, Any]] = None):
        self._raw: Dict[str, Any] = dict(raw or {})
        self._normalized: Dict[str, Any] = dict(normalized or {})

    def __getitem__(self, key: str) -> Any:
        if key in self._raw:
            return self._raw[key]
        value = self._normalized.get(key, _MISSING)
        if value is not _MISSING and value is not None:
            return value
        raise KeyError(key)

    def __iter__(self) -> Iterator[str]:
        return iter(self._raw)

    def __len__(self) -> int:
        return len(self._raw)

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        state = self.__dict__
        normalized = state.get("_normalized") or {}
        if name in normalized:
            return normalized[name]
        raw = state.get("_raw") or {}
        if name in raw:
            return raw[name]
        raise AttributeError(name)

    @property
    def raw(self) -> Dict[str, Any]:
        """Payload original (linkage/transicao). Nao usar como identidade."""
        return dict(self._raw)

    def normalized(self) -> Dict[str, Any]:
        return dict(self._normalized)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._normalized!r})"


class TrainingEvent(NormalizedRecord):
    """Evento/treino normalizado (planejado ou realizado).

    Identidade local NAO mora aqui: `external_id`/`paired_activity_id`/
    `activity_id` sao linkage metadata do provider. A identidade local e o
    `HermesWorkoutId`. A construcao a partir do payload bruto e responsabilidade
    do adapter concreto, que conhece os nomes de campo do provider.
    """

    @property
    def is_completed(self) -> bool:
        """Evidencia de execucao via linkage (nao e lifecycle local)."""
        return bool(self.paired_activity_id or self.activity_id)


class WellnessSnapshot(NormalizedRecord):
    """Leitura diaria de wellness; sinais observados, sem virar prescricao."""


class ActivitySnapshot(NormalizedRecord):
    """Atividade realizada (completion evidence / resumo)."""


@dataclass(frozen=True)
class ActivityStreamPoint:
    """Amostra temporal normalizada de atividade observada.

    `elapsed_seconds` e offset desde o inicio da atividade, nunca timestamp
    absoluto inventado. Valores ausentes ou estruturalmente invalidos ficam em
    `None`; potencia zero e preservada como observacao valida.
    """

    elapsed_seconds: Optional[float]
    power: Optional[float] = None
    heart_rate: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"elapsed_seconds": self.elapsed_seconds, "power": self.power,
                "heart_rate": self.heart_rate}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityStreamPoint":
        return cls(elapsed_seconds=data.get("elapsed_seconds"),
                   power=data.get("power"), heart_rate=data.get("heart_rate"))


@dataclass(frozen=True)
class ActivityStream:
    """Serie temporal provider-independent para uma atividade observada.

    Pontos existem somente quando as series devolvidas pelo provider tem o
    mesmo comprimento do eixo de tempo. STREAM-1 nao interpola nem preenche
    series desalinhadas; `alignment` e `*_samples` preservam esse diagnostico.
    """

    provider: str
    activity_id: str
    points: Tuple[ActivityStreamPoint, ...] = ()
    available_fields: Tuple[str, ...] = ()
    alignment: str = "empty"
    time_samples: int = 0
    power_samples: int = 0
    heart_rate_samples: Optional[int] = None
    captured_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "provider": self.provider, "activity_id": self.activity_id,
            "points": [point.to_dict() for point in self.points],
            "available_fields": list(self.available_fields),
            "alignment": self.alignment, "time_samples": self.time_samples,
            "power_samples": self.power_samples,
            "heart_rate_samples": self.heart_rate_samples,
            "captured_at": self.captured_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActivityStream":
        return cls(
            provider=str(data.get("provider") or ""),
            activity_id=str(data.get("activity_id") or ""),
            points=tuple(ActivityStreamPoint.from_dict(point)
                         for point in (data.get("points") or [])
                         if isinstance(point, dict)),
            available_fields=tuple(str(field) for field in
                                   (data.get("available_fields") or [])),
            alignment=str(data.get("alignment") or "empty"),
            time_samples=int(data.get("time_samples") or 0),
            power_samples=int(data.get("power_samples") or 0),
            heart_rate_samples=data.get("heart_rate_samples"),
            captured_at=data.get("captured_at"))


@runtime_checkable
class TrainingMetricsProvider(Protocol):
    """Leitura de carga/wellness exigida pela Application (UI-1/UI-3).

    `events`/`wellness` devolvem records normalizados. O fake de teste pode
    devolver qualquer Mapping (inclusive dict cru) durante a transicao.
    """

    def events(self, oldest: str, newest: str) -> List[TrainingEvent]: ...
    def wellness(self, oldest: str, newest: str) -> List[WellnessSnapshot]: ...


@runtime_checkable
class ActivityProvider(Protocol):
    """Leitura de detalhe de atividade (usada pelo resumo)."""

    def activity(self, activity_id: Any) -> ActivitySnapshot: ...


@runtime_checkable
class ActivityStreamProvider(Protocol):
    """Leitura remota de uma serie temporal ja normalizada."""

    def activity_stream(self, activity_id: Any) -> ActivityStream: ...


@runtime_checkable
class WorkoutSyncProvider(Protocol):
    """Escrita/sincronizacao de treinos no provider (push)."""

    def create_events(self, payloads: List[Dict[str, Any]],
                      upsert: bool = True): ...
    def delete_events(self, external_ids: List[str]): ...
    def delete_event(self, event_id: Any): ...


def provider_capabilities(provider: Any) -> frozenset:
    """Capabilities declaradas pelo provider; vazio se ele nao declarar."""
    caps = getattr(provider, "capabilities", None)
    if not caps:
        return frozenset()
    return frozenset(caps)
