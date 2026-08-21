"""Tests for SQLAlchemy ORM model definitions and constraints."""

import uuid
from decimal import Decimal

from app.models.entities import (
    Assessment,
    Concept,
    Document,
    DocumentChunk,
    Evaluation,
    Export,
    Job,
    LearningObjective,
    LLMUsageDaily,
    Profile,
    Question,
    QuestionBlueprint,
    Topic,
)


def test_profile_instantiation() -> None:
    """Verify Profile model field definitions."""
    uid = uuid.uuid4()
    profile = Profile(id=uid, display_name="Dr. Eleanor Vance")
    assert profile.id == uid
    assert profile.display_name == "Dr. Eleanor Vance"
    assert profile.__tablename__ == "profiles"


def test_document_model_defaults() -> None:
    """Verify Document model attributes and table configuration."""
    uid = uuid.uuid4()
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        user_id=uid,
        original_filename="cellular_biology.pdf",
        storage_path=f"{uid}/{doc_id}/cellular_biology.pdf",
        mime_type="application/pdf",
        size_bytes=1048576,
        status="pending",
        page_count=0,
        word_count=0,
        language="en",
        metadata_={},
    )
    assert doc.id == doc_id
    assert doc.user_id == uid
    assert doc.status == "pending"
    assert doc.page_count == 0
    assert doc.word_count == 0
    assert doc.language == "en"
    assert doc.metadata_ == {}
    assert doc.__tablename__ == "documents"


def test_document_chunk_model() -> None:
    """Verify DocumentChunk model structure and embedding field."""
    chunk = DocumentChunk(
        document_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        chunk_index=0,
        content="Mitochondria are the powerhouses of the cell.",
        token_count=8,
        embedding=[0.01] * 384,
    )
    assert chunk.chunk_index == 0
    assert chunk.token_count == 8
    assert len(chunk.embedding) == 384
    assert chunk.__tablename__ == "document_chunks"


def test_topic_and_concept_models() -> None:
    """Verify Topic, Concept and LearningObjective models."""
    uid = uuid.uuid4()
    doc_id = uuid.uuid4()
    topic_id = uuid.uuid4()

    topic = Topic(
        id=topic_id,
        document_id=doc_id,
        user_id=uid,
        name="Cellular Respiration",
        description="Processes of glycolysis, Krebs cycle, and ETC.",
        importance_score=Decimal("1.00"),
    )
    assert topic.name == "Cellular Respiration"
    assert topic.importance_score == Decimal("1.00")

    concept = Concept(
        topic_id=topic_id,
        document_id=doc_id,
        user_id=uid,
        name="ATP Synthase",
        definition="Enzyme that catalyzes the synthesis of ATP.",
        difficulty="medium",
    )
    assert concept.name == "ATP Synthase"
    assert concept.difficulty == "medium"

    obj = LearningObjective(
        document_id=doc_id,
        topic_id=topic_id,
        user_id=uid,
        bloom_level="analyze",
        description="Analyze how proton gradients power ATP synthesis.",
    )
    assert obj.bloom_level == "analyze"


def test_assessment_and_blueprint_models() -> None:
    """Verify Assessment and Blueprint models."""
    uid = uuid.uuid4()
    doc_id = uuid.uuid4()
    assessment_id = uuid.uuid4()

    assessment = Assessment(
        id=assessment_id,
        user_id=uid,
        document_id=doc_id,
        name="Cell Biology Quiz",
        status="draft",
        progress=Decimal("0.00"),
    )
    assert assessment.id == assessment_id
    assert assessment.name == "Cell Biology Quiz"

    blueprint = QuestionBlueprint(
        assessment_id=assessment_id,
        user_id=uid,
        question_type="mcq_single",
        difficulty="medium",
        bloom_level="understand",
        sequence_number=1,
    )
    assert blueprint.question_type == "mcq_single"
    assert blueprint.sequence_number == 1


def test_question_and_evaluation_models() -> None:
    """Verify Question and Evaluation models."""
    uid = uuid.uuid4()
    assessment_id = uuid.uuid4()
    q_id = uuid.uuid4()

    question = Question(
        id=q_id,
        assessment_id=assessment_id,
        user_id=uid,
        question_type="mcq_single",
        question_text="What organelle synthesizes ATP?",
        options=[
            {"id": "A", "text": "Mitochondria", "is_correct": True},
            {"id": "B", "text": "Ribosome", "is_correct": False},
        ],
        correct_answer="A",
        explanation="Mitochondria produce ATP via oxidative phosphorylation.",
        difficulty="easy",
        bloom_level="remember",
        quality_score=Decimal("4.80"),
    )
    assert question.question_text == "What organelle synthesizes ATP?"
    assert question.quality_score == Decimal("4.80")

    eval_obj = Evaluation(
        question_id=q_id,
        user_id=uid,
        grounding_score=Decimal("5.00"),
        clarity_score=Decimal("4.80"),
        overall_quality_score=Decimal("4.90"),
        decision="PASS",
    )
    assert eval_obj.decision == "PASS"
    assert eval_obj.overall_quality_score == Decimal("4.90")


def test_job_and_export_models() -> None:
    """Verify Job and Export models."""
    uid = uuid.uuid4()
    res_id = uuid.uuid4()

    job = Job(
        user_id=uid,
        resource_type="document",
        resource_id=res_id,
        job_type="document_processing",
        status="running",
        progress=Decimal("50.00"),
    )
    assert job.job_type == "document_processing"
    assert job.status == "running"

    export = Export(
        assessment_id=uuid.uuid4(),
        user_id=uid,
        format="moodle_xml",
        storage_path=f"{uid}/export.xml",
        status="pending",
    )
    assert export.format == "moodle_xml"
    assert export.status == "pending"


def test_llm_usage_daily_model() -> None:
    """Verify LLMUsageDaily model."""
    uid = uuid.uuid4()
    usage = LLMUsageDaily(
        user_id=uid,
        request_count=5,
        input_tokens=1500,
        output_tokens=800,
    )
    assert usage.user_id == uid
    assert usage.request_count == 5
    assert usage.input_tokens == 1500
    assert usage.output_tokens == 800
