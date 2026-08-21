"""Base generic user-scoped repository interface."""

import uuid
from collections.abc import Sequence
from typing import Any, Generic, TypeVar

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository enforcing strict user-scoping on all data operations."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    async def get_by_id(
        self, session: AsyncSession, *, id: uuid.UUID, user_id: uuid.UUID
    ) -> ModelType | None:
        """Fetch single record matching id and user_id."""
        stmt = select(self.model).where(
            self.model.id == id,  # type: ignore[attr-defined]
            self.model.user_id == user_id,  # type: ignore[attr-defined]
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[ModelType]:
        """List records owned by user_id with pagination."""
        stmt = (
            select(self.model)
            .where(self.model.user_id == user_id)  # type: ignore[attr-defined]
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return result.scalars().all()

    async def count(self, session: AsyncSession, *, user_id: uuid.UUID) -> int:
        """Count records owned by user_id."""
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self.model.user_id == user_id)  # type: ignore[attr-defined]
        )
        result = await session.execute(stmt)
        count_val = result.scalar_one()
        return int(count_val) if count_val is not None else 0

    async def create(
        self, session: AsyncSession, *, obj_in: dict[str, Any], user_id: uuid.UUID
    ) -> ModelType:
        """Create new record with forced user_id assignment."""
        data = {**obj_in, "user_id": user_id}
        db_obj = self.model(**data)
        session.add(db_obj)
        await session.flush()
        await session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        session: AsyncSession,
        *,
        id: uuid.UUID,
        user_id: uuid.UUID,
        obj_in: dict[str, Any],
    ) -> ModelType | None:
        """Update record matching id and user_id with attribute synchronization."""
        existing = await self.get_by_id(session, id=id, user_id=user_id)
        if not existing:
            return None

        # Exclude immutable primary keys and user ownership fields
        safe_data = {
            k: v for k, v in obj_in.items() if k not in ("id", "user_id", "created_at")
        }
        if not safe_data:
            return existing

        for key, value in safe_data.items():
            if hasattr(existing, key):
                setattr(existing, key, value)

        await session.flush()
        await session.refresh(existing)
        return existing

    async def delete(
        self, session: AsyncSession, *, id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        """Delete record matching id and user_id."""
        stmt = (
            delete(self.model)
            .where(
                self.model.id == id,  # type: ignore[attr-defined]
                self.model.user_id == user_id,  # type: ignore[attr-defined]
            )
            .execution_options(synchronize_session=False)
        )
        result = await session.execute(stmt)
        rowcount = getattr(result, "rowcount", 0)
        return bool(rowcount and rowcount > 0)
