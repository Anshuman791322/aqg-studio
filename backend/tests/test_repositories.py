"""Tests for repository interfaces and multi-tenant user scoping."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.sql.selectable import Select

from app.models.entities import Document, Job
from app.repositories.base import BaseRepository
from app.repositories.chunk import chunk_repo
from app.repositories.document import document_repo
from app.repositories.job import job_repo


@pytest.mark.asyncio
async def test_repository_get_by_id_scopes_to_user() -> None:
    """Verify repository get_by_id filters by both id and user_id."""
    user_a = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Document(
        id=doc_id, user_id=user_a, original_filename="test.pdf"
    )
    mock_session.execute.return_value = mock_result

    repo = BaseRepository(Document)
    res = await repo.get_by_id(mock_session, id=doc_id, user_id=user_a)

    assert res is not None
    assert res.id == doc_id
    assert res.user_id == user_a
    assert mock_session.execute.called

    # Inspect executed SQL statement to verify user_id where clause was added
    stmt = mock_session.execute.call_args[0][0]
    assert isinstance(stmt, Select)
    compiled_stmt = str(stmt.compile())
    assert "documents.user_id =" in compiled_stmt
    assert "documents.id =" in compiled_stmt


@pytest.mark.asyncio
async def test_repository_list_all_scopes_to_user() -> None:
    """Verify repository list_all filters strictly by user_id."""
    user_a = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [
        Document(id=uuid.uuid4(), user_id=user_a, original_filename="doc1.pdf"),
        Document(id=uuid.uuid4(), user_id=user_a, original_filename="doc2.pdf"),
    ]
    mock_session.execute.return_value = mock_result

    repo = BaseRepository(Document)
    docs = await repo.list_all(mock_session, user_id=user_a, limit=10, offset=0)

    assert len(docs) == 2
    stmt = mock_session.execute.call_args[0][0]
    compiled_stmt = str(stmt.compile())
    assert "documents.user_id =" in compiled_stmt


@pytest.mark.asyncio
async def test_repository_create_forces_user_id() -> None:
    """Verify repository create automatically attaches the user_id."""
    user_id = uuid.uuid4()
    data = {
        "original_filename": "syllabus.docx",
        "storage_path": "path/syllabus.docx",
        "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "size_bytes": 45000,
    }

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    repo = BaseRepository(Document)

    created = await repo.create(mock_session, obj_in=data, user_id=user_id)
    assert created.user_id == user_id
    assert created.original_filename == "syllabus.docx"
    assert mock_session.add.called
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_document_repo_get_by_checksum_scopes_to_user() -> None:
    """Verify DocumentRepository get_by_checksum requires user_id."""
    user_a = uuid.uuid4()
    checksum = "sha256_abcdef123456"

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Document(
        id=uuid.uuid4(),
        user_id=user_a,
        checksum=checksum,
        original_filename="notes.pdf",
    )
    mock_session.execute.return_value = mock_result

    doc = await document_repo.get_by_checksum(
        mock_session, checksum=checksum, user_id=user_a
    )
    assert doc is not None
    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "documents.checksum =" in compiled
    assert "documents.user_id =" in compiled


@pytest.mark.asyncio
async def test_chunk_repo_create_batch_enforces_user_id() -> None:
    """Verify chunk_repo create_batch attaches user_id and document_id to all chunks."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunks_data = [
        {"chunk_index": 0, "content": "Chunk zero", "token_count": 2},
        {"chunk_index": 1, "content": "Chunk one", "token_count": 2},
    ]

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    chunks = await chunk_repo.create_batch(
        mock_session,
        chunks_data=chunks_data,
        document_id=doc_id,
        user_id=user_id,
    )

    assert len(chunks) == 2
    assert chunks[0].user_id == user_id
    assert chunks[0].document_id == doc_id
    assert chunks[1].user_id == user_id
    assert chunks[1].document_id == doc_id
    assert mock_session.flush.called


@pytest.mark.asyncio
async def test_job_repo_get_active_job_scopes_to_user() -> None:
    """Verify job_repo filters active jobs strictly by user_id."""
    user_id = uuid.uuid4()
    res_id = uuid.uuid4()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = Job(
        id=uuid.uuid4(),
        user_id=user_id,
        resource_type="document",
        resource_id=res_id,
        job_type="document_processing",
        status="running",
    )
    mock_session.execute.return_value = mock_result

    job = await job_repo.get_active_job(
        mock_session,
        resource_type="document",
        resource_id=res_id,
        user_id=user_id,
    )
    assert job is not None
    stmt = mock_session.execute.call_args[0][0]
    compiled = str(stmt.compile())
    assert "jobs.user_id =" in compiled
    assert "jobs.resource_id =" in compiled
