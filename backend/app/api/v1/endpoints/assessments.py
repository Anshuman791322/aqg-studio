"""Assessment management, Question Blueprint, and Generation API endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.planning_agent import QuestionPlanningAgent
from app.agents.question_generation_agent import QuestionGenerationAgent
from app.core.auth import CurrentUser, get_current_user
from app.core.errors import NotFoundException, ValidationException
from app.db.session import get_db
from app.generation.schemas import (
    AssessmentGenerationResult,
    QuestionResponseData,
)
from app.planning.schemas import (
    AssessmentBlueprintResponse,
    AssessmentCreateRequest,
    AssessmentResponseData,
    QuestionBlueprintItemSchema,
)
from app.repositories.assessment import assessment_repo
from app.repositories.blueprint import blueprint_repo
from app.repositories.question import question_repo
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/assessments", tags=["Assessments"])
planning_agent = QuestionPlanningAgent()
generation_agent = QuestionGenerationAgent()


@router.post("", response_model=SuccessResponse[AssessmentBlueprintResponse], status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[AssessmentBlueprintResponse]:
    """Create a new assessment and deterministically design its question blueprints."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    try:
        blueprint_response = await planning_agent.create_assessment_with_blueprint(
            db,
            request=payload,
            user_id=current_user.user_id,
        )
        return SuccessResponse(
            data=blueprint_response,
            message="Assessment and question blueprints created successfully.",
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise NotFoundException(message=err_msg, code="DOCUMENT_NOT_FOUND")
        raise ValidationException(message=err_msg, code="PLANNING_VALIDATION_ERROR")


@router.get("", response_model=SuccessResponse[list[AssessmentResponseData]])
async def list_assessments(
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[list[AssessmentResponseData]]:
    """List all assessments owned by the authenticated user."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    records = await assessment_repo.list_all(db, user_id=current_user.user_id)
    items = [
        AssessmentResponseData(
            id=a.id,
            document_id=a.document_id,
            name=a.name,
            total_questions=int(dict(a.configuration or {}).get("total_questions", 0)),
            configuration=a.configuration,
            status=a.status,
            progress=float(a.progress),
            metrics=a.metrics,
            created_at=a.created_at,
            updated_at=a.updated_at,
        )
        for a in records
    ]
    return SuccessResponse(data=items)


@router.get("/{assessment_id}", response_model=SuccessResponse[AssessmentResponseData])
async def get_assessment(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[AssessmentResponseData]:
    """Retrieve details for a specific assessment."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    record = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not record:
        raise NotFoundException(
            message=f"Assessment '{assessment_id}' not found.",
            code="ASSESSMENT_NOT_FOUND",
        )

    data = AssessmentResponseData(
        id=record.id,
        document_id=record.document_id,
        name=record.name,
        total_questions=int(dict(record.configuration or {}).get("total_questions", 0)),
        configuration=record.configuration,
        status=record.status,
        progress=float(record.progress),
        metrics=record.metrics,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )
    return SuccessResponse(data=data)


@router.get("/{assessment_id}/blueprint", response_model=SuccessResponse[AssessmentBlueprintResponse])
async def get_assessment_blueprint(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[AssessmentBlueprintResponse]:
    """Retrieve the question blueprints for an assessment in sequence order."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    record = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not record:
        raise NotFoundException(
            message=f"Assessment '{assessment_id}' not found.",
            code="ASSESSMENT_NOT_FOUND",
        )

    blueprints = await blueprint_repo.list_by_assessment(
        db, assessment_id=assessment_id, user_id=current_user.user_id
    )

    bp_items = [
        QuestionBlueprintItemSchema(
            id=bp.id,
            sequence_number=bp.sequence_number,
            topic_id=bp.topic_id,
            concept_id=bp.concept_id,
            question_type=bp.question_type,
            difficulty=bp.difficulty,  # type: ignore[arg-type]
            bloom_level=bp.bloom_level,  # type: ignore[arg-type]
            learning_objective=bp.learning_objective or "",
            source_chunk_ids=list(bp.source_chunk_ids or []),
            rationale="",
            status=bp.status,
        )
        for bp in blueprints
    ]

    response_data = AssessmentBlueprintResponse(
        assessment_id=record.id,
        document_id=record.document_id,
        name=record.name,
        total_questions=len(bp_items),
        status=record.status,
        configuration=record.configuration,
        blueprints=bp_items,
    )
    return SuccessResponse(data=response_data)


@router.post("/{assessment_id}/generate", response_model=SuccessResponse[AssessmentGenerationResult])
async def generate_questions_endpoint(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[AssessmentGenerationResult]:
    """Trigger grounded batch question generation for an assessment's pending blueprints."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    try:
        result = await generation_agent.generate_assessment_questions(
            db,
            assessment_id=assessment_id,
            user_id=current_user.user_id,
        )
        return SuccessResponse(
            data=result,
            message="Question generation completed successfully.",
        )
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise NotFoundException(message=err_msg, code="ASSESSMENT_NOT_FOUND")
        raise ValidationException(message=err_msg, code="GENERATION_VALIDATION_ERROR")


@router.get("/{assessment_id}/questions", response_model=SuccessResponse[list[QuestionResponseData]])
async def list_assessment_questions(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[list[QuestionResponseData]]:
    """List all generated questions for an assessment."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    # Check assessment exists and belongs to user
    assessment = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not assessment:
        raise NotFoundException(
            message=f"Assessment '{assessment_id}' not found.",
            code="ASSESSMENT_NOT_FOUND",
        )

    records = await question_repo.list_by_assessment(
        db, assessment_id=assessment_id, user_id=current_user.user_id
    )

    items = [
        QuestionResponseData(
            id=q.id,
            assessment_id=q.assessment_id,
            blueprint_id=q.blueprint_id,
            question_type=q.question_type,
            question_text=q.question_text,
            options=q.options,
            correct_answer=q.correct_answer,
            explanation=q.explanation,
            topic=q.topic,
            difficulty=q.difficulty,
            bloom_level=q.bloom_level,
            source_chunk_ids=q.source_chunk_ids,
            source_pages=q.source_pages,
            supporting_evidence=dict(q.supporting_evidence or {}),
            status=q.status,
            version=q.version,
            created_at=q.created_at,
        )
        for q in records
    ]
    return SuccessResponse(data=items)


@router.delete("/{assessment_id}", response_model=SuccessResponse[dict[str, bool]])
async def delete_assessment(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[dict[str, bool]]:
    """Delete an assessment and its associated blueprints and questions."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    deleted = await assessment_repo.delete(db, id=assessment_id, user_id=current_user.user_id)
    if not deleted:
        raise NotFoundException(
            message=f"Assessment '{assessment_id}' not found.",
            code="ASSESSMENT_NOT_FOUND",
        )

    return SuccessResponse(
        data={"deleted": True},
        message=f"Assessment '{assessment_id}' deleted successfully.",
    )
