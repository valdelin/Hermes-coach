# Hermes Coach — Snapshot normalizado + freshness de sync (UI-4)
#
# Separa TRES eixos que antes se misturavam no payload cru do provider:
#
#   1. lifecycle LOCAL do treino (UI-2, `workout["lifecycle"]`);
#   2. evidencia de execucao observada no provider (aqui, `is_completed`);
#   3. estado/freshness da sincronizacao externa (aqui, `SyncFreshness`).
#
# O snapshot e um cache de LEITURA: guarda os campos canonicos que os workflows
# consomem, com timestamp de captura e origem. Fica em arquivo separado para
# nao inchar o `plan.json` nem acoplar plano a cache. Ler o snapshot NAO exige
# provider.
from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from provider_fields import canonical
except ImportError:  # execucao como pacote (src.snapshot)
    from .provider_fields import canonical  # type: ignore


class FreshnessStatus(str, Enum):
    FRESH = "fresh"
    STALE = "stale"
    UNKNOWN = "unknown"


# Politica OPERACIONAL (nao fisiologica, nao prescritiva): uma captura de
# provider mais velha que isto e considerada stale para fins de sincronizacao.
# E um default explicito e sobrescrivivel pelo chamador, nao um limiar oculto.
DEFAULT_STALE_AFTER_HOURS = 36.0


def _utc(now: Optional[datetime] = None) -> datetime:
    if now is None:
        return datetime.now(timezone.utc)
    if now.tzinfo is None:
        return now.replace(tzinfo=timezone.utc)
    return now


@dataclass(frozen=True)
class SyncFreshness:
    """Quando os dados externos foram observados e se isto ainda e recente."""

    synced_at: Optional[str] = None
    provider: Optional[str] = None
    stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS

    @classmethod
    def unknown(cls, provider: Optional[str] = None) -> "SyncFreshness":
        return cls(synced_at=None, provider=provider)

    @classmethod
    def captured(cls, *, provider: Optional[str] = None,
                 now: Optional[datetime] = None,
                 stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS
                 ) -> "SyncFreshness":
        return cls(synced_at=_utc(now).isoformat(), provider=provider,
                   stale_after_hours=stale_after_hours)

    def age_seconds(self, now: Optional[datetime] = None) -> Optional[float]:
        if not self.synced_at:
            return None
        try:
            at = datetime.fromisoformat(self.synced_at)
        except ValueError:
            return None
        if at.tzinfo is None:
            at = at.replace(tzinfo=timezone.utc)
        return (_utc(now) - at).total_seconds()

    def status(self, now: Optional[datetime] = None) -> FreshnessStatus:
        age = self.age_seconds(now=now)
        if age is None:
            return FreshnessStatus.UNKNOWN
        limit = self.stale_after_hours * 3600
        return FreshnessStatus.FRESH if age <= limit else FreshnessStatus.STALE

    def to_dict(self) -> Dict[str, Any]:
        return {"synced_at": self.synced_at, "provider": self.provider,
                "stale_after_hours": self.stale_after_hours}

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "SyncFreshness":
        if not data:
            return cls.unknown()
        try:
            hours = float(data.get("stale_after_hours",
                                   DEFAULT_STALE_AFTER_HOURS))
        except (TypeError, ValueError):
            hours = DEFAULT_STALE_AFTER_HOURS
        return cls(synced_at=data.get("synced_at"),
                   provider=data.get("provider"), stale_after_hours=hours)


@dataclass(frozen=True)
class TrainingSnapshot:
    """Cache normalizado do estado externo (eventos, wellness, atividades).

    `events`/`wellness`/`activities` sao listas de dicts CANONICOS (seman-
    tica de `provider_fields.canonical`): ler o snapshot nao exige conhecer o
    provider. Vazio (nunca sincronizado) e valido e nao implica erro.
    """

    events: List[Dict[str, Any]] = dc_field(default_factory=list)
    wellness: List[Dict[str, Any]] = dc_field(default_factory=list)
    activities: List[Dict[str, Any]] = dc_field(default_factory=list)
    metrics: Optional[Dict[str, Any]] = None
    captured_at: Optional[str] = None
    provider: Optional[str] = None
    freshness: SyncFreshness = dc_field(default_factory=SyncFreshness.unknown)

    @classmethod
    def capture(cls, *, events: Any = None, wellness: Any = None,
                activities: Any = None, metrics: Optional[Dict[str, Any]] = None,
                provider: Optional[str] = None,
                now: Optional[datetime] = None,
                stale_after_hours: float = DEFAULT_STALE_AFTER_HOURS
                ) -> "TrainingSnapshot":
        captured = _utc(now).isoformat()
        return cls(
            events=[canonical(e) for e in (events or [])],
            wellness=[canonical(w, with_completion=False) for w in (wellness or [])],
            activities=[canonical(a, with_completion=False)
                        for a in (activities or [])],
            metrics=metrics, captured_at=captured, provider=provider,
            freshness=SyncFreshness(synced_at=captured, provider=provider,
                                    stale_after_hours=stale_after_hours))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "events": self.events, "wellness": self.wellness,
            "activities": self.activities, "metrics": self.metrics,
            "captured_at": self.captured_at, "provider": self.provider,
            "freshness": self.freshness.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "TrainingSnapshot":
        if not data:
            return cls()
        return cls(
            events=list(data.get("events") or []),
            wellness=list(data.get("wellness") or []),
            activities=list(data.get("activities") or []),
            metrics=data.get("metrics"),
            captured_at=data.get("captured_at"),
            provider=data.get("provider"),
            freshness=SyncFreshness.from_dict(data.get("freshness")))

    def save(self, path: Any) -> pathlib.Path:
        out = pathlib.Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, ensure_ascii=False, indent=2)
        return out

    @classmethod
    def load(cls, path: Any) -> "TrainingSnapshot":
        """Le o snapshot persistido; vazio quando ausente/corrompido (sem erro)."""
        try:
            with open(pathlib.Path(path), "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()
        return cls.from_dict(data)
