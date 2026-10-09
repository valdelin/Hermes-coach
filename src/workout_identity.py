# Hermes Coach — HermesWorkoutId (UI-2)
#
# Identidade LOCAL e estavel de um treino do Hermes, independente do provider.
# Nao confundir com `external_id` (vinculo com o Intervals.icu) nem com o
# `id` numerico de um evento externo: aqueles sao metadados de sincronizacao.
#
# Formato: UUIDv5 (RFC 4122) com namespace fixo do Hermes, derivado do `day`
# do treino. A escolha e deliberada:
#
#   - gerado pelo Hermes (o namespace e nosso, nao do provider);
#   - estavel entre leituras/escritas (mesmo `day` -> mesmo UUID sempre);
#   - nao depende de `external_id`, posicao em lista nem do provider;
#   - serializavel (string UUID canonica);
#   - trivial de testar e de migrar planos antigos (ver `ensure`).
#
# Nao usamos UUIDv4 aleatorio porque o plano tem no maximo UM treino por dia
# (`build_plan` substitui o dia ao inserir prova/recuperacao), entao o dia e
# uma chave natural estavel: um UUID aleatorio exigiria reconciliar identidade
# a cada rebuild e nao teria como migrar planos antigos de forma deterministica.
from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, List, Optional

WORKOUT_ID_FIELD = "id"

# Namespace derivado de uma URL propria; nao e um UUID magico embutido a mao.
_HERMES_NAMESPACE = uuid.uuid5(uuid.NAMESPACE_URL,
                               "https://hermes-coach.local/workout")


def for_day(day: str) -> str:
    """UUIDv5 estavel do treino do dia `day` (ISO `YYYY-MM-DD`)."""
    return str(uuid.uuid5(_HERMES_NAMESPACE, str(day)))


def for_workout(workout: Dict[str, Any]) -> Optional[str]:
    """Identidade derivada do treino, ou `None` se nao ha como derivar.

    Fallback em `external_id` apenas para planos legados degenerados sem `day`;
    nunca e a fonte preferida.
    """
    day = workout.get("day")
    if day:
        return for_day(str(day)[:10])
    eid = workout.get("external_id")
    if eid:
        return str(uuid.uuid5(_HERMES_NAMESPACE, str(eid)))
    return None


def ensure(workout: Dict[str, Any]) -> Dict[str, Any]:
    """Devolve o treino com `id` preenchido, sem mutar o original.

    Idempotente: se `id` ja existe, e preservado verbatim (e a persistencia
    que estabiliza a identidade; um plano legado recebe o mesmo UUID todas as
    vezes porque a derivacao e deterministica)."""
    if workout.get(WORKOUT_ID_FIELD):
        return workout
    novo = dict(workout)
    ident = for_workout(workout)
    if ident is not None:
        novo[WORKOUT_ID_FIELD] = ident
    return novo


def ensure_plan(plan: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [ensure(w) for w in plan]


def is_valid(value: Any) -> bool:
    """O valor e um UUID canonico? (aceita qualquer versao; o Hermes usa v5)."""
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except (ValueError, AttributeError, TypeError):
        return False
    return True
