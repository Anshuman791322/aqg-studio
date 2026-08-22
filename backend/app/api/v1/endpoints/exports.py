"""Export management, package generation, and secure download endpoints."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.output_report_agent import output_report_agent
from app.core.auth import CurrentUser, get_current_user
from app.core.errors import ValidationException
from app.core.logging import get_logger
from app.db.session import get_db
from app.exports.service import export_service
from app.reporting.schemas import ExportCreateRequest, ExportResponse
from app.schemas.common import SuccessResponse

logger = get_logger("app.api.v1.endpoints.exports")

router = APIRouter()

MIME_MAP = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "json": "application/json",
    "csv": "text/csv; charset=utf-8",
    "moodle_xml": "application/xml",
    "gift": "text/plain",
    "qti_2_1": "application/zip",
}


@router.post(
    "/assessments/{assessment_id}/exports",
    response_model=SuccessResponse[ExportResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_assessment_export_endpoint(
    assessment_id: uuid.UUID,
    request: ExportCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[ExportResponse]:
    """Create and compile an assessment export package in the requested format (PDF, DOCX, JSON, CSV)."""
    if db is None:
        raise ValidationException(
            message="Database is not available.", code="DATABASE_UNAVAILABLE"
        )

    export_response = await output_report_agent.create_export(
        db,
        assessment_id=assessment_id,
        user_id=current_user.user_id,
        request=request,
    )
    return SuccessResponse(data=export_response)


@router.get(
    "/assessments/{assessment_id}/exports",
    response_model=SuccessResponse[list[ExportResponse]],
)
async def list_assessment_exports_endpoint(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[list[ExportResponse]]:
    """List all compiled export packages for an assessment."""
    if db is None:
        raise ValidationException(
            message="Database is not available.", code="DATABASE_UNAVAILABLE"
        )

    exports = await output_report_agent.list_exports(
        db,
        assessment_id=assessment_id,
        user_id=current_user.user_id,
    )
    return SuccessResponse(data=exports)


@router.get(
    "/exports/{export_id}/download",
)
async def download_export_endpoint(
    export_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> Response:
    """Download an export file securely. Verifies that the export belongs strictly to the authenticated user."""
    if db is None:
        raise ValidationException(
            message="Database is not available.", code="DATABASE_UNAVAILABLE"
        )

    export_record, file_bytes = await export_service.get_download_info(
        db,
        export_id=export_id,
        user_id=current_user.user_id,
    )

    fmt = export_record.format.lower()
    media_type = MIME_MAP.get(fmt, "application/octet-stream")
    filename = f"assessment_export_{export_record.assessment_id}_{export_id}.{fmt}"

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "Cache-Control": "private, no-cache, no-store, must-revalidate",
    }

    return Response(
        content=file_bytes,
        media_type=media_type,
        headers=headers,
    )


@router.delete(
    "/exports/{export_id}",
    response_model=SuccessResponse[dict[str, Any]],
)
async def delete_export_endpoint(
    export_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[dict[str, Any]]:
    """Delete an export package record and purge associated storage artifacts."""
    if db is None:
        raise ValidationException(
            message="Database is not available.", code="DATABASE_UNAVAILABLE"
        )

    await export_service.delete_export(
        db,
        export_id=export_id,
        user_id=current_user.user_id,
    )
    return SuccessResponse(data={"deleted": True, "export_id": str(export_id)})
