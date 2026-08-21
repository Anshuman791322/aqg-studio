"""Pytest fixtures and test environment configuration."""

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import app


def get_test_settings() -> Settings:
    """Return test-specific settings."""
    return Settings(
        ENVIRONMENT="test",
        LOG_LEVEL="DEBUG",
        DEBUG=True,
        BACKEND_CORS_ORIGINS=["http://localhost:3000", "https://aqg-studio.test"],
        DATABASE_URL=None,
    )


@pytest.fixture
def client() -> TestClient:
    """Synchronous test client."""
    app.dependency_overrides[get_settings] = get_test_settings
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client using httpx."""
    app.dependency_overrides[get_settings] = get_test_settings
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
    app.dependency_overrides.clear()
