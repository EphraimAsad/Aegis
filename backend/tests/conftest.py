"""Pytest configuration and fixtures."""

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from fastapi.testclient import TestClient
    from httpx import AsyncClient


@pytest.fixture
def client() -> "TestClient":
    """Create a test client for synchronous tests.

    Only loads the app when this fixture is actually used.
    """
    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


@pytest.fixture
async def async_client() -> AsyncGenerator["AsyncClient", None]:
    """Create an async test client.

    Only loads the app when this fixture is actually used.
    """
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac
