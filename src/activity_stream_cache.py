"""Cache local e separado para streams temporais observados (STREAM-1)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

try:
    from provider import ActivityStream
except ImportError:  # execucao como pacote (src.activity_stream_cache)
    from .provider import ActivityStream  # type: ignore


def _key(provider: str, activity_id: str) -> str:
    return f"{provider}:{activity_id}"


@dataclass(frozen=True)
class ActivityStreamCache:
    """Cache por provider + activity id; nao faz parte do training snapshot."""

    streams: Dict[str, ActivityStream] = field(default_factory=dict)

    def get(self, *, provider: str, activity_id: str) -> Optional[ActivityStream]:
        return self.streams.get(_key(provider, activity_id))

    def with_stream(self, stream: ActivityStream) -> "ActivityStreamCache":
        streams = dict(self.streams)
        streams[_key(stream.provider, stream.activity_id)] = stream
        return ActivityStreamCache(streams)

    def to_dict(self) -> dict:
        return {"streams": {key: stream.to_dict()
                            for key, stream in sorted(self.streams.items())}}

    @classmethod
    def from_dict(cls, data: object) -> "ActivityStreamCache":
        if not isinstance(data, dict) or not isinstance(data.get("streams"), dict):
            return cls()
        streams = {}
        for key, raw in data["streams"].items():
            if not isinstance(key, str) or not isinstance(raw, dict):
                continue
            stream = ActivityStream.from_dict(raw)
            if stream.provider and stream.activity_id:
                streams[key] = stream
        return cls(streams)

    def save(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                        encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "ActivityStreamCache":
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return cls()
        try:
            return cls.from_dict(data)
        except (TypeError, ValueError):
            return cls()
