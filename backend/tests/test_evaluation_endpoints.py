"""Unit and endpoint tests for Assessment Evaluation and Question Refinement endpoints."""

import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.db.session import get_db
from app.evaluation.schemas import (
    AssessmentEvaluationSummary,
)
from app.main import app
from app.models.entities import (
    Evaluation,
    Question,
)

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


def test_evaluate_assessment_unauthenticated_returns_401() -> None:
    """Verify POST /api/v1/assessments/{id}/evaluate returns 401 without auth."""
    res = client.post(f"/api/v1/assessments/{uuid.uuid4()}/evaluate")
    assert res.status_code == 401


def test_evaluate_assessment_endpoint_success() -> None:
    """Verify POST /api/v1/assessments/{id}/evaluate triggers evaluation pipeline successfully."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_summary = AssessmentEvaluationSummary(
        assessment_id=assessment_id,
        total_questions=1,
        accepted_count=1,
        refined_count=0,
        regenerated_count=0,
        failed_count=0,
        average_quality_score=0.92,
        status="ready",
        questions=[],
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.v1.endpoints.assessments.evaluation_agent.evaluate_and_refine_assessment",
        new=AsyncMock(return_value=mock_summary),
    ):
        res = client.post(f"/api/v1/assessments/{assessment_id}/evaluate", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["assessment_id"] == str(assessment_id)
    assert data["data"]["accepted_count"] == 1


def test_evaluate_single_question_endpoint_success() -> None:
    """Verify POST /api/v1/questions/{id}/evaluate evaluates single question."""
    user_id = uuid.uuid4()
    question_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_q = Question(
        id=question_id,
        assessment_id=uuid.uuid4(),
        blueprint_id=uuid.uuid4(),
        user_id=user_id,
        question_type="short_answer",
        question_text="What is cell division?",
        correct_answer="Mitosis",
        explanation="Mitosis divides cells.",
        difficulty="easy",
        bloom_level="remember",
        source_chunk_ids=[uuid.uuid4()],
        source_pages=[1],
        status="draft",
        version=1,
        generation_attempts=1,
        created_at=datetime.now(UTC),
    )

    mock_eval = Evaluation(
        id=uuid.uuid4(),
        question_id=question_id,
        user_id=user_id,
        overall_quality_score=Decimal("0.90"),
        decision="ACCEPT",
        feedback={"strengths": ["Clear definition"]},
        created_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with (
        patch(
            "app.api.v1.endpoints.questions.question_repo.get_by_id",
            new=AsyncMock(return_value=mock_q),
        ),
        patch(
            "app.api.v1.endpoints.questions.blueprint_repo.get_by_id",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.api.v1.endpoints.questions.evaluation_agent.evaluate_single_question",
            new=AsyncMock(return_value=(mock_eval, MagicMock())),
        ),
    ):
        res = client.post(f"/api/v1/questions/{question_id}/evaluate", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["decision"] == "ACCEPT"


def test_refine_question_endpoint_success() -> None:
    """Verify POST /api/v1/questions/{id}/refine refines and re-evaluates single question."""
    user_id = uuid.uuid4()
    question_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_q = Question(
        id=question_id,
        assessment_id=uuid.uuid4(),
        blueprint_id=uuid.uuid4(),
        user_id=user_id,
        question_type="short_answer",
        question_text="What is cellular division?",
        options=None,
        correct_answer="Mitosis",
        explanation="Explanation",
        difficulty="easy",
        bloom_level="remember",
        source_chunk_ids=[uuid.uuid4()],
        source_pages=[1],
        supporting_evidence={},
        status="approved",
        version=2,
        generation_attempts=2,
        quality_score=Decimal("0.92"),
        created_at=datetime.now(UTC),
    )

    mock_eval = Evaluation(
        id=uuid.uuid4(),
        question_id=question_id,
        user_id=user_id,
        overall_quality_score=Decimal("0.92"),
        decision="ACCEPT",
        feedback={},
        created_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    payload = {
        "target_issues": ["Improve stem clarity"],
        "custom_instructions": "Make it suitable for high school students",
    }

    with (
        patch(
            "app.api.v1.endpoints.questions.question_repo.get_by_id",
            new=AsyncMock(return_value=mock_q),
        ),
        patch(
            "app.api.v1.endpoints.questions.blueprint_repo.get_by_id",
            new=AsyncMock(return_value=None),
        ),
        patch(
            "app.api.v1.endpoints.questions.evaluation_agent.refine_single_question",
            new=AsyncMock(return_value=(mock_q, mock_eval)),
        ),
        patch(
            "app.api.v1.endpoints.questions.evaluation_repo.list_by_question",
            new=AsyncMock(return_value=[mock_eval]),
        ),
    ):
        res = client.post(
            f"/api/v1/questions/{question_id}/refine",
            json=payload,
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["version"] == 2


def test_list_question_evaluations_endpoint() -> None:
    """Verify GET /api/v1/questions/{id}/evaluations retrieves evaluation history."""
    user_id = uuid.uuid4()
    question_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_q = Question(
        id=question_id,
        assessment_id=uuid.uuid4(),
        user_id=user_id,
        question_type="short_answer",
        question_text="Sample question",
        correct_answer="Ans",
        explanation="Exp",
        difficulty="easy",
        bloom_level="remember",
        created_at=datetime.now(UTC),
    )

    eval1 = Evaluation(
        id=uuid.uuid4(),
        question_id=question_id,
        user_id=user_id,
        overall_quality_score=Decimal("0.70"),
        decision="REFINE",
        feedback={"issues": ["Ambiguous stem"]},
        created_at=datetime.now(UTC),
    )
    eval2 = Evaluation(
        id=uuid.uuid4(),
        question_id=question_id,
        user_id=user_id,
        overall_quality_score=Decimal("0.95"),
        decision="ACCEPT",
        feedback={"strengths": ["Crisp and clear"]},
        created_at=datetime.now(UTC),
    )

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with (
        patch(
            "app.api.v1.endpoints.questions.question_repo.get_by_id",
            new=AsyncMock(return_value=mock_q),
        ),
        patch(
            "app.api.v1.endpoints.questions.evaluation_repo.list_by_question",
            new=AsyncMock(return_value=[eval2, eval1]),
        ),
    ):
        res = client.get(f"/api/v1/questions/{question_id}/evaluations", headers=headers)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["data"]) == 2
    assert data["data"][0]["decision"] == "ACCEPT"
    assert data["data"][1]["decision"] == "REFINE"


def test_cross_user_isolation_returns_404() -> None:
    """Verify requesting another user's question evaluation returns 404."""
    user_id = uuid.uuid4()
    other_user_question_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_db = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    with patch(
        "app.api.v1.endpoints.questions.question_repo.get_by_id",
        new=AsyncMock(return_value=None),  # Scoped query returns None for wrong user
    ):
        res = client.get(
            f"/api/v1/questions/{other_user_question_id}/evaluations",
            headers=headers,
        )

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "QUESTION_NOT_FOUND"
