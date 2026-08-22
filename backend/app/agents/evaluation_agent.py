"""Evaluation and Refinement Agent for pedagogical quality assessment, multi-pass refinement, and duplicate control."""

import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.question_generation_agent import QuestionGenerationAgent
from app.core.config import get_settings
from app.core.logging import get_logger
from app.evaluation.deterministic import validate_question_deterministic
from app.evaluation.duplication import (
    detect_assessment_duplicates,
    resolve_duplicate_conflicts,
)
from app.evaluation.schemas import (
    AssessmentEvaluationSummary,
    EvaluationDecision,
    EvaluationResponseData,
    LLMEvaluationOutput,
    MetricScores,
    QuestionWithEvaluationsData,
)
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_gateway
from app.llm.schemas import ChatMessage
from app.models.entities import (
    Assessment,
    Concept,
    DocumentChunk,
    Evaluation,
    Question,
    QuestionBlueprint,
    Topic,
)
from app.prompts.evaluation import (
    QUESTION_EVALUATOR_SYSTEM_PROMPT,
    build_evaluation_user_prompt,
)
from app.prompts.refinement import (
    QUESTION_REFINEMENT_SYSTEM_PROMPT,
    build_refinement_user_prompt,
)
from app.retrieval.service import HybridRetrievalService

logger = get_logger("aqg.agents.evaluation")


class EvaluationAgent:
    """Agent orchestrating deterministic checks, LLM evaluation, iterative refinement, regeneration, and duplicate control."""

    def __init__(
        self,
        llm_provider: LLMProvider | None = None,
        retrieval_service: HybridRetrievalService | None = None,
        generation_agent: QuestionGenerationAgent | None = None,
    ) -> None:
        self.llm = llm_provider or get_llm_gateway()
        self.retrieval = retrieval_service or HybridRetrievalService()
        self.generation_agent = generation_agent or QuestionGenerationAgent(
            llm_provider=self.llm, retrieval_service=self.retrieval
        )
        self.settings = get_settings()

    async def evaluate_single_question(
        self,
        session: AsyncSession,
        *,
        question: Question,
        blueprint: QuestionBlueprint | None = None,
        available_chunks: list[DocumentChunk] | None = None,
        peer_questions: list[Question] | None = None,
        user_id: uuid.UUID,
    ) -> tuple[Evaluation, LLMEvaluationOutput]:
        """Evaluate a single question using deterministic validation and LLM evaluation."""
        logger.info(
            "Evaluating question",
            extra={"question_id": str(question.id), "user_id": str(user_id)},
        )

        # 1. Fetch document chunks if not supplied
        if available_chunks is None:
            doc_stmt = (
                select(DocumentChunk)
                .join(Assessment, Assessment.document_id == DocumentChunk.document_id)
                .where(
                    Assessment.id == question.assessment_id,
                    DocumentChunk.user_id == user_id,
                )
            )
            doc_res = await session.execute(doc_stmt)
            available_chunks = list(doc_res.scalars().all())

        available_chunk_ids = {c.id for c in available_chunks}

        # 2. Run Deterministic Checks First
        deterministic_res = validate_question_deterministic(
            question=question,
            blueprint=blueprint,
            available_chunk_ids=available_chunk_ids,
            other_questions=peer_questions,
        )

        # 3. LLM Evaluator
        if deterministic_res.critical_failure:
            # Deterministic fatal failure -> generate synthetic deterministic failure output
            grounding_val = 0.0 if "HALLUCINATED_CHUNK_IDS" in deterministic_res.rule_violations else 0.4
            scores = MetricScores(
                correctness=0.30,
                groundedness=grounding_val,
                relevance=0.50,
                clarity=0.50,
                grammar=0.70,
                answerability=0.30,
                difficulty_alignment=0.50,
                bloom_alignment=0.50,
                distractor_quality=0.20 if question.question_type.startswith("mcq") else 1.0,
                duplication_risk=1.0 if "EXACT_DUPLICATE_QUESTION" in deterministic_res.rule_violations else 0.0,
                overall_quality=0.30,
            )
            llm_output = LLMEvaluationOutput(
                question_id=str(question.id),
                scores=scores,
                decision="REGENERATE",
                strengths=[],
                issues=deterministic_res.issues,
                recommendations=[f"Remedy structural failure: {'; '.join(deterministic_res.issues)}"],
                rationale=f"Failed deterministic validation checks: {'; '.join(deterministic_res.rule_violations)}",
            )
        else:
            # Prepare context chunks corresponding to cited chunks or top chunks
            cited_chunk_ids = set(question.source_chunk_ids or [])
            relevant_chunks = [c for c in available_chunks if c.id in cited_chunk_ids]
            if not relevant_chunks:
                relevant_chunks = available_chunks[:5]

            user_prompt = build_evaluation_user_prompt(
                question=question,
                blueprint=blueprint,
                chunks=relevant_chunks,
                peer_questions=peer_questions,
            )

            messages = [
                ChatMessage(role="system", content=QUESTION_EVALUATOR_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ]

            llm_output, _ = await self.llm.complete_structured(
                messages=messages,
                response_model=LLMEvaluationOutput,
                temperature=0.1,
            )

            # Integrate non-critical deterministic issues into issues list
            if deterministic_res.issues:
                for det_issue in deterministic_res.issues:
                    if det_issue not in llm_output.issues:
                        llm_output.issues.append(det_issue)

        # 4. Decision Synthesis based on strict rules
        decision: EvaluationDecision
        if deterministic_res.critical_failure:
            decision = "REGENERATE"
        else:
            is_high_quality = (
                llm_output.scores.overall_quality >= self.settings.EVALUATION_ACCEPT_OVERALL_MIN
                and llm_output.scores.correctness >= self.settings.EVALUATION_ACCEPT_CORRECTNESS_MIN
                and llm_output.scores.groundedness >= self.settings.EVALUATION_ACCEPT_GROUNDEDNESS_MIN
                and llm_output.scores.duplication_risk <= 0.30
            )
            is_recoverable = (
                llm_output.scores.overall_quality >= self.settings.EVALUATION_REFINE_OVERALL_MIN
                and llm_output.scores.groundedness >= self.settings.EVALUATION_REFINE_GROUNDEDNESS_MIN
                and llm_output.scores.correctness >= 0.70
            )

            if is_high_quality and not deterministic_res.issues:
                decision = "ACCEPT"
            elif is_recoverable:
                decision = "REFINE"
            else:
                decision = "REGENERATE"

        llm_output.decision = decision

        # 5. Persist Evaluation Entity
        feedback_payload = {
            "strengths": llm_output.strengths,
            "issues": llm_output.issues,
            "recommendations": llm_output.recommendations,
            "rationale": llm_output.rationale,
            "deterministic_check": deterministic_res.model_dump(),
        }

        overall_dec = Decimal(str(round(llm_output.scores.overall_quality, 2)))

        evaluation_entity = Evaluation(
            id=uuid.uuid4(),
            question_id=question.id,
            user_id=user_id,
            correctness_score=Decimal(str(round(llm_output.scores.correctness, 2))),
            grounding_score=Decimal(str(round(llm_output.scores.groundedness, 2))),
            clarity_score=Decimal(str(round(llm_output.scores.clarity, 2))),
            relevance_score=Decimal(str(round(llm_output.scores.relevance, 2))),
            difficulty_score=Decimal(str(round(llm_output.scores.difficulty_alignment, 2))),
            bloom_alignment_score=Decimal(str(round(llm_output.scores.bloom_alignment, 2))),
            distractor_quality_score=Decimal(str(round(llm_output.scores.distractor_quality, 2))),
            duplication_score=Decimal(str(round(llm_output.scores.duplication_risk, 2))),
            overall_quality_score=overall_dec,
            decision=decision,
            feedback=feedback_payload,
        )

        session.add(evaluation_entity)

        # 6. Update Question State
        question.quality_score = overall_dec
        if decision == "ACCEPT":
            question.status = "approved"
        elif decision == "REFINE":
            question.status = "flagged"
        else:
            question.status = "rejected"

        await session.flush()

        logger.info(
            "Question evaluation completed",
            extra={
                "question_id": str(question.id),
                "decision": decision,
                "overall_quality": float(overall_dec),
            },
        )

        return evaluation_entity, llm_output

    async def refine_single_question(
        self,
        session: AsyncSession,
        *,
        question: Question,
        blueprint: QuestionBlueprint | None = None,
        available_chunks: list[DocumentChunk] | None = None,
        evaluator_issues: list[str] | None = None,
        evaluator_recommendations: list[str] | None = None,
        custom_instructions: str | None = None,
        user_id: uuid.UUID,
    ) -> tuple[Question, Evaluation]:
        """Refine a candidate question according to evaluator feedback and re-evaluate."""
        logger.info(
            "Executing question refinement pass",
            extra={"question_id": str(question.id), "version": question.version},
        )

        # Fetch chunks if not supplied
        if available_chunks is None:
            doc_stmt = (
                select(DocumentChunk)
                .join(Assessment, Assessment.document_id == DocumentChunk.document_id)
                .where(
                    Assessment.id == question.assessment_id,
                    DocumentChunk.user_id == user_id,
                )
            )
            doc_res = await session.execute(doc_stmt)
            available_chunks = list(doc_res.scalars().all())

        cited_ids = set(question.source_chunk_ids or [])
        context_chunks = [c for c in available_chunks if c.id in cited_ids]
        if not context_chunks:
            context_chunks = available_chunks[:5]

        from app.generation.schemas import GeneratedQuestionItem
        from app.generation.validator import format_options_for_db

        refinement_prompt = build_refinement_user_prompt(
            question=question,
            blueprint=blueprint,
            chunks=context_chunks,
            evaluator_issues=evaluator_issues or [],
            evaluator_recommendations=evaluator_recommendations or [],
            custom_instructions=custom_instructions,
        )

        messages = [
            ChatMessage(role="system", content=QUESTION_REFINEMENT_SYSTEM_PROMPT),
            ChatMessage(role="user", content=refinement_prompt),
        ]

        refined_item, _ = await self.llm.complete_structured(
            messages=messages,
            response_model=GeneratedQuestionItem,
            temperature=0.2,
        )

        # Update question fields
        question.question_text = refined_item.question_text.strip()
        question.options = format_options_for_db(refined_item)
        question.correct_answer = refined_item.correct_answer
        question.explanation = refined_item.explanation.strip()
        question.topic = refined_item.topic
        question.difficulty = refined_item.difficulty
        question.bloom_level = refined_item.bloom_level
        question.source_chunk_ids = refined_item.supporting_evidence.source_chunk_ids
        question.supporting_evidence = refined_item.supporting_evidence.model_dump(mode="json")
        question.version += 1
        question.generation_attempts += 1
        question.status = "draft"

        await session.flush()

        # Re-evaluate the refined question
        evaluation_record, _ = await self.evaluate_single_question(
            session,
            question=question,
            blueprint=blueprint,
            available_chunks=available_chunks,
            user_id=user_id,
        )

        return question, evaluation_record

    async def create_replacement_blueprint(
        self,
        session: AsyncSession,
        *,
        assessment: Assessment,
        failed_blueprint: QuestionBlueprint,
        user_id: uuid.UUID,
        sequence_number: int,
    ) -> QuestionBlueprint | None:
        """Create a replacement blueprint when a blueprint's generation attempts are permanently exhausted."""
        logger.info(
            "Creating replacement blueprint to preserve assessment question quota",
            extra={"assessment_id": str(assessment.id), "failed_bp": str(failed_blueprint.id)},
        )

        # Find concepts / topics in the document
        topics_stmt = select(Topic).where(
            Topic.document_id == assessment.document_id, Topic.user_id == user_id
        )
        topics_res = await session.execute(topics_stmt)
        topics = list(topics_res.scalars().all())

        concepts_stmt = select(Concept).where(
            Concept.document_id == assessment.document_id, Concept.user_id == user_id
        )
        concepts_res = await session.execute(concepts_stmt)
        concepts = list(concepts_res.scalars().all())

        target_topic_id = failed_blueprint.topic_id or (topics[0].id if topics else None)
        target_concept_id = failed_blueprint.concept_id or (concepts[0].id if concepts else None)

        replacement_bp = QuestionBlueprint(
            id=uuid.uuid4(),
            assessment_id=assessment.id,
            user_id=user_id,
            topic_id=target_topic_id,
            concept_id=target_concept_id,
            sequence_number=sequence_number,
            question_type=failed_blueprint.question_type,
            difficulty=failed_blueprint.difficulty,
            bloom_level=failed_blueprint.bloom_level,
            learning_objective=failed_blueprint.learning_objective or "Demonstrate conceptual understanding",
            source_chunk_ids=list(failed_blueprint.source_chunk_ids or []),
            status="planned",
        )

        session.add(replacement_bp)
        await session.flush()
        return replacement_bp

    async def evaluate_and_refine_assessment(
        self,
        session: AsyncSession,
        *,
        assessment_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> AssessmentEvaluationSummary:
        """Execute automated evaluation, refinement loops, regeneration, and duplicate control across an assessment."""
        logger.info(
            "Starting full assessment evaluation and refinement workflow",
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
                raise ValueError(f"Assessment '{assessment_id}' not found for user '{user_id}'.")

            # 2. Fetch Document Chunks & Blueprints
            chunks_stmt = select(DocumentChunk).where(
                DocumentChunk.document_id == assessment.document_id,
                DocumentChunk.user_id == user_id,
            )
            chunks_res = await session.execute(chunks_stmt)
            all_chunks = list(chunks_res.scalars().all())

            bp_stmt = (
                select(QuestionBlueprint)
                .where(
                    QuestionBlueprint.assessment_id == assessment_id,
                    QuestionBlueprint.user_id == user_id,
                )
                .order_by(QuestionBlueprint.sequence_number.asc())
            )
            bp_res = await session.execute(bp_stmt)
            blueprints_by_id = {bp.id: bp for bp in bp_res.scalars().all()}

            # Topics & Concepts lookups
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

            # 3. Fetch Questions for the Assessment
            q_stmt = (
                select(Question)
                .where(
                    Question.assessment_id == assessment_id,
                    Question.user_id == user_id,
                    Question.status != "rejected",
                )
                .order_by(Question.created_at.asc())
            )
            q_res = await session.execute(q_stmt)
            active_questions = list(q_res.scalars().all())

            replacement_blueprints_created = 0
            max_replacements = self.settings.EVALUATION_MAX_REPLACEMENT_BLUEPRINTS

            # 4. Process Every Candidate Question through Evaluation & Refinement Loop
            for q in active_questions:
                bp = blueprints_by_id.get(q.blueprint_id) if q.blueprint_id else None

                # Initial Evaluation
                evaluation_rec, eval_output = await self.evaluate_single_question(
                    session,
                    question=q,
                    blueprint=bp,
                    available_chunks=all_chunks,
                    peer_questions=active_questions,
                    user_id=user_id,
                )

                # Iterative Refinement Loop
                refinement_passes = 0
                while (
                    eval_output.decision == "REFINE"
                    and refinement_passes < self.settings.EVALUATION_MAX_REFINEMENT_ATTEMPTS
                ):
                    refinement_passes += 1
                    logger.info(
                        f"Attempting refinement pass {refinement_passes} for question {q.id}"
                    )
                    q, evaluation_rec = await self.refine_single_question(
                        session,
                        question=q,
                        blueprint=bp,
                        available_chunks=all_chunks,
                        evaluator_issues=eval_output.issues,
                        evaluator_recommendations=eval_output.recommendations,
                        user_id=user_id,
                    )
                    # Get updated decision
                    eval_decision = evaluation_rec.decision
                    if eval_decision == "ACCEPT":
                        break
                    elif eval_decision == "REGENERATE":
                        eval_output.decision = "REGENERATE"
                        break

                # Regeneration Loop if Still Rejected
                if eval_output.decision == "REGENERATE" and bp is not None:
                    regen_attempts = 0
                    while (
                        eval_output.decision == "REGENERATE"
                        and regen_attempts < self.settings.EVALUATION_MAX_REGENERATION_ATTEMPTS
                    ):
                        regen_attempts += 1
                        logger.info(
                            f"Regenerating question for blueprint {bp.id} (attempt {regen_attempts})"
                        )
                        q.status = "rejected"
                        await session.flush()

                        # Regenerate fresh question using QuestionGenerationAgent
                        saved_q_list, _ = await self.generation_agent.generate_batch_questions(
                            session,
                            blueprints=[bp],
                            document_id=assessment.document_id,
                            user_id=user_id,
                            topic_lookup=topic_lookup,
                            concept_lookup=concept_lookup,
                            custom_instructions=f"Avoid previous failure: {'; '.join(eval_output.issues)}",
                            retry_attempt=regen_attempts + 1,
                        )

                        if saved_q_list:
                            new_q = saved_q_list[0]
                            q = new_q
                            evaluation_rec, eval_output = await self.evaluate_single_question(
                                session,
                                question=new_q,
                                blueprint=bp,
                                available_chunks=all_chunks,
                                peer_questions=active_questions,
                                user_id=user_id,
                            )
                            if eval_output.decision == "ACCEPT":
                                break

                    # If regeneration exhausted and still not accepted -> create replacement blueprint
                    if (
                        eval_output.decision != "ACCEPT"
                        and replacement_blueprints_created < max_replacements
                    ):
                        bp.status = "failed"
                        replacement_blueprints_created += 1
                        max_seq = len(blueprints_by_id) + replacement_blueprints_created
                        replacement_bp = await self.create_replacement_blueprint(
                            session,
                            assessment=assessment,
                            failed_blueprint=bp,
                            user_id=user_id,
                            sequence_number=max_seq,
                        )
                        if replacement_bp:
                            blueprints_by_id[replacement_bp.id] = replacement_bp
                            rep_q_list, _ = await self.generation_agent.generate_batch_questions(
                                session,
                                blueprints=[replacement_bp],
                                document_id=assessment.document_id,
                                user_id=user_id,
                                topic_lookup=topic_lookup,
                                concept_lookup=concept_lookup,
                                retry_attempt=1,
                            )
                            if rep_q_list:
                                rep_q = rep_q_list[0]
                                _, _ = await self.evaluate_single_question(
                                    session,
                                    question=rep_q,
                                    blueprint=replacement_bp,
                                    available_chunks=all_chunks,
                                    peer_questions=active_questions,
                                    user_id=user_id,
                                )

            # 5. Duplicate Detection & Control Across Approved/Active Questions
            all_current_q_stmt = (
                select(Question)
                .where(
                    Question.assessment_id == assessment_id,
                    Question.user_id == user_id,
                    Question.status == "approved",
                )
            )
            all_curr_res = await session.execute(all_current_q_stmt)
            approved_questions = list(all_curr_res.scalars().all())

            if len(approved_questions) > 1:
                duplicate_matches = await detect_assessment_duplicates(
                    approved_questions,
                    threshold=self.settings.EVALUATION_DUPLICATE_SIMILARITY_THRESHOLD,
                )
                if duplicate_matches:
                    logger.info(
                        f"Detected {len(duplicate_matches)} duplicate pairs; executing conflict resolution."
                    )
                    questions_map = {q.id: q for q in approved_questions}
                    _, discard_ids = resolve_duplicate_conflicts(duplicate_matches, questions_map)

                    for discard_id in discard_ids:
                        discarded_q = questions_map.get(discard_id)
                        if discarded_q:
                            discarded_q.status = "rejected"
                            logger.info(
                                f"Marked duplicate question {discard_id} as rejected."
                            )

            # 6. Final Assessment Aggregation & Metrics
            final_q_stmt = (
                select(Question)
                .options(selectinload(Question.evaluations))
                .where(Question.assessment_id == assessment_id, Question.user_id == user_id)
                .order_by(Question.created_at.asc())
            )
            final_q_res = await session.execute(final_q_stmt)
            all_assessment_questions = list(final_q_res.scalars().all())

            accepted_questions = [q for q in all_assessment_questions if q.status == "approved"]
            refined_questions = [q for q in all_assessment_questions if q.version > 1]
            rejected_questions = [q for q in all_assessment_questions if q.status == "rejected"]

            total_q_count = len(all_assessment_questions)
            accepted_count = len(accepted_questions)

            avg_score = (
                float(
                    sum(q.quality_score or Decimal("0.0") for q in accepted_questions)
                    / len(accepted_questions)
                )
                if accepted_questions
                else 0.0
            )

            assessment.metrics = {
                "total_questions": total_q_count,
                "accepted_questions": accepted_count,
                "refined_questions": len(refined_questions),
                "rejected_questions": len(rejected_questions),
                "average_quality_score": round(avg_score, 2),
                "replacement_blueprints_created": replacement_blueprints_created,
            }
            assessment.progress = Decimal("100.00")
            assessment.status = "ready" if accepted_count > 0 else "failed"

            await session.commit()

            # Format Response Data
            response_items: list[QuestionWithEvaluationsData] = []
            for q in all_assessment_questions:
                eval_records = [
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
                    for e in q.evaluations
                ]

                response_items.append(
                    QuestionWithEvaluationsData(
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
                        source_chunk_ids=list(q.source_chunk_ids or []),
                        source_pages=list(q.source_pages or []),
                        supporting_evidence=dict(q.supporting_evidence or {}),
                        status=q.status,
                        version=q.version,
                        generation_attempts=q.generation_attempts,
                        quality_score=float(q.quality_score) if q.quality_score is not None else None,
                        created_at=q.created_at,
                        evaluations=eval_records,
                    )
                )

            return AssessmentEvaluationSummary(
                assessment_id=assessment_id,
                total_questions=total_q_count,
                accepted_count=accepted_count,
                refined_count=len(refined_questions),
                regenerated_count=len(rejected_questions),
                failed_count=len(rejected_questions),
                average_quality_score=round(avg_score, 2),
                status=assessment.status,
                questions=response_items,
            )

        except Exception as exc:
            await session.rollback()
            logger.error(
                "Assessment evaluation failed with unhandled exception, transaction rolled back",
                extra={"assessment_id": str(assessment_id), "error": str(exc)},
            )
            raise
