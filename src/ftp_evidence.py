"""Evidencia de FTP (FTP-H2): estimativa observada != estado canonico.

Contrato da trilha (ROADMAP/2026-10-08):

    FtpEvidence = evidence / estimate
       -> Advice = sugestao de revisar/testar/confirmar
       -> confirmacao explicita do usuario
       -> FtpReference = estado canonico confirmado

Guarda-rails, herdados do contrato:

- **Nenhuma evidencia cria referencia automaticamente.** Evidencia e estado
  canonico nao se misturam; a unica ponte permitida e a confirmacao explicita
  do usuario via use-case (`Application.confirm_ftp_evidence`).
- Fonte candidatas: `activity.icu_pm_ftp`/eFTP, `activity.icu_ftp` (evidencia
  do provider), best-20min local, proposta do `ftp-scan`, resultado de teste
  do Hermes, resultado informado pelo usuario (Zwift/outra plataforma) e
  entrada do treinador.
- Evidencia e estimativa/observacao; nao altera `build_plan`, prescricao,
  watts do calendario nem `.env` (isso e escopo do FTP-H6).
- O Advice e advisorio (heuristica do sistema), nao policy nem prescricao.

Sem politicas de promocao de "limiar de qualidade": cada estimativa guarda
consigo seus gates (`quality_ok`/`proposes_new`/`best20`) e o consumidor
decide. O `advise_ftp()` abaixo usa apenas heuristica de razoabilidade
(estimativas nao rebaixam; testes/entrada do treinador podem), jamais opina
pela prescricao.

Timestamps: o projeto nao tem fuso configurado (`readiness_eligibility`,
`_agora`); como o `FtpHistory`, este modulo exige datetime timezone-aware e
trata a origem naive do provider como UTC quando normaliza para registro.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

try:  # execucao direta `python3 src/...` e como pacote `src.ftp_evidence`
    from ftp_history import FtpProtocol, FtpReference, FtpReferenceSource
except ImportError:
    from .ftp_history import FtpProtocol, FtpReference, FtpReferenceSource


EVIDENCE_SCHEMA_VERSION = 1

# Advice de razoabilidade (heuristica do sistema, sem prescricao): abaixo de
# 3% do canonico, uma estimativa e considerada "dentro de casa" (o mesmo
# conservadorismo do `ftp-scan`, que so propoe +3%..+30%). 3% nao e limiar de
# prescricao nem de qualidade: e so o ponto em que o Advice sugere revisar.
WITHIN_CURRENT_RATIO = 1.03


class FtpEvidenceSource(str, Enum):
    PROVIDER_FTP = "provider_ftp"          # activity.icu_ftp (evidencia do provider)
    PROVIDER_PM_FTP = "provider_pm_ftp"    # activity.icu_pm_ftp / eFTP
    BEST_20_MIN = "best_20_min"            # estimativa local best-20min x 0.95
    FTP_SCAN = "ftp_scan"                  # proposta do scan de treinos fora do plano
    HERMES_TEST = "hermes_test"            # resultado de teste conduzido pelo Hermes
    USER_REPORTED_TEST = "user_reported_test"  # teste informado (Zwift, outra plataforma)
    COACH_ENTRY = "coach_entry"            # entrada do treinador


class AdviceKind(str, Enum):
    NO_EVIDENCE = "no_evidence"
    CONFIRM_PROPOSITION = "confirm_proposition"
    REVIEW_SUGGESTED = "review_suggested"
    WITHIN_CURRENT = "within_current"


_ESTIMATE_SOURCES = frozenset({
    FtpEvidenceSource.PROVIDER_FTP,
    FtpEvidenceSource.PROVIDER_PM_FTP,
    FtpEvidenceSource.BEST_20_MIN,
    FtpEvidenceSource.FTP_SCAN,
})

# Fonte de evidencia que admite rebaixamento (teste de verdade ou entrada
# deliberada do treinador); estimativa nunca rebaixa por fadiga.
_CAN_LOWER_SOURCES = frozenset({
    FtpEvidenceSource.HERMES_TEST,
    FtpEvidenceSource.USER_REPORTED_TEST,
    FtpEvidenceSource.COACH_ENTRY,
})

_SOURCE_TO_REFERENCE_SOURCE = {
    FtpEvidenceSource.HERMES_TEST: FtpReferenceSource.HERMES_TEST,
    FtpEvidenceSource.USER_REPORTED_TEST: FtpReferenceSource.USER_ENTERED,
    FtpEvidenceSource.COACH_ENTRY: FtpReferenceSource.COACH_DEFINED,
}


def _aware(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} deve ser datetime timezone-aware")
    return value


def observed_at_from_provider(value, default_day: Optional[str] = None) -> datetime:
    """Normaliza um timestamp do provider (naive) para datetime aware (UTC).

    O projeto nao tem fuso configurado; aqui o timestamp local informado vira
    UTC para satisfazer o contrato deste modulo e do `FtpHistory`. `default_day`
    (YYYY-MM-DD) cobre atividade sem `start_date_local` (07:30 local, o mesmo
    START_TIME do build).
    """
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone_utc())
    if not value and default_day:
        from datetime import time as _time
        return datetime.combine(
            _parse_day(default_day), _time(7, 30), tzinfo=timezone_utc())
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"start_date_local invalido: {text!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone_utc())
    return parsed


def _parse_day(text: str):
    from datetime import date
    return date.fromisoformat(text)


def timezone_utc():
    from datetime import timezone
    return timezone.utc


@dataclass(frozen=True)
class FtpEvidence:
    """Estimativa/observacao de FTP, com proveniencia e gates de qualidade.

    Nunca vira `FtpReference` sozinho: exige confirmacao explicita do usuario
    (use-case de confirmacao). `best20`/`quality_ok`/`proposes_new` espelham
    os gates do `ftp-scan` (#6) para o Advice decidir com transparencia.
    """

    id: str
    value_watts: float
    observed_at: datetime
    recorded_at: datetime
    source: FtpEvidenceSource
    protocol: Optional[FtpProtocol] = None
    activity_id: Optional[str] = None
    workout_id: Optional[str] = None
    provider: Optional[str] = None
    best20: Optional[float] = None
    quality_ok: Optional[bool] = None
    proposes_new: Optional[bool] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise ValueError("id da evidencia FTP deve ser nao vazio")
        try:
            watts = float(self.value_watts)
        except (TypeError, ValueError) as exc:
            raise ValueError("value_watts deve ser numerico") from exc
        if not math.isfinite(watts) or watts <= 0:
            raise ValueError("value_watts deve ser finito e maior que zero")
        object.__setattr__(self, "value_watts", watts)
        _aware(self.observed_at, "observed_at")
        _aware(self.recorded_at, "recorded_at")
        try:
            object.__setattr__(self, "source", FtpEvidenceSource(self.source))
        except ValueError as exc:
            raise ValueError(f"source de evidencia invalido: {self.source!r}") from exc
        if self.protocol is not None:
            try:
                object.__setattr__(self, "protocol", FtpProtocol(self.protocol))
            except ValueError as exc:
                raise ValueError(f"protocol FTP invalido: {self.protocol!r}") from exc
        if self.best20 is not None:
            try:
                best20 = float(self.best20)
            except (TypeError, ValueError) as exc:
                raise ValueError("best20 deve ser numerico") from exc
            if not math.isfinite(best20) or best20 <= 0:
                raise ValueError("best20 deve ser finito e maior que zero")
            object.__setattr__(self, "best20", best20)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "value_watts": self.value_watts,
            "observed_at": self.observed_at.isoformat(),
            "recorded_at": self.recorded_at.isoformat(),
            "source": self.source.value,
            "protocol": self.protocol.value if self.protocol else None,
            "activity_id": self.activity_id,
            "workout_id": self.workout_id,
            "provider": self.provider,
            "best20": self.best20,
            "quality_ok": self.quality_ok,
            "proposes_new": self.proposes_new,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data) -> "FtpEvidence":
        if not isinstance(data, dict):
            raise ValueError("evidencia FTP deve ser objeto")
        required = ("id", "value_watts", "observed_at", "recorded_at", "source")
        missing = [name for name in required if name not in data]
        if missing:
            raise ValueError(f"evidencia FTP sem campos obrigatorios: {', '.join(missing)}")
        protocol = FtpProtocol(data["protocol"]) if data.get("protocol") else None
        return cls(
            id=data["id"],
            value_watts=data["value_watts"],
            observed_at=datetime.fromisoformat(data["observed_at"]),
            recorded_at=datetime.fromisoformat(data["recorded_at"]),
            source=FtpEvidenceSource(data["source"]),
            protocol=protocol,
            activity_id=data.get("activity_id"),
            workout_id=data.get("workout_id"),
            provider=data.get("provider"),
            best20=data.get("best20"),
            quality_ok=data.get("quality_ok"),
            proposes_new=data.get("proposes_new"),
            notes=data.get("notes"),
        )


@dataclass(frozen=True)
class Advice:
    """Sugestao advisoria derivada da evidencia. Nada aqui promove referencia."""

    kind: AdviceKind
    value_watts: Optional[float] = None
    evidence_id: Optional[str] = None
    reason: Optional[str] = None
    can_lower: bool = False

    @property
    def suggests_confirmation(self) -> bool:
        return self.kind in (AdviceKind.CONFIRM_PROPOSITION,
                             AdviceKind.REVIEW_SUGGESTED)


def advise_ftp(evidence_entries, current_reference: Optional[FtpReference]) -> Advice:
    """Deriva um Advice `advisorio` da evidencia registrada.

    Heuristica (nao policy):

    - sem evidencia -> NO_EVIDENCE;
    - sem referencia canonica vigente -> CONFIRM_PROPOSITION da melhor
      evidencia (a mais recente) — confirmar e opcional, nada automatico;
    - com referencia canonica: estimativas (`PROVIDER_*`, `BEST_20_MIN`,
      `FTP_SCAN`) so
      sustentam subir (+3% ou mais); igual ou menor -> WITHIN_CURRENT
      (evidencia nao rebaixa por fadiga);
    - resultados de teste ou entrada do treinador (`HERMES_TEST`,
      `USER_REPORTED_TEST`, `COACH_ENTRY`) podem sugerir revisar para cima OU
      para baixo;
    - `FTP_SCAN` so sugere revisar quando `proposes_new` foi verdadeiro nos
      gates do scan.
    """
    _evidence = evidence_entries or ()
    if not _evidence:
        return Advice(AdviceKind.NO_EVIDENCE, None, None,
                      "sem evidencia de FTP registrada", can_lower=False)

    def usable(entry: FtpEvidence) -> bool:
        if entry.source is FtpEvidenceSource.FTP_SCAN:
            return bool(entry.proposes_new)
        return True

    candidates = sorted(
        (entry for entry in _evidence if usable(entry) and entry.value_watts > 0),
        key=lambda entry: (entry.observed_at, entry.id), reverse=True)
    if not candidates:
        return Advice(AdviceKind.NO_EVIDENCE, None, None,
                      "nenhuma evidencia utilizavel registrada", can_lower=False)

    evidence = candidates[0]
    is_estimate = evidence.source in _ESTIMATE_SOURCES
    can_lower = evidence.source in _CAN_LOWER_SOURCES

    if current_reference is None:
        return Advice(AdviceKind.CONFIRM_PROPOSITION, evidence.value_watts,
                      evidence.id,
                      f"sem FTP canonico; evidencia sugere {evidence.value_watts:.0f}W",
                      can_lower=can_lower)

    ratio = evidence.value_watts / current_reference.value_watts
    if is_estimate:
        if ratio >= WITHIN_CURRENT_RATIO:
            return Advice(AdviceKind.REVIEW_SUGGESTED, evidence.value_watts,
                          evidence.id,
                          f"estimativa {evidence.value_watts:.0f}W >= canal "
                          f"{current_reference.value_watts:.0f}W (x{ratio:.2f})",
                          can_lower=False)
        return Advice(AdviceKind.WITHIN_CURRENT, evidence.value_watts,
                      evidence.id,
                      f"estimativa {evidence.value_watts:.0f}W dentro do canonico "
                      f"{current_reference.value_watts:.0f}W",
                      can_lower=can_lower)

    if abs(ratio - 1.0) >= 0.03:
        direction = "acima" if ratio > 1.0 else "abaixo"
        return Advice(AdviceKind.REVIEW_SUGGESTED, evidence.value_watts,
                      evidence.id,
                      f"resultado/entrada {evidence.value_watts:.0f}W {direction} "
                      f"do canonico {current_reference.value_watts:.0f}W",
                      can_lower=can_lower)
    return Advice(AdviceKind.WITHIN_CURRENT, evidence.value_watts, evidence.id,
                  f"resultado/entrada {evidence.value_watts:.0f}W dentro do canonico",
                  can_lower=can_lower)


def confirmation_source(evidence: FtpEvidence) -> FtpReferenceSource:
    """Origem da referencia quando o usuario CONFIRMA a evidencia."""
    return _SOURCE_TO_REFERENCE_SOURCE.get(evidence.source,
                                           FtpReferenceSource.USER_ENTERED)


def evidence_to_reference(evidence: FtpEvidence, *, reference_id: str,
                          effective_from: datetime,
                          recorded_at: Optional[datetime] = None,
                          notes: Optional[str] = None) -> FtpReference:
    """Mapeia uma evidencia confirmada para `FtpReference` (sem persistir).

    A confirmacao e o unico ponto em que evidencia vira estado canonico; o
    chamador (use-case da Application) e quem persiste. Provenance preservada:
    a referencia guarda `evidence_id`/`evidence_activity_id`/`evidence_workout_id`
    e `provider`.
    """
    _aware(effective_from, "effective_from")
    if recorded_at is None:
        recorded_at = effective_from
    _aware(recorded_at, "recorded_at")
    if not isinstance(reference_id, str) or not reference_id.strip():
        raise ValueError("reference_id deve ser nao vazio")
    return FtpReference(
        id=reference_id,
        value_watts=evidence.value_watts,
        effective_from=effective_from,
        recorded_at=recorded_at,
        source=confirmation_source(evidence),
        protocol=evidence.protocol,
        evidence_activity_id=evidence.activity_id,
        evidence_workout_id=evidence.workout_id,
        provider=evidence.provider,
        notes=notes or ("confirmado via ftp-confirm a partir da evidencia "
                        f"{evidence.id}"),
        supersedes_reference_id=None,
        evidence_id=evidence.id,
    )


@dataclass(frozen=True)
class FtpEvidenceRepository:
    """Persistencia local de evidencia (`ftp_evidence.json`), independente do
    plano e do historico canonico. Auditavel e atomica (tempfile + os.replace)."""

    path: Path

    def load(self) -> Tuple[FtpEvidence, ...]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("ftp_evidence deve ser objeto")
        if data.get("schema_version") != EVIDENCE_SCHEMA_VERSION:
            raise ValueError(
                f"schema_version FTP evidence desconhecida: {data.get('schema_version')!r}")
        entries = data.get("evidence")
        if not isinstance(entries, list):
            raise ValueError("evidence FTP deve ser lista")
        return tuple(FtpEvidence.from_dict(entry) for entry in entries)

    def save(self, evidence_entries: Tuple[FtpEvidence, ...]) -> Path:
        ids = [entry.id for entry in evidence_entries]
        if len(ids) != len(set(ids)):
            raise ValueError("ids de evidencia FTP devem ser unicos")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "evidence": [entry.to_dict() for entry in evidence_entries],
        }, ensure_ascii=False, indent=2) + "\n"
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