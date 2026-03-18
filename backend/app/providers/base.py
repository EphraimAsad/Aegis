"""Base provider abstraction interface.

This module defines the abstract interface that all AI providers must implement.
The abstraction allows the application to work with any provider transparently.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    """Message role enumeration."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    """Chat message structure."""

    role: MessageRole
    content: str


class ChatSettings(BaseModel):
    """Settings for chat/completion requests."""

    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    stream: bool = False
    stop: list[str] | None = None

    # JSON mode (if supported)
    json_mode: bool = False

    # Provider-specific options
    extra: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    """Response from a chat/completion request."""

    content: str
    model: str
    provider: str
    finish_reason: str | None = None
    usage: dict[str, int] | None = None

    # Raw response for debugging
    raw: dict[str, Any] | None = None


class EmbeddingResponse(BaseModel):
    """Response from an embedding request."""

    embeddings: list[list[float]]
    model: str
    provider: str
    dimensions: int
    usage: dict[str, int] | None = None


class ProviderCapabilities(BaseModel):
    """Describes what a provider supports."""

    supports_chat: bool = True
    supports_completion: bool = True
    supports_embeddings: bool = False
    supports_streaming: bool = False
    supports_tools: bool = False
    supports_json_mode: bool = False
    supports_vision: bool = False

    # Model-specific capabilities
    max_context_length: int | None = None
    max_output_tokens: int | None = None


class BaseProvider(ABC):
    """
    Abstract base class for AI provider implementations.

    All providers (Ollama, OpenAI, Anthropic, etc.) must implement this interface.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Provider name identifier.

        Returns:
            str: Unique provider name (e.g., "ollama", "openai", "anthropic")
        """
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """
        Get provider capabilities.

        Returns:
            ProviderCapabilities: What this provider supports
        """
        pass

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Send chat messages and get a response.

        Args:
            messages: List of chat messages
            model: Model to use (provider-specific). If None, uses default.
            settings: Chat settings (temperature, max_tokens, etc.)

        Returns:
            ChatResponse: The model's response

        Raises:
            ProviderError: If the request fails
        """
        pass

    @abstractmethod
    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Complete a single prompt (non-chat mode).

        Args:
            prompt: The prompt to complete
            model: Model to use. If None, uses default.
            settings: Completion settings

        Returns:
            ChatResponse: The model's completion

        Raises:
            ProviderError: If the request fails
        """
        pass

    @abstractmethod
    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResponse:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed
            model: Embedding model to use. If None, uses default.

        Returns:
            EmbeddingResponse: The embeddings

        Raises:
            ProviderError: If the request fails or embeddings not supported
        """
        pass

    @abstractmethod
    async def healthcheck(self) -> bool:
        """
        Check if the provider is available and responding.

        Returns:
            bool: True if healthy, False otherwise
        """
        pass

    def supports_tools(self) -> bool:
        """
        Check if the provider supports tool/function calling.

        Returns:
            bool: True if tool calling is supported
        """
        return self.capabilities.supports_tools

    def supports_json_mode(self) -> bool:
        """
        Check if the provider supports JSON output mode.

        Returns:
            bool: True if JSON mode is supported
        """
        return self.capabilities.supports_json_mode

    def supports_streaming(self) -> bool:
        """
        Check if the provider supports streaming responses.

        Returns:
            bool: True if streaming is supported
        """
        return self.capabilities.supports_streaming

    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat responses.

        Default implementation yields the full response as a single chunk.
        Providers that support streaming should override this.

        Args:
            messages: List of chat messages
            model: Model to use
            settings: Chat settings

        Yields:
            str: Response chunks

        Raises:
            ProviderError: If the request fails
        """
        response = await self.chat(messages, model, settings)
        yield response.content

    async def list_models(self) -> list[str]:
        """
        List available models from this provider.

        Returns:
            list[str]: List of model names/identifiers

        Note:
            Not all providers support listing models.
            Returns empty list if not supported.
        """
        return []
