"""Standardized application exception classes and error response schemas."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.core.logging import correlation_id_ctx


# ------------------------------------------------------------------------------
# Pydantic Error Response Schemas
# ------------------------------------------------------------------------------
class ErrorDetail(BaseModel):
    """Detailed error issue structure."""
    field: str | None = None
    issue: str


class ErrorPayload(BaseModel):
    """Error payload containing code, message, and issues."""
    code: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class MetaPayload(BaseModel):
    """Metadata envelope with timestamp and request correlation ID."""
    timestamp: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat()
    )
    request_id: str | None = Field(
        default_factory=lambda: correlation_id_ctx.get()
    )


class ErrorResponse(BaseModel):
    """Canonical error response envelope."""
    success: bool = False
    error: ErrorPayload
    meta: MetaPayload = Field(default_factory=MetaPayload)


# ------------------------------------------------------------------------------
# Custom Exception Hierarchy
# ------------------------------------------------------------------------------
class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = 500,
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class NotFoundException(AppException):
    """Resource not found exception (404)."""

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        code: str = "RESOURCE_NOT_FOUND",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=404, details=details)


class ValidationException(AppException):
    """Input or payload validation exception (422)."""

    def __init__(
        self,
        message: str = "The provided data failed validation checks.",
        code: str = "VALIDATION_ERROR",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=422, details=details)


class UnauthorizedException(AppException):
    """Authentication required or failed exception (401)."""

    def __init__(
        self,
        message: str = "Authentication credentials are required or invalid.",
        code: str = "UNAUTHORIZED",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=401, details=details)


class ForbiddenException(AppException):
    """Permission denied exception (403)."""

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        code: str = "FORBIDDEN",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=403, details=details)


class ConflictException(AppException):
    """Resource conflict exception (409)."""

    def __init__(
        self,
        message: str = "The request conflicts with existing state.",
        code: str = "CONFLICT",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=409, details=details)


class RateLimitException(AppException):
    """Rate limit exceeded exception (429)."""

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        code: str = "RATE_LIMIT_EXCEEDED",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=429, details=details)


class ServiceUnavailableException(AppException):
    """Service or dependency unavailable exception (503)."""

    def __init__(
        self,
        message: str = "The service is temporarily unavailable.",
        code: str = "SERVICE_UNAVAILABLE",
        details: list[ErrorDetail] | None = None,
    ) -> None:
        super().__init__(message=message, code=code, status_code=503, details=details)
