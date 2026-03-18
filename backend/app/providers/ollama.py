"""Ollama provider implementation.

Ollama is the default local LLM provider for Aegis development.
API Documentation: https://github.com/ollama/ollama/blob/main/docs/api.md
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


class OllamaProvider(BaseProvider):
    """
    Ollama provider for local LLM inference.

    Ollama runs locally and provides access to various open-source models
    like Llama, Mistral, CodeLlama, etc.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        default_model: str = "llama2",
        default_embedding_model: str = "nomic-embed-text",
        timeout: float = 120.0,
    ) -> None:
        """
        Initialize the Ollama provider.

        Args:
            base_url: Ollama API base URL
            default_model: Default model for chat/completion
            default_embedding_model: Default model for embeddings
            timeout: Request timeout in seconds
        """
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model
        self._default_embedding_model = default_embedding_model
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
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
        return "ollama"

    @property
    def capabilities(self) -> ProviderCapabilities:
        """Get provider capabilities."""
        return ProviderCapabilities(
            supports_chat=True,
            supports_completion=True,
            supports_embeddings=True,
            supports_streaming=True,
            supports_tools=False,  # Ollama has limited tool support
            supports_json_mode=True,
            supports_vision=True,  # Some models support vision
        )

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Send chat messages to Ollama.

        Args:
            messages: List of chat messages
            model: Model to use (default: llama2)
            settings: Chat settings

        Returns:
            ChatResponse: The model's response
        """
        client = await self._get_client()
        model = model or self._default_model
        settings = settings or ChatSettings()

        # Convert messages to Ollama format
        ollama_messages = [
            {"role": msg.role.value, "content": msg.content} for msg in messages
        ]

        # Build request payload
        payload: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": settings.temperature,
                "top_p": settings.top_p,
            },
        }

        if settings.max_tokens:
            payload["options"]["num_predict"] = settings.max_tokens

        if settings.stop:
            payload["options"]["stop"] = settings.stop

        if settings.json_mode:
            payload["format"] = "json"

        try:
            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            return ChatResponse(
                content=data["message"]["content"],
                model=data.get("model", model),
                provider=self.name,
                finish_reason=data.get("done_reason"),
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": (
                        data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    ),
                },
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Ollama at {self._base_url}. Is Ollama running?",
                details={"error": str(e)},
            ) from e
        except httpx.HTTPStatusError as e:
            raise ProviderError(
                f"Ollama request failed: {e.response.text}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Ollama chat failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Complete a prompt using Ollama's generate endpoint.

        Args:
            prompt: The prompt to complete
            model: Model to use
            settings: Completion settings

        Returns:
            ChatResponse: The model's completion
        """
        client = await self._get_client()
        model = model or self._default_model
        settings = settings or ChatSettings()

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": settings.temperature,
                "top_p": settings.top_p,
            },
        }

        if settings.max_tokens:
            payload["options"]["num_predict"] = settings.max_tokens

        if settings.stop:
            payload["options"]["stop"] = settings.stop

        if settings.json_mode:
            payload["format"] = "json"

        try:
            response = await client.post("/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()

            return ChatResponse(
                content=data["response"],
                model=data.get("model", model),
                provider=self.name,
                finish_reason=data.get("done_reason"),
                usage={
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "total_tokens": (
                        data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    ),
                },
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Ollama at {self._base_url}",
                details={"error": str(e)},
            ) from e
        except httpx.HTTPStatusError as e:
            raise ProviderError(
                f"Ollama request failed: {e.response.text}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Ollama completion failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
    ) -> EmbeddingResponse:
        """
        Generate embeddings using Ollama.

        Args:
            texts: List of texts to embed
            model: Embedding model (default: nomic-embed-text)

        Returns:
            EmbeddingResponse: The embeddings
        """
        client = await self._get_client()
        model = model or self._default_embedding_model

        embeddings: list[list[float]] = []

        try:
            # Ollama processes one text at a time for embeddings
            for text in texts:
                response = await client.post(
                    "/api/embeddings",
                    json={"model": model, "prompt": text},
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])

            # Get dimensions from first embedding
            dimensions = len(embeddings[0]) if embeddings else 0

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                provider=self.name,
                dimensions=dimensions,
                usage={"total_tokens": len(texts)},  # Approximate
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Ollama at {self._base_url}",
                details={"error": str(e)},
            ) from e
        except httpx.HTTPStatusError as e:
            raise ProviderError(
                f"Ollama embeddings failed: {e.response.text}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Ollama embeddings failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def healthcheck(self) -> bool:
        """Check if Ollama is available."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available models in Ollama."""
        try:
            client = await self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return [model["name"] for model in data.get("models", [])]
        except Exception:
            return []

    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat responses from Ollama.

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

        ollama_messages = [
            {"role": msg.role.value, "content": msg.content} for msg in messages
        ]

        payload: dict[str, Any] = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": settings.temperature,
                "top_p": settings.top_p,
            },
        }

        if settings.max_tokens:
            payload["options"]["num_predict"] = settings.max_tokens

        try:
            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json

                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            yield data["message"]["content"]
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Ollama at {self._base_url}",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Ollama streaming failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def pull_model(self, model: str) -> bool:
        """
        Pull a model from the Ollama library.

        Args:
            model: Model name to pull

        Returns:
            bool: True if successful
        """
        try:
            client = await self._get_client()
            # Use a longer timeout for model pulls
            response = await client.post(
                "/api/pull",
                json={"name": model, "stream": False},
                timeout=600.0,  # 10 minutes for large models
            )
            return response.status_code == 200
        except Exception:
            return False
