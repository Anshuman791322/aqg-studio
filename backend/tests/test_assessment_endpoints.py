"""Unit and endpoint tests for Assessment and Question Blueprint API endpoints."""

import time
import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.db.session import get_db
from app.main import app
from app.models.entities import (
    Assessment,
    Concept,
    Document,
    QuestionBlueprint,
    Topic,
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


def test_create_assessment_unauthenticated_returns_401() -> None:
    """Verify POST /api/v1/assessments returns 401 when missing auth header."""
    payload = {
        "document_id": str(uuid.uuid4()),
        "name": "Unauthorized Assessment",
        "total_questions": 10,
    }
    response = client.post("/api/v1/assessments", json=payload)
    assert response.status_code == 401


def test_create_assessment_validation_failure_on_invalid_totals() -> None:
    """Verify POST /api/v1/assessments returns 422 on total_questions outside 1..50."""
    user_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    # total_questions = 0 (< 1)
    res_zero = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": str(uuid.uuid4()), "name": "Zero Quiz", "total_questions": 0},
    )
    assert res_zero.status_code == 422

    # total_questions = 100 (> 50)
    res_oversized = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={"document_id": str(uuid.uuid4()), "name": "Huge Quiz", "total_questions": 100},
    )
    assert res_oversized.status_code == 422


def test_create_assessment_validation_failure_on_invalid_distribution_keys() -> None:
    """Verify POST /api/v1/assessments returns 422 on unsupported distribution keys."""
    user_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    # Invalid question type key
    res_type = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "document_id": str(uuid.uuid4()),
            "name": "Bad Type",
            "question_type_distribution": {"invalid_type": 100},
        },
    )
    assert res_type.status_code == 422

    # Invalid difficulty key
    res_diff = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "document_id": str(uuid.uuid4()),
            "name": "Bad Diff",
            "difficulty_distribution": {"super_hard": 100},
        },
    )
    assert res_diff.status_code == 422

    # Invalid bloom key
    res_bloom = client.post(
        "/api/v1/assessments",
        headers=headers,
        json={
            "document_id": str(uuid.uuid4()),
            "name": "Bad Bloom",
            "bloom_distribution": {"guess": 100},
        },
    )
    assert res_bloom.status_code == 422



def test_create_assessment_endpoint_success() -> None:
    """Verify POST /api/v1/assessments creates assessment and returns blueprint design."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="calculus.pdf",
        storage_path=f"{user_id}/{doc_id}/calculus.pdf",
        mime_type="application/pdf",
        size_bytes=4096,
    )

    mock_topic = Topic(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        name="Derivatives",
        description="Rates of change.",
        importance_score=Decimal("0.9"),
        metadata_={"source_chunk_ids": [str(chunk_id)]},
    )
    mock_topic.concepts = [
        Concept(
            id=uuid.uuid4(),
            topic_id=mock_topic.id,
            document_id=doc_id,
            user_id=user_id,
            name="Chain Rule",
            definition="Derivative of composite functions.",
            difficulty="medium",
            metadata_={"source_chunk_ids": [str(chunk_id)]},
        )
    ]

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = mock_doc

    topics_res = MagicMock()
    topics_res.scalars.return_value.all.return_value = [mock_topic]

    objs_res = MagicMock()
    objs_res.scalars.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        doc_res,
        topics_res,
        objs_res,
    ]

    async def override_get_db():
        return mock_session

    app.dependency_overrides[get_db] = override_get_db

    payload = {
        "document_id": str(doc_id),
        "name": "Calculus Quiz 1",
        "total_questions": 3,
        "question_type_distribution": {"mcq": 100},
        "difficulty_distribution": {"medium": 100},
        "bloom_distribution": {"apply": 100},
    }

    response = client.post("/api/v1/assessments", headers=headers, json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["name"] == "Calculus Quiz 1"
    assert body["data"]["total_questions"] == 3
    assert len(body["data"]["blueprints"]) == 3
    assert body["data"]["blueprints"][0]["question_type"] == "mcq_single"


def test_list_and_get_assessment_endpoints() -> None:
    """Verify GET /api/v1/assessments and GET /api/v1/assessments/{id}."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=doc_id,
        name="Midterm Exam",
        configuration={"total_questions": 5},
        status="draft",
        progress=Decimal("0.00"),
        metrics={},
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def override_get_db():
        return mock_session

    app.dependency_overrides[get_db] = override_get_db

    # 1. Test List
    with patch(
        "app.repositories.assessment.assessment_repo.list_all",
        AsyncMock(return_value=[mock_assessment]),
    ):
        res_list = client.get("/api/v1/assessments", headers=headers)
        assert res_list.status_code == 200
        assert len(res_list.json()["data"]) == 1
        assert res_list.json()["data"][0]["name"] == "Midterm Exam"

    # 2. Test Get Single
    with patch(
        "app.repositories.assessment.assessment_repo.get_by_id",
        AsyncMock(return_value=mock_assessment),
    ):
        res_get = client.get(f"/api/v1/assessments/{assessment_id}", headers=headers)
        assert res_get.status_code == 200
        assert res_get.json()["data"]["id"] == str(assessment_id)


def test_get_blueprint_and_delete_assessment() -> None:
    """Verify GET /api/v1/assessments/{id}/blueprint and DELETE /api/v1/assessments/{id}."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    headers = create_test_auth_headers(user_id)

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=doc_id,
        name="Physics Test",
        configuration={"total_questions": 1},
        status="draft",
        progress=Decimal("0.00"),
        metrics={},
    )

    mock_bp = QuestionBlueprint(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        topic_id=uuid.uuid4(),
        concept_id=None,
        question_type="mcq_single",
        difficulty="easy",
        bloom_level="remember",
        learning_objective="Recall Newton's First Law.",
        source_chunk_ids=[uuid.uuid4()],
        status="planned",
        sequence_number=1,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def override_get_db():
        return mock_session

    app.dependency_overrides[get_db] = override_get_db

    # 1. Test Get Blueprint
    with (
        patch(
            "app.repositories.assessment.assessment_repo.get_by_id",
            AsyncMock(return_value=mock_assessment),
        ),
        patch(
            "app.repositories.blueprint.blueprint_repo.list_by_assessment",
            AsyncMock(return_value=[mock_bp]),
        ),
    ):
        res_bp = client.get(f"/api/v1/assessments/{assessment_id}/blueprint", headers=headers)
        assert res_bp.status_code == 200
        assert len(res_bp.json()["data"]["blueprints"]) == 1
        assert (
            res_bp.json()["data"]["blueprints"][0]["learning_objective"]
            == "Recall Newton's First Law."
        )

    # 2. Test Delete
    with patch(
        "app.repositories.assessment.assessment_repo.delete",
        AsyncMock(return_value=True),
    ):
        res_del = client.delete(f"/api/v1/assessments/{assessment_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.json()["data"]["deleted"] is True
