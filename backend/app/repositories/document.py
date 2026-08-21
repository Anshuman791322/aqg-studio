"""Document repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document entities."""

    def __init__(self) -> None:
        super().__init__(Document)

    async def get_by_checksum(
        self, session: AsyncSession, *, checksum: str, user_id: uuid.UUID
    ) -> Document | None:
        """Find an existing document for user with matching content checksum."""
        stmt = select(Document).where(
            Document.checksum == checksum,
            Document.user_id == user_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_status(
        self, session: AsyncSession, *, status: str, user_id: uuid.UUID
    ) -> Sequence[Document]:
        """List documents for user filtered by status."""
        stmt = (
            select(Document)
            .where(
                Document.status == status,
                Document.user_id == user_id,
            )
            .order_by(Document.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


document_repo = DocumentRepository()
