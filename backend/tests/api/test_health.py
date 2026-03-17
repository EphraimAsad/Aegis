"""Tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_live(async_client: AsyncClient) -> None:
    """Test liveness probe returns OK."""
    response = await async_client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_health_check_response_structure(async_client: AsyncClient) -> None:
    """Test health check returns expected structure."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "database" in data
    assert "redis" in data


@pytest.mark.asyncio
async def test_health_check_version(async_client: AsyncClient) -> None:
    """Test health check returns correct version."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["version"] == "0.1.0"
