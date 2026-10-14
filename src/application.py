# Hermes Coach — Application seam (UI-1)
#
# Application layer/use cases to decouple CLI handlers from orchestration.
# Incremental seam: the existing CLI keeps working, `plan.json` format and
# prescription behavior are untouched. No lifecycle/schema changes here.
#
from __future__ import annotations

import dataclasses
import math
import os
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import athlete_profile as _athlete_profile
    import ctl_ramp_advisory as _ctl_ramp_advisory
    import activity_stream_cache as _activity_stream_cache
    import form_advisory as _form_advisory
    import ftp_evidence as _ftp_evidence
    import ftp_history as _ftp_history
    import insight.contract as _insight
    import lifecycle as _lifecycle
    import pw_hr_decoupling as _pw_hr_decoupling
    import snapshot as _snapshot
    import training_block as _training_block
    import ui_state as _ui_state
    import workout_identity as _workout_identity
    from provider import (ActivityStream, ActivityStreamProvider, ProviderCapability,
                          ProviderError, ProviderOperationError,  # noqa: F401
                          TrainingMetricsProvider,
                          provider_capabilities as _provider_capabilities)
    from provider_fields import (field as _field,  # noqa: F401
                                 is_completed as _is_completed)
except ImportError:  # execucao como pacote (src.application)
    from . import athlete_profile as _athlete_profile  # type: ignore
    from . import ctl_ramp_advisory as _ctl_ramp_advisory  # type: ignore
    from . import activity_stream_cache as _activity_stream_cache  # type: ignore
    from . import form_advisory as _form_advisory  # type: ignore
    from . import ftp_evidence as _ftp_evidence  # type: ignore
    from . import ftp_history as _ftp_history  # type: ignore
    from .insight import contract as _insight  # type: ignore
    from . import lifecycle as _lifecycle  # type: ignore
    from . import pw_hr_decoupling as _pw_hr_decoupling  # type: ignore
    from . import snapshot as _snapshot  # type: ignore
    from . import training_block as _training_block  # type: ignore
    from . import ui_state as _ui_state  # type: ignore
    from . import workout_identity as _workout_identity  # type: ignore
    from .provider import (ActivityStream, ActivityStreamProvider,  # type: ignore
                            ProviderCapability,  # noqa: F401
                            ProviderError, ProviderOperationError,
                            TrainingMetricsProvider,
                           provider_capabilities as _provider_capabilities)
    from .provider_fields import (field as _field,  # type: ignore  # noqa: F401
                                  is_completed as _is_completed)

Plan = List[Dict[str, Any]]
_BLOCK_CONTEXT_UNSET = object()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PLAN_FILE = PROJECT_ROOT / "plan.json"
ENV_FILE = PROJECT_ROOT / ".env"
# Cache de leitura do provider, separado do plan.json (nao polui o plano).
SNAPSHOT_FILENAME = "training_snapshot.json"
ACTIVITY_STREAM_CACHE_FILENAME = "activity_streams.json"
FTP_HISTORY_FILENAME = "ftp_history.json"
FTP_EVIDENCE_FILENAME = "ftp_evidence.json"


# ---------------------------------------------------------------------------
# Config adapter
# ---------------------------------------------------------------------------

def load_env(path: Path) -> None:
    """Carrega `.env` para o ambiente sem sobrescrever valores ja definidos."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def get_env(key: str, default: Optional[str] = None,
            env_file: Path = ENV_FILE) -> Optional[str]:
    load_env(env_file)
    return os.environ.get(key, default)


# ---------------------------------------------------------------------------
# Provider contract
# ---------------------------------------------------------------------------
# O contrato (`TrainingMetricsProvider`) e os records normalizados vivem em
# `provider.py` (UI-3). A Application depende apenas desse boundary; o
# `IntervalsAdapter` (composition root) e quem fala com o Intervals.icu.


# ---------------------------------------------------------------------------
# Plan repository adapter
# ---------------------------------------------------------------------------

def _plan_module():
    if __package__:
        from . import plan  # type: ignore
    else:  # application importado pela CLI executada como script direto
        import plan  # noqa: F401
    return plan


def _append_insight_fact(
    facts: list["_insight.InsightFact"], key: str, value: Any,
    classification: "_insight.FactClassification", unit: Optional[str] = None,
) -> None:
    """Anexa um fato permitido, omitindo ausência e valores inválidos."""
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, float) and not math.isfinite(value):
        return
    if not isinstance(value, (str, int, float)):
        return
    if isinstance(value, str) and not value.strip():
        return
    if any(fact.key == key for fact in facts):
        raise ValueError(f"chave de insight duplicada: {key}")
    facts.append(_insight.InsightFact(key, value, classification, unit))


def _insight_summary_text(primary: Any, fallback: Any) -> Optional[str]:
    """Retorna somente texto planned já existente, sem criar linguagem nova."""
    for candidate in (primary, fallback):
        if isinstance(candidate, str) and candidate.strip():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Application service (composition root friendly)
# ---------------------------------------------------------------------------

@dataclass
class Application:
    """Fachada de casos de uso.

    Recebe dependencias explicitamente (config path, plan path e um
    `client_factory`) para que CLI, UI e testes possam injetar implementacoes
    diferentes sem que os casos de uso localizem `get_client()` por conta
    propria. O composition root (a CLI) e quem decide a implementacao concreta.
    """

    plan_path: Path = PLAN_FILE
    env_path: Path = ENV_FILE
    client_factory: Optional[Callable[[], TrainingMetricsProvider]] = None
    snapshot_path: Optional[Path] = None
    activity_stream_cache_path: Optional[Path] = None
    ftp_history_path: Optional[Path] = None
    ftp_evidence_path: Optional[Path] = None

    # -- config ----------------------------------------------------------
    def load_env(self) -> None:
        load_env(self.env_path)

    def get_env(self, key: str, default: Optional[str] = None) -> Optional[str]:
        self.load_env()
        return os.environ.get(key, default)

    def get_athlete_physiological_profile(
            self, *, today: Optional[date] = None,
            now: Optional[datetime] = None,
    ) -> "_athlete_profile.AthletePhysiologicalProfile":
        """Perfil local/read-only de configuracao e observacao fisiologica.

        Nunca chama provider, nao grava snapshot/plano e nao participa do
        build. `ftp` vem exclusivamente de `FtpHistory.resolve_ftp_at` no
        instante `now` (relogio da Application quando o caller nao passa um);
        sem referencia canonica vigente o resultado e ``None`` — `.env FTP` e
        `DEFAULT_FTP` deliberadamente nao passam por aqui. `now` naive nao e
        convertido: o contrato timezone-aware do `FtpHistory` vale e falha
        fechada. RHR reutiliza a View HR-3 sobre o snapshot normalizado, sem
        uma segunda extracao de wellness. HRV baseline, VO2, CP/W', max HR e
        training age permanecem desconhecidos nesta v1.
        """
        plan = _plan_module()
        reference = self.get_ftp_at(
            now if now is not None else datetime.now(timezone.utc))
        fthr = plan.parse_fthr(self.get_env("FTHR", "") or "")
        weekly_hours = plan.parse_weekly_hours(
            self.get_env("WEEKLY_HOURS", "") or "")
        raw_training_days = self.get_env("TRAINING_DAYS", "") or ""
        training_days = (plan.parse_training_days(raw_training_days)
                         if raw_training_days.strip() else ())
        long_day = plan.parse_long_day(self.get_env("LONG_DAY", "") or "")
        trend = self.get_heart_rate_trend_view(today=today, now=now)
        resting_hr = trend.rhr.current if trend.rhr is not None else None
        return _athlete_profile.build_athlete_profile(
            canonical_ftp=reference.ftp_value if reference else None,
            canonical_source=reference.source if reference else None,
            threshold_hr=fthr, weekly_training_hours=weekly_hours,
            training_days=training_days, preferred_long_day=long_day,
            resting_hr=resting_hr)

    # -- canonical FTP history -------------------------------------------
    def _ftp_history_file(self) -> Path:
        return self.ftp_history_path or (Path(self.plan_path).parent / FTP_HISTORY_FILENAME)

    def get_ftp_history(self) -> "_ftp_history.FtpHistory":
        """Historico local confirmado; nao consulta .env nem provider."""
        return _ftp_history.FtpHistoryRepository(self._ftp_history_file()).load()

    def get_ftp_at(self, timestamp: datetime) -> Optional["_ftp_history.FtpReference"]:
        return self.get_ftp_history().resolve_ftp_at(timestamp)

    def get_current_ftp_reference(
            self, now: datetime) -> Optional["_ftp_history.FtpReference"]:
        return self.get_ftp_history().current_reference(now)

    def save_ftp_reference(self, reference: "_ftp_history.FtpReference") -> None:
        """Persiste explicitamente uma referencia confirmada, sem efeitos externos."""
        repository = _ftp_history.FtpHistoryRepository(self._ftp_history_file())
        repository.save(repository.load().with_reference(reference))

    # -- FTP evidence / advice (FTP-H2) --------------------------------
    def _ftp_evidence_file(self) -> Path:
        return self.ftp_evidence_path or (
            Path(self.plan_path).parent / FTP_EVIDENCE_FILENAME)

    def get_ftp_evidence(self) -> Tuple["_ftp_evidence.FtpEvidence", ...]:
        """Evidencia local de FTP (estimativas/observacoes); nao consulta
        .env, provider nem historico canonico."""
        return _ftp_evidence.FtpEvidenceRepository(self._ftp_evidence_file()).load()

    def record_ftp_evidence(self, evidence: "_ftp_evidence.FtpEvidence") -> None:
        """Registra evidencia local (append por id). Nao promove referencia."""
        repository = _ftp_evidence.FtpEvidenceRepository(self._ftp_evidence_file())
        existing = repository.load()
        if any(entry.id == evidence.id for entry in existing):
            raise ValueError(f"evidencia FTP ja registrada: {evidence.id}")
        repository.save(existing + (evidence,))

    def get_ftp_advice(self, now: Optional[datetime] = None) -> "_ftp_evidence.Advice":
        """Advice adocional (FTP-H2) sobre a evidencia vs o FTP canonico atual."""
        current = self.get_current_ftp_reference(
            now if now is not None else datetime.now(timezone.utc))
        return _ftp_evidence.advise_ftp(self.get_ftp_evidence(), current)

    def confirm_ftp_evidence(
            self, evidence_id: str, *,
            now: Optional[datetime] = None,
            effective_from: Optional[datetime] = None,
            reference_id: Optional[str] = None,
            notes: Optional[str] = None) -> "_ftp_history.FtpReference":
        """A unica ponte evidencia -> estado canonico: requer confirmacao
        explicita do usuario. Persiste em `ftp_history.json` sem efeitos
        externos (build/prescricao/provider nao sao tocados; isso e FTP-H6)."""
        evidence_by_id = {entry.id: entry for entry in self.get_ftp_evidence()}
        if evidence_id not in evidence_by_id:
            raise ValueError(f"evidencia FTP inexistente: {evidence_id}")
        evidence = evidence_by_id[evidence_id]
        resolved_now = now if now is not None else datetime.now(timezone.utc)
        if effective_from is None:
            effective_from = resolved_now
        reference = _ftp_evidence.evidence_to_reference(
            evidence,
            reference_id=reference_id or f"ftp-{evidence.id}",
            effective_from=effective_from,
            recorded_at=resolved_now,
            notes=notes,
        )
        repository = _ftp_history.FtpHistoryRepository(self._ftp_history_file())
        history = repository.load()
        same_evidence = [entry for entry in history.references
                         if entry.evidence_id == evidence.id]
        if len(same_evidence) > 1:
            raise ValueError(
                f"historico FTP corrompido: evidencia {evidence.id} possui "
                "mais de uma referencia")
        if same_evidence:
            existing = same_evidence[0]
            provenance = (
                existing.ftp_value == reference.ftp_value
                and existing.source == reference.source
                and existing.protocol == reference.protocol
                and existing.evidence_activity_id == reference.evidence_activity_id
                and existing.evidence_workout_id == reference.evidence_workout_id
                and existing.provider == reference.provider
            )
            if provenance:
                return existing
            raise ValueError(
                f"referencia FTP existente para evidencia {evidence.id} tem "
                "provenance incompativel")
        if any(entry.id == reference.id for entry in history.references):
            raise ValueError(
                f"id de referencia FTP em conflito: {reference.id}")
        repository.save(history.with_reference(reference))
        return reference

    # -- identity / lifecycle (UI-2) -------------------------------------
    @staticmethod
    def enrich_plan(workouts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Anexa identidade local (`id`) e lifecycle explicito a cada treino.

        Fronteira do UI-2: o modulo de dominio (`build_plan`) segue agnostico de
        identidade; quem persiste/entrega plano ao consumidor e a Application,
        que garante `id` (HermesWorkoutId, estavel e independente do provider) e
        `lifecycle` (default `planned`). Idempotente e backward-compatible: um
        plano legado ganha o MESMO `id` deterministico a cada leitura.
        """
        return [_lifecycle.ensure(_workout_identity.ensure(w))
                for w in workouts]

    # -- plan persistence ------------------------------------------------
    def load_plan(self) -> List[Dict[str, Any]]:
        """Workouts do plano local; lista vazia se o arquivo nao existe.

        Conveniencia de seam para consumidores locais (UI/testes): nao forca o
        chamador a conhecer `FileNotFoundError`. O adapter delega ao modulo
        `plan`, que e a fonte do formato, e enriquece com identidade/lifecycle.
        """
        plan = _plan_module()
        try:
            workouts = plan.load_plan(self.plan_path)
        except FileNotFoundError:
            return []
        return self.enrich_plan(workouts)

    def load_plan_meta(self) -> Dict[str, Any]:
        plan = _plan_module()
        return plan.load_plan_meta(self.plan_path)

    def save_plan(
        self,
        workouts: List[Dict[str, Any]],
        *,
        goal: Optional[str] = None,
        race_date: Optional[str] = None,
        ftp_test_date: Optional[str] = None,
        ftp_candidates: Optional[List[Dict[str, Any]]] = None,
        absorbed_ids: Optional[List[str]] = None,
        block_context: object = _BLOCK_CONTEXT_UNSET,
    ) -> None:
        plan = _plan_module()
        kwargs = {}
        if block_context is not _BLOCK_CONTEXT_UNSET:
            kwargs["block_context"] = block_context
        plan.save_plan(
            self.enrich_plan(workouts),
            self.plan_path,
            goal=goal,
            race_date=race_date,
            ftp_test_date=ftp_test_date,
            ftp_candidates=ftp_candidates,
            absorbed_ids=absorbed_ids,
            **kwargs,
        )

    # -- lifecycle operations (UI-2) -------------------------------------
    def get_workout(self, workout_id: str,
                    plan: Optional[List[Dict[str, Any]]] = None
                    ) -> Optional[Dict[str, Any]]:
        for w in (self.load_plan() if plan is None else plan):
            if w.get(_workout_identity.WORKOUT_ID_FIELD) == workout_id:
                return w
        return None

    def workout_lifecycle(self, workout_id: str,
                          plan: Optional[List[Dict[str, Any]]] = None
                          ) -> Optional[str]:
        """Lifecycle DECLARADO persistido (nao resolve execucao — ver
        `derive_workout_lifecycle`)."""
        workout = self.get_workout(workout_id, plan)
        if workout is None:
            return None
        return _lifecycle.ensure(workout)["lifecycle"]

    def derive_workout_lifecycle(self, workout_id: str, *,
                                 events: List[Dict[str, Any]],
                                 today: Optional[date] = None,
                                 plan: Optional[List[Dict[str, Any]]] = None
                                 ) -> Optional[str]:
        """Lifecycle efetivo: resolve `completed`/`missed` a partir da data e da
        evidencia de execucao no provider, sem gravar nada.

        O provider entra apenas como evidencia (via `session_execution_state`,
        o mesmo criterio de `_done_and_extra`); a identidade continua sendo o
        `id` local. Estados declarados != `planned` vencem a derivacao."""
        workout = self.get_workout(workout_id, plan)
        if workout is None:
            return None
        plan_mod = _plan_module()
        exec_state = plan_mod.session_execution_state(workout, events)
        is_done = exec_state == plan_mod.SESSAO_CONCLUIDA
        return _lifecycle.derive(
            day=str(workout.get("day")), today=today or date.today(),
            is_done=is_done, declared=workout.get("lifecycle"))

    def set_workout_lifecycle(self, workout_id: str, new_state: str,
                              plan: Optional[List[Dict[str, Any]]] = None
                              ) -> Dict[str, Any]:
        """Aplica uma transicao local de lifecycle e persiste o plano.

        Nao publica no calendario e nao toca no provider. Levanta `KeyError` se
        o `id` nao existe e `ValueError` se a transicao e invalida."""
        workouts = self.load_plan() if plan is None else plan
        meta = self.load_plan_meta()
        workout = self.get_workout(workout_id, workouts)
        if workout is None:
            raise KeyError(workout_id)
        current = _lifecycle.ensure(workout)["lifecycle"]
        _lifecycle.validate_transition(current, new_state)
        workout["lifecycle"] = new_state
        self._save_with_meta(workouts, meta)
        return workout

    def postpone_workout(self, workout_id: str) -> Dict[str, Any]:
        return self.set_workout_lifecycle(workout_id,
                                          _lifecycle.LIFECYCLE_POSTPONED)

    def cancel_workout(self, workout_id: str) -> Dict[str, Any]:
        return self.set_workout_lifecycle(workout_id,
                                          _lifecycle.LIFECYCLE_CANCELLED)

    def _save_with_meta(self, workouts: List[Dict[str, Any]],
                        meta: Dict[str, Any]) -> None:
        self.save_plan(
            workouts,
            goal=meta.get("goal"), race_date=meta.get("race_date"),
            ftp_test_date=meta.get("ftp_test_date"),
            ftp_candidates=meta.get("ftp_candidates"),
            absorbed_ids=meta.get("absorbed_ids"),
            block_context=meta.get("block_context"))

    def start_training_block(
        self, block: "_training_block.BlockContext", *, replace: bool = False,
    ) -> "_training_block.BlockContext":
        """Persiste explicitamente o bloco ativo sem alterar a prescricao.

        A substituicao exige opt-in para nao apagar a identidade do bloco ativo
        por um save incidental. A policy de quando abrir/fechar blocos e futura.
        """
        meta = self.load_plan_meta()
        current = meta.get("block_context")
        if current is not None and current != block and not replace:
            raise ValueError("ja existe block context ativo; use replace explicitamente")
        self.save_plan(
            self.load_plan(), goal=meta.get("goal"), race_date=meta.get("race_date"),
            ftp_test_date=meta.get("ftp_test_date"),
            ftp_candidates=meta.get("ftp_candidates"),
            absorbed_ids=meta.get("absorbed_ids"), block_context=block)
        return block

    # -- local completion (UI-4) -----------------------------------------
    def completion_status(self, workout_id: str,
                          plan: Optional[List[Dict[str, Any]]] = None
                          ) -> Optional[Dict[str, Any]]:
        """Estado LOCAL de conclusao, sem provider.

        Distingue o lifecycle declarado (estado) do metadado de evidencia
        (`completion`: origem/timestamp). Nunca consulta o Intervals."""
        workout = self.get_workout(workout_id, plan)
        if workout is None:
            return None
        return {
            "workout_id": workout_id,
            "status": _lifecycle.ensure(workout)["lifecycle"],
            "completion": _lifecycle.completion(workout),
        }

    def mark_completed(self, workout_id: str, *, source: str,
                       observed_at: Optional[str] = None,
                       provider_event_id: Any = None,
                       activity_id: Any = None,
                       plan: Optional[List[Dict[str, Any]]] = None
                       ) -> Dict[str, Any]:
        """Marca o treino como `completed` localmente e persiste.

        `source` registra de onde veio a evidencia (local/provider_match/...).
        Levanta `KeyError` para id desconhecido e `ValueError` para transicao
        invalida (ex.: `cancelled -> completed`); nunca sobrescreve em silencio
        um estado declarado incompativel."""
        workouts = self.load_plan() if plan is None else plan
        meta = self.load_plan_meta()
        workout = self.get_workout(workout_id, workouts)
        if workout is None:
            raise KeyError(workout_id)
        current = _lifecycle.ensure(workout)["lifecycle"]
        _lifecycle.validate_transition(current, _lifecycle.LIFECYCLE_COMPLETED)
        workout["lifecycle"] = _lifecycle.LIFECYCLE_COMPLETED
        workout.update(_lifecycle.set_completion(
            workout, source=source, observed_at=observed_at,
            provider_event_id=provider_event_id, activity_id=activity_id))
        self._save_with_meta(workouts, meta)
        return workout

    def reconcile_completion(
        self, *, events: Optional[List[Dict[str, Any]]] = None,
        snapshot: Optional["_snapshot.TrainingSnapshot"] = None,
        today: Optional[date] = None, now: Optional[datetime] = None,
        plan: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Aplica evidencia observada ao lifecycle LOCAL, por HermesWorkoutId.

        Casamento atual (`external_id` -> dia) permanece como descoberta; o
        resultado aponta para o `id` local antes de mutar estado. Nunca
        sobrescreve estado declarado != `planned`, e `completed` e terminal
        (idempotente em re-sync)."""
        if events is None:
            events = list(snapshot.events) if snapshot is not None else []
        workouts = self.load_plan() if plan is None else plan
        matches = match_events_to_workouts(workouts, events)
        report: Dict[str, Any] = {"matched": len(matches), "applied": [],
                                  "conflicts": [], "unchanged": []}
        applied: List[str] = []
        for workout_id, (workout, event) in matches.items():
            current = _lifecycle.ensure(workout)["lifecycle"]
            if current == _lifecycle.LIFECYCLE_COMPLETED:
                report["unchanged"].append(workout_id)
                continue
            if current != _lifecycle.LIFECYCLE_PLANNED:
                report["conflicts"].append(
                    {"workout_id": workout_id, "declared": current})
                continue
            workout["lifecycle"] = _lifecycle.LIFECYCLE_COMPLETED
            workout.update(_lifecycle.set_completion(
                workout, source=_lifecycle.COMPLETION_SOURCE_PROVIDER,
                observed_at=_evidence_day(event, now),
                provider_event_id=_field(event, "provider_event_id"),
                activity_id=_field(event, "completion_activity_id")))
            applied.append(workout_id)
        if applied:
            self._save_with_meta(workouts, self.load_plan_meta())
        report["applied"] = applied
        return report

    # -- training snapshot / freshness (UI-4) ----------------------------
    def _snapshot_file(self) -> Path:
        if self.snapshot_path is not None:
            return Path(self.snapshot_path)
        return Path(self.plan_path).parent / SNAPSHOT_FILENAME

    def load_training_snapshot(self) -> "_snapshot.TrainingSnapshot":
        """Snapshot persistido. Vazio quando nunca sincronizado; sem provider."""
        return _snapshot.TrainingSnapshot.load(self._snapshot_file())

    def save_training_snapshot(self,
                               snapshot: "_snapshot.TrainingSnapshot") -> Path:
        return snapshot.save(self._snapshot_file())

    def sync_freshness(self) -> "_snapshot.SyncFreshness":
        """Freshness da ultima sync persistida (`unknown` se nunca houve)."""
        return self.load_training_snapshot().freshness

    # -- activity streams (STREAM-1) -------------------------------------
    def _activity_stream_cache_file(self) -> Path:
        if self.activity_stream_cache_path is not None:
            return Path(self.activity_stream_cache_path)
        return Path(self.plan_path).parent / ACTIVITY_STREAM_CACHE_FILENAME

    def load_activity_stream_cache(self) -> "_activity_stream_cache.ActivityStreamCache":
        """Cache local de streams; ausente/corrompido devolve cache vazio."""
        return _activity_stream_cache.ActivityStreamCache.load(
            self._activity_stream_cache_file())

    def get_cached_activity_stream(self, *, provider: str,
                                   activity_id: Any) -> Optional[ActivityStream]:
        """Leitura local/read-only de stream observado; nao chama provider."""
        return self.load_activity_stream_cache().get(
            provider=provider, activity_id=str(activity_id))

    def get_pw_hr_decoupling(self, *, provider: str, activity_id: Any
                             ) -> "_pw_hr_decoupling.PwHrDecouplingView":
        """Consulta local/read-only de Pw:HR; nunca busca ou escreve streams."""
        stream = self.get_cached_activity_stream(
            provider=provider, activity_id=activity_id)
        if stream is None:
            return _pw_hr_decoupling.PwHrDecouplingView.unavailable(
                provider=provider, activity_id=str(activity_id))
        return _pw_hr_decoupling.build_pw_hr_decoupling_view(stream)

    def fetch_activity_stream(
        self, activity_id: Any, *, provider: Optional[ActivityStreamProvider] = None,
        now: Optional[datetime] = None,
    ) -> ActivityStream:
        """Operacao remota explicita: busca stream normalizado e atualiza cache."""
        active = provider if provider is not None else self.client()
        capabilities = _provider_capabilities(active)
        if capabilities and ProviderCapability.READ_ACTIVITY_STREAMS not in capabilities:
            raise ProviderOperationError("provider nao declara leitura de activity streams")
        stream = active.activity_stream(activity_id)
        captured = now or datetime.now(timezone.utc)
        if captured.tzinfo is None:
            captured = captured.replace(tzinfo=timezone.utc)
        stream = replace(stream, captured_at=captured.isoformat())
        cache = self.load_activity_stream_cache().with_stream(stream)
        cache.save(self._activity_stream_cache_file())
        return stream

    def sync_provider_state(
        self, *, today: Optional[date] = None,
        now: Optional[datetime] = None, window_days: int = 60,
        provider: Optional[TrainingMetricsProvider] = None,
        metrics_fn: Optional[Callable[[List[Any]], Any]] = None,
        stale_after_hours: float = _snapshot.DEFAULT_STALE_AFTER_HOURS,
    ) -> "SyncResult":
        """Sincroniza com o provider: captura snapshot + atualiza conclusao local.

        Operacao de rede explicita. Falha do provider NAO corrompe estado e NAO
        impede leitura local: devolve `SyncResult(ok=False)` e os leitores
        locais seguem servindo o ultimo snapshot/plano persistidos."""
        active = provider if provider is not None else self.client()
        today = today or date.today()
        oldest = (today - timedelta(days=window_days)).isoformat()
        newest = today.isoformat()
        try:
            events = active.events(oldest=oldest, newest=newest)
            wellness = active.wellness(oldest=oldest, newest=newest)
        except ProviderError as exc:
            return SyncResult(ok=False, error=str(exc),
                              freshness=self.sync_freshness())
        metrics = metrics_fn(events) if metrics_fn is not None else None
        snap = _snapshot.TrainingSnapshot.capture(
            events=events, wellness=wellness, metrics=_as_metrics_dict(metrics),
            provider=_provider_name(active), now=now,
            stale_after_hours=stale_after_hours)
        self.save_training_snapshot(snap)
        completion = self.reconcile_completion(
            snapshot=snap, today=today, now=now)
        return SyncResult(ok=True, snapshot=snap, freshness=snap.freshness,
                          completion=completion)

    # -- read-only state queries (UI-5) ----------------------------------
    def plan_view(self, *, today: Optional[date] = None,
                  provider_name: Optional[str] = None) -> "_ui_state.PlanView":
        """Plano local como View imutavel. Sem provider, sem escrita.

        `provider_name` e apenas um rotulo de exibicao para o linkage; nao
        dispara nenhuma chamada de rede."""
        return _ui_state.build_plan_view(
            self.load_plan(), self.load_plan_meta(), today=today,
            provider=provider_name)

    def get_application_state(
        self, *, today: Optional[date] = None,
        now: Optional[datetime] = None,
        provider_name: Optional[str] = None,
    ) -> "_ui_state.ApplicationState":
        """Estado completo do Hermes para CLI/futura UI/API.

        QUERY PURA: nao sincroniza, nao chama provider, nao grava plano nem
        snapshot e nao altera lifecycle/freshness. Funciona offline (provider
        indisponivel, token invalido, sem rede) servindo o ultimo estado
        persistido. Para atualizar, use `sync_provider_state`/`sync` antes."""
        snapshot = self.load_training_snapshot()
        return _ui_state.ApplicationState(
            plan=self.plan_view(today=today, provider_name=provider_name),
            snapshot=_ui_state.build_snapshot_view(snapshot, now=now))

    def get_workout_execution_view(
        self, workout_id: str, *, today: Optional[date] = None,
        now: Optional[datetime] = None,
    ) -> Optional["_ui_state.WorkoutExecutionView"]:
        """View factual local de um treino e sua evidencia observada.

        Nao resolve client, nao sincroniza e nao escreve plano, snapshot ou cache.
        ``None`` significa somente que a identidade local nao esta no plano.
        """
        workout = self.get_workout(workout_id)
        if workout is None:
            return None
        return _ui_state.build_workout_execution_view(
            workout,
            snapshot=self.load_training_snapshot(),
            stream_cache=self.load_activity_stream_cache(),
            today=today, now=now)

    def get_readiness_view(
        self, *, today: Optional[date] = None,
        now: Optional[datetime] = None,
    ) -> "_ui_state.ReadinessView":
        """Readiness local para UI/API, sem provider nem alteracao de plano.

        Query separada de `get_application_state`: readiness tem `target_day`
        proprio e executa a heuristica existente sobre o snapshot local, mas
        deliberadamente NAO chama `readiness_decision` (policy/prescricao) nem
        `assess_daily_readiness` (fluxo provider-facing)."""
        target = today or date.today()
        snapshot = _ui_state.build_snapshot_view(
            self.load_training_snapshot(), now=now)
        return _ui_state.build_readiness_view(snapshot, today=target)

    def get_insight_view(
        self, *, subject: str, workout_id: Optional[str] = None,
        today: Optional[date] = None, now: Optional[datetime] = None,
    ) -> "_insight.InsightView":
        """Compõe o input local e read-only do INSIGHT M1 v2.

        Esta seam transporta somente fatos já resolvidos pelas Views locais. Não
        consulta provider, ambiente ou estado FTP; também não executa policy,
        renderer, modelo ou qualquer persistência.
        """
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("subject deve ser texto nao vazio")

        facts: list[_insight.InsightFact] = []
        provenance: list[_insight.InsightSource] = []

        readiness = self.get_readiness_view(today=today, now=now)
        readiness_fact_count = len(facts)
        pmc = readiness.pmc
        if pmc is not None:
            _append_insight_fact(facts, "ctl", pmc.ctl,
                                 _insight.FactClassification.OBSERVED)
            _append_insight_fact(facts, "atl", pmc.atl,
                                 _insight.FactClassification.OBSERVED)
            _append_insight_fact(facts, "tsb", pmc.tsb,
                                 _insight.FactClassification.OBSERVED)
            _append_insight_fact(facts, "form_pct", pmc.form_pct,
                                 _insight.FactClassification.DERIVED, "%")
        wellness = readiness.wellness
        if wellness is not None:
            _append_insight_fact(facts, "hrv", wellness.hrv,
                                 _insight.FactClassification.OBSERVED)
            _append_insight_fact(facts, "rhr", wellness.resting_hr,
                                 _insight.FactClassification.OBSERVED, "bpm")
            _append_insight_fact(facts, "sleep_secs", wellness.sleep_secs,
                                 _insight.FactClassification.OBSERVED, "s")
        if readiness.heuristic_level is not None:
            _append_insight_fact(facts, "heuristic_level", readiness.heuristic_level,
                                 _insight.FactClassification.HEURISTIC)
            _append_insight_fact(facts, "heuristic_score", readiness.heuristic_score,
                                 _insight.FactClassification.HEURISTIC)
            _append_insight_fact(
                facts, "heuristic_confidence", readiness.heuristic_confidence,
                _insight.FactClassification.HEURISTIC)
        if len(facts) > readiness_fact_count:
            provenance.append(_insight.InsightSource("readiness_view"))

        prescribed_session = None
        observed_execution = None
        if workout_id is not None:
            execution = self.get_workout_execution_view(
                workout_id, today=today, now=now)
            if execution is None:
                raise KeyError(workout_id)
            provenance.append(_insight.InsightSource("workout_execution_view"))

            workout = self.get_workout(workout_id)
            summary = _insight_summary_text(
                workout.get("name") if workout is not None else None,
                execution.planned.focus)
            if summary is not None:
                prescribed_session = _insight.PrescribedSessionSummary(summary)

            planned_fact_count = len(facts)
            _append_insight_fact(
                facts, "planned_duration_sec", execution.planned.duration_sec,
                _insight.FactClassification.PRESCRIPTION, "s")
            _append_insight_fact(facts, "planned_tss", execution.planned.tss,
                                 _insight.FactClassification.PRESCRIPTION, "TSS")
            _append_insight_fact(
                facts, "planned_ftp_watts", getattr(execution.planned, "ftp_watts"),
                _insight.FactClassification.PRESCRIPTION, "W")
            if prescribed_session is not None or len(facts) > planned_fact_count:
                provenance.append(_insight.InsightSource("local_plan"))

            availability = (_insight.ObservationAvailability.OBSERVED
                            if execution.observed_activity is not None
                            else _insight.ObservationAvailability.UNAVAILABLE)
            observed_execution = _insight.ObservedExecution(availability)

        return _insight.InsightView(
            schema_version=1, subject=subject, facts=tuple(facts), advisory=None,
            prescribed_session=prescribed_session,
            observed_execution=observed_execution,
            provenance=tuple(provenance))

    def get_form_advisory(
        self, *,
        threshold: Any = _form_advisory.DEFAULT_FORM_ADVISORY_THRESHOLD,
        now: Optional[datetime] = None,
    ) -> "_form_advisory.FormAdvisory":
        """Advisory de Form relativo, local e sem efeito no plano.

        Reutiliza o `form_pct` ja derivado em `PmcView` (PMC-1). Nao chama
        provider, nao executa readiness/policy prescritiva e nao altera estado.
        `threshold` e injetado; o default mora no modulo de policy, nao aqui.
        """
        snapshot = _ui_state.build_snapshot_view(
            self.load_training_snapshot(), now=now)
        pmc = snapshot.pmc if snapshot is not None else None
        return _form_advisory.evaluate_form_advisory(
            pmc.form_pct if pmc is not None else None,
            threshold=threshold)

    def get_heart_rate_trend_view(
        self, *, today: Optional[date] = None,
        window_days: int = _ui_state.DEFAULT_HR_TREND_WINDOW_DAYS,
        now: Optional[datetime] = None,
    ) -> "_ui_state.HeartRateTrendView":
        """HRV/RHR observados + baseline individual + delta (HR-3).

        Local, offline e read-only: le o snapshot em disco, nao chama provider,
        nao sincroniza, nao muta cache e nao escreve nada. Nao executa policy
        de readiness nem toca em plano/`ReadinessAction` — as heuristicas
        `hrv_low`/`rhr_rising` seguem intactas em `readiness.py`."""
        target = today or date.today()
        snapshot = _ui_state.build_snapshot_view(
            self.load_training_snapshot(), now=now)
        return _ui_state.build_heart_rate_trend_view(
            snapshot, today=target, window_days=window_days)

    def get_observed_wellness_view(
        self, *, today: Optional[date] = None,
        window_days: int = _ui_state.DEFAULT_WELLNESS_WINDOW_DAYS,
        now: Optional[datetime] = None,
    ) -> "_ui_state.ObservedWellnessView":
        """Sinais de wellness observados + baseline/delta (HR-4).

        Local, offline e read-only: le o snapshot em disco, nao chama provider,
        nao sincroniza, nao muta cache e nao escreve nada. Nao executa policy,
        nao compoe score e nao toca em plano/`ReadinessAction` — os limiares de
        `readiness.py` seguem intactos.

        `soreness`, `motivation` e `fatigue` voltam como
        `status="unsupported_field"`: o provider nao expoe esses campos, e o
        contrato registra a lacuna em vez de fabricar alias."""
        target = today or date.today()
        snapshot = _ui_state.build_snapshot_view(
            self.load_training_snapshot(), now=now)
        return _ui_state.build_observed_wellness_view(
            snapshot, today=target, window_days=window_days)

    def get_ctl_ramp_view(
        self, *, target_day: date,
        window_days: int = _ui_state.DEFAULT_CTL_RAMP_WINDOW_DAYS,
        now: Optional[datetime] = None,
    ) -> "_ui_state.CtlRampView":
        """CTL ramp rate local por pontos observados, sem rede ou policy."""
        snapshot = _ui_state.build_snapshot_view(
            self.load_training_snapshot(), now=now)
        return _ui_state.build_ctl_ramp_view(
            snapshot, target_day=target_day, window_days=window_days)

    def get_ctl_ramp_advisory(
        self, *, target_day: date, max_ramp_points: Any,
        window_days: int = _ui_state.DEFAULT_CTL_RAMP_WINDOW_DAYS,
        now: Optional[datetime] = None,
    ) -> "_ctl_ramp_advisory.CtlRampAdvisory":
        """Advisory opt-in para taxa de CTL, sem qualquer acao no plano.

        Nao existe threshold default em HR-1: `max_ramp_points` precisa ser
        injetado pelo consumidor/contexto. A policy recebe somente a taxa pronta.
        """
        ramp = self.get_ctl_ramp_view(
            target_day=target_day, window_days=window_days, now=now)
        return _ctl_ramp_advisory.evaluate_ctl_ramp_advisory(
            ramp.ramp_rate, max_ramp_points=max_ramp_points)

    # -- provider --------------------------------------------------------
    def client(self) -> TrainingMetricsProvider:
        """Resolve o provider pela factory injetada ou pelo composition root.

        Como pacote (`src.application`), importa explicitamente
        `src.training_plan`: um modulo top-level homonimo em ``sys.path`` nunca
        pode trocar a origem do client. A alternativa top-level existe somente
        para a execucao direta da CLI (`python3 src/training_plan.py`), na qual
        `application` nao tem pacote pai. Nao ha fallback por excecao: falha ao
        importar o composition root real precisa aparecer, nao ser mascarada.
        """
        if self.client_factory is not None:
            return self.client_factory()
        if __package__:
            from .training_plan import get_client
        else:  # application importado pela CLI executada como script direto
            from training_plan import get_client
        return get_client()  # type: ignore[return-value]

    def provider_capabilities(self) -> frozenset:
        """Capabilities declaradas pelo provider atual (vazio se nao declarar).

        Permite a camadas futuras decidir sem `if provider_name == ...`."""
        return _provider_capabilities(self.client())


# ===========================================================================
# Use cases (UI-1)
#
# Orquestracao reutilizavel, sem `argparse`, sem `print` e sem ler `.env`
# sozinha. Cada caso de uso recebe explicitamente o provider e os servicos de
# dominio de que precisa (injetados pelo composition root). Assim a CLI vira
# adapter fino: resolve configuracao, invoca o caso de uso e formata a saida.
# ===========================================================================

# Dia-zero da serie historica de PMC (mesma ancora usada pelo CLI).
_PMC_EPOCH = date(2011, 1, 1)


@dataclass
class BuildResult:
    """Saida do caso de uso de montagem do plano (nada persistido aqui)."""

    plan: Plan
    tsb: float
    metrics: Any
    events: List[Dict[str, Any]]
    decisao: Any
    trace: Any
    readiness_report: Dict[str, Any]
    recovery_ramp: Optional[List[float]] = None
    ramp_label: Optional[str] = None
    recovery_warning: Optional[str] = None
    phase_report: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReconcileResult:
    """Plano reconciliado + diagnostico, para o adapter persistir/formatar."""

    plan: Plan
    missed: List[Dict[str, Any]]
    info: Dict[str, Any]


@dataclass
class PushResult:
    """Decisao de sincronizacao + resultado das chamadas ao provider."""

    batch: List[Dict[str, Any]]
    orphans: List[str]
    dup_ids: List[int]
    beyond: List[str]
    dry_run: bool
    executed: bool = False
    orphan_status: Optional[int] = None
    orphans_deleted: Optional[int] = None
    dup_statuses: List[Tuple[int, int]] = field(default_factory=list)
    create_status: Optional[int] = None
    created: Optional[int] = None


@dataclass
class SummaryResult:
    """Dados de um resumo de atividades; graficos/export ficam na apresentacao."""

    start: date
    end: date
    period: str
    rows: List[Dict[str, Any]]
    agg: Dict[str, Any]


@dataclass
class RecoveryResult:
    """Estado real, estimativas e rampa segura de retorno a forma."""

    event_count: int
    done_count: int
    st_real: Dict[str, Any]
    st: Dict[str, Any]
    vol: float
    anchored: bool
    target: float
    schedule: Optional[List[float]] = None


@dataclass
class ReadinessProposal:
    """Leitura de prontidao do dia + proposta (sem aplicar/publicar)."""

    plan: Plan
    metrics: Any
    treino: Optional[Dict[str, Any]]
    elegibilidade: Any
    decisao: Any
    trace: Any
    avaliacao: Any
    wellness: List[Dict[str, Any]]
    events: List[Dict[str, Any]]
    today: date
    tsb: float
    status: str
    relatorio: Dict[str, Any]
    sem: Optional[Dict[str, Any]] = None
    com: Optional[Dict[str, Any]] = None
    autor: Optional[str] = None


@dataclass
class SyncResult:
    """Resultado de uma sincronizacao com o provider (UI-4).

    `ok=False` quando o provider falhou; nesse caso `snapshot`/`completion` sao
    `None` e `freshness` reflete o ultimo estado persistido (ou `unknown`)."""

    ok: bool
    error: Optional[str] = None
    snapshot: Optional[Any] = None
    freshness: Optional[Any] = None
    completion: Optional[Dict[str, Any]] = None


def _event_is_done(event: Any) -> bool:
    """Evidencia de execucao no boundary normalizado (UI-3/UI-4).

    Delega a `provider_fields.is_completed`, que cobre records normalizados e
    dicts brutos legados sem a Application conhecer `paired_activity_id`."""
    return _is_completed(event)


def match_events_to_workouts(plan: Plan, events: List[Any]
                             ) -> Dict[str, Tuple[Dict[str, Any], Any]]:
    """Casa evidencia observada com treinos locais -> HermesWorkoutId.

    O casamento usa `external_id` (mecanismo atual, biunivoco no sistema) como
    DESCOBERTA; o resultado e chaveado pelo `id` local antes de qualquer
    mutacao de estado. Eventos sem `external_id` ou nao concluidos ficam fora."""
    by_external: Dict[str, Any] = {}
    for event in events or []:
        eid = _field(event, "external_id")
        if eid and _is_completed(event):
            by_external.setdefault(eid, event)
    matches: Dict[str, Tuple[Dict[str, Any], Any]] = {}
    for workout in plan or []:
        workout_id = workout.get(_workout_identity.WORKOUT_ID_FIELD)
        eid = workout.get("external_id")
        if workout_id and eid and eid in by_external:
            matches[workout_id] = (workout, by_external[eid])
    return matches


def _evidence_day(event: Any, now: Optional[datetime]) -> str:
    """Timestamp da evidencia: dia do evento quando houver, senao agora (UTC)."""
    day = _field(event, "start_date")
    if day:
        return str(day)
    moment = now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.isoformat()


def _provider_name(provider: Any) -> Optional[str]:
    name = getattr(provider, "provider_name", None)
    return name or type(provider).__name__


def _as_metrics_dict(metrics: Any) -> Optional[Dict[str, Any]]:
    if metrics is None:
        return None
    if dataclasses.is_dataclass(metrics):
        return dataclasses.asdict(metrics)
    if isinstance(metrics, dict):
        return dict(metrics)
    return None


def compute_return_ramp(
    provider: TrainingMetricsProvider,
    *,
    recovery_module: Any,
    pmc_rows_fn: Callable[..., Any],
    ramp_pts: int,
    weeks: int,
    today: date,
) -> Optional[RecoveryResult]:
    """Rampa semanal segura a partir do historico real de treinos feitos.

    Usada por `build --recovery` e pelo comando `recovery`. Devolve `None`
    quando nao ha serie com carga (nao ha de onde derivar teto)."""
    events = recovery_module.fetch_full_history(provider)
    daily = recovery_module.actual_daily_load(events)
    rows, anchored = pmc_rows_fn(events, _PMC_EPOCH, today)
    if not rows:
        return None
    st_real = recovery_module.state(rows)
    vol = recovery_module.weekly_volume(daily)
    st = st_real
    if anchored:
        st = recovery_module.calibrated_state(st, vol) or st
    schedule = recovery_module.ramp_schedule(st["peak_ctl"], vol, ramp_pts,
                                             weeks=weeks)
    return RecoveryResult(
        event_count=len(events),
        done_count=sum(1 for e in events if _event_is_done(e)),
        st_real=st_real, st=st, vol=vol, anchored=anchored,
        target=st["peak_ctl"], schedule=schedule)


def build_workouts(
    provider: TrainingMetricsProvider,
    *,
    today: date,
    days: int,
    days_plan: int,
    ftp: int,
    fthr: Optional[int],
    goal: Optional[str],
    periodization: Optional[str],
    race_date: Optional[str],
    weekly_hours: Optional[float],
    long_day: Optional[int],
    hr_mode: bool,
    ftp_test_date: Optional[str],
    training_days: Tuple[int, ...],
    existing: Optional[Plan],
    latest_metrics_fn: Callable[[List[Dict[str, Any]]], Any],
    build_plan_fn: Callable[..., Plan],
    readiness_module: Any,
    recovery_module: Any,
    pmc_rows_fn: Callable[..., Any],
    recovery: bool = False,
    ramp_pts: int = 9,
    recovery_weeks: int = 12,
    phase_report: Optional[Dict[str, Any]] = None,
    min_regular_duration_sec: Optional[int] = None,
    active_recovery_days: Tuple[int, ...] = (),
) -> BuildResult:
    """Monta o plano a partir do historico. Nao grava em disco.

    Preserva exatamente a orquestracao que antes vivia em `cmd_build`:
    uma leitura de wellness alimenta a avaliacao de prontidao; o `--recovery`
    ora o plano pelos tetos da rampa de retorno."""
    newest = today
    oldest = newest - timedelta(days=days)
    events = provider.events(oldest=oldest.isoformat(),
                             newest=newest.isoformat())
    metrics = latest_metrics_fn(events)
    tsb = metrics.tsb if metrics else 0.0
    wellness = provider.wellness(oldest=oldest.isoformat(),
                                 newest=newest.isoformat())
    avaliacao, trace = readiness_module.assess_readiness_assessment(
        wellness, days=days)
    decisao = readiness_module.readiness_decision(
        avaliacao, trace.illness_alert, trace.composite_low, trace.coverage,
        trace.observations, reference_day=trace.reference_day)
    readiness_report: Dict[str, Any] = {}

    recovery_ramp = None
    ramp_label = None
    recovery_warning = None
    if recovery:
        weeks = max(recovery_weeks, (days_plan + 6) // 7)
        outlook = compute_return_ramp(
            provider, recovery_module=recovery_module,
            pmc_rows_fn=pmc_rows_fn, ramp_pts=ramp_pts, weeks=weeks,
            today=today)
        if outlook is None:
            recovery_warning = ("aviso: sem treinos feitos com carga no "
                                "historico; `--recovery` ignorado (orcamento "
                                "padrao).")
        else:
            recovery_ramp = outlook.schedule
            ramp_label = (
                f"teto semanal de retorno (CTL pico "
                f"{outlook.st_real['peak_ctl']:.0f}; rampa +{ramp_pts}/sem): "
                f"{outlook.schedule[0]:.0f} -> {outlook.schedule[-1]:.0f} TSS")

    plan = build_plan_fn(
        events, tsb, ftp=ftp, days=days_plan, existing=existing,
        training_days=training_days, goal=goal, race_date=race_date,
        ftp_test_date=ftp_test_date, weekly_hours=weekly_hours,
        long_day=long_day, hr_mode=hr_mode, recovery_ramp=recovery_ramp,
        periodization=periodization, readiness=decisao,
        readiness_report=readiness_report, phase_report=phase_report,
        min_regular_duration_sec=min_regular_duration_sec,
        active_recovery_days=active_recovery_days)
    return BuildResult(
        plan=Application.enrich_plan(plan), tsb=tsb, metrics=metrics,
        events=events, decisao=decisao,
        trace=trace, readiness_report=readiness_report,
        recovery_ramp=recovery_ramp, ramp_label=ramp_label,
        recovery_warning=recovery_warning, phase_report=phase_report or {})


def reconcile_workouts(
    provider: TrainingMetricsProvider,
    *,
    plan: Plan,
    meta: Dict[str, Any],
    ftp: int,
    training_days: Tuple[int, ...],
    days: int,
    today: date,
    budget_window_days: int,
    goal_budget_scale: Dict[str, float],
    reconcile_fn: Callable[..., Any],
    weekly_budget_fn: Callable[..., Any],
    avg_load_fn: Callable[..., Any],
) -> ReconcileResult:
    """Compara o plano com os treinos feitos e devolve o plano ajustado.

    Nao grava: o adapter persiste com a meta (formato do `plan.json`)."""
    newest = today + timedelta(days=1)
    oldest = newest - timedelta(days=days)
    events = provider.events(oldest=oldest.isoformat(),
                             newest=newest.isoformat())
    # O teto do reconcile precisa ser o MESMO do build_plan: mesma janela do
    # avg_load (BUDGET_WINDOW_DAYS) e mesma escala do goal.
    scale = goal_budget_scale.get(meta.get("goal"), 1.0)
    if days >= budget_window_days:
        budget_events = events
    else:
        budget_events = provider.events(
            oldest=(newest - timedelta(days=budget_window_days)).isoformat(),
            newest=newest.isoformat())
    budget = weekly_budget_fn(avg_load_fn(budget_events), training_days, scale)
    plan, missed, info = reconcile_fn(
        plan, events, ftp=ftp, training_days=training_days, budget=budget,
        absorbed_ids=meta["absorbed_ids"])
    return ReconcileResult(plan=Application.enrich_plan(plan), missed=missed,
                           info=info)


def push_workouts(
    provider: TrainingMetricsProvider,
    *,
    plan: Plan,
    start: str,
    ftp: int,
    fthr: Optional[int],
    lang: str,
    event_payload_fn: Callable[..., Dict[str, Any]],
    prev_same_focus_fn: Callable[[Plan, Dict[str, Any]], Any],
    orphan_external_ids_fn: Callable[..., List[str]],
    manual_duplicate_ids_fn: Callable[..., List[int]],
    dry_run: bool,
) -> PushResult:
    """Decide o que sincronizar (novos/orfaos/duplicatas) e executa no provider.

    A varredura de orfaos tem duas camadas: `newest` e o ultimo dia do plano,
    entao um plano anterior MAIS LONGO nao e apagado; a busca e ampla
    (start+120) para ver o que existe, mas so removemos o que esta DENTRO do
    horizonte do plano."""
    batch = [event_payload_fn(w, ftp, lang=lang,
                              prev=prev_same_focus_fn(plan, w), fthr=fthr)
             for w in plan if w["day"] >= start]
    start_dt = date.fromisoformat(start)
    plan_end = max((w["day"] for w in plan), default=None)
    fetch_end = (start_dt + timedelta(days=120)).isoformat()
    recent = provider.events(oldest=start, newest=fetch_end)
    all_orphans = orphan_external_ids_fn(plan, recent, start=start)
    orphans = [oid for oid in all_orphans
               if plan_end is None or oid <= f"hermes-plan-{plan_end}"]
    beyond = [oid for oid in all_orphans if oid not in orphans]
    dup_ids = manual_duplicate_ids_fn(plan, recent, start=start)
    result = PushResult(batch=batch, orphans=orphans, dup_ids=dup_ids,
                        beyond=beyond, dry_run=dry_run)
    if dry_run:
        return result
    result.executed = True
    if orphans:
        result.orphan_status, body = provider.delete_events(orphans)
        result.orphans_deleted = body.get("eventsDeleted")
    for did in dup_ids:
        dup_status = provider.delete_event(did)
        result.dup_statuses.append((did, dup_status))
    result.create_status, created = provider.create_events(batch)
    result.created = len(created)
    return result


def summarize_period(
    provider: TrainingMetricsProvider,
    *,
    period: str,
    anchor: date,
    start: Optional[str],
    end: Optional[str],
    plan_days: Optional[List[date]],
    resolve_period_fn: Callable[..., Tuple[date, date]],
    done_activities_fn: Callable[..., List[Dict[str, Any]]],
    summarize_fn: Callable[[List[Dict[str, Any]]], Dict[str, Any]],
) -> SummaryResult:
    """Coleta as atividades feitas no periodo e agrega. Sem graficos/print."""
    resolved_start, resolved_end = resolve_period_fn(
        anchor, period, start=start, end=end, plan_days=plan_days)
    rows = done_activities_fn(provider, resolved_start, resolved_end)
    agg = summarize_fn(rows)
    return SummaryResult(start=resolved_start, end=resolved_end, period=period,
                         rows=rows, agg=agg)


def recovery_outlook(
    provider: TrainingMetricsProvider,
    *,
    recovery_module: Any,
    pmc_rows_fn: Callable[..., Any],
    ramp_pts: int,
    weeks: int,
    today: date,
) -> Optional[RecoveryResult]:
    """Historico real -> PMC -> retorno a forma + rampa (sem formatacao)."""
    return compute_return_ramp(
        provider, recovery_module=recovery_module, pmc_rows_fn=pmc_rows_fn,
        ramp_pts=ramp_pts, weeks=weeks, today=today)


def _steps_equal(a: Dict[str, Any], b: Dict[str, Any]) -> bool:
    return (a["focus"] == b["focus"] and a["params"] == b["params"]
            and abs(float(a["tss"]) - float(b["tss"])) < 1e-9)


def assess_daily_readiness(
    provider: TrainingMetricsProvider,
    *,
    plan: Plan,
    meta: Dict[str, Any],
    today: date,
    now: Any,
    days: int,
    ftp: int,
    training_days: Tuple[int, ...],
    weekly_hours: Optional[float],
    long_day: Optional[int],
    periodization: Optional[str],
    tsb_adapt_limit: float,
    latest_metrics_fn: Callable[[List[Dict[str, Any]]], Any],
    build_plan_fn: Callable[..., Plan],
    readiness_module: Any,
    eligibility_fn: Callable[..., Any],
    active_recovery_days: Tuple[int, ...] = (),
    min_regular_duration_sec: Optional[int] = None,
) -> ReadinessProposal:
    """Avalia a sessao de HOJE e decide se ha proposta de adaptacao por
    prontidao. Nao grava e nao publica: o adapter decide `--apply`/`--dry-run`.

    Reusa o MESMO motor do `build` (`build_plan`) e compara tres versoes do dia
    (sem/com/atual), resolvendo a cumulatividade por construcao."""
    events = provider.events(oldest=(today - timedelta(days=days)).isoformat(),
                             newest=today.isoformat())
    metrics = latest_metrics_fn(events)
    wellness = provider.wellness(
        oldest=(today - timedelta(days=days)).isoformat(),
        newest=today.isoformat())
    elegibilidade = eligibility_fn(plan, events, today=today, now=now)
    treino = elegibilidade.workout
    avaliacao, trace = readiness_module.assess_readiness_assessment(
        wellness, days=days)
    decisao = readiness_module.readiness_decision(
        avaliacao, trace.illness_alert, trace.composite_low, trace.coverage,
        trace.observations, reference_day=trace.reference_day)
    result = ReadinessProposal(
        plan=plan, metrics=metrics, treino=treino, elegibilidade=elegibilidade,
        decisao=decisao, trace=trace, avaliacao=avaliacao, wellness=wellness,
        events=events, today=today,
        tsb=metrics.tsb if metrics else 0.0, status="", relatorio={})

    if not decisao.is_adaptive:
        result.status = "not_adaptive"
        return result
    if decisao.applies_to_day != today.isoformat():
        result.status = "wrong_day"
        return result
    if treino is None or not elegibilidade.eligible:
        result.status = "not_eligible"
        return result

    comum = dict(ftp=ftp, days=1, start=today, existing=None,
                 training_days=training_days, goal=meta.get("goal"),
                 race_date=meta.get("race_date"),
                  ftp_test_date=meta.get("ftp_test_date"),
                  weekly_hours=weekly_hours, long_day=long_day,
                  hr_mode=bool(treino.get("hr_mode")),
                  periodization=periodization,
                  active_recovery_days=active_recovery_days,
                  min_regular_duration_sec=min_regular_duration_sec)
    tsb = result.tsb
    relatorio: Dict[str, Any] = {}
    sem = build_plan_fn(events, tsb, readiness=None, **comum)[0]
    com = build_plan_fn(events, tsb, readiness=decisao,
                        readiness_report=relatorio, **comum)[0]
    result.sem, result.com = sem, com
    result.relatorio = relatorio
    result.autor = "prontidao" if relatorio.get("aplicada_em") else "TSB"

    if not relatorio.get("aplicada_em") or _steps_equal(sem, com):
        if not _steps_equal(treino, sem) and tsb < tsb_adapt_limit:
            result.status = "tsb_wins"
        else:
            result.status = "nothing"
    elif _steps_equal(treino, com):
        result.status = "already"
    elif not _steps_equal(treino, sem):
        result.status = "divergent"
    else:
        result.status = "propose"
    return result
