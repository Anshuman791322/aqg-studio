"""Export repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Export
from app.repositories.base import BaseRepository


class ExportRepository(BaseRepository[Export]):
    """Repository for Export entities."""

    def __init__(self) -> None:
        super().__init__(Export)

    async def list_by_assessment(
        self, session: AsyncSession, *, assessment_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Export]:
        """List exports for an assessment."""
        stmt = (
            select(Export)
            .where(
                Export.assessment_id == assessment_id,
                Export.user_id == user_id,
            )
            .order_by(Export.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


export_repo = ExportRepository()
