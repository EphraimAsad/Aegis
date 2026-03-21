"""Google AI (Gemini) provider implementation.

Supports Gemini models via the Google AI API.
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


class GoogleProvider(BaseProvider):
    """
    Google AI provider for Gemini models.

    Supports Gemini 1.5 Pro, Gemini 1.5 Flash, and Gemini 1.0 Pro.
    """

    # Available Gemini models
    MODELS = [
        "gemini-1.5-pro",
        "gemini-1.5-flash",
        "gemini-1.0-pro",
        "gemini-pro",
    ]

    # Embedding models
    EMBEDDING_MODELS = [
        "text-embedding-004",
        "embedding-001",
    ]

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = "https://generativelanguage.googleapis.com",
        default_model: str = "gemini-1.5-flash",
        default_embedding_model: str = "text-embedding-004",
        timeout: float = 120.0,
    ) -> None:
        """
        Initialize the Google AI provider.

        Args:
            api_key: Google AI API key
            base_url: API base URL
            default_model: Default model for chat/completion
            default_embedding_model: Default model for embeddings
            timeout: Request timeout in seconds
        """
        self._api_key = api_key
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
                headers={"Content-Type": "application/json"},
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
        return "google"

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
            max_context_length=1000000,  # Gemini 1.5 Pro context window
            max_output_tokens=8192,
        )

    def _build_url(self, model: str, action: str) -> str:
        """Build the API URL with model and API key."""
        return f"/v1beta/models/{model}:{action}?key={self._api_key}"

    def _convert_messages(
        self, messages: list[Message]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """
        Convert messages to Google AI format.

        Returns:
            Tuple of (system_instruction, contents)
        """
        system_instruction = None
        contents = []

        for msg in messages:
            if msg.role == MessageRole.SYSTEM:
                system_instruction = msg.content
            elif msg.role == MessageRole.USER:
                contents.append(
                    {
                        "role": "user",
                        "parts": [{"text": msg.content}],
                    }
                )
            elif msg.role == MessageRole.ASSISTANT:
                contents.append(
                    {
                        "role": "model",
                        "parts": [{"text": msg.content}],
                    }
                )

        return system_instruction, contents

    async def chat(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Send chat messages to Google AI.

        Args:
            messages: List of chat messages
            model: Model to use (default: gemini-1.5-flash)
            settings: Chat settings

        Returns:
            ChatResponse: The model's response
        """
        client = await self._get_client()
        model = model or self._default_model
        settings = settings or ChatSettings()

        system_instruction, contents = self._convert_messages(messages)

        # Build request payload
        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": settings.temperature,
                "topP": settings.top_p,
                "maxOutputTokens": settings.max_tokens or 8192,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        if settings.stop:
            payload["generationConfig"]["stopSequences"] = settings.stop

        try:
            url = self._build_url(model, "generateContent")
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract content from response
            content = ""
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "text" in part:
                        content += part["text"]

            # Extract usage metadata
            usage_metadata = data.get("usageMetadata", {})

            return ChatResponse(
                content=content,
                model=model,
                provider=self.name,
                finish_reason=candidates[0].get("finishReason") if candidates else None,
                usage={
                    "prompt_tokens": usage_metadata.get("promptTokenCount", 0),
                    "completion_tokens": usage_metadata.get("candidatesTokenCount", 0),
                    "total_tokens": usage_metadata.get("totalTokenCount", 0),
                },
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Google AI API at {self._base_url}",
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
                f"Google AI request failed: {error_detail}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Google AI chat failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def complete(
        self,
        prompt: str,
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> ChatResponse:
        """
        Complete a prompt using Google AI.

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
        Generate embeddings using Google AI.

        Args:
            texts: List of texts to embed
            model: Embedding model to use

        Returns:
            EmbeddingResponse: Embedding vectors
        """
        client = await self._get_client()
        model = model or self._default_embedding_model

        try:
            # Google AI supports batch embedding
            payload = {
                "requests": [
                    {
                        "model": f"models/{model}",
                        "content": {"parts": [{"text": text}]},
                    }
                    for text in texts
                ]
            }

            url = f"/v1beta/models/{model}:batchEmbedContents?key={self._api_key}"
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()

            embeddings = []
            for embedding_data in data.get("embeddings", []):
                embeddings.append(embedding_data.get("values", []))

            return EmbeddingResponse(
                embeddings=embeddings,
                model=model,
                provider=self.name,
                dimensions=len(embeddings[0]) if embeddings else 0,
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Google AI API at {self._base_url}",
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
                f"Google AI embedding failed: {error_detail}",
                details={"status_code": e.response.status_code},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Google AI embed failed: {str(e)}",
                details={"error": str(e)},
            ) from e

    async def healthcheck(self) -> bool:
        """Check if Google AI API is available."""
        try:
            client = await self._get_client()
            # List models to check API connectivity
            url = f"/v1beta/models?key={self._api_key}"
            response = await client.get(url)
            return response.status_code in [200, 401]
        except Exception:
            return False

    async def list_models(self) -> list[str]:
        """List available Gemini models."""
        try:
            client = await self._get_client()
            url = f"/v1beta/models?key={self._api_key}"
            response = await client.get(url)

            if response.status_code == 200:
                data = response.json()
                models = []
                for model in data.get("models", []):
                    name = model.get("name", "").replace("models/", "")
                    if name.startswith("gemini"):
                        models.append(name)
                return models
        except Exception:
            pass

        # Return known models as fallback
        return self.MODELS.copy()

    async def chat_stream(
        self,
        messages: list[Message],
        model: str | None = None,
        settings: ChatSettings | None = None,
    ) -> AsyncIterator[str]:
        """
        Stream chat responses from Google AI.

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

        system_instruction, contents = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": settings.temperature,
                "topP": settings.top_p,
                "maxOutputTokens": settings.max_tokens or 8192,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        try:
            url = self._build_url(model, "streamGenerateContent")
            url += "&alt=sse"

            async with client.stream("POST", url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        import json

                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            candidates = data.get("candidates", [])
                            if candidates:
                                parts = (
                                    candidates[0].get("content", {}).get("parts", [])
                                )
                                for part in parts:
                                    if "text" in part:
                                        yield part["text"]
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError as e:
            raise ProviderUnavailableError(
                f"Cannot connect to Google AI API at {self._base_url}",
                details={"error": str(e)},
            ) from e
        except Exception as e:
            raise ProviderError(
                f"Google AI streaming failed: {str(e)}",
                details={"error": str(e)},
            ) from e
