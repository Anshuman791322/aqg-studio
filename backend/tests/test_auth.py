"""Comprehensive tests for JWT verification, session handling, and authorization boundaries."""

import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.auth import CurrentUser, verify_supabase_jwt
from app.core.config import get_settings
from app.main import app
from app.repositories.document import document_repo

client = TestClient(app)

TEST_SECRET = "dev-insecure-supabase-jwt-secret-for-offline-testing-32bytes!"
WRONG_SECRET = "completely-wrong-secret-used-for-invalid-signature-tests-32b"


def create_test_token(
    *,
    sub: str | None = None,
    email: str = "educator@example.com",
    role: str = "authenticated",
    aud: str | list[str] | None = "authenticated",
    exp_delta_seconds: int = 3600,
    secret: str = TEST_SECRET,
    algorithm: str = "HS256",
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Helper to construct and sign test JWT tokens."""
    now = int(time.time())
    user_id = sub if sub is not None else str(uuid.uuid4())

    claims: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "iat": now,
        "exp": now + exp_delta_seconds,
        "app_metadata": {"provider": "email"},
        "user_metadata": {"display_name": "Prof. Test"},
    }
    if aud is not None:
        claims["aud"] = aud
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(claims, secret, algorithm=algorithm)


def test_auth_me_missing_token_returns_401() -> None:
    """Verify endpoint rejects requests without Authorization header with 401."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401

    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert "token is required" in payload["error"]["message"].lower()


def test_auth_me_malformed_token_returns_401() -> None:
    """Verify endpoint rejects malformed tokens with 401."""
    headers = {"Authorization": "Bearer this_is_not_a_valid_jwt_token"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "TOKEN_INVALID"


def test_auth_me_expired_token_returns_401() -> None:
    """Verify endpoint rejects expired tokens with 401."""
    expired_token = create_test_token(exp_delta_seconds=-300)
    headers = {"Authorization": f"Bearer {expired_token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "TOKEN_EXPIRED"
    assert "expired" in payload["error"]["message"].lower()


def test_auth_me_invalid_signature_returns_401() -> None:
    """Verify endpoint rejects tokens signed with an untrusted secret."""
    tampered_token = create_test_token(secret=WRONG_SECRET)
    headers = {"Authorization": f"Bearer {tampered_token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "TOKEN_INVALID"


def test_auth_me_missing_audience_returns_401() -> None:
    """Verify endpoint rejects tokens missing the aud claim entirely."""
    no_aud_token = create_test_token(aud=None)
    headers = {"Authorization": f"Bearer {no_aud_token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "TOKEN_MISSING_AUDIENCE"


def test_auth_me_invalid_audience_returns_401() -> None:
    """Verify endpoint rejects tokens with invalid audience."""
    invalid_aud_token = create_test_token(aud="unauthorized_service")
    headers = {"Authorization": f"Bearer {invalid_aud_token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401

    payload = response.json()
    assert payload["success"] is False
    assert payload["error"]["code"] == "TOKEN_INVALID_AUDIENCE"


def test_auth_me_missing_sub_returns_401() -> None:
    """Verify endpoint rejects tokens missing the sub (user ID) claim."""
    now = int(time.time())
    token = jwt.encode(
        {"email": "test@example.com", "aud": "authenticated", "exp": now + 3600},
        TEST_SECRET,
        algorithm="HS256",
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_MISSING_SUB"


def test_auth_me_invalid_sub_uuid_returns_401() -> None:
    """Verify endpoint rejects tokens where sub is not a valid UUID."""
    token = create_test_token(sub="not-a-valid-uuid-12345")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TOKEN_INVALID_SUB"


def test_verify_supabase_jwt_handles_bearer_prefix_gracefully() -> None:
    """Verify verify_supabase_jwt strips leading Bearer prefix if present."""
    settings = get_settings()
    user_id = str(uuid.uuid4())
    token = create_test_token(sub=user_id)

    # Prefix with Bearer
    prefixed_token = f"Bearer {token}"
    claims = verify_supabase_jwt(prefixed_token, settings)
    assert claims["sub"] == user_id


def test_auth_me_valid_token_success() -> None:
    """Verify valid token returns 200 and matches user context."""
    user_id = str(uuid.uuid4())
    token = create_test_token(
        sub=user_id,
        email="instructor@school.edu",
        role="authenticated",
    )
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["data"]["user_id"] == user_id
    assert payload["data"]["email"] == "instructor@school.edu"
    assert payload["data"]["role"] == "authenticated"
    assert payload["data"]["display_name"] == "Prof. Test"
    assert "quota" in payload["data"]


def test_me_alias_endpoint_success() -> None:
    """Verify /api/v1/me alias returns identical user context."""
    user_id = str(uuid.uuid4())
    token = create_test_token(sub=user_id, email="dean@university.edu")
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/api/v1/me", headers=headers)
    assert response.status_code == 200
    assert response.json()["data"]["email"] == "dean@university.edu"


@pytest.mark.asyncio
async def test_body_user_id_tampering_overridden_by_authenticated_user() -> None:
    """Verify that supplied body user_id cannot override authenticated user identity."""
    actual_user = CurrentUser(user_id=uuid.uuid4(), email="victim@uni.edu")
    attacker_user_id = uuid.uuid4()

    # Payload where attacker maliciously injects a forged user_id in body
    untrusted_payload = {
        "user_id": attacker_user_id,
        "original_filename": "final_exam.pdf",
        "storage_path": f"{attacker_user_id}/final_exam.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 1000,
    }

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    created = await document_repo.create(
        mock_session,
        obj_in=untrusted_payload,
        user_id=actual_user.user_id,
    )

    # Repository forces actual_user.user_id regardless of untrusted payload
    assert created.user_id == actual_user.user_id
    assert created.user_id != attacker_user_id
