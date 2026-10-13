"""Contratos read-only do INSIGHT M1 v2.

Este pacote ainda nao possui runtime, provider, prompt ou integracao com a
Application. Ele apenas define os tipos offline do contrato.
"""

from .contract import (
    FactClassification,
    InsightAdvisory,
    InsightFact,
    InsightPresentation,
    InsightSource,
    InsightView,
    ObservedExecution,
    ObservationAvailability,
    PrescribedSessionSummary,
    validate_presentation_payload,
)

__all__ = [
    "FactClassification",
    "InsightAdvisory",
    "InsightFact",
    "InsightPresentation",
    "InsightSource",
    "InsightView",
    "ObservedExecution",
    "ObservationAvailability",
    "PrescribedSessionSummary",
    "validate_presentation_payload",
]
