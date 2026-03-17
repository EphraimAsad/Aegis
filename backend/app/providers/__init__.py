"""AI Provider abstraction layer.

This module provides a unified interface for interacting with different
AI providers (Ollama, OpenAI, Anthropic, etc.).

Usage:
    from app.providers import get_provider_manager

    manager = get_provider_manager()
    provider = manager.get("ollama")  # or manager.get_default()

    response = await provider.chat(messages)
"""

from app.providers.base import (
    BaseProvider,
    ChatResponse,
    ChatSettings,
    EmbeddingResponse,
    Message,
    MessageRole,
    ProviderCapabilities,
)
from app.providers.manager import (
    ProviderManager,
    cleanup_providers,
    get_provider_manager,
)

__all__ = [
    # Base classes and types
    "BaseProvider",
    "Message",
    "MessageRole",
    "ChatSettings",
    "ChatResponse",
    "EmbeddingResponse",
    "ProviderCapabilities",
    # Manager
    "ProviderManager",
    "get_provider_manager",
    "cleanup_providers",
]
