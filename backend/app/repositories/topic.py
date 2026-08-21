"""Topic and Concept repository implementations."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Concept, Topic
from app.repositories.base import BaseRepository


class TopicRepository(BaseRepository[Topic]):
    """Repository for Topic entities."""

    def __init__(self) -> None:
        super().__init__(Topic)

    async def list_by_document(
        self, session: AsyncSession, *, document_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Topic]:
        """List topics for a specific document."""
        stmt = (
            select(Topic)
            .where(
                Topic.document_id == document_id,
                Topic.user_id == user_id,
            )
            .order_by(Topic.importance_score.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


class ConceptRepository(BaseRepository[Concept]):
    """Repository for Concept entities."""

    def __init__(self) -> None:
        super().__init__(Concept)

    async def list_by_topic(
        self, session: AsyncSession, *, topic_id: uuid.UUID, user_id: uuid.UUID
    ) -> Sequence[Concept]:
        """List concepts under a topic."""
        stmt = select(Concept).where(
            Concept.topic_id == topic_id,
            Concept.user_id == user_id,
        )
        result = await session.execute(stmt)
        return result.scalars().all()


topic_repo = TopicRepository()
concept_repo = ConceptRepository()
