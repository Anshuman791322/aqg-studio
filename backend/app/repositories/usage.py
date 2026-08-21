"""LLMUsageDaily repository implementation."""

import uuid
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import LLMUsageDaily
from app.repositories.base import BaseRepository


class LLMUsageDailyRepository(BaseRepository[LLMUsageDaily]):
    """Repository for LLMUsageDaily entities."""

    def __init__(self) -> None:
        super().__init__(LLMUsageDaily)

    async def get_or_create_today(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        for_date: date | None = None,
    ) -> LLMUsageDaily:
        """Get or create daily usage row for user."""
        target_date = for_date or datetime.now(UTC).date()
        stmt = select(LLMUsageDaily).where(
            LLMUsageDaily.user_id == user_id,
            LLMUsageDaily.usage_date == target_date,
        )
        result = await session.execute(stmt)
        record = result.scalar_one_or_none()
        if record is None:
            record = LLMUsageDaily(
                user_id=user_id,
                usage_date=target_date,
                request_count=0,
                input_tokens=0,
                output_tokens=0,
                assessments_created=0,
            )
            session.add(record)
            await session.flush()
            await session.refresh(record)
        return record

    async def record_usage(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        input_tokens: int,
        output_tokens: int,
        assessments_increment: int = 0,
    ) -> LLMUsageDaily:
        """Atomically increment tokens and request counts for today."""
        usage = await self.get_or_create_today(session, user_id=user_id)
        usage.request_count += 1
        usage.input_tokens += input_tokens
        usage.output_tokens += output_tokens
        usage.assessments_created += assessments_increment
        await session.flush()
        return usage


usage_repo = LLMUsageDailyRepository()
