"""Question Generation Agent for grounded, batched question generation from assessment blueprints."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.generation.schemas import (
    AssessmentGenerationResult,
    BatchQuestionGenerationOutput,
    GeneratedQuestionItem,
    QuestionResponseData,
)
from app.generation.validator import (
    format_options_for_db,
    validate_generated_question,
)
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_gateway
from app.llm.schemas import ChatMessage
from app.models.entities import (
    Assessment,
    Concept,
    DocumentChunk,
    Question,
    QuestionBlueprint,
    Topic,
)
from app.prompts.generation import (
    QUESTION_GENERATOR_SYSTEM_PROMPT,
    build_batch_generation_user_prompt,
)
from app.retrieval.service import HybridRetrievalService

logger = get_logger("aqg.agents.generation")
settings = get_settings()


class QuestionGenerationAgent:
    """Agent orchestrating RAG retrieval, batched LLM question generation, validation, and draft persistence."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        retrieval_service: HybridRetrievalService | None = None,
    ) -> None:
        self.llm = llm_provider or get_llm_gateway()
        self.retrieval = retrieval_service or HybridRetrievalService()
        self.settings = get_settings()

    async def generate_batch_questions(
        self,
        session: AsyncSession,
        *,
        blueprints: list[QuestionBlueprint],
        document_id: uuid.UUID,
        user_id: uuid.UUID,
        topic_lookup: dict[uuid.UUID, Topic],
        concept_lookup: dict[uuid.UUID, Concept],
        custom_instructions: str | None = None,
        retry_attempt: int = 1,
    ) -> tuple[list[Question], list[QuestionBlueprint]]:
        """Generate, validate, and persist questions for a single batch of blueprints.

        Returns:
            (saved_questions, failed_blueprints)
        """
        if not blueprints:
            return [], []

        logger.info(
            "Executing question generation batch",
            extra={
                "blueprint_count": len(blueprints),
                "retry_attempt": retry_attempt,
                "document_id": str(document_id),
            },
        )

        blueprints_with_context: list[dict[str, Any]] = []
        bp_available_chunk_ids: dict[uuid.UUID, set[uuid.UUID]] = {}
        bp_chunk_pages_map: dict[uuid.UUID, dict[uuid.UUID, list[int]]] = {}

        # 1. Per-Blueprint RAG Retrieval & Context Assembly
        for bp in blueprints:
            topic_obj = topic_lookup.get(bp.topic_id) if bp.topic_id else None
            concept_obj = concept_lookup.get(bp.concept_id) if bp.concept_id else None

            topic_name = topic_obj.name if topic_obj else "General Knowledge"
            concept_name = concept_obj.name if concept_obj else None

            # Construct query targeting learning objective and pedagogical parameters
            query_parts = [
                bp.learning_objective or "",
                topic_name,
                concept_name or "",
                bp.bloom_level,
                bp.question_type,
            ]
            query_str = " ".join(p for p in query_parts if p).strip()

            retrieved = await self.retrieval.retrieve(
                session,
                user_id=user_id,
                document_id=document_id,
                query=query_str,
                top_k=self.settings.GENERATION_RAG_TOP_K,
            )

            # Collect retrieved chunk IDs
            retrieved_chunk_ids = [r.chunk_id for r in retrieved]
            # Merge with blueprint's initial source_chunk_ids if not already included
            all_target_ids = list(dict.fromkeys(retrieved_chunk_ids + list(bp.source_chunk_ids)))

            # Fetch actual chunk records to get page numbers and full bounded text
            chunks_stmt = select(DocumentChunk).where(
                DocumentChunk.id.in_(all_target_ids),
                DocumentChunk.user_id == user_id,
                DocumentChunk.document_id == document_id,
            )
            chunks_res = await session.execute(chunks_stmt)
            chunk_records = list(chunks_res.scalars().all())

            context_chunks_data: list[dict[str, Any]] = []
            available_ids: set[uuid.UUID] = set()
            chunk_pages: dict[uuid.UUID, list[int]] = {}

            for cr in chunk_records:
                available_ids.add(cr.id)
                pages = []
                if cr.page_start is not None:
                    pages.append(cr.page_start)
                if cr.page_end is not None and cr.page_end != cr.page_start:
                    pages.append(cr.page_end)
                chunk_pages[cr.id] = pages

                content_preview = cr.content
                if len(content_preview) > self.settings.GENERATION_MAX_CHUNK_CHARS:
                    content_preview = (
                        content_preview[: self.settings.GENERATION_MAX_CHUNK_CHARS] + "..."
                    )

                context_chunks_data.append(
                    {
                        "chunk_id": str(cr.id),
                        "page_start": cr.page_start,
                        "content": content_preview,
                    }
                )

            bp_available_chunk_ids[bp.id] = available_ids
            bp_chunk_pages_map[bp.id] = chunk_pages

            blueprints_with_context.append(
                {
                    "blueprint_id": str(bp.id),
                    "sequence_number": bp.sequence_number,
                    "question_type": bp.question_type,
                    "difficulty": bp.difficulty,
                    "bloom_level": bp.bloom_level,
                    "topic_name": topic_name,
                    "concept_name": concept_name,
                    "learning_objective": bp.learning_objective or f"Assess comprehension of {topic_name}",
                    "context_chunks": context_chunks_data,
                }
            )

        # 2. Build User Prompt & Invoke LLM
        user_prompt = build_batch_generation_user_prompt(
            blueprints_with_context=blueprints_with_context,
            custom_instructions=custom_instructions,
        )

        messages = [
            ChatMessage(role="system", content=QUESTION_GENERATOR_SYSTEM_PROMPT),
            ChatMessage(role="user", content=user_prompt),
        ]

        batch_output: BatchQuestionGenerationOutput | None = None
        try:
            batch_output, _ = await self.llm.complete_structured(
                messages,
                response_model=BatchQuestionGenerationOutput,
                temperature=self.settings.GENERATION_TEMPERATURE,
            )
        except Exception as exc:
            logger.warning(
                f"Batch question generation LLM call failed ({str(exc)}). Marking blueprints for retry.",
                extra={"blueprint_count": len(blueprints)},
            )
            return [], blueprints

        if not batch_output or not batch_output.questions:
            logger.warning("LLM returned empty questions list for batch.")
            return [], blueprints

        # Index returned items by blueprint_id
        items_by_bp: dict[uuid.UUID, GeneratedQuestionItem] = {}
        for item in batch_output.questions:
            items_by_bp[item.blueprint_id] = item

        saved_questions: list[Question] = []
        failed_blueprints: list[QuestionBlueprint] = []

        # 3. Validate Each Item Independently & Persist
        for bp in blueprints:
            item = items_by_bp.get(bp.id)
            if not item:
                logger.warning(f"Blueprint {bp.id} was omitted in LLM batch output.")
                failed_blueprints.append(bp)
                continue

            available_ids = bp_available_chunk_ids.get(bp.id, set())
            is_valid, error_reason = validate_generated_question(item, bp, available_ids)

            if not is_valid:
                logger.warning(
                    f"Generated question failed validation for blueprint {bp.id}: {error_reason}"
                )
                failed_blueprints.append(bp)
                continue

            # Gather cited pages
            cited_pages: list[int] = []
            chunk_pages = bp_chunk_pages_map.get(bp.id, {})
            for cid in item.supporting_evidence.source_chunk_ids:
                if cid in chunk_pages:
                    cited_pages.extend(chunk_pages[cid])
            if item.supporting_evidence.page_numbers:
                cited_pages.extend(item.supporting_evidence.page_numbers)
            unique_pages = sorted(set(cited_pages))

            question_entity = Question(
                id=uuid.uuid4(),
                assessment_id=bp.assessment_id,
                blueprint_id=bp.id,
                user_id=user_id,
                question_type=item.question_type,
                question_text=item.question_text.strip(),
                options=format_options_for_db(item),
                correct_answer=item.correct_answer,
                explanation=item.explanation.strip(),
                topic=item.topic,
                difficulty=item.difficulty,
                bloom_level=item.bloom_level,
                source_chunk_ids=item.supporting_evidence.source_chunk_ids,
                source_pages=unique_pages,
                supporting_evidence=item.supporting_evidence.model_dump(mode="json"),
                status="draft",
                version=1,
                generation_attempts=retry_attempt,
                quality_score=None,
            )

            session.add(question_entity)
            bp.status = "generated"
            saved_questions.append(question_entity)

        return saved_questions, failed_blueprints

    async def generate_assessment_questions(
        self,
        session: AsyncSession,
        *,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID,
        batch_size: int | None = None,
    ) -> AssessmentGenerationResult:
        """Orchestrate grounded question generation for an assessment's pending blueprints."""
        logger.info(
            "Starting question generation workflow for assessment",
            extra={"assessment_id": str(assessment_id), "user_id": str(user_id)},
        )

        try:
            # 1. Fetch & Verify Assessment
            assessment_stmt = select(Assessment).where(
                Assessment.id == assessment_id, Assessment.user_id == user_id
            )
            assessment_res = await session.execute(assessment_stmt)
            assessment = assessment_res.scalar_one_or_none()
            if not assessment:
                raise ValueError(
                    f"Assessment '{assessment_id}' not found for user '{user_id}'."
                )

            assessment.status = "generating"
            await session.commit()

            # 2. Fetch Pending Blueprints
            bp_stmt = (
                select(QuestionBlueprint)
                .where(
                    QuestionBlueprint.assessment_id == assessment_id,
                    QuestionBlueprint.user_id == user_id,
                    QuestionBlueprint.status.in_(["planned", "generating", "failed"]),
                )
                .order_by(QuestionBlueprint.sequence_number.asc())
            )
            bp_res = await session.execute(bp_stmt)
            pending_blueprints = list(bp_res.scalars().all())

            # Fetch Topics & Concepts for Context Enrichment
            topics_stmt = select(Topic).where(
                Topic.document_id == assessment.document_id, Topic.user_id == user_id
            )
            topics_res = await session.execute(topics_stmt)
            topic_lookup = {t.id: t for t in topics_res.scalars().all()}

            concepts_stmt = select(Concept).where(
                Concept.document_id == assessment.document_id, Concept.user_id == user_id
            )
            concepts_res = await session.execute(concepts_stmt)
            concept_lookup = {c.id: c for c in concepts_res.scalars().all()}

            effective_batch_size = batch_size or self.settings.GENERATION_BATCH_SIZE
            custom_instructions = dict(assessment.configuration or {}).get("custom_instructions")

            all_saved_questions: list[Question] = []
            permanently_failed_blueprints: list[QuestionBlueprint] = []

            # 3. Process Initial Batches
            for i in range(0, len(pending_blueprints), effective_batch_size):
                batch = pending_blueprints[i : i + effective_batch_size]
                saved, failed = await self.generate_batch_questions(
                    session,
                    blueprints=batch,
                    document_id=assessment.document_id,
                    user_id=user_id,
                    topic_lookup=topic_lookup,
                    concept_lookup=concept_lookup,
                    custom_instructions=custom_instructions,
                    retry_attempt=1,
                )
                all_saved_questions.extend(saved)

                # 4. Retry Failed Items with Reduced Batch Size (Size 1)
                for failed_bp in failed:
                    logger.info(
                        f"Retrying blueprint {failed_bp.id} with individual batch fallback."
                    )
                    retry_saved: list[Question] = []
                    for attempt in range(2, self.settings.GENERATION_MAX_RETRIES + 2):
                        s, f = await self.generate_batch_questions(
                            session,
                            blueprints=[failed_bp],
                            document_id=assessment.document_id,
                            user_id=user_id,
                            topic_lookup=topic_lookup,
                            concept_lookup=concept_lookup,
                            custom_instructions=custom_instructions,
                            retry_attempt=attempt,
                        )
                        if s:
                            retry_saved.extend(s)
                            all_saved_questions.extend(s)
                            break

                    if not retry_saved:
                        failed_bp.status = "failed"
                        permanently_failed_blueprints.append(failed_bp)

                await session.flush()

            # 5. Finalize Assessment Status & Metrics
            total_bp_stmt = select(QuestionBlueprint).where(
                QuestionBlueprint.assessment_id == assessment_id
            )
            total_bp_res = await session.execute(total_bp_stmt)
            all_blueprints = list(total_bp_res.scalars().all())
            total_count = len(all_blueprints)

            # Load all questions for this assessment
            all_q_stmt = (
                select(Question)
                .where(Question.assessment_id == assessment_id)
                .order_by(Question.created_at.asc())
            )
            all_q_res = await session.execute(all_q_stmt)
            existing_questions = list(all_q_res.scalars().all())
            gen_count = len(existing_questions)

            progress_val = Decimal(str(round((gen_count / total_count * 100) if total_count > 0 else 100.0, 2)))
            assessment.progress = progress_val
            assessment.metrics = {
                "total_questions": total_count,
                "generated_questions": gen_count,
                "failed_questions": len(permanently_failed_blueprints),
            }

            if gen_count > 0:
                assessment.status = "ready"
            else:
                assessment.status = "failed"

            await session.commit()

            logger.info(
                "Question generation complete for assessment",
                extra={
                    "assessment_id": str(assessment_id),
                    "generated_count": gen_count,
                    "failed_count": len(permanently_failed_blueprints),
                    "status": assessment.status,
                },
            )

            response_questions = [
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
                for q in existing_questions
            ]

            return AssessmentGenerationResult(
                assessment_id=assessment_id,
                total_blueprints=total_count,
                generated_questions=gen_count,
                failed_blueprints=len(permanently_failed_blueprints),
                status=assessment.status,
                questions=response_questions,
            )
        except Exception as exc:
            await session.rollback()
            logger.error(
                "Question generation failed with unhandled exception, transaction rolled back",
                extra={"assessment_id": str(assessment_id), "error": str(exc)},
            )
            raise
