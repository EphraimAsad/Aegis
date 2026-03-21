"""Tests for AI providers."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.providers.base import (
    ChatResponse,
    ChatSettings,
    EmbeddingResponse,
    Message,
    MessageRole,
    ProviderCapabilities,
)
from app.providers.google import GoogleProvider


class TestGoogleProvider:
    """Tests for Google/Gemini provider."""

    @pytest.fixture
    def provider(self) -> GoogleProvider:
        """Create Google provider instance."""
        return GoogleProvider(
            api_key="test-api-key",
            default_model="gemini-1.5-flash",
        )

    def test_provider_name(self, provider: GoogleProvider) -> None:
        """Test provider name is 'google'."""
        assert provider.name == "google"

    def test_capabilities(self, provider: GoogleProvider) -> None:
        """Test provider capabilities."""
        caps = provider.capabilities

        assert isinstance(caps, ProviderCapabilities)
        assert caps.supports_chat is True
        assert caps.supports_completion is True
        assert caps.supports_embeddings is True
        assert caps.supports_streaming is True
        assert caps.supports_tools is True
        assert caps.supports_vision is True
        assert caps.max_context_length == 1000000

    def test_convert_messages_user_only(self, provider: GoogleProvider) -> None:
        """Test message conversion with user message only."""
        messages = [Message(role=MessageRole.USER, content="Hello")]

        system, contents = provider._convert_messages(messages)

        assert system is None
        assert len(contents) == 1
        assert contents[0]["role"] == "user"
        assert contents[0]["parts"][0]["text"] == "Hello"

    def test_convert_messages_with_system(self, provider: GoogleProvider) -> None:
        """Test message conversion with system message."""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are helpful"),
            Message(role=MessageRole.USER, content="Hello"),
        ]

        system, contents = provider._convert_messages(messages)

        assert system == "You are helpful"
        assert len(contents) == 1
        assert contents[0]["role"] == "user"

    def test_convert_messages_with_assistant(self, provider: GoogleProvider) -> None:
        """Test message conversion with assistant message."""
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
            Message(role=MessageRole.USER, content="How are you?"),
        ]

        system, contents = provider._convert_messages(messages)

        assert system is None
        assert len(contents) == 3
        assert contents[0]["role"] == "user"
        assert contents[1]["role"] == "model"  # Assistant maps to model
        assert contents[2]["role"] == "user"

    def test_build_url(self, provider: GoogleProvider) -> None:
        """Test URL building."""
        url = provider._build_url("gemini-1.5-flash", "generateContent")

        assert "gemini-1.5-flash" in url
        assert "generateContent" in url
        assert "key=test-api-key" in url

    @pytest.mark.asyncio
    async def test_chat_response_parsing(self, provider: GoogleProvider) -> None:
        """Test parsing of chat response."""
        mock_response = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Hello! How can I help?"}]},
                    "finishReason": "STOP",
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 10,
                "candidatesTokenCount": 20,
                "totalTokenCount": 30,
            },
        }

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            mock_http_response = MagicMock()
            mock_http_response.raise_for_status = MagicMock()
            mock_http_response.json.return_value = mock_response

            mock_client.post = AsyncMock(return_value=mock_http_response)

            messages = [Message(role=MessageRole.USER, content="Hi")]
            response = await provider.chat(messages)

            assert isinstance(response, ChatResponse)
            assert response.content == "Hello! How can I help?"
            assert response.provider == "google"
            assert response.usage["prompt_tokens"] == 10
            assert response.usage["completion_tokens"] == 20
            assert response.usage["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_complete_uses_chat(self, provider: GoogleProvider) -> None:
        """Test complete method uses chat internally."""
        with patch.object(provider, "chat") as mock_chat:
            mock_chat.return_value = ChatResponse(
                content="Completed",
                model="gemini-1.5-flash",
                provider="google",
            )

            result = await provider.complete("Test prompt")

            mock_chat.assert_called_once()
            args = mock_chat.call_args
            messages = args[0][0]
            assert len(messages) == 1
            assert messages[0].role == MessageRole.USER
            assert messages[0].content == "Test prompt"
            assert result.content == "Completed"

    @pytest.mark.asyncio
    async def test_embed_response_parsing(self, provider: GoogleProvider) -> None:
        """Test parsing of embedding response."""
        mock_response = {
            "embeddings": [
                {"values": [0.1, 0.2, 0.3, 0.4, 0.5]},
                {"values": [0.2, 0.3, 0.4, 0.5, 0.6]},
            ]
        }

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            mock_http_response = MagicMock()
            mock_http_response.raise_for_status = MagicMock()
            mock_http_response.json.return_value = mock_response

            mock_client.post = AsyncMock(return_value=mock_http_response)

            response = await provider.embed(["text1", "text2"])

            assert isinstance(response, EmbeddingResponse)
            assert len(response.embeddings) == 2
            assert response.embeddings[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
            assert response.dimensions == 5

    @pytest.mark.asyncio
    async def test_list_models_returns_known_models(
        self, provider: GoogleProvider
    ) -> None:
        """Test list_models returns known models on API failure."""
        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=Exception("API error"))

            models = await provider.list_models()

            assert "gemini-1.5-pro" in models
            assert "gemini-1.5-flash" in models

    @pytest.mark.asyncio
    async def test_healthcheck_success(self, provider: GoogleProvider) -> None:
        """Test healthcheck returns True on success."""
        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await provider.healthcheck()

            assert result is True

    @pytest.mark.asyncio
    async def test_healthcheck_failure(self, provider: GoogleProvider) -> None:
        """Test healthcheck returns False on failure."""
        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            mock_client.get = AsyncMock(side_effect=Exception("Connection error"))

            result = await provider.healthcheck()

            assert result is False

    @pytest.mark.asyncio
    async def test_close_client(self, provider: GoogleProvider) -> None:
        """Test closing the HTTP client."""
        # Create a mock client
        mock_client = AsyncMock()
        mock_client.is_closed = False
        provider._client = mock_client

        await provider.close()

        mock_client.aclose.assert_called_once()


class TestChatSettings:
    """Tests for chat settings."""

    def test_default_settings(self) -> None:
        """Test default chat settings."""
        settings = ChatSettings()

        assert settings.temperature == 0.7
        assert settings.top_p == 1.0  # Default top_p
        assert settings.max_tokens is None
        assert settings.stop is None

    def test_custom_settings(self) -> None:
        """Test custom chat settings."""
        settings = ChatSettings(
            temperature=0.5,
            top_p=0.8,
            max_tokens=100,
            stop=["END"],
        )

        assert settings.temperature == 0.5
        assert settings.top_p == 0.8
        assert settings.max_tokens == 100
        assert settings.stop == ["END"]


class TestMessage:
    """Tests for message class."""

    def test_user_message(self) -> None:
        """Test user message creation."""
        msg = Message(role=MessageRole.USER, content="Hello")

        assert msg.role == MessageRole.USER
        assert msg.content == "Hello"

    def test_system_message(self) -> None:
        """Test system message creation."""
        msg = Message(role=MessageRole.SYSTEM, content="Be helpful")

        assert msg.role == MessageRole.SYSTEM
        assert msg.content == "Be helpful"

    def test_assistant_message(self) -> None:
        """Test assistant message creation."""
        msg = Message(role=MessageRole.ASSISTANT, content="Hi there")

        assert msg.role == MessageRole.ASSISTANT
        assert msg.content == "Hi there"
