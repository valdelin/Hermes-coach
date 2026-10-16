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
from .response_validation import (
    InsightResponseError,
    decode_insight_presentation_template,
    parse_validate_render_insight_response,
    render_insight_presentation,
    validate_insight_presentation_template,
)
from .model_provider import (
    InsightInvocationStatus,
    InsightModelProvider,
    InsightModelRequest,
    InsightModelResponse,
    InsightProvenanceError,
    InsightProviderAuthError,
    InsightProviderConfigError,
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
from .runtime import (
    InsightRuntimeResult,
    InsightRuntimeStatus,
    run_insight_runtime,
)
from .serialization import serialize_insight_view
from .openai_provider import OpenAIInsightModelProvider

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
    "InsightResponseError",
    "decode_insight_presentation_template",
    "validate_insight_presentation_template",
    "render_insight_presentation",
    "parse_validate_render_insight_response",
    "InsightInvocationStatus",
    "InsightModelProvider",
    "InsightModelRequest",
    "InsightModelResponse",
    "InsightProvenanceError",
    "InsightProviderAuthError",
    "InsightProviderConfigError",
    "InsightProviderError",
    "InsightProviderInvalidResponseError",
    "InsightProviderRateLimitError",
    "InsightProviderTimeoutError",
    "InsightProviderUnavailableError",
    "InsightRuntimeProvenance",
    "InsightSizeLimitError",
    "INSIGHT_PROMPT_VERSION",
    "build_insight_model_request",
    "InsightRuntimeResult",
    "InsightRuntimeStatus",
    "run_insight_runtime",
    "serialize_insight_view",
    "OpenAIInsightModelProvider",
]
