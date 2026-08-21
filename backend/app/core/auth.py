"""Authentication and JWT verification dependency for Supabase Auth tokens."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, cast

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedException

logger = logging.getLogger("aqg.auth")

http_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class CurrentUser:
    """Authenticated user context extracted from verified JWT."""

    user_id: uuid.UUID
    email: str | None = None
    role: str = "authenticated"
    app_metadata: dict[str, Any] = field(default_factory=dict)
    user_metadata: dict[str, Any] = field(default_factory=dict)
    raw_claims: dict[str, Any] = field(default_factory=dict)


def _get_jwt_secret(settings: Settings) -> str:
    """Retrieve configured JWT verification secret or safe testing fallback."""
    if settings.SUPABASE_JWT_SECRET:
        return settings.SUPABASE_JWT_SECRET
    if settings.ENVIRONMENT in ("development", "test"):
        # Development fallback secret for offline testing
        return "dev-insecure-supabase-jwt-secret-for-offline-testing-32bytes!"
    raise UnauthorizedException(
        message="JWT secret is not configured on the server.",
        code="AUTH_CONFIG_ERROR",
    )


def verify_supabase_jwt(token: str, settings: Settings) -> dict[str, Any]:
    """Verify Supabase JWT signature, expiration, audience, and structure."""
    if not token or not token.strip():
        raise UnauthorizedException(
            message="Authentication token is missing or empty.",
            code="TOKEN_MISSING",
        )

    # Normalize token in case of redundant prefix
    clean_token = token.removeprefix("Bearer ").removeprefix("bearer ").strip()
    if not clean_token:
        raise UnauthorizedException(
            message="Authentication token is missing or empty.",
            code="TOKEN_MISSING",
        )

    secret = _get_jwt_secret(settings)
    algorithms = [settings.JWT_ALGORITHM, "HS256"]

    try:
        # Decode and strictly verify signature and expiration
        decoded = jwt.decode(
            clean_token,
            secret,
            algorithms=algorithms,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": False,  # Custom strict verification below
            },
        )
        payload = cast(dict[str, Any], decoded)
    except jwt.ExpiredSignatureError as e:
        logger.warning("Supabase JWT expired: %s", str(e))
        raise UnauthorizedException(
            message="Authentication token has expired. Please sign in again.",
            code="TOKEN_EXPIRED",
        ) from e
    except JWTError as e:
        logger.warning("Supabase JWT validation failed: %s", str(e))
        raise UnauthorizedException(
            message="Invalid or malformed authentication token signature.",
            code="TOKEN_INVALID",
        ) from e

    # Verify audience claims strictly
    aud = payload.get("aud")
    if not aud:
        raise UnauthorizedException(
            message="Token is missing required audience claim (aud).",
            code="TOKEN_MISSING_AUDIENCE",
        )

    valid_audiences = {"authenticated", "anon"}
    if isinstance(aud, str) and aud not in valid_audiences:
        raise UnauthorizedException(
            message=f"Invalid token audience '{aud}'.",
            code="TOKEN_INVALID_AUDIENCE",
        )
    elif isinstance(aud, list) and not any(a in valid_audiences for a in aud):
        raise UnauthorizedException(
            message="Invalid token audience list.",
            code="TOKEN_INVALID_AUDIENCE",
        )

    # Validate subject (User UUID)
    sub = payload.get("sub")
    if not sub:
        raise UnauthorizedException(
            message="Token is missing required subject claim (user ID).",
            code="TOKEN_MISSING_SUB",
        )

    try:
        uuid.UUID(str(sub))
    except ValueError as e:
        raise UnauthorizedException(
            message="Token subject claim is not a valid UUID.",
            code="TOKEN_INVALID_SUB",
        ) from e

    return payload


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser:
    """FastAPI dependency that extracts, verifies, and returns the CurrentUser."""
    if not credentials or not credentials.credentials:
        raise UnauthorizedException(
            message="Bearer authentication token is required to access this endpoint.",
            code="AUTHENTICATION_REQUIRED",
        )

    token = credentials.credentials
    claims = verify_supabase_jwt(token, settings)

    user_id = uuid.UUID(str(claims["sub"]))
    email = claims.get("email")
    role = claims.get("role", "authenticated")
    app_metadata = claims.get("app_metadata", {})
    user_metadata = claims.get("user_metadata", {})

    current_user = CurrentUser(
        user_id=user_id,
        email=email,
        role=role,
        app_metadata=app_metadata,
        user_metadata=user_metadata,
        raw_claims=claims,
    )

    # Attach to request state for downstream middlewares / logging
    request.state.current_user = current_user
    return current_user


async def get_optional_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(http_bearer),
    settings: Settings = Depends(get_settings),
) -> CurrentUser | None:
    """Optional authentication dependency for endpoints that allow guest access."""
    if not credentials or not credentials.credentials:
        return None

    try:
        return await get_current_user(request, credentials, settings)
    except UnauthorizedException:
        return None
