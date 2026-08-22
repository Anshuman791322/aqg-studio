"""Integration tests for LangGraph workflows, PostgreSQL job runner, crash recovery, and resumability."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.evaluation_agent import EvaluationAgent
from app.agents.knowledge_agent import KnowledgeAnalysisAgent
from app.embeddings.fake import FakeEmbeddingProvider
from app.llm.fake import FakeLLMProvider
from app.models.entities import (
    Assessment,
    Document,
    DocumentChunk,
    Job,
    Question,
    QuestionBlueprint,
    Topic,
)
from app.orchestration.assessment_flow import assessment_workflow
from app.orchestration.document_flow import document_workflow
from app.orchestration.runner import PostgresJobRunner


@pytest.mark.asyncio
async def test_document_langgraph_workflow_end_to_end() -> None:
    """Verify complete 7-node Document LangGraph workflow execution with Fake providers."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    fake_llm = FakeLLMProvider(
        scripted_responses=[
            {
                "summary": "Document on system architectures.",
                "estimated_difficulty": "medium",
                "topics": [
                    {
                        "name": "Microservices",
                        "description": "Architectural principles of microservices.",
                        "importance_score": 0.95,
                        "order_index": 1,
                        "concepts": [
                            {
                                "name": "Service Discovery",
                                "definition": "Locating services dynamically.",
                                "importance_score": 0.9,
                                "difficulty": "medium",
                                "source_chunk_ids": [str(doc_id)],
                            }
                        ],
                        "source_chunk_ids": [str(doc_id)],
                    }
                ],
                "learning_objectives": [
                    {
                        "bloom_level": "understand",
                        "description": "Understand microservice decomposition patterns.",
                        "source_chunk_ids": [str(doc_id)],
                    }
                ],
                "key_facts": [
                    {
                        "fact": "Services should be loosely coupled.",
                        "importance_score": 0.95,
                        "source_chunk_ids": [str(doc_id)],
                    }
                ],
            }
        ]
    )
    fake_embed = FakeEmbeddingProvider()
    knowledge_agent = KnowledgeAnalysisAgent(llm_provider=fake_llm)

    mock_doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="architecture.txt",
        storage_path=f"{user_id}/{doc_id}/architecture.txt",
        mime_type="text/plain",
        size_bytes=256,
        status="queued",
    )

    created_chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        chunk_index=0,
        content="Microservices provide scalability and fault isolation.",
        token_count=10,
        content_hash="hash1",
    )

    created_topic = Topic(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        name="Microservices",
        description="Architectural principles.",
        importance_score=Decimal("0.95"),
    )

    mock_session = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    initial_state = {
        "document_id": str(doc_id),
        "user_id": str(user_id),
        "raw_bytes": b"# System Architectures\n\nMicroservices provide scalability and fault isolation.",
        "current_step": "validate_document",
        "progress": 0.0,
    }

    config = {
        "configurable": {
            "session": mock_session,
            "embedding_provider": fake_embed,
            "knowledge_agent": knowledge_agent,
        }
    }

    with (
        patch("app.orchestration.document_flow.document_repo.get_by_id", AsyncMock(return_value=mock_doc)),
        patch("app.orchestration.document_flow.document_repo.update", AsyncMock(return_value=mock_doc)),
        patch("app.orchestration.document_flow.chunk_repo.list_by_document", AsyncMock(side_effect=[[], [created_chunk]])),
        patch("app.orchestration.document_flow.chunk_repo.delete_by_document", AsyncMock(return_value=True)),
        patch("app.orchestration.document_flow.chunk_repo.create_batch", AsyncMock(return_value=[created_chunk])),
        patch.object(knowledge_agent, "analyze_document", AsyncMock()),
    ):
        # Mock Topic query in analyze_knowledge node
        mock_topic_res = MagicMock()
        mock_topic_res.scalars.return_value.all.return_value = [created_topic]
        mock_session.execute.return_value = mock_topic_res

        final_state = await document_workflow.ainvoke(initial_state, config=config)

        assert final_state["current_step"] == "finalize_document"
        assert final_state["progress"] == 100.0
        assert len(final_state.get("chunk_ids", [])) == 1
        assert len(final_state.get("topic_ids", [])) == 1


@pytest.mark.asyncio
async def test_assessment_langgraph_workflow_end_to_end() -> None:
    """Verify complete 10-node Assessment LangGraph workflow execution with exact question quotas."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    bp_id = uuid.uuid4()
    q_id = uuid.uuid4()

    mock_doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="doc.txt",
        status="ready",
    )

    mock_assessment = Assessment(
        id=assessment_id,
        document_id=doc_id,
        user_id=user_id,
        name="Microservices Quiz",
        status="queued",
        progress=Decimal("0.00"),
        configuration={"total_questions": 1},
    )

    mock_bp = QuestionBlueprint(
        id=bp_id,
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="mcq_single",
        difficulty="medium",
        bloom_level="understand",
        learning_objective="Understand service discovery",
        source_chunk_ids=[chunk_id],
        status="planned",
        sequence_number=1,
    )

    mock_question = Question(
        id=q_id,
        assessment_id=assessment_id,
        blueprint_id=bp_id,
        user_id=user_id,
        question_type="mcq_single",
        question_text="What is service discovery?",
        options=[{"key": "A", "text": "Locating services"}],
        correct_answer="A",
        explanation="Dynamic lookup",
        status="approved",
        quality_score=Decimal("0.92"),
        version=1,
    )
    mock_question.evaluations = [MagicMock()]  # Mark as already evaluated

    mock_session = AsyncMock()
    mock_session.get.return_value = mock_doc
    mock_session.commit = AsyncMock()
    mock_session.flush = AsyncMock()

    initial_state = {
        "assessment_id": str(assessment_id),
        "document_id": str(doc_id),
        "user_id": str(user_id),
        "target_questions": 1,
        "current_step": "load_assessment",
        "progress": 0.0,
    }

    fake_eval_llm = FakeLLMProvider(
        scripted_responses=[
            {
                "correctness": 0.95,
                "groundedness": 0.95,
                "relevance": 0.95,
                "clarity": 0.95,
                "grammar": 0.95,
                "answerability": 0.95,
                "difficulty_alignment": 0.95,
                "bloom_alignment": 0.95,
                "distractor_quality": 0.95,
                "duplication_risk": 0.05,
                "overall_quality": 0.95,
                "decision": "ACCEPT",
                "critique": "Excellent question.",
                "recommendations": [],
            }
        ]
    )
    eval_agent = EvaluationAgent(llm_provider=fake_eval_llm)

    config = {
        "configurable": {
            "session": mock_session,
            "evaluation_agent": eval_agent,
        }
    }

    with (
        patch("app.orchestration.assessment_flow.assessment_repo.get_by_id", AsyncMock(return_value=mock_assessment)),
        patch("app.orchestration.assessment_flow.blueprint_repo.list_by_assessment", AsyncMock(return_value=[mock_bp])),
        patch("app.orchestration.assessment_flow.question_repo.list_by_assessment", AsyncMock(return_value=[mock_question])),
        patch("app.orchestration.assessment_flow.detect_assessment_duplicates", AsyncMock(return_value=[])),
    ):
        mock_chunks_res = MagicMock()
        mock_chunks_res.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_chunks_res

        final_state = await assessment_workflow.ainvoke(initial_state, config=config)

        assert final_state["current_step"] == "finalize_assessment"
        assert final_state["progress"] == 100.0
        assert len(final_state.get("accepted_question_ids", [])) == 1
        assert final_state.get("average_quality_score") == 0.92


@pytest.mark.asyncio
async def test_worker_transactional_claim_and_enqueue() -> None:
    """Verify atomic job claiming and duplicate job prevention."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job = Job(
        id=job_id,
        user_id=user_id,
        resource_type="document",
        resource_id=doc_id,
        job_type="document_processing",
        status="queued",
        attempts=0,
    )

    runner = PostgresJobRunner()
    mock_session = AsyncMock()

    with (
        patch("app.orchestration.runner.job_repo.get_active_job", AsyncMock(side_effect=[None, mock_job])),
    ):
        # 1. First enqueue creates new job
        job1 = await runner.enqueue_job(
            mock_session,
            user_id=user_id,
            resource_type="document",
            resource_id=doc_id,
            job_type="document_processing",
        )
        assert job1.status == "queued"
        assert job1.resource_id == doc_id

        # 2. Second enqueue returns existing active job
        job2 = await runner.enqueue_job(
            mock_session,
            user_id=user_id,
            resource_type="document",
            resource_id=doc_id,
            job_type="document_processing",
        )
        assert job2.id == mock_job.id

    # 3. Transactional Claim
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_result

    claimed = await runner.claim_next_job(mock_session)
    assert claimed is not None
    assert claimed.status == "running"
    assert claimed.locked_at is not None
    assert claimed.heartbeat_at is not None
    assert claimed.attempts == 1


@pytest.mark.asyncio
async def test_startup_crash_recovery() -> None:
    """Verify stale running jobs from crashed process instances are recovered to queued state."""
    runner = PostgresJobRunner()
    mock_session = AsyncMock()
    mock_res = MagicMock()
    mock_res.rowcount = 2
    mock_session.execute.return_value = mock_res

    recovered = await runner.recover_stale_running_jobs(mock_session)
    assert recovered == 2
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_job_cancellation() -> None:
    """Verify job cancellation updates status and error metadata."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    runner = PostgresJobRunner()
    mock_session = AsyncMock()

    mock_job = Job(
        id=uuid.uuid4(),
        user_id=user_id,
        resource_type="assessment",
        resource_id=assessment_id,
        job_type="question_generation",
        status="running",
    )

    with patch("app.orchestration.runner.job_repo.get_active_job", AsyncMock(return_value=mock_job)):
        cancelled = await runner.cancel_job(
            mock_session,
            resource_type="assessment",
            resource_id=assessment_id,
            user_id=user_id,
        )
        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert cancelled.error_code == "USER_CANCELLED"
        assert mock_session.commit.called
