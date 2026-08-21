"""Unit and endpoint tests for Question Generation and Question listing API endpoints."""

import time
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.db.session import get_db
from app.main import app
from app.generation.schemas import AssessmentGenerationResult, QuestionResponseData
from app.models.entities import (
    Assessment,
    Question,
    QuestionBlueprint,
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


def test_generate_questions_unauthenticated_returns_401() -> None:
    """Verify POST /api/v1/assessments/{id}/generate returns 401 without auth header."""
    res = client.post(f"/api/v1/assessments/{uuid.uuid4()}/generate")
    assert res.status_code == 401


def test_generate_questions_endpoint_success() -> None:
    """Verify POST /api/v1/assessments/{id}/generate successfully triggers generation."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=doc_id,
        name="Genetics Quiz",
        configuration={"total_questions": 1},
        status="draft",
        progress=Decimal("0.00"),
        metrics={},
    )

    mock_bp = QuestionBlueprint(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        topic_id=None,
        concept_id=None,
        question_type="mcq_single",
        difficulty="easy",
        bloom_level="remember",
        learning_objective="Recall DNA base pairing.",
        source_chunk_ids=[chunk_id],
        status="planned",
        sequence_number=1,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # Mock assessment, blueprints, topics, concepts, chunks queries
    assessment_res = MagicMock()
    assessment_res.scalar_one_or_none.return_value = mock_assessment

    bp_res = MagicMock()
    bp_res.scalars.return_value.all.return_value = [mock_bp]

    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        assessment_res,
        bp_res,
        empty_res,  # topics
        empty_res,  # concepts
        empty_res,  # chunks
        bp_res,     # total blueprints check
        empty_res,  # existing questions
    ]

    async def override_get_db():
        return mock_session

    app.dependency_overrides[get_db] = override_get_db

    fake_res = AssessmentGenerationResult(
        assessment_id=assessment_id,
        total_blueprints=1,
        generated_questions=1,
        failed_blueprints=0,
        status="ready",
        questions=[
            QuestionResponseData(
                id=uuid.uuid4(),
                assessment_id=assessment_id,
                blueprint_id=mock_bp.id,
                question_type="mcq_single",
                question_text="Which base pairs with Adenine?",
                options=[{"key": "A", "text": "Thymine"}],
                correct_answer="A",
                explanation="Adenine pairs with Thymine.",
                difficulty="easy",
                bloom_level="remember",
            )
        ],
    )
    with patch(
        "app.api.v1.endpoints.assessments.generation_agent.generate_assessment_questions",
        AsyncMock(return_value=fake_res),
    ):
        res = client.post(
            f"/api/v1/assessments/{assessment_id}/generate",
            headers=headers,
        )

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["data"]["generated_questions"] == 1
    assert data["data"]["status"] == "ready"


def test_list_assessment_questions_and_get_single_question() -> None:
    """Verify GET /api/v1/assessments/{id}/questions and GET /api/v1/questions/{id}."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    question_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=uuid.uuid4(),
        name="Sample Assessment",
        status="ready",
    )

    mock_question = Question(
        id=question_id,
        assessment_id=assessment_id,
        user_id=user_id,
        blueprint_id=uuid.uuid4(),
        question_type="mcq_single",
        question_text="What is ATP?",
        options=[
            {"key": "A", "text": "Adenosine triphosphate"},
            {"key": "B", "text": "Amino acid"},
        ],
        correct_answer="A",
        explanation="ATP is the cellular energy currency.",
        topic="Biochemistry",
        difficulty="easy",
        bloom_level="remember",
        source_chunk_ids=[uuid.uuid4()],
        source_pages=[2],
        supporting_evidence={"verbatim_excerpt": "ATP powers cellular reactions."},
        status="draft",
        version=1,
    )

    mock_session = AsyncMock()

    async def override_get_db():
        return mock_session

    app.dependency_overrides[get_db] = override_get_db

    # 1. List questions
    with (
        patch("app.repositories.assessment.assessment_repo.get_by_id", AsyncMock(return_value=mock_assessment)),
        patch("app.repositories.question.question_repo.list_by_assessment", AsyncMock(return_value=[mock_question])),
    ):
        res_list = client.get(f"/api/v1/assessments/{assessment_id}/questions", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()["data"]) == 1
        assert res_list.json()["data"][0]["question_text"] == "What is ATP?"

    # 2. Get single question
    with patch("app.repositories.question.question_repo.get_by_id", AsyncMock(return_value=mock_question)):
        res_single = client.get(f"/api/v1/questions/{question_id}", headers=headers)
        assert res_single.status_code == 200
        assert res_single.json()["data"]["id"] == str(question_id)
        assert res_single.json()["data"]["correct_answer"] == "A"


def test_cross_user_isolation_on_questions() -> None:
    """Verify attacker cannot access another user's assessment questions."""
    attacker_user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(attacker_user_id)

    mock_session = AsyncMock()

    async def override_get_db():
        return mock_session

    app.dependency_overrides[get_db] = override_get_db

    # Assessment not found for attacker
    with patch("app.repositories.assessment.assessment_repo.get_by_id", AsyncMock(return_value=None)):
        res = client.get(f"/api/v1/assessments/{assessment_id}/questions", headers=headers)
        assert res.status_code == 404
