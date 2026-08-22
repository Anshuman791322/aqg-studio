"""Assessment management, Question Blueprint, and Generation API endpoints."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluation_agent import EvaluationAgent
from app.agents.output_report_agent import output_report_agent
from app.agents.planning_agent import QuestionPlanningAgent
from app.agents.question_generation_agent import QuestionGenerationAgent
from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.core.errors import NotFoundException, ValidationException
from app.core.quota import quota_service
from app.db.session import get_db
from app.evaluation.schemas import AssessmentEvaluationSummary
from app.generation.schemas import QuestionResponseData
from app.orchestration.runner import job_runner
from app.orchestration.schemas import JobStatusResponse
from app.planning.schemas import (
    AssessmentBlueprintResponse,
    AssessmentCreateRequest,
    AssessmentResponseData,
    QuestionBlueprintItemSchema,
)
from app.reporting.schemas import AssessmentReportResponse
from app.repositories.assessment import assessment_repo
from app.repositories.blueprint import blueprint_repo
from app.repositories.export import export_repo
from app.repositories.job import job_repo
from app.repositories.question import question_repo
from app.schemas.common import SuccessResponse
from app.services.storage import delete_file_from_storage

settings = get_settings()
router = APIRouter(prefix="/assessments", tags=["Assessments"])
planning_agent = QuestionPlanningAgent()
generation_agent = QuestionGenerationAgent()
evaluation_agent = EvaluationAgent()


@router.post("", response_model=SuccessResponse[AssessmentBlueprintResponse], status_code=status.HTTP_201_CREATED)
async def create_assessment(
    payload: AssessmentCreateRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[AssessmentBlueprintResponse]:
    """Create a new assessment and deterministically design its question blueprints."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    # 1. Enforce per-assessment question bounds
    quota_service.validate_question_count(payload.total_questions)

    # 2. Atomically verify and increment daily assessment creation quota
    await quota_service.check_and_increment_assessment_quota(db, current_user.user_id)

    try:
        blueprint_response = await planning_agent.create_assessment_with_blueprint(
            db,
            request=payload,
            user_id=current_user.user_id,
        )
        return SuccessResponse(data=blueprint_response)
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise NotFoundException(message=err_msg, code="DOCUMENT_NOT_FOUND") from val_err
        raise ValidationException(message=err_msg, code="PLANNING_VALIDATION_ERROR") from val_err


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
        raise NotFoundException(message=f"Assessment '{assessment_id}' not found.", code="ASSESSMENT_NOT_FOUND")

    record = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not record:
        raise NotFoundException(message=f"Assessment '{assessment_id}' not found.", code="ASSESSMENT_NOT_FOUND")

    data = AssessmentResponseData(
        id=record.id,
        document_id=record.document_id,
        name=record.name,
        total_questions=int(dict(record.configuration or {}).get("total_questions", 0)),
        status=record.status,
        progress=float(record.progress),
        configuration=record.configuration,
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
    """Retrieve question blueprints for an assessment in sequence order."""
    if db is None:
        raise NotFoundException(message=f"Assessment '{assessment_id}' not found.", code="ASSESSMENT_NOT_FOUND")

    assessment = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not assessment:
        raise NotFoundException(message=f"Assessment '{assessment_id}' not found.", code="ASSESSMENT_NOT_FOUND")

    blueprints = await blueprint_repo.list_by_assessment(db, assessment_id=assessment_id, user_id=current_user.user_id)
    items = [
        QuestionBlueprintItemSchema(
            id=bp.id,
            sequence_number=bp.sequence_number,
            topic_id=bp.topic_id,
            concept_id=bp.concept_id,
            question_type=bp.question_type,
            difficulty=bp.difficulty if bp.difficulty in ("easy", "medium", "hard") else "medium",  # type: ignore[arg-type]
            bloom_level=bp.bloom_level if bp.bloom_level in ("remember", "understand", "apply", "analyze", "evaluate", "create") else "understand",  # type: ignore[arg-type]
            learning_objective=bp.learning_objective or "",
            source_chunk_ids=list(bp.source_chunk_ids or []),
            status=bp.status,
        )
        for bp in blueprints
    ]

    response_data = AssessmentBlueprintResponse(
        assessment_id=assessment.id,
        document_id=assessment.document_id,
        name=assessment.name,
        total_questions=len(items),
        status=assessment.status,
        configuration=assessment.configuration,
        blueprints=items,
    )
    return SuccessResponse(data=response_data)


@router.post("/{assessment_id}/generate", response_model=SuccessResponse[JobStatusResponse])
async def generate_questions_endpoint(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[JobStatusResponse]:
    """Enqueue an asynchronous background job for assessment question planning, generation, evaluation, and dedup."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    assessment = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not assessment:
        raise NotFoundException(message=f"Assessment '{assessment_id}' not found.", code="ASSESSMENT_NOT_FOUND")

    target_q = int(dict(assessment.configuration or {}).get("total_questions", 10))

    initial_state = {
        "assessment_id": str(assessment_id),
        "document_id": str(assessment.document_id),
        "user_id": str(current_user.user_id),
        "target_questions": target_q,
    }

    job = await job_runner.enqueue_job(
        db,
        user_id=current_user.user_id,
        resource_type="assessment",
        resource_id=assessment_id,
        job_type="question_generation",
        initial_state=initial_state,
    )

    questions = await question_repo.list_by_assessment(db, assessment_id=assessment_id, user_id=current_user.user_id)
    accepted_count = len([q for q in questions if q.status == "approved"])

    data = JobStatusResponse(
        job_id=job.id,
        resource_type=job.resource_type,
        resource_id=job.resource_id,
        job_type=job.job_type,
        status=job.status,
        progress=float(job.progress),
        current_step=job.current_step,
        accepted_questions=accepted_count,
        target_questions=target_q,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        locked_at=job.locked_at,
        heartbeat_at=job.heartbeat_at,
        state=dict(job.state or {}),
    )
    return SuccessResponse(data=data)


@router.get("/{assessment_id}/status", response_model=SuccessResponse[JobStatusResponse])
async def get_assessment_status(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[JobStatusResponse]:
    """Retrieve background execution progress, current step, accepted items, and error details for an assessment."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    assessment = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not assessment:
        raise NotFoundException(message=f"Assessment '{assessment_id}' not found.", code="ASSESSMENT_NOT_FOUND")

    target_q = int(dict(assessment.configuration or {}).get("total_questions", 10))
    questions = await question_repo.list_by_assessment(db, assessment_id=assessment_id, user_id=current_user.user_id)
    accepted_count = len([q for q in questions if q.status == "approved"])

    job = await job_repo.get_active_job(
        db,
        resource_type="assessment",
        resource_id=assessment_id,
        user_id=current_user.user_id,
    )
    if not job:
        history = await job_repo.list_by_resource(
            db, resource_id=assessment_id, user_id=current_user.user_id
        )
        job = history[0] if history else None

    if not job:
        # Synthetic status reflecting assessment table
        data = JobStatusResponse(
            job_id=uuid.uuid4(),
            resource_type="assessment",
            resource_id=assessment_id,
            job_type="question_generation",
            status="completed" if assessment.status == "ready" else assessment.status,
            progress=float(assessment.progress),
            current_step="finalize_assessment" if assessment.status == "ready" else None,
            accepted_questions=accepted_count,
            target_questions=target_q,
            created_at=assessment.created_at,
            updated_at=assessment.updated_at,
        )
        return SuccessResponse(data=data)

    data = JobStatusResponse(
        job_id=job.id,
        resource_type=job.resource_type,
        resource_id=job.resource_id,
        job_type=job.job_type,
        status=job.status,
        progress=float(job.progress),
        current_step=job.current_step,
        accepted_questions=accepted_count,
        target_questions=target_q,
        error_code=job.error_code,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
        locked_at=job.locked_at,
        heartbeat_at=job.heartbeat_at,
        state=dict(job.state or {}),
    )
    return SuccessResponse(data=data)


@router.post("/{assessment_id}/cancel", response_model=SuccessResponse[JobStatusResponse])
async def cancel_assessment_generation(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[JobStatusResponse]:
    """Request immediate cancellation of a running assessment generation job."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    assessment = await assessment_repo.get_by_id(db, id=assessment_id, user_id=current_user.user_id)
    if not assessment:
        raise NotFoundException(message=f"Assessment '{assessment_id}' not found.", code="ASSESSMENT_NOT_FOUND")

    cancelled_job = await job_runner.cancel_job(
        db,
        resource_type="assessment",
        resource_id=assessment_id,
        user_id=current_user.user_id,
    )
    if not cancelled_job:
        raise ValidationException(
            message=f"No active running or queued job found for assessment '{assessment_id}'.",
            code="NO_ACTIVE_JOB",
        )

    target_q = int(dict(assessment.configuration or {}).get("total_questions", 10))
    questions = await question_repo.list_by_assessment(db, assessment_id=assessment_id, user_id=current_user.user_id)
    accepted_count = len([q for q in questions if q.status == "approved"])

    data = JobStatusResponse(
        job_id=cancelled_job.id,
        resource_type=cancelled_job.resource_type,
        resource_id=cancelled_job.resource_id,
        job_type=cancelled_job.job_type,
        status=cancelled_job.status,
        progress=float(cancelled_job.progress),
        current_step=cancelled_job.current_step,
        accepted_questions=accepted_count,
        target_questions=target_q,
        error_code=cancelled_job.error_code,
        error_message=cancelled_job.error_message,
        created_at=cancelled_job.created_at,
        updated_at=cancelled_job.updated_at,
        locked_at=cancelled_job.locked_at,
        heartbeat_at=cancelled_job.heartbeat_at,
        state=dict(cancelled_job.state or {}),
    )
    return SuccessResponse(data=data)


@router.post("/{assessment_id}/evaluate", response_model=SuccessResponse[AssessmentEvaluationSummary])
async def evaluate_assessment_endpoint(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[AssessmentEvaluationSummary]:
    """Trigger automated evaluation, refinement loops, regeneration, and duplicate control across an assessment."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    try:
        summary = await evaluation_agent.evaluate_and_refine_assessment(
            db,
            assessment_id=assessment_id,
            user_id=current_user.user_id,
        )
        return SuccessResponse(data=summary)
    except ValueError as val_err:
        err_msg = str(val_err)
        if "not found" in err_msg.lower():
            raise NotFoundException(message=err_msg, code="ASSESSMENT_NOT_FOUND") from val_err
        raise ValidationException(message=err_msg, code="EVALUATION_VALIDATION_ERROR") from val_err


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
    """Delete an assessment, its blueprints, questions, and associated export storage artifacts."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    # Clean up associated export artifacts from Supabase Storage
    exports = await export_repo.list_by_assessment(db, assessment_id=assessment_id, user_id=current_user.user_id)
    for exp in exports:
        if exp.storage_path:
            await delete_file_from_storage(
                bucket=settings.SUPABASE_STORAGE_BUCKET_EXPORTS,
                path=exp.storage_path,
            )

    deleted = await assessment_repo.delete(db, id=assessment_id, user_id=current_user.user_id)
    if not deleted:
        raise NotFoundException(
            message=f"Assessment '{assessment_id}' not found.",
            code="ASSESSMENT_NOT_FOUND",
        )

    return SuccessResponse(data={"deleted": True})


@router.get(
    "/{assessment_id}/report",
    response_model=SuccessResponse[AssessmentReportResponse],
)
async def get_assessment_report_endpoint(
    assessment_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[AssessmentReportResponse]:
    """Retrieve comprehensive pedagogical quality metrics, distribution analyses, and export links for an assessment."""
    if db is None:
        raise ValidationException(
            message="Database is not available.", code="DATABASE_UNAVAILABLE"
        )

    report = await output_report_agent.generate_assessment_report(
        db,
        assessment_id=assessment_id,
        user_id=current_user.user_id,
    )
    return SuccessResponse(data=report)
