"""Provider-related schemas."""

from pydantic import BaseModel, Field

from app.providers.base import MessageRole


class ProviderCapabilitiesResponse(BaseModel):
    """Provider capabilities response."""

    supports_chat: bool
    supports_completion: bool
    supports_embeddings: bool
    supports_streaming: bool
    supports_tools: bool
    supports_json_mode: bool
    supports_vision: bool
    max_context_length: int | None = None
    max_output_tokens: int | None = None


class ProviderInfo(BaseModel):
    """Provider information response."""

    name: str
    is_default: bool
    is_healthy: bool | None = None
    capabilities: ProviderCapabilitiesResponse


class ProviderListResponse(BaseModel):
    """Response for listing all providers."""

    providers: list[ProviderInfo]
    default_provider: str | None


class ProviderHealthResponse(BaseModel):
    """Provider health check response."""

    providers: dict[str, bool]


class ModelListResponse(BaseModel):
    """Response for listing models."""

    provider: str
    models: list[str]


class ChatMessageRequest(BaseModel):
    """Chat message in request."""

    role: MessageRole
    content: str


class ChatRequest(BaseModel):
    """Chat completion request."""

    messages: list[ChatMessageRequest]
    model: str | None = None
    provider: str | None = None
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    stream: bool = False


class ChatResponseSchema(BaseModel):
    """Chat completion response."""

    content: str
    model: str
    provider: str
    finish_reason: str | None = None
    usage: dict[str, int] | None = None


class EmbeddingRequest(BaseModel):
    """Embedding request."""

    texts: list[str]
    model: str | None = None
    provider: str | None = None


class EmbeddingResponseSchema(BaseModel):
    """Embedding response."""

    embeddings: list[list[float]]
    model: str
    provider: str
    dimensions: int
    usage: dict[str, int] | None = None
