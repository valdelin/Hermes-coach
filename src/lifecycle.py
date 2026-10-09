# Hermes Coach — Lifecycle local do treino (UI-2)
#
# Modelo explicito do ciclo de vida LOCAL de um treino do Hermes. Substitui a
# inferencia espalhada ("se tem external_id e paired_activity_id entao feito")
# por um vocabulario unico e um resolvedor puro.
#
# Duas camadas, de proposito:
#
#   DECLARADO (persistido em `workout["lifecycle"]`, default `planned`):
#     intencao local do atleta/treinador. Nao depende de provider.
#     planned | postponed | substituted | cancelled | completed | missed
#
#   OBSERVADO (resolvido em tempo de leitura por `derive`):
#     `completed`/`missed` normalmente sao derivados de (data + evidencia de
#     execucao). Podem tambem ser DECLARADOS manualmente (retro-atestacao),
#     e nesse caso vencem a derivacao.
#
# A dimensao de SINCRONIZACAO com o provider (evento publicado, atividade
# pareada, estado "desconhecido" com sync pendente) e OUTRO eixo e NAO entra
# aqui: ver `plan.session_execution_state`. UI-4 unifica completion/sync.
#
# `reconciled` NAO e estado deste lifecycle: no dominio atual ele e o
# livro-razao de faltas ja absorvidas (`absorbed_ids` no `plan.json`), ou seja,
# status de processamento/sync — nao um estado do treino. Forcar `reconciled`
# como lifecycle misturaria os dois eixos.
from __future__ import annotations

from typing import Any, Dict, Optional

LIFECYCLE_PLANNED = "planned"
LIFECYCLE_COMPLETED = "completed"
LIFECYCLE_MISSED = "missed"
LIFECYCLE_POSTPONED = "postponed"
LIFECYCLE_SUBSTITUTED = "substituted"
LIFECYCLE_CANCELLED = "cancelled"

ALL_LIFECYCLES = frozenset({
    LIFECYCLE_PLANNED, LIFECYCLE_COMPLETED, LIFECYCLE_MISSED,
    LIFECYCLE_POSTPONED, LIFECYCLE_SUBSTITUTED, LIFECYCLE_CANCELLED,
})

# Estados que representam decisao local (nao derivam de provider). `planned`
# e o default; `completed`/`missed` tambem podem ser declarados manualmente.
DECLARED_LIFECYCLES = ALL_LIFECYCLES

# Observados: normalmente resolvidos por `derive`, nao gravados.
OBSERVED_LIFECYCLES = frozenset({LIFECYCLE_COMPLETED, LIFECYCLE_MISSED})

# Transicoes validas de estado DECLARADO. Cada uma documenta o evento que a
# causa e se depende de sync externo:
#
#   planned  -> completed    execucao observada (sync: paired_activity_id)
#   planned  -> missed       dia passou sem evidencia de execucao
#   planned  -> postponed    atleta/treinador adia a sessao (local, sem sync)
#   planned  -> substituted  sessao trocada por outra (local, sem sync)
#   planned  -> cancelled    sessao cancelada (local, sem sync)
#   missed   -> *            remediacao manual (reabrir/adiar/trocar/executar)
#   postponed-> *            a sessao adiada volta a planned ou resolve
#   substituted -> cancelled/planned/completed/missed
#   cancelled-> planned      reabrir uma sessao cancelada
#   completed-> (nenhuma)    estado observado final; UI-4 define reversao por
#                            re-sync (aqui permanece terminal)
VALID_TRANSITIONS = {
    LIFECYCLE_PLANNED: {
        LIFECYCLE_COMPLETED, LIFECYCLE_MISSED, LIFECYCLE_POSTPONED,
        LIFECYCLE_SUBSTITUTED, LIFECYCLE_CANCELLED,
    },
    LIFECYCLE_POSTPONED: {
        LIFECYCLE_PLANNED, LIFECYCLE_COMPLETED, LIFECYCLE_MISSED,
        LIFECYCLE_SUBSTITUTED, LIFECYCLE_CANCELLED,
    },
    LIFECYCLE_SUBSTITUTED: {
        LIFECYCLE_PLANNED, LIFECYCLE_COMPLETED, LIFECYCLE_MISSED,
        LIFECYCLE_CANCELLED,
    },
    LIFECYCLE_CANCELLED: {LIFECYCLE_PLANNED},
    LIFECYCLE_COMPLETED: set(),
    LIFECYCLE_MISSED: {
        LIFECYCLE_PLANNED, LIFECYCLE_COMPLETED, LIFECYCLE_POSTPONED,
        LIFECYCLE_SUBSTITUTED, LIFECYCLE_CANCELLED,
    },
}

# Estados terminais (nao ha transicao de saida no modelo atual).
TERMINAL_LIFECYCLES = frozenset(
    state for state, destinos in VALID_TRANSITIONS.items() if not destinos)

# Origem da conclusao (UI-4). Distingue "como o treino chegou a completed",
# sem virar um segundo lifecycle: a ORIGEM e metadado da evidencia.
COMPLETION_SOURCE_LOCAL = "local"           # atestado pelo atleta/treinador
COMPLETION_SOURCE_PROVIDER = "provider_match"  # atividade pareada observada
COMPLETION_SOURCE_RECONCILE = "reconcile"    # inferida no reconcile


def completion(workout: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Metadado de conclusao persistido, ou `None`. Nao e o lifecycle."""
    value = workout.get("completion")
    return value if isinstance(value, dict) else None


def set_completion(workout: Dict[str, Any], *, source: str,
                   observed_at: Optional[str] = None,
                   provider_event_id: Any = None,
                   activity_id: Any = None) -> Dict[str, Any]:
    """Devolve copia do treino com o metadado de conclusao anexado.

    Nao mexe no lifecycle (quem decide o estado e `Application.mark_completed`).
    Idempotente: reescrever a mesma evidencia produz o mesmo dict.
    """
    novo = dict(workout)
    meta: Dict[str, Any] = {"source": source}
    if observed_at is not None:
        meta["observed_at"] = observed_at
    if provider_event_id is not None:
        meta["provider_event_id"] = provider_event_id
    if activity_id is not None:
        meta["activity_id"] = activity_id
    novo["completion"] = meta
    return novo


def default_lifecycle() -> str:
    return LIFECYCLE_PLANNED


def ensure(workout: Dict[str, Any]) -> Dict[str, Any]:
    """Devolve o treino com `lifecycle` preenchido (default `planned`).

    Sem mutar o original e idempotente: nunca sobrescreve um estado declarado.
    """
    if workout.get("lifecycle") in ALL_LIFECYCLES:
        return workout
    novo = dict(workout)
    novo["lifecycle"] = default_lifecycle()
    return novo


def can_transition(current: str, new: str) -> bool:
    if new not in ALL_LIFECYCLES:
        return False
    if current == new:
        return True  # idempotente
    return new in VALID_TRANSITIONS.get(current, set())


def validate_transition(current: str, new: str) -> None:
    if current not in ALL_LIFECYCLES:
        raise ValueError(f"lifecycle atual invalido: {current!r}")
    if not can_transition(current, new):
        raise ValueError(f"transicao de lifecycle invalida: {current} -> {new}")


def derive(*, day: str, today, is_done: bool = False,
           declared: Optional[str] = None) -> str:
    """Resolve o lifecycle efetivo do treino.

    Regras (nesta ordem):
    - um estado DECLARADO != `planned` sempre vence (postponed/cancelled/... e
      tambem completed/missed retro-atestados);
    - dia ainda nao passou (>= hoje) -> `planned`;
    - dia passou com evidencia -> `completed`, sem evidencia -> `missed`.
    """
    state = declared or default_lifecycle()
    if state not in ALL_LIFECYCLES:
        state = default_lifecycle()
    if state != LIFECYCLE_PLANNED:
        return state
    if str(day) >= _iso(today):
        return LIFECYCLE_PLANNED
    return LIFECYCLE_COMPLETED if is_done else LIFECYCLE_MISSED


def _iso(today) -> str:
    return today.isoformat() if hasattr(today, "isoformat") else str(today)
