"""LangGraph compiled workflow for Assessment Blueprint Planning, Generation, Evaluation, Refinement, and Dedup."""

import uuid
from decimal import Decimal
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agents.evaluation_agent import EvaluationAgent
from app.agents.question_generation_agent import QuestionGenerationAgent
from app.core.config import get_settings
from app.core.logging import get_logger
from app.evaluation.duplication import (
    detect_assessment_duplicates,
    resolve_duplicate_conflicts,
)
from app.models.entities import (
    Concept,
    Document,
    DocumentChunk,
    QuestionBlueprint,
    Topic,
)
from app.orchestration.schemas import AssessmentGraphState
from app.repositories.assessment import assessment_repo
from app.repositories.blueprint import blueprint_repo
from app.repositories.question import question_repo

logger = get_logger("aqg.orchestration.assessment_flow")
settings = get_settings()


async def node_load_assessment(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 1: Verify assessment entity, document readiness, and target question count."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    user_id = uuid.UUID(state["user_id"])

    logger.info("Executing node_load_assessment", extra={"assessment_id": str(assessment_id)})
    assessment = await assessment_repo.get_by_id(session, id=assessment_id, user_id=user_id)
    if not assessment:
        raise ValueError(f"Assessment '{assessment_id}' not found for user '{user_id}'.")

    # Verify document exists and is ready
    doc = await session.get(Document, assessment.document_id)
    if not doc or doc.status != "ready":
        raise ValueError(f"Underlying document '{assessment.document_id}' is not in 'ready' state.")

    target_q = int(dict(assessment.configuration or {}).get("total_questions", 10))

    return {
        "document_id": str(assessment.document_id),
        "target_questions": target_q,
        "current_step": "load_assessment",
        "progress": 5.0,
    }


async def node_create_or_load_blueprints(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 2: Plan blueprints deterministically if not already created."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    doc_id = uuid.UUID(state["document_id"])
    user_id = uuid.UUID(state["user_id"])

    # Idempotent check: if blueprints already exist for this assessment, load them
    existing_bps = await blueprint_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    if existing_bps:
        bp_ids = [str(bp.id) for bp in existing_bps]
        return {
            "blueprint_ids": bp_ids,
            "current_step": "create_or_load_blueprints",
            "progress": 15.0,
        }

    assessment = await assessment_repo.get_by_id(session, id=assessment_id, user_id=user_id)
    if not assessment:
        raise ValueError(f"Assessment '{assessment_id}' not found.")

    topics_stmt = (
        select(Topic)
        .where(Topic.document_id == doc_id, Topic.user_id == user_id)
        .options(selectinload(Topic.concepts))
        .order_by(Topic.importance_score.desc(), Topic.created_at.asc())
    )
    topics_res = await session.execute(topics_stmt)
    available_topics = list(topics_res.scalars().all())

    config_dict = dict(assessment.configuration or {})
    target_count = state.get("target_questions", 10)

    from app.planning.allocator import build_blueprint_slots

    slots = build_blueprint_slots(
        total_questions=target_count,
        topics=available_topics,
        type_distribution=config_dict.get("question_type_distribution"),
        difficulty_distribution=config_dict.get("difficulty_distribution"),
        bloom_distribution=config_dict.get("bloom_distribution"),
    )

    created_bps = []
    for slot in slots:
        concept_meta = dict(slot.concept.metadata_ or {}) if slot.concept else {}
        topic_meta = dict(slot.topic.metadata_ or {})
        source_chunk_ids = [
            uuid.UUID(cid) if isinstance(cid, str) else cid
            for cid in (concept_meta.get("source_chunk_ids") or topic_meta.get("source_chunk_ids") or [doc_id])
        ]
        target_name = slot.concept.name if slot.concept else slot.topic.name
        bp_id = uuid.uuid4()
        bp = QuestionBlueprint(
            id=bp_id,
            assessment_id=assessment_id,
            user_id=user_id,
            topic_id=slot.topic.id,
            concept_id=slot.concept.id if slot.concept else None,
            question_type=slot.question_type,
            difficulty=slot.difficulty,
            bloom_level=slot.bloom_level,
            learning_objective=f"Understand key mechanisms of {target_name}.",
            source_chunk_ids=source_chunk_ids,
            status="planned",
            sequence_number=slot.sequence_number,
        )
        session.add(bp)
        created_bps.append(bp)

    await session.flush()
    bp_ids = [str(bp.id) for bp in created_bps]

    return {
        "blueprint_ids": bp_ids,
        "current_step": "create_or_load_blueprints",
        "progress": 15.0,
    }


async def node_retrieve_and_generate_batches(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 3: Execute batched RAG retrieval and question drafting."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    doc_id = uuid.UUID(state["document_id"])
    user_id = uuid.UUID(state["user_id"])

    # Idempotent check: if draft/approved questions already generated, load their IDs
    existing_qs = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    if existing_qs:
        q_ids = [str(q.id) for q in existing_qs]
        return {
            "generated_question_ids": q_ids,
            "current_step": "retrieve_and_generate_batches",
            "progress": 40.0,
        }

    # Fetch blueprints
    bps = await blueprint_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    topics_res = await session.execute(
        select(Topic).where(Topic.document_id == doc_id, Topic.user_id == user_id)
    )
    topic_lookup = {t.id: t for t in topics_res.scalars().all()}

    concepts_res = await session.execute(
        select(Concept).where(Concept.document_id == doc_id, Concept.user_id == user_id)
    )
    concept_lookup = {c.id: c for c in concepts_res.scalars().all()}

    gen_agent = configurable.get("generation_agent") or QuestionGenerationAgent()

    saved_questions, _ = await gen_agent.generate_batch_questions(
        session=session,
        blueprints=list(bps),
        document_id=doc_id,
        user_id=user_id,
        topic_lookup=topic_lookup,
        concept_lookup=concept_lookup,
    )
    await session.flush()

    q_ids = [str(q.id) for q in saved_questions]
    return {
        "generated_question_ids": q_ids,
        "current_step": "retrieve_and_generate_batches",
        "progress": 40.0,
    }


async def node_evaluate_batches(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 4: Run deterministic and LLM evaluation scorecards across candidate questions."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    user_id = uuid.UUID(state["user_id"])

    eval_agent = configurable.get("evaluation_agent") or EvaluationAgent()

    questions = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    bps = await blueprint_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    bp_map = {bp.id: bp for bp in bps}

    chunks_res = await session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == uuid.UUID(state["document_id"]))
    )
    all_chunks = list(chunks_res.scalars().all())

    for q in questions:
        # If question is already evaluated and approved, skip
        if q.status == "approved" and q.evaluations:
            continue
        bp = bp_map.get(q.blueprint_id) if q.blueprint_id else None
        await eval_agent.evaluate_single_question(
            session,
            question=q,
            blueprint=bp,
            available_chunks=all_chunks,
            peer_questions=list(questions),
            user_id=user_id,
        )

    await session.flush()

    return {
        "current_step": "evaluate_batches",
        "progress": 55.0,
    }


async def node_route_failed_questions(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 5: Categorize questions by acceptance, refinement need, or rejection."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    user_id = uuid.UUID(state["user_id"])

    questions = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)

    accepted = [str(q.id) for q in questions if q.status == "approved"]
    rejected = [str(q.id) for q in questions if q.status in ("rejected", "flagged")]

    return {
        "accepted_question_ids": accepted,
        "rejected_question_ids": rejected,
        "current_step": "route_failed_questions",
        "progress": 65.0,
    }


async def node_refine_or_regenerate(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 6: Execute multi-pass refinement and fresh regeneration loops."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    doc_id = uuid.UUID(state["document_id"])
    user_id = uuid.UUID(state["user_id"])

    eval_agent = configurable.get("evaluation_agent") or EvaluationAgent()

    questions = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    bps = await blueprint_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    bp_map = {bp.id: bp for bp in bps}

    chunks_res = await session.execute(
        select(DocumentChunk).where(DocumentChunk.document_id == doc_id)
    )
    all_chunks = list(chunks_res.scalars().all())

    for q in questions:
        if q.status == "flagged":
            # Attempt refinement
            await eval_agent.refine_single_question(
                session,
                question=q,
                blueprint=bp_map.get(q.blueprint_id) if q.blueprint_id else None,
                available_chunks=all_chunks,
                user_id=user_id,
            )

    await session.flush()

    # Re-query questions to update accepted IDs
    updated_qs = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    accepted = [str(q.id) for q in updated_qs if q.status == "approved"]

    return {
        "accepted_question_ids": accepted,
        "current_step": "refine_or_regenerate",
        "progress": 75.0,
    }


async def node_deduplicate(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 7: Detect exact, lexical, and semantic duplicates among approved questions."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    user_id = uuid.UUID(state["user_id"])

    questions = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    approved_qs = [q for q in questions if q.status == "approved"]

    if len(approved_qs) > 1:
        dup_matches = await detect_assessment_duplicates(
            approved_qs,
            threshold=settings.EVALUATION_DUPLICATE_SIMILARITY_THRESHOLD,
        )
        if dup_matches:
            q_map = {q.id: q for q in approved_qs}
            _, discard_ids = resolve_duplicate_conflicts(dup_matches, q_map)
            for d_id in discard_ids:
                d_q = q_map.get(d_id)
                if d_q:
                    d_q.status = "rejected"
            await session.flush()

    # Refresh accepted list
    final_qs = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    accepted = [str(q.id) for q in final_qs if q.status == "approved"]

    return {
        "accepted_question_ids": accepted,
        "current_step": "deduplicate",
        "progress": 82.0,
    }


async def node_verify_requested_count(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 8: Verify accepted question count matches requested target; create replacements if needed."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    doc_id = uuid.UUID(state["document_id"])
    user_id = uuid.UUID(state["user_id"])
    target_count = state.get("target_questions", 10)

    questions = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    accepted_qs = [q for q in questions if q.status == "approved"]
    current_accepted = len(accepted_qs)

    replacement_count = state.get("replacement_count", 0)
    max_replacements = settings.EVALUATION_MAX_REPLACEMENT_BLUEPRINTS

    if current_accepted < target_count and replacement_count < max_replacements:
        eval_agent = configurable.get("evaluation_agent") or EvaluationAgent()
        assessment = await assessment_repo.get_by_id(session, id=assessment_id, user_id=user_id)
        bps = await blueprint_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
        if assessment and bps:
            needed = min(target_count - current_accepted, max_replacements - replacement_count)
            for i in range(needed):
                failed_bp = bps[0]
                rep_bp = await eval_agent.create_replacement_blueprint(
                    session,
                    assessment=assessment,
                    failed_blueprint=failed_bp,
                    user_id=user_id,
                    sequence_number=len(bps) + replacement_count + 1 + i,
                )
                if rep_bp:
                    replacement_count += 1
                    # Generate item for replacement blueprint
                    topics_res = await session.execute(
                        select(Topic).where(Topic.document_id == doc_id, Topic.user_id == user_id)
                    )
                    topic_lookup = {t.id: t for t in topics_res.scalars().all()}
                    concepts_res = await session.execute(
                        select(Concept).where(Concept.document_id == doc_id, Concept.user_id == user_id)
                    )
                    concept_lookup = {c.id: c for c in concepts_res.scalars().all()}

                    saved_q_list, _ = await eval_agent.generation_agent.generate_batch_questions(
                        session=session,
                        blueprints=[rep_bp],
                        document_id=doc_id,
                        user_id=user_id,
                        topic_lookup=topic_lookup,
                        concept_lookup=concept_lookup,
                    )
                    if saved_q_list:
                        new_q = saved_q_list[0]
                        await eval_agent.evaluate_single_question(
                            session,
                            question=new_q,
                            blueprint=rep_bp,
                            user_id=user_id,
                        )
            await session.flush()

    # Re-count accepted
    final_qs = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    accepted = [str(q.id) for q in final_qs if q.status == "approved"]

    return {
        "accepted_question_ids": accepted,
        "replacement_count": replacement_count,
        "current_step": "verify_requested_count",
        "progress": 90.0,
    }


async def node_calculate_metrics(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 9: Calculate overall assessment statistics and average quality score."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    user_id = uuid.UUID(state["user_id"])

    questions = await question_repo.list_by_assessment(session, assessment_id=assessment_id, user_id=user_id)
    accepted_qs = [q for q in questions if q.status == "approved"]
    refined_qs = [q for q in questions if q.version > 1]
    rejected_qs = [q for q in questions if q.status == "rejected"]

    avg_score = (
        float(sum(q.quality_score or Decimal("0.0") for q in accepted_qs) / len(accepted_qs))
        if accepted_qs
        else 0.0
    )

    assessment = await assessment_repo.get_by_id(session, id=assessment_id, user_id=user_id)
    if assessment:
        assessment.metrics = {
            "total_questions": len(questions),
            "accepted_questions": len(accepted_qs),
            "refined_questions": len(refined_qs),
            "rejected_questions": len(rejected_qs),
            "average_quality_score": round(avg_score, 2),
            "replacement_blueprints_created": state.get("replacement_count", 0),
        }
        await session.flush()

    return {
        "average_quality_score": round(avg_score, 2),
        "current_step": "calculate_metrics",
        "progress": 95.0,
    }


async def node_finalize_assessment(state: AssessmentGraphState, config: RunnableConfig) -> dict[str, Any]:
    """Node 10: Finalize assessment status to ready and progress to 100%."""
    configurable = config.get("configurable", {})
    session: AsyncSession = configurable["session"]
    assessment_id = uuid.UUID(state["assessment_id"])
    user_id = uuid.UUID(state["user_id"])

    assessment = await assessment_repo.get_by_id(session, id=assessment_id, user_id=user_id)
    if assessment:
        accepted_count = len(state.get("accepted_question_ids", []))
        assessment.status = "ready" if accepted_count > 0 else "failed"
        assessment.progress = Decimal("100.00")
        await session.commit()

    return {
        "current_step": "finalize_assessment",
        "progress": 100.0,
    }


# ------------------------------------------------------------------------------
# Build and Compile Assessment StateGraph
# ------------------------------------------------------------------------------
def build_assessment_workflow() -> Any:
    """Construct and compile the 10-node Assessment Generation StateGraph."""
    builder = StateGraph(AssessmentGraphState)

    builder.add_node("load_assessment", node_load_assessment)
    builder.add_node("create_or_load_blueprints", node_create_or_load_blueprints)
    builder.add_node("retrieve_and_generate_batches", node_retrieve_and_generate_batches)
    builder.add_node("evaluate_batches", node_evaluate_batches)
    builder.add_node("route_failed_questions", node_route_failed_questions)
    builder.add_node("refine_or_regenerate", node_refine_or_regenerate)
    builder.add_node("deduplicate", node_deduplicate)
    builder.add_node("verify_requested_count", node_verify_requested_count)
    builder.add_node("calculate_metrics", node_calculate_metrics)
    builder.add_node("finalize_assessment", node_finalize_assessment)

    builder.add_edge(START, "load_assessment")
    builder.add_edge("load_assessment", "create_or_load_blueprints")
    builder.add_edge("create_or_load_blueprints", "retrieve_and_generate_batches")
    builder.add_edge("retrieve_and_generate_batches", "evaluate_batches")
    builder.add_edge("evaluate_batches", "route_failed_questions")
    builder.add_edge("route_failed_questions", "refine_or_regenerate")
    builder.add_edge("refine_or_regenerate", "deduplicate")
    builder.add_edge("deduplicate", "verify_requested_count")
    builder.add_edge("verify_requested_count", "calculate_metrics")
    builder.add_edge("calculate_metrics", "finalize_assessment")
    builder.add_edge("finalize_assessment", END)

    return builder.compile()


assessment_workflow = build_assessment_workflow()
