"""Version and system status API endpoint."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.common import VersionData, VersionResponse

router = APIRouter(tags=["System"])
settings = get_settings()


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Get API version and status",
    description="Returns current API version, build status, and active environment.",
)
async def get_version() -> VersionResponse:
    """Return application version information wrapped in standard response envelope."""
    return VersionResponse(
        data=VersionData(
            name=settings.APP_NAME,
            version=settings.APP_VERSION,
            api_version="v1",
            environment=settings.ENVIRONMENT,
            status="operational",
        )
    )
