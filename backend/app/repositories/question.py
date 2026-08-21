"""Question repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.entities import Question
from app.repositories.base import BaseRepository


class QuestionRepository(BaseRepository[Question]):
    """Repository for Question entities."""

    def __init__(self) -> None:
        super().__init__(Question)

    async def list_by_assessment(
        self,
        session: AsyncSession,
        *,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID,
        status: str | None = None,
    ) -> Sequence[Question]:
        """List questions for an assessment with evaluations loaded."""
        stmt = (
            select(Question)
            .where(
                Question.assessment_id == assessment_id,
                Question.user_id == user_id,
            )
            .options(selectinload(Question.evaluations))
        )
        if status:
            stmt = stmt.where(Question.status == status)

        stmt = stmt.order_by(Question.created_at.asc())
        result = await session.execute(stmt)
        return result.scalars().all()


question_repo = QuestionRepository()
