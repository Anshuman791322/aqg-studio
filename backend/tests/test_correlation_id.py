"""Tests for request correlation ID tracking."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_auto_generated_correlation_id(async_client: AsyncClient) -> None:
    """Verify backend automatically generates X-Correlation-ID when not provided."""
    response = await async_client.get("/health/live")
    assert response.status_code == 200
    assert "x-correlation-id" in response.headers
    corr_id = response.headers["x-correlation-id"]
    assert corr_id.startswith("req_")


@pytest.mark.asyncio
async def test_preserved_correlation_id(async_client: AsyncClient) -> None:
    """Verify backend propagates existing X-Correlation-ID header."""
    custom_id = "custom-test-correlation-id-9988"
    response = await async_client.get(
        "/health/live",
        headers={"X-Correlation-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers.get("x-correlation-id") == custom_id


@pytest.mark.asyncio
async def test_preserved_request_id(async_client: AsyncClient) -> None:
    """Verify backend honors incoming X-Request-ID header."""
    custom_id = "custom-test-req-id-1234"
    response = await async_client.get(
        "/api/v1/version",
        headers={"X-Request-ID": custom_id},
    )
    assert response.status_code == 200
    assert response.headers.get("x-correlation-id") == custom_id
    body = response.json()
    assert body["meta"]["request_id"] == custom_id
