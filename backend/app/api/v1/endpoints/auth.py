"""Authentication and User Profile endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.logging import get_logger
from app.db.session import get_db
from app.repositories.profile import profile_repo
from app.repositories.usage import usage_repo
from app.schemas.auth import UserProfileData, UserQuotaSummary
from app.schemas.common import SuccessResponse

logger = get_logger("app.api.v1.endpoints.auth")
router = APIRouter()


@router.get("/me", response_model=SuccessResponse[UserProfileData])
async def get_my_profile(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[UserProfileData]:
    """Retrieve the authenticated user's profile, role, and today's usage statistics."""
    meta = current_user.user_metadata
    display_name = meta.get("display_name") or meta.get("full_name")
    quota = UserQuotaSummary()

    if db is not None:
        try:
            profile = await profile_repo.get_by_id(db, user_id=current_user.user_id)
            if profile and profile.display_name:
                display_name = profile.display_name

            usage = await usage_repo.get_or_create_today(db, user_id=current_user.user_id)
            quota = UserQuotaSummary(
                today_requests=usage.request_count,
                today_input_tokens=usage.input_tokens,
                today_output_tokens=usage.output_tokens,
                today_assessments=usage.assessments_created,
            )
        except Exception as exc:
            logger.warning(
                f"Graceful fallback: failed to fetch profile/usage for user '{current_user.user_id}': {exc}"
            )

    profile_data = UserProfileData(
        user_id=current_user.user_id,
        email=current_user.email,
        role=current_user.role,
        display_name=display_name,
        app_metadata=current_user.app_metadata,
        user_metadata=current_user.user_metadata,
        quota=quota,
    )

    return SuccessResponse(data=profile_data)
