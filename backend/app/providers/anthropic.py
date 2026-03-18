"""Anthropic provider implementation.

Supports Claude models via the Anthropic API.
"""

from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.exceptions import ProviderError, ProviderUnavailableError
from app.providers.base import (
    BaseProvider,
    ChatResponse,
    ChatSettings,
    EmbeddingResponse,
    Message,
    MessageRole,
    ProviderCapabilities,
)


class AnthropicProvider(BaseProvider):
    """
    Anthropic provider for Claude models.

    Supports Claude 3 family: Opus, Sonnet, Haiku.
    """

    # Available Claude models
    MODELS = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
        "claude-3-5-sonnet-20241022",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.anthropic.com",
        default_model: str = "claude-3-5-sonnet-20241022",
        timeout: float = 120.0,
        api_version: str = "2023-06-01",
    ) -> None:
        """
        Initialize the Anthropic provider.

        Args:
            api_key: Anthropic API key
            base_url: API base URL
            default_model: Default model for chat/completion
            timeout: Request timeout in seconds
            api_version: Anthropic API version
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._timeout = timeout
        self._api_version = api_version
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with auth headers."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {
                "Content-Type": "application/json",
                "anthropic-version": self._api_version,
            }

            if self._api_key:
                headers["x-api-key"] = self._api_key

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=headers,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    @property
    def name(self) -> str:
        """Provider name identifier."""
        return "anthropic"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        return ProviderCapabilities(
            supports_chat=True,
            supports_completion=True,
            supports_embeddings=False,  # Anthropic doesn't provide embeddings
            supports_streaming=True,
            supports_tools=True,
            supports_json_mode=False,  # Uses tool_use for structured output
            supports_vision=True,
            max_context_length=200000,  # Claude 3 context window
            max_output_tokens=4096,
        )

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Send chat messages to Anthropic.

        Args:
            messages: List of chat messages
            model: Model to use (default: claude-3-5-sonnet)
            settings: Chat settings

        Returns:
            ChatResponse: The model's response
        """
        client = await self._get_client()
        model = model or self._default_model
        settings = settings or ChatSettings()

        # Anthropic has a different message format - system is separate
        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                anthropic_messages.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                    }
                )

        # Build request payload
        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": settings.max_tokens or 4096,
            "temperature": settings.temperature,
            "top_p": settings.top_p,
        }

        if system_message:
            payload["system"] = system_message

        if settings.stop:
            payload["stop_sequences"] = settings.stop

        try:
            response = await client.post("/v1/messages", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract content from response
            content = ""
            for block in data.get("content", []):
                if block.get("type") == "text":
                    content += block.get("text", "")

            usage = data.get("usage", {})

            return ChatResponse(
                content=content,
                model=data.get("model", model),
                provider=self.name,
                finish_reason=data.get("stop_reason"),
                usage={
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": (
                        usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
                    ),
                },
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Anthropic API at {self._base_url}",
                details={"error": str(e)},
            ) from e
        except httpx.HTTPStatusError as e:
            error_detail = "Unknown error"
            try:
                error_data = e.response.json()
                error_detail = error_data.get("error", {}).get("message", str(e))
            except Exception:
                error_detail = e.response.text

            raise ProviderError(
                f"Anthropic request failed: {error_detail}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Anthropic chat failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Complete a prompt using Anthropic.

        Args:
            prompt: The prompt to complete
            model: Model to use
            settings: Completion settings

        Returns:
            ChatResponse: The model's completion
        """
        messages = [Message(role=MessageRole.USER, content=prompt)]
        return await self.chat(messages, model, settings)

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResponse:
        """
        Generate embeddings - NOT SUPPORTED by Anthropic.

        Raises:
            ProviderError: Always, as Anthropic doesn't support embeddings
        """
        raise ProviderError(
            "Anthropic does not support embeddings. Use a different provider.",
            details={"provider": self.name},
        )

    async def healthcheck(self) -> bool:
        """Check if Anthropic API is available."""
        # Anthropic doesn't have a dedicated health endpoint
        # We'll check if we can reach the API
        try:
            client = await self._get_client()
            # Make a minimal request to check connectivity
            response = await client.post(
                "/v1/messages",
                json={
                    "model": self._default_model,
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
            )
            # 200 = success, 401 = auth error (but API is reachable)
            return response.status_code in [200, 401]
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available Claude models."""
        # Anthropic doesn't have a models endpoint, return known models
        return self.MODELS.copy()

    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat responses from Anthropic.

        Args:
            messages: List of chat messages
            model: Model to use
            settings: Chat settings

        Yields:
            str: Response chunks
        """
        client = await self._get_client()
        model = model or self._default_model
        settings = settings or ChatSettings()

        system_message = None
        anthropic_messages = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_message = msg.content
            else:
                anthropic_messages.append(
                    {
                        "role": msg.role.value,
                        "content": msg.content,
                    }
                )

        payload: dict[str, Any] = {
            "model": model,
            "messages": anthropic_messages,
            "max_tokens": settings.max_tokens or 4096,
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "stream": True,
        }

        if system_message:
            payload["system"] = system_message

        try:
            async with client.stream("POST", "/v1/messages", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json

                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Anthropic API at {self._base_url}",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Anthropic streaming failed: {str(e)}",
                details={"error": str(e)},
            ) from e
