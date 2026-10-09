"""UI-5 — View models e ApplicationState (consultas puras).

Contratos de leitura independentes de UI/CLI/provider/armazenamento. Views sao
imutaveis, side-effect free e nao sabem de Intervals.icu nem do `plan.json` cru.

Invariantes:
- nenhuma View executa sync, chama provider, altera lifecycle, recalcula PMC,
  aplica heuristica ou prescreve treino;
- identidade local (`id`) e distinta de linkage do provider;
- `declared` (persistido) nunca e sobrescrito por `effective` (derivado);
- completion vem do estado local (UI-4), nunca de `paired_activity_id` cru.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Any, Dict, Mapping, Optional

try:  # execucao como pacote (src.ui_state)
    from . import lifecycle as _lifecycle
except ImportError:  # execucao com src/ no path
    import lifecycle as _lifecycle  # type: ignore

WORKOUT_ID_FIELD = "id"
DEFAULT_CTL_RAMP_WINDOW_DAYS = 7
DEFAULT_HR_TREND_WINDOW_DAYS = 7


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _f(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _snapshot_field(record: Any, name: str) -> Any:
    """Le somente campos canonicos ja persistidos no snapshot local."""
    if isinstance(record, Mapping):
        return record.get(name)
    return getattr(record, name, None)


# ---------------------------------------------------------------------------
# Derivacao de leitura: Form relativo (PMC-1)
# ---------------------------------------------------------------------------

def derive_form_pct(ctl: Any, tsb: Any) -> Optional[float]:
    """Form relativo (%) = TSB / CTL x 100 (PMC-1).

    DERIVACAO PURA, local e side-effect free: nao chama provider, nao le
    disco, nao recalcula CTL/ATL/TSB e nao muta nenhum argumento.CTL, ATL e TSB
    sao OBSERVADOS do provider (UI-3); o Hermes so divide.

    Devolve `None` — nunca 0 — quando a razao nao e definida: `ctl is None`,
    `tsb is None` ou `ctl <= 0` (CTL ausente, zero ou negativo). Sem clamp
    arbitrario e sem arredondamento: o float full vai para a View e a
    formatacao (ex.: `-25.3%`) e do consumidor.

    `form_pct` e representacao derivada, NAO regra fisiologica: nao e limiar de
    deload e nao tem efeito prescritivo (POL-1 e quem interpreta valor)."""
    c = _f(ctl)
    t = _f(tsb)
    if c is None or t is None or c <= 0:
        return None
    return (t / c) * 100.0


# ---------------------------------------------------------------------------
# Contratos de leitura
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CompletionView:
    """Completion LOCAL (UI-4): evidencia de que o treino foi feito."""

    completed: bool
    source: Optional[str] = None
    observed_at: Optional[str] = None
    provider_event_id: Optional[Any] = None
    activity_id: Optional[Any] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProviderLinkView:
    """Linkage com o provider. NUNCA e identidade nem lifecycle."""

    provider: Optional[str] = None
    external_id: Optional[str] = None
    provider_event_id: Optional[Any] = None
    activity_id: Optional[Any] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkoutView:
    """Um treino do plano, visto por um consumidor de UI."""

    id: str
    day: str
    title: Optional[str] = None
    focus: Optional[str] = None
    lifecycle_declared: str = _lifecycle.LIFECYCLE_PLANNED
    lifecycle_effective: str = _lifecycle.LIFECYCLE_PLANNED
    completed: bool = False
    completion: Optional[CompletionView] = None
    provider_link: Optional[ProviderLinkView] = None
    conflict: bool = False
    tss: Optional[float] = None
    planned_duration: Optional[int] = None
    hr_mode: Optional[bool] = None

    @property
    def lifecycle(self) -> str:
        """Atalho para o estado efetivo (o que o usuario ve)."""
        return self.lifecycle_effective

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "day": self.day,
            "title": self.title,
            "focus": self.focus,
            "lifecycle": self.lifecycle,
            "lifecycle_declared": self.lifecycle_declared,
            "lifecycle_effective": self.lifecycle_effective,
            "completed": self.completed,
            "completion": (self.completion.to_dict()
                           if self.completion else None),
            "provider_link": (self.provider_link.to_dict()
                              if self.provider_link else None),
            "conflict": self.conflict,
            "tss": self.tss,
            "planned_duration": self.planned_duration,
            "hr_mode": self.hr_mode,
        }


class LinkageStatus(str, Enum):
    """Estado factual entre um treino local e dados observados do provider."""

    NO_EVIDENCE = "no_evidence"
    PAIRED = "paired"
    AMBIGUOUS = "ambiguous"
    ACTIVITY_UNAVAILABLE = "activity_unavailable"


@dataclass(frozen=True)
class PlannedExecutionContext:
    """Contexto prescritivo copiado do plano, nunca da atividade observada."""

    focus: Optional[str] = None
    duration_sec: Optional[float] = None
    tss: Optional[float] = None
    ftp_watts: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObservedActivityView:
    """Metricas brutas reportadas pelo provider para uma atividade pareada."""

    activity_id: Any
    moving_time_sec: Optional[float] = None
    elapsed_time_sec: Optional[float] = None
    distance: Optional[float] = None
    elevation: Optional[float] = None
    average_power: Optional[float] = None
    normalized_power: Optional[float] = None
    average_hr: Optional[float] = None
    provider_training_load: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ActivityStreamView:
    """Disponibilidade e integridade factual do stream cacheado da atividade."""

    available: bool
    aligned: Optional[bool] = None
    available_fields: tuple[str, ...] = ()
    captured_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorkoutExecutionView:
    """Estado factual local de planejado, evidencia e atividade observada.

    Nao infere familia executada, aderencia, zonas, IF ou TSS recalculado.
    """

    workout_id: Optional[str]
    day: Optional[str]
    planned: PlannedExecutionContext
    lifecycle_declared: str
    lifecycle_effective: str
    completion: Optional[CompletionView]
    linkage_status: LinkageStatus
    provider_external_id: Optional[str]
    provider_event_id: Any = None
    activity_id: Any = None
    observed_activity: Optional[ObservedActivityView] = None
    stream: ActivityStreamView = ActivityStreamView(available=False)
    provider: Optional[str] = None
    snapshot_available: bool = False
    snapshot_captured_at: Optional[str] = None
    snapshot_freshness: Optional[FreshnessView] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workout_id": self.workout_id,
            "day": self.day,
            "planned": self.planned.to_dict(),
            "lifecycle_declared": self.lifecycle_declared,
            "lifecycle_effective": self.lifecycle_effective,
            "completion": self.completion.to_dict() if self.completion else None,
            "linkage_status": self.linkage_status.value,
            "provider_external_id": self.provider_external_id,
            "provider_event_id": self.provider_event_id,
            "activity_id": self.activity_id,
            "observed_activity": (self.observed_activity.to_dict()
                                  if self.observed_activity else None),
            "stream": self.stream.to_dict(),
            "provider": self.provider,
            "snapshot_available": self.snapshot_available,
            "snapshot_captured_at": self.snapshot_captured_at,
            "snapshot_freshness": (self.snapshot_freshness.to_dict()
                                   if self.snapshot_freshness else None),
        }


@dataclass(frozen=True)
class PlanMetaView:
    goal: Optional[str] = None
    race_date: Optional[str] = None
    ftp_test_date: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PlanView:
    """Plano local em leitura, com os agregados uteis a uma UI."""

    workouts: tuple[WorkoutView, ...] = ()
    meta: PlanMetaView = PlanMetaView()
    has_plan: bool = False
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    workout_count: int = 0
    completed_count: int = 0
    missed_count: int = 0
    next_workout: Optional[WorkoutView] = None

    def workout(self, workout_id: str) -> Optional[WorkoutView]:
        for w in self.workouts:
            if w.id == workout_id:
                return w
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "workouts": [w.to_dict() for w in self.workouts],
            "meta": self.meta.to_dict(),
            "has_plan": self.has_plan,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "workout_count": self.workout_count,
            "completed_count": self.completed_count,
            "missed_count": self.missed_count,
            "next_workout": (self.next_workout.to_dict()
                             if self.next_workout else None),
        }


@dataclass(frozen=True)
class FreshnessView:
    """Idade dos dados externos (politica vem do snapshot, nao da View)."""

    status: str
    provider: Optional[str] = None
    synced_at: Optional[str] = None
    stale_after_hours: Optional[float] = None
    age_seconds: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PmcView:
    """PMC em leitura: CTL/ATL/TSB **observados** + `form_pct` **derivado**.

    Provenance (PMC-1):
      ctl / atl / tsb -> provider observed (nao recalculados pelo Hermes)
      form_pct        -> derivacao local pura (TSB / CTL x 100)

    `form_pct` e representacao derivada para leitura. Nao e regra fisiologica,
    nao e limiar de deload e nao tem efeito prescritivo — interpretar valor e
    decidir sobre ele pertence a policy (POL-1), nao a este contrato."""

    ctl: Optional[float] = None
    atl: Optional[float] = None
    tsb: Optional[float] = None
    form_pct: Optional[float] = None
    tss: Optional[float] = None
    ftp: Optional[float] = None
    day: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CtlRampView:
    """Tendencia temporal de CTL observada, separada do PMC pontual.

    `ramp_rate` e derivacao local: CTL(target_day) - CTL(target_day - janela).
    Nao interpola gaps nem recalcula CTL; `None` torna a falta de observacao
    explicita. `freshness` descreve a idade do snapshot, nao bloqueia o calculo.
    """

    target_day: str
    window_days: int
    baseline_day: str
    target_ctl: Optional[float] = None
    baseline_ctl: Optional[float] = None
    ramp_rate: Optional[float] = None
    observed_days: int = 0
    freshness: Optional[FreshnessView] = None
    captured_at: Optional[str] = None

    @property
    def available(self) -> bool:
        return self.ramp_rate is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_day": self.target_day,
            "window_days": self.window_days,
            "baseline_day": self.baseline_day,
            "target_ctl": self.target_ctl,
            "baseline_ctl": self.baseline_ctl,
            "ramp_rate": self.ramp_rate,
            "observed_days": self.observed_days,
            "freshness": self.freshness.to_dict() if self.freshness else None,
            "captured_at": self.captured_at,
        }


@dataclass(frozen=True)
class WellnessView:
    """Ultima leitura de wellness observada, sem normalizacao nova."""

    day: Optional[str] = None
    resting_hr: Optional[float] = None
    hrv: Optional[float] = None
    hrv_sdnn: Optional[float] = None
    sleep_secs: Optional[float] = None
    sleep_score: Optional[float] = None
    readiness_score: Optional[float] = None
    stress: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HeuristicObservationView:
    """Resultado de um eixo da heuristica existente, nao dado observado."""

    axis: str
    score: float
    source: str
    flagged: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessAxisView:
    """Estado de um eixo do modelo, sem atribuir valor a dado ausente."""

    axis: str
    label: str
    implemented: bool
    available: bool
    score: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReadinessView:
    """Readiness em leitura: observacoes + derivacoes + heuristica existente.

    Nao contem `ReadinessAction`, advice nem prescricao. A classificacao e os
    sinais sao resultados da heuristica ja existente; policy/alteracao de plano
    continuam nos use cases atuais e em POL-1.
    """

    target_day: str
    available: bool = False
    reference_day: Optional[str] = None
    wellness: Optional[WellnessView] = None
    pmc: Optional[PmcView] = None
    freshness: Optional[FreshnessView] = None
    captured_at: Optional[str] = None
    heuristic_level: Optional[str] = None
    heuristic_score: Optional[float] = None
    heuristic_confidence: float = 0.0
    heuristic_observations: tuple[HeuristicObservationView, ...] = ()
    axis_states: tuple[ReadinessAxisView, ...] = ()
    model_axis_count: int = 0
    implemented_axis_count: int = 0
    available_axis_count: int = 0
    heuristic_signals: tuple[tuple[str, bool], ...] = ()
    illness_alert: bool = False
    composite_low: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_day": self.target_day,
            "available": self.available,
            "reference_day": self.reference_day,
            "wellness": self.wellness.to_dict() if self.wellness else None,
            "pmc": self.pmc.to_dict() if self.pmc else None,
            "freshness": self.freshness.to_dict() if self.freshness else None,
            "captured_at": self.captured_at,
            "heuristic_level": self.heuristic_level,
            "heuristic_score": self.heuristic_score,
            "heuristic_confidence": self.heuristic_confidence,
            "heuristic_observations": [
                observation.to_dict()
                for observation in self.heuristic_observations
            ],
            "axis_states": [axis.to_dict() for axis in self.axis_states],
            "model_axis_count": self.model_axis_count,
            "implemented_axis_count": self.implemented_axis_count,
            "available_axis_count": self.available_axis_count,
            "heuristic_signals": dict(self.heuristic_signals),
            "illness_alert": self.illness_alert,
            "composite_low": self.composite_low,
        }


@dataclass(frozen=True)
class SnapshotView:
    """Leitura do cache normalizado (UI-4). Nao recalcula PMC."""

    events: tuple[Mapping[str, Any], ...] = ()
    wellness: tuple[Mapping[str, Any], ...] = ()
    activities: tuple[Mapping[str, Any], ...] = ()
    pmc: Optional[PmcView] = None
    captured_at: Optional[str] = None
    provider: Optional[str] = None
    freshness: Optional[FreshnessView] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [dict(e) for e in self.events],
            "wellness": [dict(w) for w in self.wellness],
            "activities": [dict(a) for a in self.activities],
            "pmc": self.pmc.to_dict() if self.pmc else None,
            "captured_at": self.captured_at,
            "provider": self.provider,
            "freshness": (self.freshness.to_dict()
                          if self.freshness else None),
        }


@dataclass(frozen=True)
class ApplicationState:
    """Visao coerente do estado atual do Hermes, 100% local.

    Um unico container para o que uma UI precisa ler. Nao ha `SyncView`
    separado: a idade/estado da ultima sincronizacao ja vive em
    `SnapshotView.freshness` (uma representacao por conceito)."""

    plan: PlanView = PlanView()
    snapshot: Optional[SnapshotView] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan": self.plan.to_dict(),
            "snapshot": self.snapshot.to_dict() if self.snapshot else None,
        }


# ---------------------------------------------------------------------------
# Builders puros (recebem dados ja carregados; nao conhecem Application)
# ---------------------------------------------------------------------------

def build_freshness_view(freshness: Any, *, now: Optional[datetime] = None
                         ) -> Optional[FreshnessView]:
    """Envolve `SyncFreshness` (UI-4) sem duplicar a politica de staleness."""
    if freshness is None:
        return None
    status = freshness.status(now=now)
    age = freshness.age_seconds(now=now) if hasattr(freshness, "age_seconds") \
        else None
    return FreshnessView(
        status=getattr(status, "value", str(status)),
        provider=getattr(freshness, "provider", None),
        synced_at=_iso(getattr(freshness, "synced_at", None)),
        stale_after_hours=_f(getattr(freshness, "stale_after_hours", None)),
        age_seconds=_f(age),
    )


def build_completion_view(workout: Mapping[str, Any]) -> Optional[CompletionView]:
    meta = _lifecycle.completion(dict(workout))
    if meta is None:
        return None
    return CompletionView(
        completed=True,
        source=meta.get("source"),
        observed_at=_iso(meta.get("observed_at")),
        provider_event_id=meta.get("provider_event_id"),
        activity_id=meta.get("activity_id"),
    )


def build_workout_view(workout: Mapping[str, Any], *,
                       today: Optional[date] = None,
                       provider: Optional[str] = None) -> WorkoutView:
    """Um treino -> View, so com estado LOCAL.

    `effective` usa a mesma resolucao de UI-2 (`lifecycle.derive`), mas a
    evidencia `is_done` vem do completion local (UI-4), nao do provider: a View
    nunca sincroniza. `conflict` marca evidencia de provider presente com estado
    declarado incompativel (ex.: cancelado localmente, mas o provider tem
    activity) — o conflito fica visivel em vez de ser escondido.
    """
    workout = dict(workout)
    declared = _lifecycle.ensure(workout)["lifecycle"]
    completion = build_completion_view(workout)
    effective = _lifecycle.derive(
        day=str(workout.get("day")), today=today or date.today(),
        is_done=completion is not None and declared in (
            _lifecycle.LIFECYCLE_COMPLETED, _lifecycle.LIFECYCLE_PLANNED),
        declared=declared)
    has_provider_evidence = bool(
        (completion and (completion.activity_id or completion.provider_event_id))
        or (completion and completion.source
            == _lifecycle.COMPLETION_SOURCE_PROVIDER))
    external_id = workout.get("external_id")
    link = (ProviderLinkView(provider=provider, external_id=external_id,
                             provider_event_id=(completion.provider_event_id
                                                if completion else None),
                             activity_id=(completion.activity_id
                                          if completion else None))
            if (external_id or has_provider_evidence) else None)
    return WorkoutView(
        id=str(workout.get(WORKOUT_ID_FIELD) or ""),
        day=str(workout.get("day") or ""),
        title=workout.get("name"),
        focus=workout.get("focus"),
        lifecycle_declared=declared,
        lifecycle_effective=effective,
        completed=effective == _lifecycle.LIFECYCLE_COMPLETED,
        completion=completion,
        provider_link=link,
        conflict=has_provider_evidence
        and declared != _lifecycle.LIFECYCLE_COMPLETED,
        tss=_f(workout.get("tss")),
        planned_duration=workout.get("planned_duration"),
        hr_mode=workout.get("hr_mode"),
    )


def _activity_for_id(activities: Any, activity_id: Any) -> Optional[Mapping[str, Any]]:
    """Atividade canonica identificada pelo provider, sem fallback por data/nome."""
    matches = [activity for activity in (activities or ())
               if _snapshot_field(activity, "provider_event_id") == activity_id]
    return matches[0] if len(matches) == 1 else None


def _provider_training_load(activity: Any) -> Any:
    """Carga reportada pelo provider, preservando zero como observacao valida."""
    load = _snapshot_field(activity, "training_load")
    return load if load is not None else _snapshot_field(activity, "tss")


def build_workout_execution_view(
    workout: Mapping[str, Any], *, snapshot: Any = None,
    stream_cache: Any = None, today: Optional[date] = None,
    now: Optional[datetime] = None,
) -> WorkoutExecutionView:
    """Deriva uma View factual a partir de estado local ja persistido.

    O pareamento so e aceito quando existe exatamente um evento provider para o
    ``external_id`` do plano. Duplicatas sao expostas como ambiguidade, sem
    escolher um evento ou atividade pela ordem recebida.
    """
    raw_workout = dict(workout)
    workout_view = build_workout_view(
        raw_workout, today=today,
        provider=getattr(snapshot, "provider", None))
    external_id = raw_workout.get("external_id")
    events = getattr(snapshot, "events", ()) if snapshot is not None else ()
    matching_events = [event for event in events or ()
                       if external_id is not None
                       and _snapshot_field(event, "external_id") == external_id]
    freshness = (build_freshness_view(getattr(snapshot, "freshness", None), now=now)
                 if snapshot is not None else None)
    common = dict(
        workout_id=workout_view.id or None,
        day=workout_view.day or None,
        planned=PlannedExecutionContext(
            focus=raw_workout.get("focus"),
            duration_sec=_f(raw_workout.get("planned_duration")),
            tss=_f(raw_workout.get("tss")),
            ftp_watts=_f(raw_workout.get("ftp_watts"))),
        lifecycle_declared=workout_view.lifecycle_declared,
        lifecycle_effective=workout_view.lifecycle_effective,
        completion=workout_view.completion,
        provider_external_id=external_id,
        provider=getattr(snapshot, "provider", None),
        snapshot_available=bool(getattr(snapshot, "captured_at", None)),
        snapshot_captured_at=_iso(getattr(snapshot, "captured_at", None)),
        snapshot_freshness=freshness,
    )
    if len(matching_events) > 1:
        return WorkoutExecutionView(
            linkage_status=LinkageStatus.AMBIGUOUS,
            stream=ActivityStreamView(available=False), **common)
    if not matching_events:
        return WorkoutExecutionView(
            linkage_status=LinkageStatus.NO_EVIDENCE,
            stream=ActivityStreamView(available=False), **common)

    event = matching_events[0]
    event_id = _snapshot_field(event, "provider_event_id")
    activity_id = _snapshot_field(event, "completion_activity_id")
    if activity_id is None:
        return WorkoutExecutionView(
            linkage_status=LinkageStatus.NO_EVIDENCE,
            provider_event_id=event_id,
            stream=ActivityStreamView(available=False), **common)

    activity = _activity_for_id(getattr(snapshot, "activities", ()), activity_id)
    if activity is None:
        return WorkoutExecutionView(
            linkage_status=LinkageStatus.ACTIVITY_UNAVAILABLE,
            provider_event_id=event_id, activity_id=activity_id,
            stream=ActivityStreamView(available=False), **common)

    provider = getattr(snapshot, "provider", None)
    stream = (stream_cache.get(provider=provider, activity_id=str(activity_id))
              if provider and stream_cache is not None else None)
    stream_view = ActivityStreamView(
        available=stream is not None,
        aligned=(stream.alignment == "aligned") if stream is not None else None,
        available_fields=tuple(stream.available_fields) if stream is not None else (),
        captured_at=_iso(stream.captured_at) if stream is not None else None)
    return WorkoutExecutionView(
        linkage_status=LinkageStatus.PAIRED,
        provider_event_id=event_id, activity_id=activity_id,
        observed_activity=ObservedActivityView(
            activity_id=activity_id,
            moving_time_sec=_f(_snapshot_field(activity, "moving_time")),
            elapsed_time_sec=_f(_snapshot_field(activity, "elapsed_time")),
            distance=_f(_snapshot_field(activity, "distance")),
            elevation=_f(_snapshot_field(activity, "elevation_gain")),
            average_power=_f(_snapshot_field(activity, "avg_power")),
            normalized_power=_f(_snapshot_field(activity, "np")),
            average_hr=_f(_snapshot_field(activity, "avg_hr")),
            provider_training_load=_f(_provider_training_load(activity)),
        ),
        stream=stream_view, **common)


def _next_workout(views: list[WorkoutView], today: date) -> Optional[WorkoutView]:
    """Proximo treino DERIVADO (sem prescricao): primeiro nao resolvido de hoje
    em diante. `planned`/`postponed`/`substituted` sao candidatos; `cancelled`,
    `missed` e `completed` jaresolveram."""
    pending = {_lifecycle.LIFECYCLE_PLANNED, _lifecycle.LIFECYCLE_POSTPONED,
               _lifecycle.LIFECYCLE_SUBSTITUTED}
    hoje = today.isoformat()
    for view in views:
        if view.lifecycle_effective in pending and view.day >= hoje:
            return view
    return None


def build_plan_view(workouts, meta, *,
                    today: Optional[date] = None,
                    provider: Optional[str] = None) -> PlanView:
    """Plano local -> PlanView, so com estado LOCAL."""
    today = today or date.today()
    views = [build_workout_view(w, today=today, provider=provider)
             for w in (workouts or [])]
    ordered = sorted(views, key=lambda v: (v.day, v.id))
    return PlanView(
        workouts=tuple(ordered),
        meta=PlanMetaView(
            goal=(meta or {}).get("goal"),
            race_date=(meta or {}).get("race_date"),
            ftp_test_date=(meta or {}).get("ftp_test_date")),
        has_plan=bool(ordered),
        start_date=ordered[0].day if ordered else None,
        end_date=ordered[-1].day if ordered else None,
        workout_count=len(ordered),
        completed_count=sum(1 for v in ordered if v.completed),
        missed_count=sum(1 for v in ordered
                         if v.lifecycle_effective == _lifecycle.LIFECYCLE_MISSED),
        next_workout=_next_workout(ordered, today),
    )


def build_pmc_view(metrics: Optional[Mapping[str, Any]]) -> Optional[PmcView]:
    """PMC observada -> `PmcView`, acrescentando `form_pct` derivado (PMC-1).

    Aceita o dict canonico ja persistido no snapshot (UI-4). `None` quando nao
    ha PMC alguma, para nao criar objeto artificial so para expor `form_pct`.
    CTL/ATL/TSB sao copiados como observados; a unica conta e o `form_pct`."""
    if not metrics:
        return None
    ctl = _f(metrics.get("ctl"))
    atl = _f(metrics.get("atl"))
    tsb = _f(metrics.get("tsb"))
    if ctl is None and atl is None and tsb is None:
        return None
    day = metrics.get("day")
    return PmcView(
        ctl=ctl, atl=atl, tsb=tsb, form_pct=derive_form_pct(ctl, tsb),
        tss=_f(metrics.get("tss")), ftp=_f(metrics.get("ftp")),
        day=day if isinstance(day, str) else None)


def build_snapshot_view(snapshot: Any, *,
                        now: Optional[datetime] = None
                        ) -> Optional[SnapshotView]:
    """`TrainingSnapshot` (UI-4) -> SnapshotView, ou `None` se nunca houve sync.

    Nao duplica a representation do snapshot: expoe os dados canonicos ja
    persistidos, delega a politica de staleness ao proprio `SyncFreshness` e
    deriva `form_pct` a partir da PMC observada (PMC-1)."""
    if snapshot is None:
        return None
    events = tuple(snapshot.events or ())
    wellness = tuple(snapshot.wellness or ())
    activities = tuple(snapshot.activities or ())
    pmc = build_pmc_view(getattr(snapshot, "metrics", None))
    if not (events or wellness or activities or pmc):
        return None
    return SnapshotView(
        events=events, wellness=wellness, activities=activities,
        pmc=pmc,
        captured_at=_iso(getattr(snapshot, "captured_at", None)),
        provider=getattr(snapshot, "provider", None),
        freshness=build_freshness_view(getattr(snapshot, "freshness", None),
                                       now=now),
    )


_HEURISTIC_SOURCES = {
    "hrv_score": "wellness.hrv",
    "rhr_score": "wellness.resting_hr",
    "sleep_score": "wellness.sleep_secs",
}


def _readiness_module():
    """Import tardio: a View depende somente da heuristica pura existente."""
    try:
        from . import readiness
    except ImportError:
        import readiness  # type: ignore
    return readiness


def build_wellness_view(records: tuple[Mapping[str, Any], ...]
                        ) -> Optional[WellnessView]:
    """Ultimo wellness canonico por dia, sem criar score nem imputar ausencia."""
    if not records:
        return None
    last = max(records, key=lambda record: str(record.get("day") or ""))
    return WellnessView(
        day=_iso(last.get("day")),
        resting_hr=_f(last.get("resting_hr")),
        hrv=_f(last.get("hrv")),
        hrv_sdnn=_f(last.get("hrv_sdnn")),
        sleep_secs=_f(last.get("sleep_secs")),
        sleep_score=_f(last.get("sleep_score")),
        readiness_score=_f(last.get("readiness")),
        stress=_f(last.get("stress")),
    )


def build_readiness_view(snapshot: Optional[SnapshotView], *,
                         today: date) -> ReadinessView:
    """Snapshot local -> ReadinessView, sem provider, policy ou prescricao.

    A classificacao reutiliza `assess_readiness_assessment` tal qual existe. A
    View NAO chama `readiness_decision`: `ReadinessAction` e a consequente
    adaptacao de plano pertencem ao fluxo prescritivo existente, nao a leitura.
    `target_day` e o contexto solicitado; `reference_day` registra o dia que o
    ultimo wellness realmente descreve, inclusive quando eles divergem.
    """
    target_day = today.isoformat()
    readiness = _readiness_module()
    assessment, trace = readiness.assess_readiness_assessment(
        snapshot.wellness if snapshot is not None else (), today=today)
    observations = tuple(
        HeuristicObservationView(
            axis=observation.axis,
            score=observation.score,
            source=_HEURISTIC_SOURCES.get(observation.axis, observation.axis),
            flagged=observation.flagged,
        )
        for observation in trace.observations
    )
    observed = {observation.axis: observation.score for observation in observations}
    implemented = set(readiness.IMPLEMENTED_READINESS_AXES)
    axis_states = tuple(
        ReadinessAxisView(
            axis=axis, label=label, implemented=axis in implemented,
            available=axis in observed, score=observed.get(axis),
        )
        for axis, label in readiness.READINESS_AXIS_SPECS
    )
    level = assessment.level() if assessment is not None else None
    return ReadinessView(
        target_day=target_day,
        available=assessment is not None,
        reference_day=trace.reference_day,
        wellness=(build_wellness_view(snapshot.wellness) if snapshot else None),
        pmc=snapshot.pmc if snapshot else None,
        freshness=snapshot.freshness if snapshot else None,
        captured_at=snapshot.captured_at if snapshot else None,
        heuristic_level=getattr(level, "value", None),
        heuristic_score=(assessment.overall_readiness
                         if assessment is not None else None),
        heuristic_confidence=trace.coverage,
        heuristic_observations=observations,
        axis_states=axis_states,
        model_axis_count=len(axis_states),
        implemented_axis_count=len(implemented),
        available_axis_count=len(observed),
        heuristic_signals=tuple(sorted(trace.signals.items())),
        illness_alert=trace.illness_alert,
        composite_low=trace.composite_low,
    )


def _date(value: Any) -> Optional[date]:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def ctl_history_by_day(snapshot: Optional[SnapshotView]) -> dict[date, float]:
    """CTL observado por dia no snapshot, sem preencher gaps.

    Eventos do provider sao consumidos na ordem persistida; duplicatas do mesmo
    dia seguem a semantica ja usada por `coach.real_pmc_by_day`: a ultima
    observacao daquele dia vence. O `PmcView` atual, quando datado, e a ultima
    observacao e tambem vence. Nenhum CTL e recalculado pelo Hermes.
    """
    if snapshot is None:
        return {}
    history: dict[date, float] = {}
    for event in snapshot.events:
        day = _date(event.get("day"))
        ctl = _f(event.get("ctl"))
        if day is not None and ctl is not None:
            history[day] = ctl
    if snapshot.pmc is not None:
        day = _date(snapshot.pmc.day)
        if day is not None and snapshot.pmc.ctl is not None:
            history[day] = snapshot.pmc.ctl
    return history


def derive_ctl_ramp_rate(history: Mapping[date, Any], *, target_day: date,
                         window_days: int = DEFAULT_CTL_RAMP_WINDOW_DAYS
                         ) -> Optional[float]:
    """CTL ramp rate = CTL(D) - CTL(D - window_days), sem interpolacao.

    Unidade: **pontos de CTL por `window_days` dias**. Ambos os pontos precisam
    existir exatamente na serie observada. `None` para serie parcial, gap ou
    valor invalido; ausencia nunca vira zero. A funcao e pura e nao muta a
    serie. Valores negativos sao preservados se presentes no provider.
    """
    if isinstance(window_days, bool) or not isinstance(window_days, int) \
            or window_days <= 0:
        raise ValueError("window_days deve ser inteiro positivo")
    target = _f(history.get(target_day))
    baseline = _f(history.get(target_day - timedelta(days=window_days)))
    if target is None or baseline is None:
        return None
    return target - baseline


# ---------------------------------------------------------------------------
# Tendencias observadas de FC em repouso: HRV / RHR (HR-3)
# ---------------------------------------------------------------------------

# Um sinal de recuperacao e uma serie OBSERVADA individual. Baseline e delta
# sao ferramenta computacional de leitura; o significado fisiologico do delta
# (bom, ruim, illness, overreaching) NAO e decidido aqui — ver readiness, que
# ja expoe `hrv_low`/`rhr_rising` como heuristica existente e inalterada.
#
# `FCR` = "frequencia cardiaca de repouso", o termo portugues de RHR. Nao e
# uma terceira metrica e por isso nao tem campo: `rhr` ja a expoe. O codigo
# fala em RHR/resting_hr; a equivalencia fica na documentacao.
# `heart-rate recovery` (queda da FC pos-esforco) e outro conceito, fora do
# escopo de HR-3, sem campo aqui.

HR_TREND_AVAILABLE = "available"
HR_TREND_INSUFFICIENT_HISTORY = "insufficient_history"
HR_TREND_MISSING_CURRENT_VALUE = "missing_current_value"


def _hr_metric(value: Any, *, allow_zero: bool) -> Optional[float]:
    """Coerce para float OBSERVADO, ou `None` se ausente/invalido.

    Deliberadamente mais estrito que `_f`: rejeita `bool` (True nao e 1.0 bpm),
    string nao numerica, `NaN` e infinito. Ausencia nunca vira zero. Zero so
    sobrevive em campo onde zero e semanticamente valido — para HRV e RHR
    NAO e: FC de repouso zero e leitura quebrada de sensor, nao observacao.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = float(stripped)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        number = float(value)
    else:
        return None
    if number != number:  # NaN
        return None
    if number in (float("inf"), float("-inf")):
        return None
    if number == 0.0 and not allow_zero:
        return None
    return number


def _hr_series(records: Any, *, field: str,
               allow_zero: bool) -> dict[date, float]:
    """Serie observada {dia: valor}, deduplicando pelo ultimo registro do dia.

    Nao interpola gap e nao preenche dia ausente. Dias repetidos nao sao
    misturados: o provider pode reenviar o mesmo dia com correcao.
    """
    series: dict[date, float] = {}
    for record in records or []:
        if not isinstance(record, Mapping):
            continue
        day = _date(record.get("day") or record.get("id"))
        if day is None:
            continue
        value = _hr_metric(record.get(field), allow_zero=allow_zero)
        if value is not None:
            series[day] = value
    return series


def derive_hr_baseline(series: Mapping[date, Any], *, reference_day: date,
                       window_days: int = DEFAULT_HR_TREND_WINDOW_DAYS
                       ) -> tuple[Optional[float], int]:
    """Baseline individual = media dos valores observados ate `reference_day`.

    Janela de `window_days` dias **inclusiva**, terminando em `reference_day`.
    Devolve `(media, n_observacoes)`. Media e `None` sem nenhuma observacao —
    nunca 0. Nao exige numero minimo de amostras: expor `n` deixa o consumidor
    decidir se aceita uma base fraca, em vez de esta View inventar um corte.
    """
    if isinstance(window_days, bool) or not isinstance(window_days, int) \
            or window_days <= 0:
        raise ValueError("window_days deve ser inteiro positivo")
    start = reference_day - timedelta(days=window_days - 1)
    values: list[float] = []
    for day, value in series.items():
        if start <= day <= reference_day:
            parsed = _hr_metric(value, allow_zero=False)
            if parsed is not None:
                values.append(parsed)
    if not values:
        return None, 0
    return sum(values) / len(values), len(values)


def derive_hr_delta(current: Any, baseline: Any) -> Optional[float]:
    """Delta absoluto = observado - baseline. `None` se algum falta."""
    target = _hr_metric(current, allow_zero=False)
    base = _hr_metric(baseline, allow_zero=False)
    if target is None or base is None:
        return None
    return target - base


def derive_hr_delta_pct(current: Any, baseline: Any) -> Optional[float]:
    """Delta percentual = (observado - baseline) / baseline x 100.

    `None` quando o baseline e 0 (razao indefinida): divisao por zero nao e
    feita e o sinal nao vira 0%.
    """
    target = _hr_metric(current, allow_zero=False)
    base = _hr_metric(baseline, allow_zero=False)
    if target is None or base is None or base == 0:
        return None
    return (target - base) / base * 100.0


@dataclass(frozen=True)
class HeartRateMetricTrend:
    """Tendencia de UMA serie observada (HRV ou RHR). Sem policy."""

    field: str
    status: str
    current: Optional[float] = None
    baseline: Optional[float] = None
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    sample_count: int = 0
    unit: Optional[str] = None

    @property
    def available(self) -> bool:
        return self.current is not None and self.baseline is not None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HeartRateTrendView:
    """HRV / RHR observados + baseline individual + delta (HR-3).

    LEITURA OBSERVACIONAL. Nao contem policy, advice nem prescricao, e nao
    altera `ReadinessAction`. As heuristicas existentes (`hrv_low`,
    `rhr_rising`) continuam em `readiness.py` com os mesmos thresholds; esta
    View expoe os valores e tendencias **subjacentes** que elas usam, sem
    reimplementar nem reinterpretar.

    Duas metricas reais, dois campos: `hrv` e `rhr`. Nao existe um terceiro
    sinal. `FCR` e o termo portugues de `rhr` ("frequencia cardiaca de
    repouso"), portanto nao ganha campo proprio — duplica-lo seria repetir o
    mesmo numero sob dois nomes. `heart-rate recovery` (queda da FC pos-
    esforco) e outro conceito, esta fora do escopo de HR-3 e sem campo aqui.
    """

    target_day: str
    window_days: int
    reference_day: Optional[str] = None
    hrv: Optional[HeartRateMetricTrend] = None
    rhr: Optional[HeartRateMetricTrend] = None
    hrv_field: Optional[str] = None
    freshness: Optional[FreshnessView] = None
    captured_at: Optional[str] = None
    provider: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_day": self.target_day,
            "window_days": self.window_days,
            "reference_day": self.reference_day,
            "hrv": self.hrv.to_dict() if self.hrv else None,
            "rhr": self.rhr.to_dict() if self.rhr else None,
            "hrv_field": self.hrv_field,
            "freshness": self.freshness.to_dict() if self.freshness else None,
            "captured_at": self.captured_at,
            "provider": self.provider,
        }


def _hr_trend(series: Mapping[date, float], *, field: str, unit: str,
              reference_day: date,
              window_days: int) -> HeartRateMetricTrend:
    current = series.get(reference_day)
    baseline, samples = derive_hr_baseline(
        series, reference_day=reference_day, window_days=window_days)
    if current is None:
        status = HR_TREND_MISSING_CURRENT_VALUE
    elif baseline is None:
        status = HR_TREND_INSUFFICIENT_HISTORY
    else:
        status = HR_TREND_AVAILABLE
    return HeartRateMetricTrend(
        field=field, status=status, current=current, baseline=baseline,
        delta=derive_hr_delta(current, baseline),
        delta_pct=derive_hr_delta_pct(current, baseline),
        sample_count=samples, unit=unit)


def build_heart_rate_trend_view(
        snapshot: Optional[SnapshotView], *, today: date,
        window_days: int = DEFAULT_HR_TREND_WINDOW_DAYS
) -> HeartRateTrendView:
    """Snapshot local -> tendencias observadas de HRV/RHR, sem provider.

    `today` e explicito (nenhum `date.today()` escondido) e `window_days` tem
    default **do projeto** (`DEFAULT_HR_TREND_WINDOW_DAYS`, igual a janela ja
    usada por `readiness._rising_rhr`/`_low_hrv`); nao ha limiar fisiologico
    novo.

    HRV nao mistura metricas: usa `hrv` quando existe na serie e **declara
    isso** em `hrv_field`; so cai para `hrv_sdnn` quando `hrv` esta ausente
    em toda a janela. `hrv` e `hrv_sdnn` sao unidades/metodologias diferentes
    (ex.: RMSSD vs. SDNN) e a escolha fica visivel, nunca silenciosa.

    Freshness e reportada mas nunca bloqueia: dado stale ainda produz baseline.
    """
    if isinstance(window_days, bool) or not isinstance(window_days, int) \
            or window_days <= 0:
        raise ValueError("window_days deve ser inteiro positivo")
    target_day = today.isoformat()
    if snapshot is None:
        return HeartRateTrendView(target_day=target_day,
                                  window_days=window_days)
    records = snapshot.wellness
    # `reference_day` = ultimo dia com wellness **de qualquer tipo**,
    # independente de `target_day`. Assim um wellness de ontem ainda produz
    # leitura, e o consumidor ve o dia exato a que os valores se referem. Nao
    # derivar de uma serie especifica: um dia com so `hrv` continua sendo o
    # dia de referencia mesmo sem `resting_hr`.
    observed_days = sorted(
        day for day in
        (_date(record.get("day") or record.get("id"))
         for record in records or []
         if isinstance(record, Mapping))
        if day is not None)
    reference_day = observed_days[-1] if observed_days else None
    if reference_day is None:
        return HeartRateTrendView(
            target_day=target_day, window_days=window_days,
            freshness=snapshot.freshness, captured_at=snapshot.captured_at,
            provider=snapshot.provider)

    hrv_series = _hr_series(records, field="hrv", allow_zero=False)
    hrv_field = "hrv"
    if not hrv_series:
        hrv_series = _hr_series(records, field="hrv_sdnn", allow_zero=False)
        hrv_field = "hrv_sdnn"
    rhr_series = _hr_series(records, field="resting_hr", allow_zero=False)

    return HeartRateTrendView(
        target_day=target_day, window_days=window_days,
        reference_day=reference_day.isoformat(),
        hrv=_hr_trend(hrv_series, field=hrv_field, unit=None,
                      reference_day=reference_day, window_days=window_days),
        rhr=_hr_trend(rhr_series, field="resting_hr", unit="bpm",
                      reference_day=reference_day, window_days=window_days),
        hrv_field=hrv_field if hrv_series else None,
        freshness=snapshot.freshness, captured_at=snapshot.captured_at,
        provider=snapshot.provider)


# ---------------------------------------------------------------------------
# Wellness observado (HR-4)
# ---------------------------------------------------------------------------
#
# Camada de LEITURA para os sinais de wellness que o provider REALMENTE
# entrega. Ela para em "observado -> contexto" e nunca em "score -> decisao ->
# prescricao": nao cria `ReadinessAction`, nao compoe score, nao combina sinais
# e nao duplica threshold de `readiness.py`.
#
# ## Nome
#
# A View nao se chama `SubjectiveWellnessView`. "Subjetivo" seria factualmente
# errado: `sleep_secs`, `sleep_score`, `stress` e `readiness` vem do
# provider/wearable, nao de auto-relato. Os itens genuinamente subjetivos —
# soreness, motivation, fatigue — sao exatamente os que o provider NAO expoe
# (§41: `unsupported_field`). `ObservedWellnessView` diz o que ha dentro: valor
# observado do provider mais contexto derivado.
#
# ## Direction: nenhuma
#
# Nenhum campo de HR-4 tem direcao documentada no contrato do repositorio, e nao
# ha fonte primaria que a fixe. Portanto **nenhuma metrica carrega rotulo
# high-is-good / high-is-bad**: os valores sao numeros observados, e o que eles
# significam pertence a policy, fora daqui (§4, §18).

DEFAULT_WELLNESS_WINDOW_DAYS = 7

WELLNESS_STATUS_OBSERVED = "observed"
WELLNESS_STATUS_MISSING_CURRENT = "missing_current"
WELLNESS_STATUS_UNSUPPORTED = "unsupported_field"

#: Escala/direcao sem contrato documentado. Preferivel a afirmar sem evidencia.
WELLNESS_SCALE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class WellnessMetricSpec:
    """Contrato de leitura de UM conceito de wellness (§3, §7-§9).

    Descreve o que o provider entrega de fato, incluindo o que ele nao
    entrega. `field is None` significa `unsupported_field`: o conceito existe no
    vocabulario do dominio mas nao tem chave no boundary — e nao se cria alias
    nem chave parecida para preencher a lacuna (§41).
    """

    concept: str
    field: Optional[str]
    source: str
    unit: Optional[str] = None
    scale: Optional[str] = None
    baseline: bool = False
    allow_zero: bool = True


#: Inventario HR-4. Ordem estavel: a View expoe esses conceitos por nome.
#:
#: `allow_zero=True` em todos os campos, decisao documentada por caso:
#:   - `sleep_secs` 0 e semanticamente possivel (dia sem sono registrado); a
#:     View nao consegue distinguir isso de sync falha — e por isso nao
#:     interpreta o zero.
#:   - `sleep_score`/`stress`/`readiness` tem escala nao documentada, logo o
#:     range 0..N nao pode ser assumido para rejeitar zero.
#: `baseline=False` em `readiness` porque e composto do lado do provider, cuja
#: composicao interna nao e contrato estavel: media entre dias pode misturar
#: versoes diferentes do score.
WELLNESS_METRIC_SPECS: tuple[WellnessMetricSpec, ...] = (
    WellnessMetricSpec(
        concept="sleep_duration", field="sleep_secs", baseline=True,
        unit="seconds", scale=None,
        source="intervals.icu /wellness `sleepSecs`, em segundos"),
    WellnessMetricSpec(
        concept="sleep_score", field="sleep_score", baseline=True,
        unit="points", scale=WELLNESS_SCALE_UNKNOWN,
        source="intervals.icu /wellness `sleepScore`"),
    WellnessMetricSpec(
        concept="stress", field="stress", baseline=True,
        unit=WELLNESS_SCALE_UNKNOWN, scale=WELLNESS_SCALE_UNKNOWN,
        source="intervals.icu /wellness `stress`"),
    WellnessMetricSpec(
        concept="soreness", field=None,
        source="sem chave em /wellness; contrato ausente no provider"),
    WellnessMetricSpec(
        concept="motivation", field=None,
        source="sem chave em /wellness; contrato ausente no provider"),
    WellnessMetricSpec(
        concept="fatigue", field=None,
        source="sem chave em /wellness; contrato ausente no provider"),
    WellnessMetricSpec(
        concept="provider_readiness", field="readiness", baseline=False,
        unit="points", scale=WELLNESS_SCALE_UNKNOWN,
        source="intervals.icu /wellness `readiness`, composto do provider"),
)

@dataclass(frozen=True)
class WellnessMetricView:
    """Um sinal de wellness: valor observado + contexto derivado. Sem veredito."""

    concept: str
    field: Optional[str]
    status: str
    source: str
    current: Optional[float] = None
    baseline: Optional[float] = None
    delta: Optional[float] = None
    delta_pct: Optional[float] = None
    sample_count: int = 0
    unit: Optional[str] = None
    scale: Optional[str] = None

    @property
    def available(self) -> bool:
        return self.status == WELLNESS_STATUS_OBSERVED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ObservedWellnessView:
    """Sinais de wellness observados + baseline/delta, sem policy (HR-4).

    LEITURA OBSERVACIONAL. Nao contem `ReadinessAction`, advice, score composto
    nem prescricao, e nao altera `ReadinessView`. Os limiares existentes
    (`SLEEP_SHORT_HOURS`, `SLEEP_BELOW_AVG_HOURS`, `READINESS_LOW`) continuam
    em `readiness.py` com o mesmo significado; esta View expoe os valores
    **subjacentes** que eles leem, sem reimplementar nem reinterpretar (§25,
    §26).

    Os sete conceitos do inventario aparecem sempre, inclusive os que o provider
    nao expoe — nesses, `status == "unsupported_field"`. Ausencia de campo e um
    resultado, nao um campo omitido (§3, §41).
    """

    target_day: str
    window_days: int
    reference_day: Optional[str] = None
    sleep_duration: Optional[WellnessMetricView] = None
    sleep_score: Optional[WellnessMetricView] = None
    stress: Optional[WellnessMetricView] = None
    soreness: Optional[WellnessMetricView] = None
    motivation: Optional[WellnessMetricView] = None
    fatigue: Optional[WellnessMetricView] = None
    provider_readiness: Optional[WellnessMetricView] = None
    freshness: Optional[FreshnessView] = None
    captured_at: Optional[str] = None
    provider: Optional[str] = None

    @property
    def metrics(self) -> tuple[WellnessMetricView, ...]:
        return tuple(
            metric for metric in (
                self.sleep_duration, self.sleep_score, self.stress,
                self.soreness, self.motivation, self.fatigue,
                self.provider_readiness)
            if metric is not None)

    @property
    def unsupported(self) -> tuple[str, ...]:
        """Conceitos sem chave real no boundary."""
        return tuple(metric.concept for metric in self.metrics
                     if metric.status == WELLNESS_STATUS_UNSUPPORTED)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_day": self.target_day,
            "window_days": self.window_days,
            "reference_day": self.reference_day,
            "available": self.available,
            "metrics": [metric.to_dict() for metric in self.metrics],
            "unsupported": list(self.unsupported),
            "freshness": self.freshness.to_dict() if self.freshness else None,
            "captured_at": self.captured_at,
            "provider": self.provider,
        }

    @property
    def available(self) -> bool:
        return any(metric.available for metric in self.metrics)


def _wellness_number(value: Any, *, allow_zero: bool) -> Optional[float]:
    """Coerce para float OBSERVADO, ou `None` se ausente/invalido (§19, §20).

    Mesma recusa de `_hr_metric` para `bool`, string nao numerica, `NaN` e
    infinito, mais um criterio que HR-3 nao tinha: **negativo e sempre
    rejeitado**. Nenhuma grandeza de wellness aqui (segundos, pontos, escala
    proprietaria) e negativa, entao valor negativo e leitura quebrada.

    Nao e o mesmo criterio de zero: aqui zero sobrevive em todos os campos
    (§ decisao `allow_zero` em `WELLNESS_METRIC_SPECS`), porque a escala nao e
    contrato documentado. Ausencia nunca vira zero.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            number = float(stripped)
        except ValueError:
            return None
    elif isinstance(value, (int, float)):
        number = float(value)
    else:
        return None
    if number != number:  # NaN
        return None
    if number in (float("inf"), float("-inf")):
        return None
    if number < 0.0:
        return None
    if number == 0.0 and not allow_zero:
        return None
    return number


def _wellness_series(records: Any, *, field: str,
                     allow_zero: bool) -> dict[date, float]:
    """Serie observada {dia: valor}, deduplicando pelo ultimo registro do dia.

    Mesma politica de `_hr_series`: nao interpola gap e nao preenche dia
    ausente. Dia repetido nao e misturado — o provider pode reenviar o mesmo
    dia com correcao, e a ultima versao vence.
    """
    series: dict[date, float] = {}
    for record in records or []:
        if not isinstance(record, Mapping):
            continue
        day = _date(record.get("day") or record.get("id"))
        if day is None:
            continue
        value = _wellness_number(record.get(field), allow_zero=allow_zero)
        if value is not None:
            series[day] = value
    return series


def _wellness_baseline(series: Mapping[date, Any], *, reference_day: date,
                       window_days: int, allow_zero: bool
                       ) -> tuple[Optional[float], int]:
    """Baseline = media das observacoes na janela, terminando em `reference_day`.

    Nao reaproveita `derive_hr_baseline` de proposito: aquele descarta zero
    (`allow_zero=False` interno), o que mataria um baseline legitimately 0 e o
    `delta` de um dia observado com 0. Mesma formula, criterio de admissao
    diferente — o campo manda (§16, §20).
    """
    if isinstance(window_days, bool) or not isinstance(window_days, int) \
            or window_days <= 0:
        raise ValueError("window_days deve ser inteiro positivo")
    start = reference_day - timedelta(days=window_days - 1)
    values: list[float] = []
    for day, value in series.items():
        if start <= day <= reference_day:
            parsed = _wellness_number(value, allow_zero=allow_zero)
            if parsed is not None:
                values.append(parsed)
    if not values:
        return None, 0
    return sum(values) / len(values), len(values)


def _wellness_delta(current: Any, baseline: Any, *,
                    allow_zero: bool) -> Optional[float]:
    target = _wellness_number(current, allow_zero=allow_zero)
    base = _wellness_number(baseline, allow_zero=allow_zero)
    if target is None or base is None:
        return None
    return target - base


def _wellness_delta_pct(current: Any, baseline: Any, *,
                        allow_zero: bool) -> Optional[float]:
    """`(current - baseline) / baseline x 100`; `None` quando baseline e 0.

    Divisao por zero nao e feita e o sinal nao vira 0% (§36).
    """
    target = _wellness_number(current, allow_zero=allow_zero)
    base = _wellness_number(baseline, allow_zero=allow_zero)
    if target is None or base is None or base == 0:
        return None
    return (target - base) / base * 100.0


def _unsupported_metric(spec: WellnessMetricSpec) -> WellnessMetricView:
    """Concepto sem chave no boundary: resultado declarado, nao campo omitido."""
    return WellnessMetricView(
        concept=spec.concept, field=None, status=WELLNESS_STATUS_UNSUPPORTED,
        source=spec.source, unit=spec.unit, scale=spec.scale)


def _wellness_change(current: Any, baseline: Any, samples: int, *,
                     allow_zero: bool) -> tuple[Optional[float],
                                               Optional[float]]:
    """`(delta, delta_pct)`, ou `(None, None)` quando nao ha o que comparar.

    Alem de `baseline is None` e de `baseline == 0` (razao indefinida -> o sinal
    nao vira 0%, §36), exige `samples >= 2`. Com uma unica observacao a media da
    janela **e** o proprio current, entao `delta == 0.0` e `delta_pct == 0.0`
    seriam tautologias: a View estaria afirmando "sem mudanca" sem nenhuma
   mudanca observavel. `baseline` continua exposto (com `sample_count` ao lado,
    que e a autoridade sobre a qualidade da base) — o que nao se emite e a
    **afirmacao de tendencia**, nao o dado.
    """
    if samples < 2:
        return None, None
    return (_wellness_delta(current, baseline, allow_zero=allow_zero),
            _wellness_delta_pct(current, baseline, allow_zero=allow_zero))


def _wellness_metric_view(spec: WellnessMetricSpec, records: Any, *,
                          reference_day: date,
                          window_days: int) -> WellnessMetricView:
    if spec.field is None:
        # Sem chave no boundary: `unsupported_field` e o resultado, mesmo com
        # historico presente. Nao se procura campo parecido no registro (§41).
        return _unsupported_metric(spec)
    series = _wellness_series(records, field=spec.field,
                              allow_zero=spec.allow_zero)
    current = series.get(reference_day)
    if spec.baseline:
        baseline, samples = _wellness_baseline(
            series, reference_day=reference_day, window_days=window_days,
            allow_zero=spec.allow_zero)
    else:
        # baseline por design ausente; `sample_count` ainda expoe a cobertura.
        baseline, samples = None, len([
            day for day in series
            if reference_day - timedelta(days=window_days - 1)
            <= day <= reference_day])
    status = (WELLNESS_STATUS_OBSERVED if current is not None
              else WELLNESS_STATUS_MISSING_CURRENT)
    delta, delta_pct = _wellness_change(current, baseline, samples,
                                        allow_zero=spec.allow_zero)
    return WellnessMetricView(
        concept=spec.concept, field=spec.field, status=status,
        source=spec.source, current=current, baseline=baseline,
        delta=delta, delta_pct=delta_pct,
        sample_count=samples, unit=spec.unit, scale=spec.scale)


def build_observed_wellness_view(
        snapshot: Optional[SnapshotView], *, today: date,
        window_days: int = DEFAULT_WELLNESS_WINDOW_DAYS
) -> ObservedWellnessView:
    """Snapshot local -> sinais de wellness observados, sem provider (§22, §23).

    `today` e explicito (nenhum `date.today()` escondido) e `window_days` tem o
    default tecnico ja usado por `DEFAULT_HR_TREND_WINDOW_DAYS` /
    `readiness._low_hrv`; nao ha janela fisiologica nova (§17).

    `reference_day` e o ultimo dia com wellness de qualquer tipo, igual a
    HR-3, para que os valores dos sete sinais sejam comparaveis entre si: um dia
    que so tem `sleep_secs` ainda e o dia de referencia, e `stress` aparece como
    `missing_current` em vez de roubar o dia de outro sinal.

    Freshness e reportada mas nunca bloqueia: dado stale continua produzindo
    baseline e tendencia (§21).
    """
    if isinstance(window_days, bool) or not isinstance(window_days, int) \
            or window_days <= 0:
        raise ValueError("window_days deve ser inteiro positivo")
    target_day = today.isoformat()
    if snapshot is None:
        return ObservedWellnessView(
            target_day=target_day, window_days=window_days,
            **_unobserved_metrics())

    records = snapshot.wellness
    observed_days = sorted(
        day for day in
        (_date(record.get("day") or record.get("id"))
         for record in records or []
         if isinstance(record, Mapping))
        if day is not None)
    reference_day = observed_days[-1] if observed_days else None
    if reference_day is None:
        return ObservedWellnessView(
            target_day=target_day, window_days=window_days,
            freshness=snapshot.freshness, captured_at=snapshot.captured_at,
            provider=snapshot.provider,
            **_unobserved_metrics())

    metrics = {
        spec.concept: _wellness_metric_view(
            spec, records, reference_day=reference_day, window_days=window_days)
        for spec in WELLNESS_METRIC_SPECS
    }
    return ObservedWellnessView(
        target_day=target_day, window_days=window_days,
        reference_day=reference_day.isoformat(),
        freshness=snapshot.freshness, captured_at=snapshot.captured_at,
        provider=snapshot.provider, **metrics)


def _unobserved_metrics() -> Dict[str, Any]:
    """View sem snapshot/registro: nenhum conceito tem valor observado.

    Cobre o contrato inteiro mesmo sem dado (§33): quem tem chave volta
    `missing_current`, quem nao tem volta `unsupported_field`. Nenhum vira 0.
    """
    out: Dict[str, Any] = {}
    for spec in WELLNESS_METRIC_SPECS:
        out[spec.concept] = (
            _unsupported_metric(spec) if spec.field is None else
            WellnessMetricView(
                concept=spec.concept, field=spec.field,
                status=WELLNESS_STATUS_MISSING_CURRENT, source=spec.source,
                unit=spec.unit, scale=spec.scale))
    return out


def build_ctl_ramp_view(snapshot: Optional[SnapshotView], *, target_day: date,
                        window_days: int = DEFAULT_CTL_RAMP_WINDOW_DAYS
                        ) -> CtlRampView:
    """Snapshot local -> tendencia de CTL, sem provider e sem policy."""
    if isinstance(window_days, bool) or not isinstance(window_days, int) \
            or window_days <= 0:
        raise ValueError("window_days deve ser inteiro positivo")
    baseline_day = target_day - timedelta(days=window_days)
    history = ctl_history_by_day(snapshot)
    target_ctl = _f(history.get(target_day))
    baseline_ctl = _f(history.get(baseline_day))
    return CtlRampView(
        target_day=target_day.isoformat(), window_days=window_days,
        baseline_day=baseline_day.isoformat(), target_ctl=target_ctl,
        baseline_ctl=baseline_ctl,
        ramp_rate=derive_ctl_ramp_rate(
            history, target_day=target_day, window_days=window_days),
        observed_days=len(history),
        freshness=snapshot.freshness if snapshot is not None else None,
        captured_at=snapshot.captured_at if snapshot is not None else None,
    )
