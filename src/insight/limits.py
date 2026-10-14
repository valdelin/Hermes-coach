"""Limites operacionais e helpers de tamanho do INSIGHT M1.1-A."""
from __future__ import annotations

import json
from typing import Any


MAX_FACT_COUNT = 32
MAX_PROVENANCE_COUNT = 16
MAX_FACT_KEY_BYTES = 64
MAX_FACT_STRING_VALUE_BYTES = 512
MAX_FACT_UNIT_BYTES = 32
MAX_INSIGHT_VIEW_BYTES = 16_384
MAX_MODEL_INPUT_BYTES = 24_576
MAX_PROVIDER_RESPONSE_BYTES = 8_192
MAX_PRESENTATION_TOTAL_BYTES = 4_096

MAX_HEADLINE_CHARS = 240
MAX_EXPLANATION_CHARS = 2_000
MAX_NEXT_ACTION_TEXT_CHARS = 1_000
MAX_CAUTION_TEXT_CHARS = 1_000
MAX_TEMPLATE_CHARS = 2_000


class InsightSizeLimitError(ValueError):
    """Valor excedeu um limite operacional sem reter seu payload."""

    def __init__(self, limit_name: str, actual_size: int, max_size: int):
        if not isinstance(limit_name, str) or not limit_name.strip():
            raise ValueError("limit_name deve ser texto nao vazio")
        for value, name in ((actual_size, "actual_size"), (max_size, "max_size")):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name} deve ser inteiro nao negativo")
        self.limit_name = limit_name
        self.actual_size = actual_size
        self.max_size = max_size
        super().__init__(f"{limit_name} excede limite: {actual_size} > {max_size}")


def utf8_size(value: str) -> int:
    """Retorna o tamanho UTF-8 sem depender de locale."""
    if not isinstance(value, str):
        raise TypeError("value deve ser texto")
    return len(value.encode("utf-8"))


def require_max_size(actual_size: int, limit_name: str, max_size: int) -> None:
    """Falha fechada quando uma medida já calculada excede seu máximo."""
    if actual_size > max_size:
        raise InsightSizeLimitError(limit_name, actual_size, max_size)


def require_max_utf8_bytes(value: str, limit_name: str, max_size: int) -> None:
    """Valida um texto contra um orçamento em bytes UTF-8."""
    require_max_size(utf8_size(value), limit_name, max_size)


def canonical_json_bytes(payload: Any) -> bytes:
    """Codifica JSON estável usado pelos orçamentos canônicos do Insight."""
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def presentation_bytes(
        headline: str, explanation: str, next_action_text: str,
        caution_text: str | None,
) -> bytes:
    """Representação canônica fechada usada no orçamento total da Presentation."""
    return canonical_json_bytes({
        "headline": headline,
        "explanation": explanation,
        "next_action_text": next_action_text,
        "caution_text": caution_text,
    })
