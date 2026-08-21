"""Evaluation repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Evaluation
from app.repositories.base import BaseRepository


class EvaluationRepository(BaseRepository[Evaluation]):
    """Repository for Evaluation entities."""

    def __init__(self) -> None:
        super().__init__(Evaluation)

    async def list_by_question(
        self, session: AsyncSession, *, question_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Evaluation]:
        """List evaluations for a question."""
        stmt = (
            select(Evaluation)
            .where(
                Evaluation.question_id == question_id,
                Evaluation.user_id == user_id,
            )
            .order_by(Evaluation.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


evaluation_repo = EvaluationRepository()
