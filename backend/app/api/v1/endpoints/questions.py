"""Question entity REST endpoints for retrieval, evaluation, refinement, and audit scorecards."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluation_agent import EvaluationAgent
from app.core.auth import CurrentUser, get_current_user
from app.core.errors import NotFoundException, ValidationException
from app.db.session import get_db
from app.evaluation.schemas import (
    EvaluationResponseData,
    QuestionWithEvaluationsData,
    RefinementRequest,
)
from app.generation.schemas import QuestionResponseData
from app.repositories.blueprint import blueprint_repo
from app.repositories.evaluation import evaluation_repo
from app.repositories.question import question_repo
from app.schemas.common import SuccessResponse

router = APIRouter(prefix="/questions", tags=["Questions"])
evaluation_agent = EvaluationAgent()


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


@router.post("/{question_id}/evaluate", response_model=SuccessResponse[EvaluationResponseData])
async def evaluate_question_endpoint(
    question_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[EvaluationResponseData]:
    """Trigger automated pedagogical evaluation and scoring for a single question."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    question = await question_repo.get_by_id(db, id=question_id, user_id=current_user.user_id)
    if not question:
        raise NotFoundException(
            message=f"Question '{question_id}' not found.",
            code="QUESTION_NOT_FOUND",
        )

    blueprint = None
    if question.blueprint_id:
        blueprint = await blueprint_repo.get_by_id(db, id=question.blueprint_id, user_id=current_user.user_id)

    eval_rec, _ = await evaluation_agent.evaluate_single_question(
        db,
        question=question,
        blueprint=blueprint,
        user_id=current_user.user_id,
    )
    await db.commit()

    data = EvaluationResponseData(
        id=eval_rec.id,
        question_id=eval_rec.question_id,
        correctness_score=float(eval_rec.correctness_score) if eval_rec.correctness_score is not None else None,
        grounding_score=float(eval_rec.grounding_score) if eval_rec.grounding_score is not None else None,
        clarity_score=float(eval_rec.clarity_score) if eval_rec.clarity_score is not None else None,
        relevance_score=float(eval_rec.relevance_score) if eval_rec.relevance_score is not None else None,
        difficulty_score=float(eval_rec.difficulty_score) if eval_rec.difficulty_score is not None else None,
        bloom_alignment_score=float(eval_rec.bloom_alignment_score) if eval_rec.bloom_alignment_score is not None else None,
        distractor_quality_score=float(eval_rec.distractor_quality_score) if eval_rec.distractor_quality_score is not None else None,
        duplication_score=float(eval_rec.duplication_score) if eval_rec.duplication_score is not None else None,
        overall_quality_score=float(eval_rec.overall_quality_score),
        decision=eval_rec.decision,
        feedback=dict(eval_rec.feedback or {}),
        created_at=eval_rec.created_at,
    )
    return SuccessResponse(data=data)


@router.post("/{question_id}/refine", response_model=SuccessResponse[QuestionWithEvaluationsData])
async def refine_question_endpoint(
    question_id: uuid.UUID,
    payload: RefinementRequest,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[QuestionWithEvaluationsData]:
    """Execute targeted refinement on a question and return updated entity with re-evaluation scorecard."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    question = await question_repo.get_by_id(db, id=question_id, user_id=current_user.user_id)
    if not question:
        raise NotFoundException(
            message=f"Question '{question_id}' not found.",
            code="QUESTION_NOT_FOUND",
        )

    blueprint = None
    if question.blueprint_id:
        blueprint = await blueprint_repo.get_by_id(db, id=question.blueprint_id, user_id=current_user.user_id)

    refined_q, eval_rec = await evaluation_agent.refine_single_question(
        db,
        question=question,
        blueprint=blueprint,
        evaluator_issues=payload.target_issues,
        custom_instructions=payload.custom_instructions,
        user_id=current_user.user_id,
    )
    await db.commit()

    all_evals = await evaluation_repo.list_by_question(db, question_id=question_id, user_id=current_user.user_id)
    eval_items = [
        EvaluationResponseData(
            id=e.id,
            question_id=e.question_id,
            correctness_score=float(e.correctness_score) if e.correctness_score is not None else None,
            grounding_score=float(e.grounding_score) if e.grounding_score is not None else None,
            clarity_score=float(e.clarity_score) if e.clarity_score is not None else None,
            relevance_score=float(e.relevance_score) if e.relevance_score is not None else None,
            difficulty_score=float(e.difficulty_score) if e.difficulty_score is not None else None,
            bloom_alignment_score=float(e.bloom_alignment_score) if e.bloom_alignment_score is not None else None,
            distractor_quality_score=float(e.distractor_quality_score) if e.distractor_quality_score is not None else None,
            duplication_score=float(e.duplication_score) if e.duplication_score is not None else None,
            overall_quality_score=float(e.overall_quality_score),
            decision=e.decision,
            feedback=dict(e.feedback or {}),
            created_at=e.created_at,
        )
        for e in all_evals
    ]

    data = QuestionWithEvaluationsData(
        id=refined_q.id,
        assessment_id=refined_q.assessment_id,
        blueprint_id=refined_q.blueprint_id,
        question_type=refined_q.question_type,
        question_text=refined_q.question_text,
        options=refined_q.options,
        correct_answer=refined_q.correct_answer,
        explanation=refined_q.explanation,
        topic=refined_q.topic,
        difficulty=refined_q.difficulty,
        bloom_level=refined_q.bloom_level,
        source_chunk_ids=refined_q.source_chunk_ids,
        source_pages=refined_q.source_pages,
        supporting_evidence=dict(refined_q.supporting_evidence or {}),
        status=refined_q.status,
        version=refined_q.version,
        generation_attempts=refined_q.generation_attempts,
        quality_score=float(refined_q.quality_score) if refined_q.quality_score is not None else None,
        created_at=refined_q.created_at,
        evaluations=eval_items,
    )
    return SuccessResponse(data=data)


@router.get("/{question_id}/evaluations", response_model=SuccessResponse[list[EvaluationResponseData]])
async def list_question_evaluations(
    question_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession | None = Depends(get_db),
) -> SuccessResponse[list[EvaluationResponseData]]:
    """Retrieve full evaluation audit scorecard history for a question."""
    if db is None:
        raise ValidationException(message="Database is not available.", code="DATABASE_UNAVAILABLE")

    question = await question_repo.get_by_id(db, id=question_id, user_id=current_user.user_id)
    if not question:
        raise NotFoundException(
            message=f"Question '{question_id}' not found.",
            code="QUESTION_NOT_FOUND",
        )

    records = await evaluation_repo.list_by_question(db, question_id=question_id, user_id=current_user.user_id)
    items = [
        EvaluationResponseData(
            id=e.id,
            question_id=e.question_id,
            correctness_score=float(e.correctness_score) if e.correctness_score is not None else None,
            grounding_score=float(e.grounding_score) if e.grounding_score is not None else None,
            clarity_score=float(e.clarity_score) if e.clarity_score is not None else None,
            relevance_score=float(e.relevance_score) if e.relevance_score is not None else None,
            difficulty_score=float(e.difficulty_score) if e.difficulty_score is not None else None,
            bloom_alignment_score=float(e.bloom_alignment_score) if e.bloom_alignment_score is not None else None,
            distractor_quality_score=float(e.distractor_quality_score) if e.distractor_quality_score is not None else None,
            duplication_score=float(e.duplication_score) if e.duplication_score is not None else None,
            overall_quality_score=float(e.overall_quality_score),
            decision=e.decision,
            feedback=dict(e.feedback or {}),
            created_at=e.created_at,
        )
        for e in records
    ]
    return SuccessResponse(data=items)
