"""Common generic Pydantic response models and schemas."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.core.errors import ErrorPayload, MetaPayload

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standard success envelope matching API contract."""
    success: bool = True
    data: T
    meta: MetaPayload = Field(default_factory=MetaPayload)


class HealthLiveResponse(BaseModel):
    """Liveness probe response."""
    status: str = "ok"


class HealthReadyResponse(BaseModel):
    """Readiness probe response."""
    status: str = "ready"
    database: str = "connected"
    environment: str = "development"


class VersionData(BaseModel):
    """Version payload model."""
    name: str
    version: str
    api_version: str
    environment: str
    status: str = "operational"


class VersionResponse(SuccessResponse[VersionData]):
    """Version endpoint response wrapper."""
    pass


__all__ = [
    "ErrorPayload",
    "HealthLiveResponse",
    "HealthReadyResponse",
    "MetaPayload",
    "SuccessResponse",
    "VersionData",
    "VersionResponse",
]
