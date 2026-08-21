"""Tests for version API endpoint."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_version_endpoint(async_client: AsyncClient) -> None:
    """Verify /api/v1/version returns standardized envelope with version payload."""
    response = await async_client.get("/api/v1/version")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert "meta" in body

    data = body["data"]
    assert data["name"] == "AQG Studio Backend"
    assert data["version"] == "0.1.0"
    assert data["api_version"] == "v1"
    assert data["status"] == "operational"

    meta = body["meta"]
    assert "timestamp" in meta
    assert "request_id" in meta
