"""Profile repository implementation."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Profile


class ProfileRepository:
    """Repository for Profile entities mapping to auth.users."""

    async def get_by_id(
        self, session: AsyncSession, *, user_id: uuid.UUID
    ) -> Profile | None:
        """Fetch user profile matching user_id."""
        stmt = select(Profile).where(Profile.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_or_update(
        self, session: AsyncSession, *, user_id: uuid.UUID, display_name: str | None
    ) -> Profile:
        """Create or update user profile upon auth sync."""
        profile = await self.get_by_id(session, user_id=user_id)
        if profile is None:
            profile = Profile(id=user_id, display_name=display_name)
            session.add(profile)
        else:
            profile.display_name = display_name
        await session.flush()
        await session.refresh(profile)
        return profile

    async def update_display_name(
        self, session: AsyncSession, *, user_id: uuid.UUID, display_name: str
    ) -> Profile | None:
        """Update display name for authenticated user."""
        profile = await self.get_by_id(session, user_id=user_id)
        if not profile:
            return None
        profile.display_name = display_name
        await session.flush()
        await session.refresh(profile)
        return profile


profile_repo = ProfileRepository()
