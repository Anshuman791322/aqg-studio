"""LearningObjective repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import LearningObjective
from app.repositories.base import BaseRepository


class LearningObjectiveRepository(BaseRepository[LearningObjective]):
    """Repository for LearningObjective entities."""

    def __init__(self) -> None:
        super().__init__(LearningObjective)

    async def list_by_document(
        self, session: AsyncSession, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[LearningObjective]:
        """List learning objectives for a specific document."""
        stmt = (
            select(LearningObjective)
            .where(
                LearningObjective.document_id == document_id,
                LearningObjective.user_id == user_id,
            )
            .order_by(LearningObjective.created_at.asc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


objective_repo = LearningObjectiveRepository()
