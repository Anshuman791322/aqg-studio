"""Job repository implementation."""

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Job
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """Repository for Job entities."""

    def __init__(self) -> None:
        super().__init__(Job)

    async def get_active_job(
        self,
        session: AsyncSession,
        *,
        resource_type: str,
        resource_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Job | None:
        """Find currently queued or running job for a specific resource."""
        stmt = select(Job).where(
            Job.resource_type == resource_type,
            Job.resource_id == resource_id,
            Job.user_id == user_id,
            Job.status.in_(["queued", "running"]),
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_resource(
        self,
        session: AsyncSession,
        *,
        resource_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Sequence[Job]:
        """List execution history for a resource."""
        stmt = (
            select(Job)
            .where(
                Job.resource_id == resource_id,
                Job.user_id == user_id,
            )
            .order_by(Job.created_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().all()


job_repo = JobRepository()
