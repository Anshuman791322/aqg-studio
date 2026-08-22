"""Endpoint integration tests for Assessment Exports and Quality Reports."""

import time
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.db.session import get_db
from app.main import app
from app.models.entities import Assessment, Export, Question
from app.reporting.schemas import AssessmentReportResponse, PedagogicalQualityMetrics

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
            "email": "educator@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


def test_exports_unauthenticated_returns_401():
    """Verify that unauthenticated requests to export endpoints are rejected with 401."""
    res1 = client.post(f"/api/v1/assessments/{uuid.uuid4()}/exports", json={"format": "pdf"})
    assert res1.status_code == 401

    res2 = client.get(f"/api/v1/assessments/{uuid.uuid4()}/exports")
    assert res2.status_code == 401

    res3 = client.get(f"/api/v1/exports/{uuid.uuid4()}/download")
    assert res3.status_code == 401

    res4 = client.get(f"/api/v1/assessments/{uuid.uuid4()}/report")
    assert res4.status_code == 401


def test_get_assessment_report_endpoint_success():
    """Verify GET /api/v1/assessments/{id}/report returns 200 with full metrics payload."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_report = AssessmentReportResponse(
        assessment_id=assessment_id,
        document_id=uuid.uuid4(),
        assessment_name="Genetics Midterm",
        document_filename="Genetics.pdf",
        status="ready",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        metrics=PedagogicalQualityMetrics(
            total_requested=1,
            total_generated=1,
            total_accepted=1,
            total_rejected=0,
            total_flagged=0,
            total_draft=0,
            approval_rate=100.0,
            average_overall_quality=0.98,
            average_groundedness=0.99,
            average_correctness=1.0,
            average_clarity=0.95,
            average_distractor_quality=0.92,
            number_refined=0,
            number_regenerated=0,
            duplicate_count=0,
            failed_blueprints=0,
        ),
        question_type_distribution={},
        difficulty_distribution={},
        bloom_distribution={},
        topic_coverage=[],
        available_exports=[],
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.v1.endpoints.assessments.output_report_agent.generate_assessment_report",
        new=AsyncMock(return_value=mock_report),
    ):
        res = client.get(f"/api/v1/assessments/{assessment_id}/report", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["assessment_name"] == "Genetics Midterm"
    assert data["data"]["metrics"]["total_accepted"] == 1


def test_create_assessment_export_endpoint_success():
    """Verify POST /api/v1/assessments/{id}/exports generates an export package."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=uuid.uuid4(),
        name="Genetics Assessment",
        status="ready",
    )
    mock_q = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="mcq_single",
        question_text="What is the ratio in a monohybrid cross?",
        options=[{"key": "A", "text": "3:1", "is_correct": True}],
        correct_answer="A",
        explanation="Ratio is 3:1",
        difficulty="easy",
        bloom_level="remember",
        status="approved",
    )

    with (
        patch("app.exports.service.assessment_repo.get_by_id", new=AsyncMock(return_value=mock_assessment)),
        patch("app.exports.service.question_repo.list_by_assessment", new=AsyncMock(return_value=[mock_q])),
    ):
        res = client.post(
            f"/api/v1/assessments/{assessment_id}/exports",
            json={"format": "pdf", "configuration": {"include_answers": True, "shuffle_questions": True}},
            headers=headers,
        )

    assert res.status_code == 201
    data = res.json()
    assert data["success"] is True
    assert data["data"]["format"] == "pdf"
    assert data["data"]["status"] == "completed"


def test_download_export_endpoint_success():
    """Verify GET /api/v1/exports/{id}/download serves export file bytes."""
    user_id = uuid.uuid4()
    export_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_export = Export(
        id=export_id,
        assessment_id=assessment_id,
        user_id=user_id,
        format="pdf",
        storage_path=f"{user_id}/{assessment_id}/{export_id}.pdf",
        status="completed",
    )

    fake_pdf_bytes = b"%PDF-1.4 test pdf content"

    with patch(
        "app.api.v1.endpoints.exports.export_service.get_download_info",
        new=AsyncMock(return_value=(mock_export, fake_pdf_bytes)),
    ):
        res = client.get(f"/api/v1/exports/{export_id}/download", headers=headers)

    assert res.status_code == 200
    assert res.headers["content-type"] == "application/pdf"
    assert res.content == fake_pdf_bytes


def test_delete_export_endpoint_success():
    """Verify DELETE /api/v1/exports/{id} purges the export."""
    user_id = uuid.uuid4()
    export_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.v1.endpoints.exports.export_service.delete_export",
        new=AsyncMock(return_value=True),
    ):
        res = client.delete(f"/api/v1/exports/{export_id}", headers=headers)

    assert res.status_code == 200
    assert res.json()["data"]["deleted"] is True


def test_cross_user_isolation_on_exports():
    """Verify that User B cannot download or delete User A's export package."""
    user_a = uuid.uuid4()
    export_id = uuid.uuid4()

    # User A headers
    headers_a = create_test_auth_headers(user_a)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.exports.service.export_repo.get_by_id",
        new=AsyncMock(return_value=None),  # Not found for user A
    ):
        dl_res = client.get(f"/api/v1/exports/{export_id}/download", headers=headers_a)
        assert dl_res.status_code == 404

        del_res = client.delete(f"/api/v1/exports/{export_id}", headers=headers_a)
        assert del_res.status_code == 404


def test_create_export_assessment_not_found():
    """Verify POST /api/v1/assessments/{id}/exports returns 404 when assessment does not exist."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch("app.exports.service.assessment_repo.get_by_id", new=AsyncMock(return_value=None)):
        res = client.post(
            f"/api/v1/assessments/{assessment_id}/exports",
            json={"format": "pdf"},
            headers=headers,
        )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "ASSESSMENT_NOT_FOUND"


def test_create_export_no_questions_returns_validation_error():
    """Verify POST /api/v1/assessments/{id}/exports returns 400/422 when assessment has no questions."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=uuid.uuid4(),
        name="Empty Assessment",
        status="draft",
    )

    with (
        patch("app.exports.service.assessment_repo.get_by_id", new=AsyncMock(return_value=mock_assessment)),
        patch("app.exports.service.question_repo.list_by_assessment", new=AsyncMock(return_value=[])),
    ):
        res = client.post(
            f"/api/v1/assessments/{assessment_id}/exports",
            json={"format": "pdf"},
            headers=headers,
        )

    assert res.status_code == 422
    assert res.json()["error"]["code"] == "NO_QUESTIONS_TO_EXPORT"

