"""Historico local de referencias de FTP confirmadas pelo usuario."""
from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


SCHEMA_VERSION = 1


class FtpReferenceSource(str, Enum):
    USER_ENTERED = "user_entered"
    HERMES_TEST = "hermes_test"
    ZWIFT_TEST = "zwift_test"
    OTHER_PLATFORM_TEST = "other_platform_test"
    COACH_DEFINED = "coach_defined"


class FtpProtocol(str, Enum):
    FTP_20_MIN = "ftp_20_min"
    RAMP_TEST = "ramp_test"
    FTP_60_MIN = "ftp_60_min"
    PLATFORM_RESULT = "platform_result"
    COACH_DEFINED = "coach_defined"
    UNKNOWN = "unknown"


def _aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} deve ser datetime timezone-aware")
    return value


def _parse_datetime(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} deve ser ISO-8601")
    try:
        return _aware(datetime.fromisoformat(value), field_name)
    except ValueError as exc:
        raise ValueError(f"{field_name} invalido: {value!r}") from exc


@dataclass(frozen=True)
class FtpReference:
    """Referencia canônica confirmada, com inicio de vigencia explicito."""

    id: str
    value_watts: float
    effective_from: datetime
    recorded_at: datetime
    source: FtpReferenceSource
    protocol: Optional[FtpProtocol] = None
    evidence_activity_id: Optional[str] = None
    evidence_workout_id: Optional[str] = None
    evidence_id: Optional[str] = None
    provider: Optional[str] = None
    notes: Optional[str] = None
    supersedes_reference_id: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id da referencia FTP deve ser nao vazio")
        try:
            watts = float(self.value_watts)
        except (TypeError, ValueError) as exc:
            raise ValueError("value_watts deve ser numerico") from exc
        if not math.isfinite(watts) or watts <= 0:
            raise ValueError("value_watts deve ser finito e maior que zero")
        object.__setattr__(self, "value_watts", watts)
        _aware(self.effective_from, "effective_from")
        _aware(self.recorded_at, "recorded_at")
        try:
            object.__setattr__(self, "source", FtpReferenceSource(self.source))
        except ValueError as exc:
            raise ValueError(f"source FTP invalido: {self.source!r}") from exc
        if self.protocol is not None:
            try:
                object.__setattr__(self, "protocol", FtpProtocol(self.protocol))
            except ValueError as exc:
                raise ValueError(f"protocol FTP invalido: {self.protocol!r}") from exc
        if self.supersedes_reference_id == self.id:
            raise ValueError("uma referencia nao pode substituir a si mesma")

    @property
    def ftp_value(self) -> float:
        return self.value_watts

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "value_watts": self.value_watts,
            "effective_from": self.effective_from.isoformat(),
            "recorded_at": self.recorded_at.isoformat(),
            "source": self.source.value,
            "protocol": self.protocol.value if self.protocol else None,
            "evidence_activity_id": self.evidence_activity_id,
            "evidence_workout_id": self.evidence_workout_id,
            "evidence_id": self.evidence_id,
            "provider": self.provider,
            "notes": self.notes,
            "supersedes_reference_id": self.supersedes_reference_id,
        }

    @classmethod
    def from_dict(cls, data: Any) -> "FtpReference":
        if not isinstance(data, dict):
            raise ValueError("referencia FTP deve ser objeto")
        required = ("id", "value_watts", "effective_from", "recorded_at", "source")
        missing = [name for name in required if name not in data]
        if missing:
            raise ValueError(f"referencia FTP sem campos obrigatorios: {', '.join(missing)}")
        return cls(
            id=data["id"], value_watts=data["value_watts"],
            effective_from=_parse_datetime(data["effective_from"], "effective_from"),
            recorded_at=_parse_datetime(data["recorded_at"], "recorded_at"),
            source=FtpReferenceSource(data["source"]),
            protocol=FtpProtocol(data["protocol"]) if data.get("protocol") else None,
            evidence_activity_id=data.get("evidence_activity_id"),
            evidence_workout_id=data.get("evidence_workout_id"),
            evidence_id=data.get("evidence_id"),
            provider=data.get("provider"), notes=data.get("notes"),
            supersedes_reference_id=data.get("supersedes_reference_id"),
        )


@dataclass(frozen=True)
class FtpHistory:
    """Historico auditavel; somente referencias confirmadas entram aqui."""

    references: tuple[FtpReference, ...] = ()
    athlete_id: Optional[str] = None

    def __post_init__(self) -> None:
        refs = tuple(sorted(
            self.references,
            key=lambda reference: (reference.effective_from, reference.recorded_at,
                                   reference.id)))
        ids = [reference.id for reference in refs]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de referencias FTP devem ser unicos")
        by_id = {reference.id: reference for reference in refs}
        for reference in refs:
            target = reference.supersedes_reference_id
            if target is None:
                continue
            if target not in by_id:
                raise ValueError(f"referencia FTP substituida inexistente: {target}")
            if reference.effective_from != by_id[target].effective_from:
                raise ValueError("correcao FTP deve manter effective_from original")
        self._validate_corrections(by_id)
        superseded = {reference.supersedes_reference_id for reference in refs
                      if reference.supersedes_reference_id is not None}
        active = [reference for reference in refs if reference.id not in superseded]
        effective_from = [reference.effective_from for reference in active]
        if len(effective_from) != len(set(effective_from)):
            raise ValueError("referencias FTP ativas nao podem compartilhar effective_from")
        object.__setattr__(self, "references", refs)

    @staticmethod
    def _validate_corrections(by_id: dict[str, FtpReference]) -> None:
        for reference in by_id.values():
            visited = set()
            current = reference
            while current.supersedes_reference_id is not None:
                if current.id in visited:
                    raise ValueError("ciclo de correcoes FTP")
                visited.add(current.id)
                current = by_id[current.supersedes_reference_id]

    @property
    def active_references(self) -> tuple[FtpReference, ...]:
        superseded = {reference.supersedes_reference_id for reference in self.references
                      if reference.supersedes_reference_id is not None}
        return tuple(reference for reference in self.references
                     if reference.id not in superseded)

    def resolve_ftp_at(self, timestamp: datetime) -> Optional[FtpReference]:
        timestamp = _aware(timestamp, "timestamp")
        eligible = [reference for reference in self.active_references
                    if reference.effective_from <= timestamp]
        if not eligible:
            return None
        return max(eligible, key=lambda reference: reference.effective_from)

    def current_reference(self, now: datetime) -> Optional[FtpReference]:
        return self.resolve_ftp_at(now)

    def with_reference(self, reference: FtpReference) -> "FtpHistory":
        return FtpHistory(self.references + (reference,), athlete_id=self.athlete_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "athlete_id": self.athlete_id,
            "references": [reference.to_dict() for reference in self.references],
        }

    @classmethod
    def from_dict(cls, data: Any) -> "FtpHistory":
        if not isinstance(data, dict):
            raise ValueError("ftp history deve ser objeto")
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise ValueError(f"schema_version FTP desconhecida: {version!r}")
        refs = data.get("references")
        if not isinstance(refs, list):
            raise ValueError("references FTP deve ser lista")
        athlete_id = data.get("athlete_id")
        if athlete_id is not None and not isinstance(athlete_id, str):
            raise ValueError("athlete_id FTP deve ser texto ou null")
        return cls(tuple(FtpReference.from_dict(reference) for reference in refs),
                   athlete_id=athlete_id)


@dataclass(frozen=True)
class FtpHistoryRepository:
    path: Path

    def load(self) -> FtpHistory:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return FtpHistory()
        return FtpHistory.from_dict(json.loads(raw))

    def save(self, history: FtpHistory) -> Path:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(history.to_dict(), ensure_ascii=False, indent=2) + "\n"
        with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", dir=self.path.parent,
                prefix=f".{self.path.name}.", delete=False) as handle:
            handle.write(payload)
            temp_path = Path(handle.name)
        try:
            os.replace(temp_path, self.path)
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise
        return self.path
