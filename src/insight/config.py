"""Configuração fail-closed do rollout online INSIGHT M2-8."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


INSIGHT_ENABLED_ENV = "HERMES_INSIGHT_ENABLED"
INSIGHT_ONLINE_ENABLED_ENV = "HERMES_INSIGHT_ONLINE_ENABLED"
OPENAI_API_KEY_ENV = "OPENAI_API_KEY"
INSIGHT_PROVIDER = "openai"
INSIGHT_MODEL = "gpt-5.4-nano-2026-03-17"

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


def parse_insight_flag(value: object) -> bool:
    """Aceita somente valores explicitamente autorizados; desconhecidos são OFF."""
    return isinstance(value, str) and value.strip().lower() in _TRUE_VALUES


@dataclass(frozen=True)
class InsightRuntimeConfig:
    """Configuração fechada sem credencial, provider variável ou modelo variável."""

    insight_enabled: bool
    online_enabled: bool
    provider: str = INSIGHT_PROVIDER
    requested_model: str = INSIGHT_MODEL

    def __post_init__(self) -> None:
        if type(self.insight_enabled) is not bool or type(self.online_enabled) is not bool:
            raise ValueError("flags de insight devem ser bool")
        if self.provider != INSIGHT_PROVIDER:
            raise ValueError("provider de insight não autorizado")
        if self.requested_model != INSIGHT_MODEL:
            raise ValueError("modelo de insight não autorizado")

    @property
    def online_permitted(self) -> bool:
        return self.insight_enabled and self.online_enabled


def load_insight_runtime_config(environment: Mapping[str, str]) -> InsightRuntimeConfig:
    """Carrega flags de mapping injetável, sem snapshot global nem I/O."""
    return InsightRuntimeConfig(
        insight_enabled=parse_insight_flag(environment.get(INSIGHT_ENABLED_ENV)),
        online_enabled=parse_insight_flag(environment.get(INSIGHT_ONLINE_ENABLED_ENV)),
    )


def read_openai_api_key(environment: Mapping[str, str]) -> Optional[str]:
    """Retorna só credencial não vazia quando o boundary online já foi autorizado."""
    value = environment.get(OPENAI_API_KEY_ENV)
    return value if isinstance(value, str) and value.strip() else None
