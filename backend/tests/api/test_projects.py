"""Tests for project endpoints."""

import os

import pytest
from httpx import AsyncClient

# Skip tests that require database connection in CI
skip_in_ci = pytest.mark.skipif(
    os.getenv("CI") == "true",
    reason="Requires database connection",
)


@skip_in_ci
@pytest.mark.asyncio
async def test_create_project(async_client: AsyncClient) -> None:
    """Test creating a new project."""
    response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "description": "A test research project",
            "research_objective": "Investigate the effects of AI on academic research productivity",
        },
    )

    assert response.status_code == 201


@skip_in_ci
@pytest.mark.asyncio
async def test_list_projects(async_client: AsyncClient) -> None:
    """Test listing projects."""
    response = await async_client.get("/api/v1/projects")

    assert response.status_code == 200


@skip_in_ci
@pytest.mark.asyncio
async def test_list_projects_with_pagination(async_client: AsyncClient) -> None:
    """Test listing projects with pagination parameters."""
    response = await async_client.get(
        "/api/v1/projects",
        params={"page": 1, "page_size": 10},
    )

    assert response.status_code == 200


@skip_in_ci
@pytest.mark.asyncio
async def test_list_projects_with_status_filter(async_client: AsyncClient) -> None:
    """Test listing projects filtered by status."""
    response = await async_client.get(
        "/api/v1/projects",
        params={"status": "draft"},
    )

    assert response.status_code == 200


@skip_in_ci
@pytest.mark.asyncio
async def test_get_project_not_found(async_client: AsyncClient) -> None:
    """Test getting a non-existent project."""
    response = await async_client.get("/api/v1/projects/99999")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_project_validation(async_client: AsyncClient) -> None:
    """Test project creation validation."""
    # Missing required field
    response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            # Missing research_objective
        },
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_project_short_objective(async_client: AsyncClient) -> None:
    """Test project creation with too short objective."""
    response = await async_client.post(
        "/api/v1/projects",
        json={
            "name": "Test Project",
            "research_objective": "Too short",  # Less than 10 chars
        },
    )

    assert response.status_code == 422  # Validation error
