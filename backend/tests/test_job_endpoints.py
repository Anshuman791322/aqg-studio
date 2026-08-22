"""Unit and endpoint tests for background job queueing, status polling, and cancellation."""

import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.db.session import get_db
from app.main import app
from app.models.entities import Assessment, Job

client = TestClient(app)
TEST_SECRET = "dev-insecure-supabase-jwt-secret-for-offline-testing-32bytes!"


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Ensure clean dependency overrides for every test."""
    yield
    app.dependency_overrides.clear()


def create_test_auth_headers(user_id: uuid.UUID) -> dict[str, str]:
    """Create test JWT authorization header."""
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(user_id),
            "email": "researcher@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_document_process_unauthenticated_returns_401() -> None:
    """Verify POST /api/v1/documents/{id}/process returns 401 without auth."""
    res = client.post(f"/api/v1/documents/{uuid.uuid4()}/process")
    assert res.status_code == 401


def test_document_status_unauthenticated_returns_401() -> None:
    """Verify GET /api/v1/documents/{id}/status returns 401 without auth."""
    res = client.get(f"/api/v1/documents/{uuid.uuid4()}/status")
    assert res.status_code == 401


def test_assessment_generate_and_status_endpoints() -> None:
    """Verify POST /api/v1/assessments/{id}/generate and GET status work with background job runner."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    job_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_assessment = Assessment(
        id=assessment_id,
        document_id=uuid.uuid4(),
        user_id=user_id,
        name="Security Architecture Quiz",
        status="queued",
        progress=Decimal("0.00"),
        configuration={"total_questions": 5},
    )

    mock_job = Job(
        id=job_id,
        user_id=user_id,
        resource_type="assessment",
        resource_id=assessment_id,
        job_type="question_generation",
        status="queued",
        progress=Decimal("0.00"),
        current_step=None,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.api.v1.endpoints.assessments.assessment_repo.get_by_id", new_callable=AsyncMock) as mock_get_a,
        patch("app.api.v1.endpoints.assessments.question_repo.list_by_assessment", new_callable=AsyncMock) as mock_list_q,
        patch("app.api.v1.endpoints.assessments.job_runner.enqueue_job", new_callable=AsyncMock) as mock_enqueue,
        patch("app.api.v1.endpoints.assessments.job_repo.get_active_job", new_callable=AsyncMock) as mock_get_job,
    ):
        mock_get_a.return_value = mock_assessment
        mock_list_q.return_value = []
        mock_enqueue.return_value = mock_job
        mock_get_job.return_value = mock_job

        # 1. Enqueue generation job
        gen_res = client.post(f"/api/v1/assessments/{assessment_id}/generate", headers=headers)
        assert gen_res.status_code == 200
        gen_body = gen_res.json()
        assert gen_body["success"] is True
        assert gen_body["data"]["job_id"] == str(job_id)
        assert gen_body["data"]["status"] == "queued"
        assert gen_body["data"]["progress"] == 0.0

        # 2. Check status endpoint
        status_res = client.get(f"/api/v1/assessments/{assessment_id}/status", headers=headers)
        assert status_res.status_code == 200
        status_body = status_res.json()
        assert status_body["success"] is True
        assert status_body["data"]["job_id"] == str(job_id)
        assert status_body["data"]["target_questions"] == 5


def test_assessment_cancel_endpoint() -> None:
    """Verify POST /api/v1/assessments/{id}/cancel cancels active job."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    job_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_assessment = Assessment(
        id=assessment_id,
        document_id=uuid.uuid4(),
        user_id=user_id,
        name="Security Quiz",
        status="running",
        progress=Decimal("50.00"),
        configuration={"total_questions": 10},
    )

    mock_cancelled_job = Job(
        id=job_id,
        user_id=user_id,
        resource_type="assessment",
        resource_id=assessment_id,
        job_type="question_generation",
        status="cancelled",
        progress=Decimal("50.00"),
        current_step="evaluate_batches",
        error_code="USER_CANCELLED",
        error_message="Job was cancelled by the user.",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.api.v1.endpoints.assessments.assessment_repo.get_by_id", new_callable=AsyncMock) as mock_get_a,
        patch("app.api.v1.endpoints.assessments.question_repo.list_by_assessment", new_callable=AsyncMock) as mock_list_q,
        patch("app.api.v1.endpoints.assessments.job_runner.cancel_job", new_callable=AsyncMock) as mock_cancel,
    ):
        mock_get_a.return_value = mock_assessment
        mock_list_q.return_value = []
        mock_cancel.return_value = mock_cancelled_job

        cancel_res = client.post(f"/api/v1/assessments/{assessment_id}/cancel", headers=headers)
        assert cancel_res.status_code == 200
        cancel_body = cancel_res.json()
        assert cancel_body["success"] is True
        assert cancel_body["data"]["status"] == "cancelled"
        assert cancel_body["data"]["error_code"] == "USER_CANCELLED"


def test_cross_tenant_job_status_isolation() -> None:
    """Verify User B cannot view status for User A's document."""
    user_b = uuid.uuid4()
    doc_id = uuid.uuid4()
    headers_b = create_test_auth_headers(user_b)

    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.api.v1.endpoints.documents.document_repo.get_by_id", new_callable=AsyncMock) as mock_get_doc:
        # Document belongs to User A, so get_by_id with user_id=User B returns None
        mock_get_doc.return_value = None

        res = client.get(f"/api/v1/documents/{doc_id}/status", headers=headers_b)
        assert res.status_code == 404
        assert res.json()["error"]["code"] == "DOCUMENT_NOT_FOUND"
