"""Tests for multi-tenant cross-user access rejection across repositories and storage."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.selectable import Select

from app.models.entities import Profile
from app.repositories.assessment import assessment_repo
from app.repositories.chunk import chunk_repo
from app.repositories.document import document_repo
from app.repositories.objective import objective_repo
from app.repositories.profile import profile_repo
from app.repositories.question import question_repo
from app.services.storage import validate_storage_path


@pytest.mark.asyncio
async def test_cross_user_document_read_rejected() -> None:
    """Verify User B cannot read User A's document."""
    user_b = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_session = AsyncMock()
    # When query executed with user_b, database returns None
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    res = await document_repo.get_by_id(mock_session, id=doc_id, user_id=user_b)
    assert res is None

    stmt = mock_session.execute.call_args[0][0]
    assert isinstance(stmt, Select)
    compiled = str(stmt.compile())
    assert "documents.user_id =" in compiled
    assert "documents.id =" in compiled


@pytest.mark.asyncio
async def test_cross_user_document_update_rejected() -> None:
    """Verify User B cannot update User A's document."""
    user_b = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_session = AsyncMock()
    # get_by_id returns None for User B
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    updated = await document_repo.update(
        mock_session,
        id=doc_id,
        user_id=user_b,
        obj_in={"original_filename": "hijacked.pdf"},
    )
    assert updated is None
    # No flush should be called for non-existent/unowned record
    assert not mock_session.flush.called


@pytest.mark.asyncio
async def test_cross_user_document_delete_rejected() -> None:
    """Verify User B cannot delete User A's document."""
    user_b = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 0
    mock_session.execute.return_value = mock_result

    deleted = await document_repo.delete(mock_session, id=doc_id, user_id=user_b)
    assert deleted is False

    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "documents.user_id =" in compiled
    assert "documents.id =" in compiled


@pytest.mark.asyncio
async def test_cross_user_assessment_relations_rejected() -> None:
    """Verify User B cannot fetch User A's assessment with relations."""
    user_b = uuid.uuid4()
    assessment_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    res = await assessment_repo.get_with_relations(
        mock_session, id=assessment_id, user_id=user_b
    )
    assert res is None

    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "assessments.user_id =" in compiled
    assert "assessments.id =" in compiled


@pytest.mark.asyncio
async def test_cross_user_chunks_list_isolated() -> None:
    """Verify chunk listing strictly enforces user_id filter."""
    user_b = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    chunks = await chunk_repo.list_by_document(
        mock_session, document_id=doc_id, user_id=user_b
    )
    assert len(chunks) == 0

    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "document_chunks.user_id =" in compiled
    assert "document_chunks.document_id =" in compiled


@pytest.mark.asyncio
async def test_cross_user_questions_list_isolated() -> None:
    """Verify questions listing strictly enforces user_id filter."""
    user_b = uuid.uuid4()
    assessment_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    questions = await question_repo.list_by_assessment(
        mock_session, assessment_id=assessment_id, user_id=user_b
    )
    assert len(questions) == 0

    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "questions.user_id =" in compiled
    assert "questions.assessment_id =" in compiled


@pytest.mark.asyncio
async def test_cross_user_learning_objectives_list_isolated() -> None:
    """Verify learning objectives listing strictly enforces user_id filter."""
    user_b = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    objs = await objective_repo.list_by_document(
        mock_session, document_id=doc_id, user_id=user_b
    )
    assert len(objs) == 0

    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "learning_objectives.user_id =" in compiled
    assert "learning_objectives.document_id =" in compiled


@pytest.mark.asyncio
async def test_cross_user_profile_access_isolated() -> None:
    """Verify profile lookup strictly uses target user_id."""
    user_b = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Profile(
        id=user_b, display_name="User B"
    )
    mock_session.execute.return_value = mock_result

    profile = await profile_repo.get_by_id(mock_session, user_id=user_b)
    assert profile is not None
    assert profile.id == user_b

    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "profiles.id =" in compiled


def test_cross_user_storage_path_rejected() -> None:
    """Verify storage path validation rejects any cross-user path prefix."""
    user_a = uuid.uuid4()
    user_b = uuid.uuid4()

    user_a_path = f"{user_a}/document_99/confidential.pdf"
    assert validate_storage_path(user_a_path, user_b) is False
    assert validate_storage_path(user_a_path, user_a) is True


def test_storage_path_handles_case_insensitive_uuids() -> None:
    """Verify storage path validates uppercase UUID representations correctly."""
    user_id = uuid.uuid4()
    upper_path = f"{str(user_id).upper()}/doc_123/file.pdf"
    assert validate_storage_path(upper_path, user_id) is True
