"""Main FastAPI application entrypoint for AQG Studio."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.api.v1.router import api_v1_router
from app.core.config import get_settings
from app.core.errors import AppException, ErrorDetail, ErrorPayload, ErrorResponse, MetaPayload
from app.core.logging import correlation_id_ctx, get_logger, setup_logging
from app.core.quota import burst_rate_limiter
from app.db.session import check_db_health, get_engine
from app.orchestration.runner import job_runner
from app.schemas.common import HealthLiveResponse, HealthReadyResponse

settings = get_settings()
setup_logging(
    log_level=settings.LOG_LEVEL,
    json_format=(settings.LOG_FORMAT == "json" if settings.LOG_FORMAT != "auto" else None),
    environment=settings.ENVIRONMENT,
)
logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown routines."""
    logger.info(
        f"Starting AQG Studio Backend (v: {settings.APP_VERSION}, env: {settings.ENVIRONMENT})"
    )
    db_engine = get_engine()
    if db_engine:
        logger.info("Database engine initialized.")
        await job_runner.start()
    else:
        logger.info("Database URL not configured; running in standalone mode.")

    yield

    if db_engine:
        logger.info("Stopping job runner and disposing database engine connection pool...")
        await job_runner.stop()
        await db_engine.dispose()
    logger.info("AQG Studio Backend shutdown complete.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Multi-Agent Automated Question-Generation Backend Service",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)


def _create_error_response(
    code: str,
    message: str,
    status_code: int,
    details: list[Any] | None = None,
    correlation_id: str | None = None,
) -> JSONResponse:
    """Helper to produce consistent error JSONResponse."""
    req_id = correlation_id or correlation_id_ctx.get()
    parsed_details: list[ErrorDetail] = []
    if details:
        for d in details:
            if isinstance(d, ErrorDetail):
                parsed_details.append(d)
            elif isinstance(d, dict):
                parsed_details.append(
                    ErrorDetail(field=d.get("field"), issue=str(d.get("issue", d)))
                )
            else:
                parsed_details.append(ErrorDetail(field=None, issue=str(d)))

    error_payload = ErrorPayload(code=code, message=message, details=parsed_details)
    meta = MetaPayload(
        timestamp=datetime.now(UTC).isoformat(),
        request_id=req_id,
    )
    envelope = ErrorResponse(success=False, error=error_payload, meta=meta)
    return JSONResponse(status_code=status_code, content=envelope.model_dump())


# ------------------------------------------------------------------------------
# Correlation ID & Global Exception Middleware
# ------------------------------------------------------------------------------
class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware extracting or generating request correlation ID and catching unhandled errors."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        req_id = (
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or f"req_{uuid.uuid4().hex[:16]}"
        )
        token = correlation_id_ctx.set(req_id)
        request.state.correlation_id = req_id

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.exception(f"Unhandled exception during request processing: {exc}")
            response = _create_error_response(
                code="INTERNAL_SERVER_ERROR",
                message="An unexpected internal server error occurred.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                correlation_id=req_id,
            )
        finally:
            correlation_id_ctx.reset(token)

        response.headers["X-Correlation-ID"] = req_id
        return response


# ------------------------------------------------------------------------------
# Security Headers & Rate Limiting Middlewares
# ------------------------------------------------------------------------------
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware injecting OWASP-recommended security headers."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none';"

        if settings.ENVIRONMENT.lower() in ("production", "staging"):
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response


class BurstRateLimiterMiddleware(BaseHTTPMiddleware):
    """Middleware applying in-memory burst rate limiting per client identifier."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Exempt health probes from rate limiting
        if request.url.path in ("/health/live", "/health/ready"):
            return await call_next(request)

        # Derive client identifier from Authorization Bearer hash or client IP
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            client_key = f"auth_{auth_header[-16:]}"
        else:
            forwarded = request.headers.get("X-Forwarded-For")
            client_ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "anonymous")
            client_key = f"ip_{client_ip}"

        allowed, retry_after, remaining = burst_rate_limiter.is_allowed(client_key)
        if not allowed:
            req_id = getattr(request.state, "correlation_id", None)
            resp = _create_error_response(
                code="RATE_LIMIT_EXCEEDED",
                message=f"Too many requests. Please slow down and try again in {retry_after} seconds.",
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                details=[{"retry_after_seconds": retry_after}],
                correlation_id=req_id,
            )
            resp.headers["Retry-After"] = str(retry_after)
            return resp

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(settings.BURST_RATE_LIMIT_PER_MINUTE)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(BurstRateLimiterMiddleware)

# ------------------------------------------------------------------------------
# CORS Middleware (Configured Strictly from Environment)
# ------------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID", "X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)


# ------------------------------------------------------------------------------
# Standardized Error Exception Handlers
# ------------------------------------------------------------------------------
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    logger.warning(
        f"AppException: {exc.code} - {exc.message} (status: {exc.status_code})"
    )
    return _create_error_response(
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation errors."""
    details: list[ErrorDetail] = []
    for err in exc.errors():
        loc_str = " -> ".join([str(loc) for loc in err.get("loc", [])])
        details.append(ErrorDetail(field=loc_str, issue=err.get("msg", "Invalid input")))

    logger.info(f"Validation error on {request.method} {request.url.path}: {details}")
    return _create_error_response(
        code="VALIDATION_ERROR",
        message="Request payload or parameters failed validation.",
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        details=details,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle standard HTTP exceptions."""
    code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else "HTTP_ERROR"
    return _create_error_response(
        code=code,
        message=str(exc.detail),
        status_code=exc.status_code,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all unhandled exception handler."""
    logger.exception(f"Unhandled server exception: {exc}")
    return _create_error_response(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected internal server error occurred.",
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        correlation_id=getattr(request.state, "correlation_id", None),
    )


# ------------------------------------------------------------------------------
# Health Endpoints
# ------------------------------------------------------------------------------
@app.get(
    "/health/live",
    response_model=HealthLiveResponse,
    tags=["Health"],
    summary="Liveness check",
    description="Returns 200 OK if FastAPI process is alive.",
)
async def health_live() -> HealthLiveResponse:
    """Liveness probe."""
    return HealthLiveResponse(status="ok")


@app.get(
    "/health/ready",
    response_model=HealthReadyResponse,
    tags=["Health"],
    summary="Readiness check",
    description="Returns readiness state including database reachability.",
)
async def health_ready() -> HealthReadyResponse:
    """Readiness probe."""
    db_healthy = await check_db_health()
    if db_healthy:
        db_status = "connected"
    elif settings.DATABASE_URL is None:
        db_status = "not_configured"
    else:
        db_status = "disconnected"

    return HealthReadyResponse(
        status="ready",
        database=db_status,
        environment=settings.ENVIRONMENT,
    )


# ------------------------------------------------------------------------------
# Mount API v1 Router
# ------------------------------------------------------------------------------
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
