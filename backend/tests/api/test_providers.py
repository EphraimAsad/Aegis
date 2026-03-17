"""Tests for provider endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_providers(async_client: AsyncClient) -> None:
    """Test listing all providers."""
    response = await async_client.get("/api/v1/providers")
    assert response.status_code == 200

    data = response.json()
    assert "providers" in data
    assert "default_provider" in data
    assert isinstance(data["providers"], list)


@pytest.mark.asyncio
async def test_list_providers_contains_ollama(async_client: AsyncClient) -> None:
    """Test that Ollama is always registered as a provider."""
    response = await async_client.get("/api/v1/providers")
    assert response.status_code == 200

    data = response.json()
    provider_names = [p["name"] for p in data["providers"]]
    assert "ollama" in provider_names


@pytest.mark.asyncio
async def test_provider_info_structure(async_client: AsyncClient) -> None:
    """Test provider info has correct structure."""
    response = await async_client.get("/api/v1/providers")
    assert response.status_code == 200

    data = response.json()
    if data["providers"]:
        provider = data["providers"][0]
        assert "name" in provider
        assert "is_default" in provider
        assert "capabilities" in provider

        caps = provider["capabilities"]
        assert "supports_chat" in caps
        assert "supports_completion" in caps
        assert "supports_embeddings" in caps


@pytest.mark.asyncio
async def test_get_provider_not_found(async_client: AsyncClient) -> None:
    """Test getting a non-existent provider returns 404."""
    response = await async_client.get("/api/v1/providers/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_providers_health_endpoint(async_client: AsyncClient) -> None:
    """Test the providers health check endpoint."""
    response = await async_client.get("/api/v1/providers/health")
    assert response.status_code == 200

    data = response.json()
    assert "providers" in data
    assert isinstance(data["providers"], dict)
