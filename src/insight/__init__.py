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
from .render import (
    InsightPresentationTemplate,
    InsightRenderError,
    fallback_presentation,
    render_presentation,
    render_template,
)
from .model_provider import (
    InsightInvocationStatus,
    InsightModelProvider,
    InsightModelRequest,
    InsightModelResponse,
    InsightProvenanceError,
    InsightProviderAuthError,
    InsightProviderError,
    InsightProviderInvalidResponseError,
    InsightProviderRateLimitError,
    InsightProviderTimeoutError,
    InsightProviderUnavailableError,
    InsightRuntimeProvenance,
)
from .limits import InsightSizeLimitError
from .request_builder import (
    INSIGHT_PROMPT_VERSION,
    build_insight_model_request,
)
from .serialization import serialize_insight_view

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
    "InsightPresentationTemplate",
    "InsightRenderError",
    "fallback_presentation",
    "render_presentation",
    "render_template",
    "InsightInvocationStatus",
    "InsightModelProvider",
    "InsightModelRequest",
    "InsightModelResponse",
    "InsightProvenanceError",
    "InsightProviderAuthError",
    "InsightProviderError",
    "InsightProviderInvalidResponseError",
    "InsightProviderRateLimitError",
    "InsightProviderTimeoutError",
    "InsightProviderUnavailableError",
    "InsightRuntimeProvenance",
    "InsightSizeLimitError",
    "INSIGHT_PROMPT_VERSION",
    "build_insight_model_request",
    "serialize_insight_view",
]
