"""Question entity REST endpoints."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUser, get_current_user
from app.core.errors import NotFoundException, ValidationException
from app.db.session import get_db
from app.generation.schemas import QuestionResponseData
from app.repositories.question import question_repo
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/questions", tags=["Questions"])


@router.get("/{question_id}", response_model=SuccessResponse[QuestionResponseData])
async def get_question(
    question_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[QuestionResponseData]:
    """Retrieve details for a single question with citations and evidence."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    record = await question_repo.get_by_id(db, id=question_id, user_id=current_user.user_id)
    if not record:
        raise NotFoundException(
            message=f"Question '{question_id}' not found.",
            code="QUESTION_NOT_FOUND",
        )

    data = QuestionResponseData(
        id=record.id,
        assessment_id=record.assessment_id,
        blueprint_id=record.blueprint_id,
        question_type=record.question_type,
        question_text=record.question_text,
        options=record.options,
        correct_answer=record.correct_answer,
        explanation=record.explanation,
        topic=record.topic,
        difficulty=record.difficulty,
        bloom_level=record.bloom_level,
        source_chunk_ids=record.source_chunk_ids,
        source_pages=record.source_pages,
        supporting_evidence=dict(record.supporting_evidence or {}),
        status=record.status,
        version=record.version,
        created_at=record.created_at,
    )
    return SuccessResponse(data=data)
