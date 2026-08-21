"""QuestionBlueprint repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import QuestionBlueprint
from app.repositories.base import BaseRepository


class QuestionBlueprintRepository(BaseRepository[QuestionBlueprint]):
    """Repository for QuestionBlueprint entities."""

    def __init__(self) -> None:
        super().__init__(QuestionBlueprint)

    async def list_by_assessment(
        self, session: AsyncSession, *, assessment_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[QuestionBlueprint]:
        """List blueprint items for an assessment in sequence order."""
        stmt = (
            select(QuestionBlueprint)
            .where(
                QuestionBlueprint.assessment_id == assessment_id,
                QuestionBlueprint.user_id == user_id,
            )
            .order_by(QuestionBlueprint.sequence_number.asc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


blueprint_repo = QuestionBlueprintRepository()
