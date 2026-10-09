# Hermes Coach — Campos canonicos + aliases legados (boundary de leitura) UI-4
#
# Os modulos de dominio leem eventos/wellness/atividades por NOME CANONICO
# (`field(record, "training_load")`), nunca por campos especificos de um
# provider. Este e o UNICO lugar, alem do `intervals_adapter`, que conhece os
# nomes legados (`icu_*`, `restingHR`, `paired_activity_id`): records
# normalizados (UI-3) ja trazem os campos canonicos; dicionarios brutos legados
# (planos antigos, fakes de teste) continuam legiveis via a tabela de aliases.
#
# Nao e o contrato de provider (esse e `provider.py`, agnostico) nem o
# tradutor de payload (esse e o adapter): e a camada de compatibilidade de
# leitura compartilhada pelos dois lados.
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# name canonico -> aliases legados, em ordem de prioridade.
_ALIASES: Dict[str, Tuple[str, ...]] = {
    "provider_event_id": ("id", "uid"),
    # `start_date` usa `start_time_local` antes de `start_date_local` para
    # preservar o criterio historico do `coach._raw_metrics`.
    "start_date": ("start_time_local", "start_date_local"),
    "day": ("day", "start_date_local", "start_time_local", "id", "date"),
    "name": ("name",),
    "type": ("type",),
    "category": ("category",),
    "training_load": ("icu_training_load",),
    "tss": ("tss",),
    "ctl": ("icu_ctl",),
    "atl": ("icu_atl",),
    "tsb": ("icu_tsb",),
    "ftp": ("icu_ftp",),
    "external_id": ("external_id",),
    "paired_activity_id": ("paired_activity_id",),
    "activity_id": ("activity_id",),
    # Atividade efetivamente pareada (qualquer um dos dois vinculos).
    "completion_activity_id": ("activity_id", "paired_activity_id"),
    "moving_time": ("moving_time",),
    "elapsed_time": ("elapsed_time",),
    "distance": ("distance",),
    "elevation_gain": ("total_elevation_gain",),
    "avg_power": ("icu_average_watts", "average_power"),
    "np": ("icu_weighted_avg_watts",),
    "avg_hr": ("average_heartrate",),
    "resting_hr": ("restingHR",),
    "hrv": ("hrv",),
    "hrv_sdnn": ("hrvSDNN",),
    "sleep_secs": ("sleepSecs",),
    "sleep_score": ("sleepScore",),
    "readiness": ("readiness",),
    "stress": ("stress",),
    "weight": ("weight",),
}

ALL_FIELDS: Tuple[str, ...] = tuple(_ALIASES)


def field(source: Any, name: str, default: Any = None) -> Any:
    """Le um campo canonico, tolerante a record normalizado e a dict cru legado.

    Ordem: valor canonico no proprio objeto (records normalizados resolvem
    aqui via `NormalizedRecord.__getitem__`), depois os aliases legados.
    Valores `None` sao tratados como ausentes, para preservar os fallbacks
    historicos (`item.get("ctl", summary.get("ctl"))`).
    """
    if source is None:
        return default
    getter = getattr(source, "get", None)
    if callable(getter):
        value = getter(name)
        if value is not None:
            return value
        for alias in _ALIASES.get(name, ()):
            if alias == name:
                continue
            value = getter(alias)
            if value is not None:
                return value
        return default
    value = getattr(source, name, None)
    if value is not None:
        return value
    for alias in _ALIASES.get(name, ()):
        if alias == name:
            continue
        value = getattr(source, alias, None)
        if value is not None:
            return value
    return default


def is_completed(source: Any) -> bool:
    """Evidencia de que uma atividade correspondente foi observada.

    E evidencia, nao lifecycle local: `TrainingEvent.is_completed` (boundary)
    ou presenca de atividade pareada. Nao grava estado.
    """
    if getattr(source, "is_completed", None) is True:
        return True
    return bool(field(source, "completion_activity_id"))


def canonical(source: Any, fields: Optional[Tuple[str, ...]] = None,
              with_completion: bool = True) -> Dict[str, Any]:
    """Representacao canonica, JSON-safe, de um record/dict.

    Descarta chaves ausentes e nunca expoe nomes legados, para que o snapshot
    persistido possa ser lido sem conhecer o provider. `with_completion` so
    faz sentido para eventos.
    """
    out: Dict[str, Any] = {}
    for name in (fields or ALL_FIELDS):
        value = field(source, name)
        if value is not None:
            out[name] = value
    if with_completion:
        out["is_completed"] = is_completed(source)
    return out
