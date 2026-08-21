"""Unit and integration tests for Question Planning Agent and allocator."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.agents.planning_agent import QuestionPlanningAgent
from app.llm.fake import FakeLLMProvider
from app.models.entities import Concept, Document, LearningObjective, Topic
from app.planning.allocator import (
    build_blueprint_slots,
    largest_remainder_distribution,
)
from app.planning.schemas import AssessmentCreateRequest


# ------------------------------------------------------------------------------
# 1. Largest Remainder Method & Quota Math Tests
# ------------------------------------------------------------------------------
def test_largest_remainder_exact_total_and_rounding() -> None:
    """Verify Largest Remainder method yields exact integer sum across various distributions."""
    weights = {"mcq": 33.333, "short_answer": 33.333, "true_false": 33.334}

    for total in [1, 3, 7, 10, 25, 50]:
        alloc = largest_remainder_distribution(total, weights)
        assert sum(alloc.values()) == total
        assert all(isinstance(v, int) for v in alloc.values())


def test_largest_remainder_empty_or_zero_weights_fallback() -> None:
    """Verify empty or zero weights fall back safely to default distribution."""
    alloc_empty = largest_remainder_distribution(10, {})
    assert sum(alloc_empty.values()) == 10

    alloc_zeros = largest_remainder_distribution(10, {"easy": 0.0, "hard": 0.0})
    assert sum(alloc_zeros.values()) == 10


def test_largest_remainder_one_item_assessment() -> None:
    """Verify 1-question assessment assigns 1 to highest-remainder category."""
    weights = {"easy": 0.7, "medium": 0.2, "hard": 0.1}
    alloc = largest_remainder_distribution(1, weights)
    assert alloc == {"easy": 1, "medium": 0, "hard": 0}
    assert sum(alloc.values()) == 1


# ------------------------------------------------------------------------------
# 2. Schema Validation for Distribution Keys
# ------------------------------------------------------------------------------
def test_invalid_question_type_distribution_raises_validation_error() -> None:
    """Verify request schema rejects unsupported question types."""
    with pytest.raises(ValidationError) as exc_info:
        AssessmentCreateRequest(
            document_id=uuid.uuid4(),
            name="Invalid Types",
            total_questions=5,
            question_type_distribution={"unsupported_type": 100},
        )
    assert "Unsupported question type" in str(exc_info.value)


def test_invalid_difficulty_distribution_raises_validation_error() -> None:
    """Verify request schema rejects unsupported difficulty levels."""
    with pytest.raises(ValidationError) as exc_info:
        AssessmentCreateRequest(
            document_id=uuid.uuid4(),
            name="Invalid Difficulty",
            total_questions=5,
            difficulty_distribution={"super_hard": 100},
        )
    assert "Unsupported difficulty level" in str(exc_info.value)


def test_invalid_bloom_distribution_raises_validation_error() -> None:
    """Verify request schema rejects unsupported Bloom cognitive levels."""
    with pytest.raises(ValidationError) as exc_info:
        AssessmentCreateRequest(
            document_id=uuid.uuid4(),
            name="Invalid Bloom",
            total_questions=5,
            bloom_distribution={"memorize": 100},
        )
    assert "Unsupported Bloom level" in str(exc_info.value)


# ------------------------------------------------------------------------------
# 3. Slot Skeleton Builder Tests
# ------------------------------------------------------------------------------
def test_build_blueprint_slots_exact_counts_and_stability() -> None:
    """Verify slot builder generates exact requested slot count with valid distributions."""
    topic_1 = Topic(
        id=uuid.uuid4(),
        name="Topic 1",
        importance_score=Decimal("0.8"),
        metadata_={"source_chunk_ids": [str(uuid.uuid4())]},
    )
    topic_1.concepts = [
        Concept(id=uuid.uuid4(), name="Concept 1A", definition="Def 1A", metadata_={}),
        Concept(id=uuid.uuid4(), name="Concept 1B", definition="Def 1B", metadata_={}),
    ]

    topic_2 = Topic(
        id=uuid.uuid4(),
        name="Topic 2",
        importance_score=Decimal("0.6"),
        metadata_={"source_chunk_ids": [str(uuid.uuid4())]},
    )
    topic_2.concepts = []  # Topic with no concepts

    slots = build_blueprint_slots(
        total_questions=15,
        topics=[topic_1, topic_2],
        type_distribution={"mcq": 60, "short_answer": 40},
        difficulty_distribution={"easy": 30, "medium": 50, "hard": 20},
        bloom_distribution={"remember": 40, "understand": 40, "apply": 20},
    )

    assert len(slots) == 15
    assert slots[0].sequence_number == 1
    assert slots[-1].sequence_number == 15

    # Check question types
    mcq_count = sum(1 for s in slots if s.question_type == "mcq_single")
    sa_count = sum(1 for s in slots if s.question_type == "short_answer")
    assert mcq_count == 9  # 60% of 15
    assert sa_count == 6   # 40% of 15
    assert mcq_count + sa_count == 15


# ------------------------------------------------------------------------------
# 4. Question Planning Agent Execution Tests
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_planning_agent_creates_blueprints_without_final_questions() -> None:
    """Verify planning agent outputs structured blueprints without generating question text."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    chunk_id = uuid.uuid4()

    mock_doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="ai_ethics.pdf",
        storage_path=f"{user_id}/{doc_id}/ai_ethics.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
    )

    topic_id = uuid.uuid4()
    concept_id = uuid.uuid4()

    mock_concept = Concept(
        id=concept_id,
        topic_id=topic_id,
        document_id=doc_id,
        user_id=user_id,
        name="Algorithmic Bias",
        definition="Systematic and repeatable errors in a computer system creating unfair outcomes.",
        difficulty="medium",
        metadata_={"source_chunk_ids": [str(chunk_id)]},
    )

    mock_topic = Topic(
        id=topic_id,
        document_id=doc_id,
        user_id=user_id,
        name="Fairness & Transparency",
        description="Core tenets of ethical AI.",
        importance_score=Decimal("0.9"),
        metadata_={"source_chunk_ids": [str(chunk_id)]},
    )
    mock_topic.concepts = [mock_concept]

    mock_objective = LearningObjective(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        bloom_level="analyze",
        description="Analyze causes and mitigations for algorithmic bias in ML models.",
        metadata_={"source_chunk_ids": [str(chunk_id)]},
    )

    fake_refinement = {
        "items": [
            {
                "sequence_number": 1,
                "learning_objective": "Analyze sources of bias in training data.",
                "rationale": "Evaluates analytical comprehension of fairness.",
                "source_chunk_ids": [str(chunk_id)],
            },
            {
                "sequence_number": 2,
                "learning_objective": "Identify transparency mechanisms in ML pipelines.",
                "rationale": "Evaluates recall of ethical guidelines.",
                "source_chunk_ids": [str(chunk_id)],
            },
        ]
    }

    fake_llm = FakeLLMProvider(scripted_responses=[fake_refinement])
    agent = QuestionPlanningAgent(llm_provider=fake_llm)

    request = AssessmentCreateRequest(
        document_id=doc_id,
        name="AI Ethics Midterm",
        total_questions=2,
        question_type_distribution={"mcq": 50, "short_answer": 50},
        difficulty_distribution={"easy": 50, "medium": 50},
        bloom_distribution={"remember": 50, "analyze": 50},
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # Query mocks
    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = mock_doc

    topics_res = MagicMock()
    topics_res.scalars.return_value.all.return_value = [mock_topic]

    objs_res = MagicMock()
    objs_res.scalars.return_value.all.return_value = [mock_objective]

    mock_session.execute.side_effect = [
        doc_res,
        topics_res,
        objs_res,
    ]

    result = await agent.create_assessment_with_blueprint(
        mock_session,
        request=request,
        user_id=user_id,
    )

    assert result.total_questions == 2
    assert len(result.blueprints) == 2
    assert result.status == "draft"

    bp_1 = result.blueprints[0]
    assert bp_1.sequence_number == 1
    assert bp_1.topic_name == "Fairness & Transparency"
    assert bp_1.concept_name == "Algorithmic Bias"
    assert bp_1.learning_objective == "Analyze sources of bias in training data."
    assert bp_1.source_chunk_ids == [chunk_id]

    # Critical Assertion: verify no final question text exists in blueprint
    assert not hasattr(bp_1, "question_text")
    assert not hasattr(bp_1, "options")
    assert not hasattr(bp_1, "correct_answer")


@pytest.mark.asyncio
async def test_planning_agent_rejects_un_analyzed_document() -> None:
    """Verify planning agent raises clear ValueError when document has no topics."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    mock_doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="raw.pdf",
        storage_path=f"{user_id}/{doc_id}/raw.pdf",
        mime_type="application/pdf",
        size_bytes=500,
    )

    agent = QuestionPlanningAgent()
    request = AssessmentCreateRequest(
        document_id=doc_id,
        name="Empty Assessment",
        total_questions=5,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = mock_doc

    topics_res = MagicMock()
    topics_res.scalars.return_value.all.return_value = []  # No topics

    mock_session.execute.side_effect = [
        doc_res,
        topics_res,
    ]

    with pytest.raises(ValueError) as exc_info:
        await agent.create_assessment_with_blueprint(
            mock_session,
            request=request,
            user_id=user_id,
        )

    assert "not been analyzed yet" in str(exc_info.value)


@pytest.mark.asyncio
async def test_planning_agent_rejects_cross_user_document() -> None:
    """Verify planning agent raises NotFound / ValueError if document does not belong to user."""
    attacker_user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    agent = QuestionPlanningAgent()
    request = AssessmentCreateRequest(
        document_id=doc_id,
        name="Hacked Assessment",
        total_questions=5,
    )

    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    doc_res = MagicMock()
    doc_res.scalar_one_or_none.return_value = None  # Document not found for attacker

    mock_session.execute.side_effect = [
        doc_res,
    ]

    with pytest.raises(ValueError) as exc_info:
        await agent.create_assessment_with_blueprint(
            mock_session,
            request=request,
            user_id=attacker_user_id,
        )

    assert "not found for user" in str(exc_info.value)
