"""Question Planning Agent for assessment blueprint generation."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_gateway
from app.llm.schemas import ChatMessage
from app.models.entities import Assessment, Document, LearningObjective, QuestionBlueprint, Topic
from app.planning.allocator import build_blueprint_slots
from app.planning.schemas import (
    AssessmentBlueprintResponse,
    AssessmentCreateRequest,
    PlanningRefinementOutput,
    QuestionBlueprintItemSchema,
)
from app.prompts.planning import (
    PLANNING_AGENT_SYSTEM_PROMPT,
    build_planning_refinement_user_prompt,
)

logger = get_logger("aqg.agents.planning")


class QuestionPlanningAgent:
    """Agent responsible for deterministic allocation and LLM-assisted assessment blueprint design."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm = llm_provider or get_llm_gateway()

    async def create_assessment_with_blueprint(
        self,
        session: AsyncSession,
        *,
        request: AssessmentCreateRequest,
        user_id: uuid.UUID,
    ) -> AssessmentBlueprintResponse:
        """Create assessment record and design structured question blueprints."""
        logger.info(
            "Starting question planning for assessment",
            extra={
                "document_id": str(request.document_id),
                "user_id": str(user_id),
                "total_questions": request.total_questions,
            },
        )

        try:
            # 1. Verify Document Ownership
            doc_stmt = select(Document).where(
                Document.id == request.document_id, Document.user_id == user_id
            )
            doc_res = await session.execute(doc_stmt)
            document = doc_res.scalar_one_or_none()
            if not document:
                raise ValueError(
                    f"Document '{request.document_id}' not found for user '{user_id}'."
                )

            # 2. Fetch Topics & Concepts
            topics_stmt = (
                select(Topic)
                .where(
                    Topic.document_id == request.document_id,
                    Topic.user_id == user_id,
                )
                .options(selectinload(Topic.concepts))
                .order_by(Topic.importance_score.desc(), Topic.created_at.asc())
            )
            topics_res = await session.execute(topics_stmt)
            available_topics = list(topics_res.scalars().all())

            if not available_topics:
                raise ValueError(
                    f"Document '{request.document_id}' has not been analyzed yet. "
                    "Please run knowledge analysis before creating an assessment."
                )

            # Filter by topic_ids if provided
            if request.topic_ids:
                selected_ids = set(request.topic_ids)
                filtered_topics = [t for t in available_topics if t.id in selected_ids]
                if not filtered_topics:
                    raise ValueError("None of the requested topic IDs exist in this document.")
                topics_to_use = filtered_topics
            else:
                topics_to_use = available_topics

            # 3. Fetch Learning Objectives
            objs_stmt = select(LearningObjective).where(
                LearningObjective.document_id == request.document_id,
                LearningObjective.user_id == user_id,
            )
            objs_res = await session.execute(objs_stmt)
            available_objs = list(objs_res.scalars().all())

            # 4. Deterministic Slot Allocation
            slots = build_blueprint_slots(
                total_questions=request.total_questions,
                topics=topics_to_use,
                type_distribution=request.question_type_distribution,
                difficulty_distribution=request.difficulty_distribution,
                bloom_distribution=request.bloom_distribution,
            )

            # 5. Prepare LLM Refinement Prompt Context
            slots_data: list[dict[str, Any]] = []
            for slot in slots:
                concept_meta = dict(slot.concept.metadata_ or {}) if slot.concept else {}
                topic_meta = dict(slot.topic.metadata_ or {})
                c_chunk_ids = concept_meta.get("source_chunk_ids", [])
                t_chunk_ids = topic_meta.get("source_chunk_ids", [])
                fallback_chunks = c_chunk_ids or t_chunk_ids or [str(document.id)]

                slots_data.append(
                    {
                        "sequence_number": slot.sequence_number,
                        "topic_name": slot.topic.name,
                        "concept_name": slot.concept.name if slot.concept else None,
                        "concept_definition": slot.concept.definition if slot.concept else None,
                        "question_type": slot.question_type,
                        "difficulty": slot.difficulty,
                        "bloom_level": slot.bloom_level,
                        "available_source_chunk_ids": fallback_chunks,
                    }
                )

            objs_data = [
                {
                    "bloom_level": o.bloom_level,
                    "description": o.description,
                    "source_chunk_ids": dict(o.metadata_ or {}).get("source_chunk_ids", []),
                }
                for o in available_objs
            ]

            user_prompt = build_planning_refinement_user_prompt(
                slots_data=slots_data,
                available_objectives=objs_data,
                custom_instructions=request.custom_instructions,
            )

            messages = [
                ChatMessage(role="system", content=PLANNING_AGENT_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ]

            # 6. Call LLM for Refinement with Graceful Deterministic Fallback
            refinement_map: dict[int, Any] = {}
            try:
                raw_refinement, _ = await self.llm.complete_structured(
                    messages,
                    response_model=PlanningRefinementOutput,
                    temperature=0.2,
                )
                for item in raw_refinement.items:
                    refinement_map[item.sequence_number] = item
            except Exception as llm_err:
                logger.warning(
                    f"LLM refinement pass skipped ({str(llm_err)}), applying deterministic objective synthesis.",
                    extra={"assessment_name": request.name},
                )

            # 7. Create Assessment Record
            assessment_id = uuid.uuid4()
            assessment_config = request.model_dump(mode="json")
            assessment_entity = Assessment(
                id=assessment_id,
                user_id=user_id,
                document_id=request.document_id,
                name=request.name,
                configuration=assessment_config,
                status="draft",
                progress=Decimal("0.00"),
                metrics={
                    "total_questions": request.total_questions,
                    "generated_questions": 0,
                    "evaluated_questions": 0,
                },
            )
            session.add(assessment_entity)
            await session.flush()

            # 8. Create QuestionBlueprint Records
            blueprint_schemas: list[QuestionBlueprintItemSchema] = []
            for slot in slots:
                seq = slot.sequence_number
                refinement = refinement_map.get(seq)

                concept_meta = dict(slot.concept.metadata_ or {}) if slot.concept else {}
                topic_meta = dict(slot.topic.metadata_ or {})
                default_chunk_str_ids = (
                    concept_meta.get("source_chunk_ids")
                    or topic_meta.get("source_chunk_ids")
                    or [str(document.id)]
                )
                default_chunk_uuids = [
                    uuid.UUID(cid) if isinstance(cid, str) else cid
                    for cid in default_chunk_str_ids
                ]

                target_name = slot.concept.name if slot.concept else slot.topic.name
                if refinement and refinement.learning_objective:
                    objective = refinement.learning_objective
                    rationale = refinement.rationale
                    source_ids = (
                        refinement.source_chunk_ids
                        if refinement.source_chunk_ids
                        else default_chunk_uuids
                    )
                else:
                    objective = (
                        f"{slot.bloom_level.capitalize()} the core principles and mechanisms of {target_name}."
                    )
                    rationale = (
                        f"Tests {slot.difficulty} cognitive comprehension of {target_name}."
                    )
                    source_ids = default_chunk_uuids

                blueprint_id = uuid.uuid4()
                bp_entity = QuestionBlueprint(
                    id=blueprint_id,
                    assessment_id=assessment_id,
                    user_id=user_id,
                    topic_id=slot.topic.id,
                    concept_id=slot.concept.id if slot.concept else None,
                    question_type=slot.question_type,
                    difficulty=slot.difficulty,
                    bloom_level=slot.bloom_level,
                    learning_objective=objective,
                    source_chunk_ids=source_ids,
                    status="planned",
                    sequence_number=seq,
                )
                session.add(bp_entity)

                blueprint_schemas.append(
                    QuestionBlueprintItemSchema(
                        id=blueprint_id,
                        sequence_number=seq,
                        topic_id=slot.topic.id,
                        topic_name=slot.topic.name,
                        concept_id=slot.concept.id if slot.concept else None,
                        concept_name=slot.concept.name if slot.concept else None,
                        question_type=slot.question_type,
                        difficulty=slot.difficulty,  # type: ignore[arg-type]
                        bloom_level=slot.bloom_level,  # type: ignore[arg-type]
                        learning_objective=objective,
                        source_chunk_ids=source_ids,
                        rationale=rationale,
                        status="planned",
                    )
                )

            await session.commit()

            logger.info(
                "Assessment and blueprints successfully created",
                extra={
                    "assessment_id": str(assessment_id),
                    "blueprint_count": len(blueprint_schemas),
                },
            )

            return AssessmentBlueprintResponse(
                assessment_id=assessment_id,
                document_id=request.document_id,
                name=request.name,
                total_questions=request.total_questions,
                status="draft",
                configuration=assessment_config,
                blueprints=blueprint_schemas,
            )
        except Exception as exc:
            await session.rollback()
            logger.error(
                "Question planning failed with error, transaction rolled back",
                extra={"document_id": str(request.document_id), "error": str(exc)},
            )
            raise
