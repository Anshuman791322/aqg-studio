"""Tests for standardized error handling and response shapes."""

import pytest
from fastapi import APIRouter
from httpx import AsyncClient

from app.core.errors import (
    ErrorDetail,
    ForbiddenException,
    NotFoundException,
    UnauthorizedException,
    ValidationException,
)
from app.main import app

# Register error trigger router (prefixed to avoid PytestCollectionWarning)
error_trigger_router = APIRouter(prefix="/test-errors", tags=["Testing"])


@error_trigger_router.get("/not-found")
async def trigger_not_found() -> None:
    raise NotFoundException(message="Item 42 does not exist.", code="ITEM_NOT_FOUND")


@error_trigger_router.get("/unauthorized")
async def trigger_unauthorized() -> None:
    raise UnauthorizedException(message="Invalid bearer token.")


@error_trigger_router.get("/forbidden")
async def trigger_forbidden() -> None:
    raise ForbiddenException(message="Access forbidden to this resource.")


@error_trigger_router.get("/custom-validation")
async def trigger_validation() -> None:
    raise ValidationException(
        message="Invalid payload structure.",
        details=[ErrorDetail(field="title", issue="Title cannot be blank.")],
    )


@error_trigger_router.get("/unhandled-crash")
async def trigger_crash() -> None:
    raise RuntimeError("Unexpected simulated database disconnect.")


app.include_router(error_trigger_router)


@pytest.mark.asyncio
async def test_404_unmatched_route(async_client: AsyncClient) -> None:
    """Verify 404 on unmatched route returns standard error envelope."""
    response = await async_client.get("/non-existent-route-99")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert "error" in body
    assert body["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert "meta" in body
    assert "timestamp" in body["meta"]
    assert "request_id" in body["meta"]


@pytest.mark.asyncio
async def test_custom_not_found_exception(async_client: AsyncClient) -> None:
    """Verify custom NotFoundException returns 404 with custom error code."""
    response = await async_client.get("/test-errors/not-found")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "ITEM_NOT_FOUND"
    assert body["error"]["message"] == "Item 42 does not exist."


@pytest.mark.asyncio
async def test_custom_validation_exception(async_client: AsyncClient) -> None:
    """Verify custom ValidationException returns 422 with structured field details."""
    response = await async_client.get("/test-errors/custom-validation")
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert len(body["error"]["details"]) == 1
    assert body["error"]["details"][0]["field"] == "title"
    assert body["error"]["details"][0]["issue"] == "Title cannot be blank."


@pytest.mark.asyncio
async def test_unauthorized_exception(async_client: AsyncClient) -> None:
    """Verify UnauthorizedException returns 401."""
    response = await async_client.get("/test-errors/unauthorized")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_forbidden_exception(async_client: AsyncClient) -> None:
    """Verify ForbiddenException returns 403."""
    response = await async_client.get("/test-errors/forbidden")
    assert response.status_code == 403
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_unhandled_crash_exception(async_client: AsyncClient) -> None:
    """Verify unhandled exception returns 500 without leaking stack traces."""
    response = await async_client.get("/test-errors/unhandled-crash")
    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INTERNAL_SERVER_ERROR"
    assert body["error"]["message"] == "An unexpected internal server error occurred."
