"""DocumentChunk repository implementation."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import DocumentChunk
from app.repositories.base import BaseRepository


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    """Repository for DocumentChunk entities."""

    def __init__(self) -> None:
        super().__init__(DocumentChunk)

    async def list_by_document(
        self, session: AsyncSession, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[DocumentChunk]:
        """List all chunks for a document ordered by chunk_index."""
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.user_id == user_id,
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def delete_by_document(
        self, session: AsyncSession, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> int:
        """Delete all chunks for a document belonging to a user."""
        stmt = delete(DocumentChunk).where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.user_id == user_id,
        )
        result = await session.execute(stmt)
        await session.flush()
        rowcount = getattr(result, "rowcount", 0)
        return int(rowcount) if rowcount is not None else 0

    async def create_batch(
        self,
        session: AsyncSession,
        *,
        chunks_in: list[dict[str, Any]] | None = None,
        chunks_data: list[dict[str, Any]] | None = None,
        document_id: uuid.UUID | None = None,
        user_id: uuid.UUID,
    ) -> list[DocumentChunk]:
        """Create multiple chunks in batch ensuring user_id scoping."""
        raw_chunks = chunks_in or chunks_data or []
        chunks: list[DocumentChunk] = []
        for item in raw_chunks:
            data = dict(item)
            data["user_id"] = user_id
            if document_id is not None and "document_id" not in data:
                data["document_id"] = document_id
            chunk = DocumentChunk(**data)
            session.add(chunk)
            chunks.append(chunk)
        await session.flush()
        return chunks


chunk_repo = DocumentChunkRepository()
