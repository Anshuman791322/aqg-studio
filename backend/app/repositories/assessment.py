"""Assessment repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Assessment
from app.repositories.base import BaseRepository


class AssessmentRepository(BaseRepository[Assessment]):
    """Repository for Assessment entities."""

    def __init__(self) -> None:
        super().__init__(Assessment)

    async def get_with_relations(
        self, session: AsyncSession, *, id: uuid.UUID, user_id: uuid.UUID
    ) -> Assessment | None:
        """Fetch assessment with blueprints, questions, and exports loaded."""
        stmt = (
            select(Assessment)
            .where(
                Assessment.id == id,
                Assessment.user_id == user_id,
            )
            .options(
                selectinload(Assessment.blueprints),
                selectinload(Assessment.questions),
                selectinload(Assessment.exports),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_document(
        self, session: AsyncSession, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Assessment]:
        """List assessments for a specific document."""
        stmt = (
            select(Assessment)
            .where(
                Assessment.document_id == document_id,
                Assessment.user_id == user_id,
            )
            .order_by(Assessment.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


assessment_repo = AssessmentRepository()
