"""Unit tests for Output & Report Agent and deterministic pedagogical metrics calculation."""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.output_report_agent import output_report_agent
from app.models.entities import Assessment, Document, Evaluation, Question, QuestionBlueprint, Topic
from app.reporting.calculator import calculate_assessment_report, calculate_distribution_counts


def test_calculate_distribution_counts_math():
    """Verify exact count and percentage calculation across discrete categories."""
    items = ["mcq_single", "mcq_single", "mcq_multi", "true_false"]
    valid_keys = ["mcq_single", "mcq_multi", "true_false", "short_answer", "descriptive"]

    dist = calculate_distribution_counts(items, valid_keys)
    assert dist["mcq_single"].count == 2
    assert dist["mcq_single"].percentage == 50.0
    assert dist["mcq_multi"].count == 1
    assert dist["mcq_multi"].percentage == 25.0
    assert dist["true_false"].count == 1
    assert dist["true_false"].percentage == 25.0
    assert dist["short_answer"].count == 0
    assert dist["short_answer"].percentage == 0.0


def test_calculate_assessment_report_metrics():
    """Verify deterministic aggregation of quality averages, topic coverage, and distributions."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    assessment_id = uuid.uuid4()

    doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="Photosynthesis.pdf",
        storage_path=f"{user_id}/{doc_id}/Photosynthesis.pdf",
        size_bytes=1024,
        mime_type="application/pdf",
        status="parsed",
    )

    assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=doc_id,
        name="Photosynthesis Assessment",
        configuration={"total_questions": 4},
        status="ready",
        metrics={"duplicate_count": 1, "regeneration_count": 2},
    )

    blueprints = [
        QuestionBlueprint(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            user_id=user_id,
            question_type="mcq_single",
            difficulty="easy",
            bloom_level="remember",
            sequence_number=1,
            status="generated",
        ),
        QuestionBlueprint(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            user_id=user_id,
            question_type="short_answer",
            difficulty="hard",
            bloom_level="analyze",
            sequence_number=2,
            status="failed",
        ),
    ]

    q1 = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        blueprint_id=blueprints[0].id,
        user_id=user_id,
        question_type="mcq_single",
        question_text="What pigment absorbs blue and red light?",
        correct_answer="A",
        explanation="Chlorophyll a absorbs primarily blue and red light.",
        topic="Light Reactions",
        difficulty="easy",
        bloom_level="remember",
        status="approved",
        version=1,
        generation_attempts=1,
        quality_score=Decimal("0.96"),
    )

    q2 = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="true_false",
        question_text="Calvin cycle produces ATP.",
        correct_answer="False",
        explanation="Calvin cycle consumes ATP.",
        topic="Dark Reactions",
        difficulty="medium",
        bloom_level="understand",
        status="rejected",
        version=2,  # Refined
        generation_attempts=2,  # Regenerated
        quality_score=Decimal("0.80"),
    )

    eval1 = Evaluation(
        id=uuid.uuid4(),
        question_id=q1.id,
        user_id=user_id,
        correctness_score=Decimal("1.00"),
        grounding_score=Decimal("0.98"),
        clarity_score=Decimal("0.95"),
        distractor_quality_score=Decimal("0.92"),
        overall_quality_score=Decimal("0.96"),
        decision="ACCEPT",
    )

    topics = [
        Topic(id=uuid.uuid4(), document_id=doc_id, user_id=user_id, name="Light Reactions", importance_score=Decimal("1.0")),
        Topic(id=uuid.uuid4(), document_id=doc_id, user_id=user_id, name="Dark Reactions", importance_score=Decimal("0.8")),
        Topic(id=uuid.uuid4(), document_id=doc_id, user_id=user_id, name="Photorespiration", importance_score=Decimal("0.6")),
    ]

    report = calculate_assessment_report(
        assessment=assessment,
        document=doc,
        questions=[q1, q2],
        blueprints=blueprints,
        evaluations=[eval1],
        topics=topics,
    )

    assert report.assessment_id == assessment_id
    assert report.document_filename == "Photosynthesis.pdf"
    assert report.metrics.total_requested == 4
    assert report.metrics.total_generated == 2
    assert report.metrics.total_accepted == 1
    assert report.metrics.total_rejected == 1
    assert report.metrics.approval_rate == 50.0
    assert report.metrics.average_overall_quality == 0.88
    assert report.metrics.average_groundedness == 0.98
    assert report.metrics.number_refined == 1
    assert report.metrics.number_regenerated >= 1
    assert report.metrics.failed_blueprints == 1

    # Topic coverage verification
    cov_dict = {t.topic_name: t for t in report.topic_coverage}
    assert cov_dict["Light Reactions"].is_covered is True
    assert cov_dict["Light Reactions"].question_count == 1
    assert cov_dict["Photorespiration"].is_covered is False
    assert cov_dict["Photorespiration"].question_count == 0


@pytest.mark.asyncio
async def test_output_report_agent_fetch_and_assemble():
    """Verify OutputReportAgent entity retrieval and report calculation."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    assessment_id = uuid.uuid4()

    mock_doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="Cellular_Bio.pdf",
        storage_path=f"{user_id}/Cellular_Bio.pdf",
        size_bytes=2048,
        mime_type="application/pdf",
        status="parsed",
    )

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=doc_id,
        name="Cell Biology Quiz",
        configuration={"total_questions": 2},
        status="ready",
    )

    mock_q = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="mcq_single",
        question_text="Where is the electron transport chain located?",
        options=[
            {"key": "A", "text": "Inner mitochondrial membrane", "is_correct": True},
            {"key": "B", "text": "Outer membrane", "is_correct": False},
        ],
        correct_answer="A",
        explanation="The ETC complexes are embedded in the inner mitochondrial membrane.",
        topic="Mitochondria",
        difficulty="medium",
        bloom_level="remember",
        status="approved",
        quality_score=Decimal("0.98"),
    )

    mock_session = AsyncMock()

    with (
        patch("app.agents.output_report_agent.assessment_repo.get_by_id", new=AsyncMock(return_value=mock_assessment)),
        patch("app.agents.output_report_agent.document_repo.get_by_id", new=AsyncMock(return_value=mock_doc)),
        patch("app.agents.output_report_agent.question_repo.list_by_assessment", new=AsyncMock(return_value=[mock_q])),
        patch("app.agents.output_report_agent.blueprint_repo.list_by_assessment", new=AsyncMock(return_value=[])),
        patch("app.agents.output_report_agent.evaluation_repo.list_by_question", new=AsyncMock(return_value=[])),
        patch("app.agents.output_report_agent.topic_repo.list_by_document", new=AsyncMock(return_value=[])),
        patch("app.agents.output_report_agent.export_repo.list_by_assessment", new=AsyncMock(return_value=[])),
    ):
        report = await output_report_agent.generate_assessment_report(
            mock_session,
            assessment_id=assessment_id,
            user_id=user_id,
        )

    assert report.assessment_name == "Cell Biology Quiz"
    assert report.metrics.total_accepted == 1
    assert report.metrics.approval_rate == 100.0
    assert report.metrics.average_overall_quality == 0.98
