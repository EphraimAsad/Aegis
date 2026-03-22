"""Provider management endpoints."""

from fastapi import APIRouter, HTTPException

from app.core.exceptions import ProviderError, ProviderNotFoundError
from app.providers import ChatSettings, Message, get_provider_manager
from app.schemas.provider import (
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

router = APIRouter()


@router.get("", response_model=ProviderListResponse)
async def list_providers() -> ProviderListResponse:
    """
    List all registered AI providers.

    Returns provider names, capabilities, and which is the default.
    """
    manager = get_provider_manager()
    providers_info = []

    for name in manager.list_providers():
        info = manager.get_provider_info(name)
        # Perform health check for each provider
        try:
            provider = manager.get(name)
            is_healthy = await provider.healthcheck()
        except Exception:
            is_healthy = False

        providers_info.append(
            ProviderInfo(
                name=info["name"],
                is_default=info["is_default"],
                is_healthy=is_healthy,
                capabilities=ProviderCapabilitiesResponse(**info["capabilities"]),
            )
        )

    default = None
    try:
        default = manager.get_default().name
    except ProviderNotFoundError:
        pass

    return ProviderListResponse(
        providers=providers_info,
        default_provider=default,
    )


@router.get("/health", response_model=ProviderHealthResponse)
async def check_providers_health() -> ProviderHealthResponse:
    """
    Check health status of all registered providers.

    Returns a mapping of provider name to health status.
    """
    manager = get_provider_manager()
    health = await manager.healthcheck_all()
    return ProviderHealthResponse(providers=health)


@router.get("/{provider_name}", response_model=ProviderInfo)
async def get_provider(provider_name: str) -> ProviderInfo:
    """
    Get detailed information about a specific provider.

    Args:
        provider_name: The provider identifier (e.g., "ollama", "openai")
    """
    manager = get_provider_manager()

    try:
        info = manager.get_provider_info(provider_name)
        provider = manager.get(provider_name)
        is_healthy = await provider.healthcheck()

        return ProviderInfo(
            name=info["name"],
            is_default=info["is_default"],
            is_healthy=is_healthy,
            capabilities=ProviderCapabilitiesResponse(**info["capabilities"]),
        )
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.get("/{provider_name}/models", response_model=ModelListResponse)
async def list_provider_models(provider_name: str) -> ModelListResponse:
    """
    List available models for a specific provider.

    Args:
        provider_name: The provider identifier
    """
    manager = get_provider_manager()

    try:
        provider = manager.get(provider_name)
        models = await provider.list_models()
        return ModelListResponse(provider=provider_name, models=models)
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e


@router.post("/chat", response_model=ChatResponseSchema)
async def chat_completion(request: ChatRequest) -> ChatResponseSchema:
    """
    Send a chat completion request to an AI provider.

    Uses the specified provider or falls back to the default.
    """
    manager = get_provider_manager()

    try:
        provider = manager.get(request.provider)

        messages = [
            Message(role=msg.role, content=msg.content) for msg in request.messages
        ]

        settings = ChatSettings(
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            stream=False,  # Non-streaming endpoint
        )

        response = await provider.chat(messages, request.model, settings)

        return ChatResponseSchema(
            content=response.content,
            model=response.model,
            provider=response.provider,
            finish_reason=response.finish_reason,
            usage=response.usage,
        )
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=e.message) from e


@router.post("/embed", response_model=EmbeddingResponseSchema)
async def generate_embeddings(request: EmbeddingRequest) -> EmbeddingResponseSchema:
    """
    Generate embeddings for texts using an AI provider.

    Uses the specified provider or falls back to the default.
    """
    manager = get_provider_manager()

    try:
        provider = manager.get(request.provider)

        if not provider.capabilities.supports_embeddings:
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider.name}' does not support embeddings",
            )

        response = await provider.embed(request.texts, request.model)

        return EmbeddingResponseSchema(
            embeddings=response.embeddings,
            model=response.model,
            provider=response.provider,
            dimensions=response.dimensions,
            usage=response.usage,
        )
    except ProviderNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message) from e
    except ProviderError as e:
        raise HTTPException(status_code=502, detail=e.message) from e
