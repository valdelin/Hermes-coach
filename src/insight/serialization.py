"""Serialização canônica e limitada do InsightView."""
from __future__ import annotations

from .contract import InsightView
from .limits import (MAX_INSIGHT_VIEW_BYTES, canonical_json_bytes,
                     require_max_size)


def serialize_insight_view(view: InsightView) -> bytes:
    """Retorna bytes JSON determinísticos sem metadata de runtime ou provider."""
    if not isinstance(view, InsightView):
        raise ValueError("view deve ser InsightView")
    payload = {
        "schema_version": view.schema_version,
        "subject": view.subject,
        "facts": [
            {
                "key": fact.key,
                "value": fact.value,
                "classification": fact.classification.value,
                "unit": fact.unit,
            }
            for fact in view.facts
        ],
        "advisory": None if view.advisory is None else {"text": view.advisory.text},
        "prescribed_session": (
            None if view.prescribed_session is None
            else {"summary": view.prescribed_session.summary}
        ),
        "observed_execution": (
            None if view.observed_execution is None else {
                "availability": view.observed_execution.availability.value,
                "summary": view.observed_execution.summary,
            }
        ),
        "provenance": [{"name": source.name} for source in view.provenance],
    }
    serialized = canonical_json_bytes(payload)
    require_max_size(len(serialized), "serialized_view_bytes", MAX_INSIGHT_VIEW_BYTES)
    return serialized
