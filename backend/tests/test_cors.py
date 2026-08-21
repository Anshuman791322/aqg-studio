"""Tests for CORS middleware configuration."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_cors_allowed_origin(async_client: AsyncClient) -> None:
    """Verify allowed origin receives appropriate CORS headers."""
    response = await async_client.options(
        "/api/v1/version",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert "access-control-allow-credentials" in response.headers


@pytest.mark.asyncio
async def test_cors_disallowed_origin(async_client: AsyncClient) -> None:
    """Verify disallowed origin does not receive access-control-allow-origin header."""
    response = await async_client.options(
        "/api/v1/version",
        headers={
            "Origin": "https://malicious-unauthorized-site.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Origin should not be allowed in response header
    assert response.headers.get("access-control-allow-origin") is None
