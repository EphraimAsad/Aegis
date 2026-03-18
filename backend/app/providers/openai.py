"""OpenAI provider implementation.

Supports OpenAI's API and OpenAI-compatible endpoints (e.g., Azure OpenAI, local proxies).
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
    ProviderCapabilities,
)


class OpenAIProvider(BaseProvider):
    """
    OpenAI provider for GPT models.

    Supports:
    - OpenAI API (api.openai.com)
    - Azure OpenAI
    - OpenAI-compatible endpoints
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com/v1",
        default_model: str = "gpt-3.5-turbo",
        default_embedding_model: str = "text-embedding-3-small",
        organization: str | None = None,
        timeout: float = 120.0,
    ) -> None:
        """
        Initialize the OpenAI provider.

        Args:
            api_key: OpenAI API key (required for OpenAI, optional for some compatible endpoints)
            base_url: API base URL
            default_model: Default model for chat/completion
            default_embedding_model: Default model for embeddings
            organization: OpenAI organization ID (optional)
            timeout: Request timeout in seconds
        """
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._default_embedding_model = default_embedding_model
        self._organization = organization
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with auth headers."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {
                "Content-Type": "application/json",
            }

            if self._api_key:
                headers["Authorization"] = f"Bearer {self._api_key}"

            if self._organization:
                headers["OpenAI-Organization"] = self._organization

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
        return "openai"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        return ProviderCapabilities(
            supports_chat=True,
            supports_completion=True,
            supports_embeddings=True,
            supports_streaming=True,
            supports_tools=True,
            supports_json_mode=True,
            supports_vision=True,
            max_context_length=128000,  # GPT-4 Turbo
            max_output_tokens=4096,
        )

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Send chat messages to OpenAI.

        Args:
            messages: List of chat messages
            model: Model to use (default: gpt-3.5-turbo)
            settings: Chat settings

        Returns:
            ChatResponse: The model's response
        """
        client = await self._get_client()
        model = model or self._default_model
        settings = settings or ChatSettings()

        # Convert messages to OpenAI format
        openai_messages = [
            {"role": msg.role.value, "content": msg.content} for msg in messages
        ]

        # Build request payload
        payload: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "temperature": settings.temperature,
            "top_p": settings.top_p,
        }

        if settings.max_tokens:
            payload["max_tokens"] = settings.max_tokens

        if settings.stop:
            payload["stop"] = settings.stop

        if settings.json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            choice = data["choices"][0]
            usage = data.get("usage", {})

            return ChatResponse(
                content=choice["message"]["content"],
                model=data.get("model", model),
                provider=self.name,
                finish_reason=choice.get("finish_reason"),
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to OpenAI API at {self._base_url}",
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
                f"OpenAI request failed: {error_detail}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"OpenAI chat failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Complete a prompt using OpenAI.

        Note: Uses chat completions API with a single user message,
        as the legacy completions API is deprecated.

        Args:
            prompt: The prompt to complete
            model: Model to use
            settings: Completion settings

        Returns:
            ChatResponse: The model's completion
        """
        # Convert to chat format
        messages = [Message(role="user", content=prompt)]
        return await self.chat(messages, model, settings)

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResponse:
        """
        Generate embeddings using OpenAI.

        Args:
            texts: List of texts to embed
            model: Embedding model (default: text-embedding-3-small)

        Returns:
            EmbeddingResponse: The embeddings
        """
        client = await self._get_client()
        model = model or self._default_embedding_model

        try:
            response = await client.post(
                "/embeddings",
                json={"model": model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()

            embeddings = [item["embedding"] for item in data["data"]]
            dimensions = len(embeddings[0]) if embeddings else 0
            usage = data.get("usage", {})

            return EmbeddingResponse(
                embeddings=embeddings,
                model=data.get("model", model),
                provider=self.name,
                dimensions=dimensions,
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to OpenAI API at {self._base_url}",
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
                f"OpenAI embeddings failed: {error_detail}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"OpenAI embeddings failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def healthcheck(self) -> bool:
        """Check if OpenAI API is available."""
        try:
            client = await self._get_client()
            response = await client.get("/models")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models from OpenAI."""
        try:
            client = await self._get_client()
            response = await client.get("/models")
            response.raise_for_status()
            data = response.json()
            return [model["id"] for model in data.get("data", [])]
        except Exception:
            return []

    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat responses from OpenAI.

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

        openai_messages = [
            {"role": msg.role.value, "content": msg.content} for msg in messages
        ]

        payload: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "temperature": settings.temperature,
            "top_p": settings.top_p,
            "stream": True,
        }

        if settings.max_tokens:
            payload["max_tokens"] = settings.max_tokens

        try:
            async with client.stream(
                "POST", "/chat/completions", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        import json

                        data = json.loads(data_str)
                        if "choices" in data and len(data["choices"]) > 0:
                            delta = data["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to OpenAI API at {self._base_url}",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"OpenAI streaming failed: {str(e)}",
                details={"error": str(e)},
            ) from e
