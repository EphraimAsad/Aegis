"""Pydantic schemas for request/response validation."""

from app.schemas.clarification import (
    AnswerQuestionRequest,
    ClarificationQuestionResponse,
    ClarificationQuestionsListResponse,
    ClarificationStatusResponse,
    GenerateQuestionsRequest,
    QuestionCategory,
    QuestionOption,
    QuestionType,
)
from app.schemas.health import HealthResponse, HealthStatus
from app.schemas.project import (
    ProjectCreateRequest,
    ProjectDetail,
    ProjectListResponse,
    ProjectScope,
    ProjectScopeUpdateRequest,
    ProjectStatus,
    ProjectStatusUpdateRequest,
    ProjectSummary,
    ProjectUpdateRequest,
)
from app.schemas.provider import (
    ChatMessageRequest,
    ChatRequest,
    ChatResponseSchema,
    EmbeddingRequest,
    EmbeddingResponseSchema,
    ModelListResponse,
    ProviderCapabilitiesResponse,
    ProviderHealthResponse,
    ProviderInfo,
    ProviderListResponse,
)

__all__ = [
    # Health
    "HealthResponse",
    "HealthStatus",
    # Provider
    "ProviderCapabilitiesResponse",
    "ProviderInfo",
    "ProviderListResponse",
    "ProviderHealthResponse",
    "ModelListResponse",
    "ChatMessageRequest",
    "ChatRequest",
    "ChatResponseSchema",
    "EmbeddingRequest",
    "EmbeddingResponseSchema",
    # Project
    "ProjectStatus",
    "ProjectScope",
    "ProjectCreateRequest",
    "ProjectUpdateRequest",
    "ProjectScopeUpdateRequest",
    "ProjectStatusUpdateRequest",
    "ProjectSummary",
    "ProjectDetail",
    "ProjectListResponse",
    # Clarification
    "QuestionType",
    "QuestionCategory",
    "QuestionOption",
    "AnswerQuestionRequest",
    "GenerateQuestionsRequest",
    "ClarificationQuestionResponse",
    "ClarificationQuestionsListResponse",
    "ClarificationStatusResponse",
]
