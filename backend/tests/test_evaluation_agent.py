"""Unit and integration tests for Evaluation Agent, deterministic checks, refinement, and duplicate control."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.agents.evaluation_agent import EvaluationAgent
from app.evaluation.deterministic import (
    validate_question_deterministic,
)
from app.evaluation.duplication import (
    compute_jaccard_similarity,
    detect_assessment_duplicates,
    is_exact_normalized_duplicate,
    resolve_duplicate_conflicts,
)
from app.evaluation.schemas import (
    LLMEvaluationOutput,
    MetricScores,
)
from app.generation.schemas import (
    GeneratedQuestionItem,
    SupportingEvidence,
)
from app.llm.fake import FakeLLMProvider
from app.llm.schemas import LLMUsage
from app.models.entities import (
    Assessment,
    Concept,
    DocumentChunk,
    Question,
    QuestionBlueprint,
    Topic,
)


# ------------------------------------------------------------------------------
# 1. Deterministic Validation Tests
# ------------------------------------------------------------------------------
def test_deterministic_validator_mcq_rules() -> None:
    """Verify deterministic validator rejects MCQs with prohibited phrases or wrong option count."""
    chunk_id = uuid.uuid4()
    bp_id = uuid.uuid4()
    bp = QuestionBlueprint(
        id=bp_id,
        assessment_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question_type="mcq_single",
        difficulty="medium",
        bloom_level="understand",
        source_chunk_ids=[chunk_id],
        sequence_number=1,
    )

    # Valid question
    valid_q = Question(
        id=uuid.uuid4(),
        assessment_id=bp.assessment_id,
        blueprint_id=bp_id,
        user_id=bp.user_id,
        question_type="mcq_single",
        question_text="Which gas is essential for plant photosynthesis?",
        options=[
            {"key": "A", "text": "Oxygen"},
            {"key": "B", "text": "Carbon Dioxide"},
            {"key": "C", "text": "Nitrogen"},
            {"key": "D", "text": "Hydrogen"},
        ],
        correct_answer="B",
        explanation="Carbon dioxide is fixed into sugars during the Calvin cycle.",
        topic="Biology",
        difficulty="medium",
        bloom_level="understand",
        source_chunk_ids=[chunk_id],
        source_pages=[1],
        supporting_evidence={"source_chunk_ids": [str(chunk_id)]},
    )

    res = validate_question_deterministic(valid_q, bp, {chunk_id})
    assert res.is_valid is True
    assert res.critical_failure is False

    # Prohibited phrase in distractor
    bad_q = Question(
        id=uuid.uuid4(),
        assessment_id=bp.assessment_id,
        blueprint_id=bp_id,
        user_id=bp.user_id,
        question_type="mcq_single",
        question_text="Which gas is essential for plant photosynthesis?",
        options=[
            {"key": "A", "text": "Oxygen"},
            {"key": "B", "text": "Carbon Dioxide"},
            {"key": "C", "text": "Nitrogen"},
            {"key": "D", "text": "All of the above"},  # Prohibited
        ],
        correct_answer="B",
        explanation="Explanation here.",
        topic="Biology",
        difficulty="medium",
        bloom_level="understand",
        source_chunk_ids=[chunk_id],
    )

    bad_res = validate_question_deterministic(bad_q, bp, {chunk_id})
    assert bad_res.is_valid is False
    assert bad_res.critical_failure is True
    assert "PROHIBITED_MCQ_PHRASE" in bad_res.rule_violations


def test_deterministic_validator_hallucinated_chunk_id() -> None:
    """Verify validator flags critical failure when cited chunk is not in document."""
    real_chunk_id = uuid.uuid4()
    hallucinated_chunk_id = uuid.uuid4()

    q = Question(
        id=uuid.uuid4(),
        assessment_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        question_type="short_answer",
        question_text="What is the capital of France?",
        options=None,
        correct_answer="Paris",
        explanation="Paris is the capital.",
        topic="Geography",
        difficulty="easy",
        bloom_level="remember",
        source_chunk_ids=[hallucinated_chunk_id],
    )

    res = validate_question_deterministic(q, None, {real_chunk_id})
    assert res.is_valid is False
    assert res.critical_failure is True
    assert "HALLUCINATED_CHUNK_IDS" in res.rule_violations


# ------------------------------------------------------------------------------
# 2. Duplicate Detection Tests
# ------------------------------------------------------------------------------
def test_exact_normalized_and_jaccard_duplication() -> None:
    """Verify exact normalized duplicate and lexical Jaccard similarity detection."""
    stem1 = "What is the primary function of mitochondria in eukaryotic cells?"
    stem2 = "What is the primary function of mitochondria in eukaryotic cells?? "
    stem3 = "Explain the role and function of mitochondria within eukaryotic cells."

    assert is_exact_normalized_duplicate(stem1, stem2) is True
    assert is_exact_normalized_duplicate(stem1, stem3) is False

    jaccard_score = compute_jaccard_similarity(stem1, stem3)
    assert jaccard_score > 0.40


@pytest.mark.asyncio
async def test_duplicate_detection_and_conflict_resolution() -> None:
    """Verify duplicate detection across questions and winner retention by quality score."""
    q1_id = uuid.uuid4()
    q2_id = uuid.uuid4()
    assessment_id = uuid.uuid4()

    q1 = Question(
        id=q1_id,
        assessment_id=assessment_id,
        user_id=uuid.uuid4(),
        question_type="short_answer",
        question_text="What is Newton's First Law of Motion?",
        correct_answer="Law of Inertia",
        explanation="An object at rest stays at rest.",
        difficulty="easy",
        bloom_level="remember",
        quality_score=Decimal("0.95"),
    )
    q2 = Question(
        id=q2_id,
        assessment_id=assessment_id,
        user_id=uuid.uuid4(),
        question_type="short_answer",
        question_text="What is Newton's First Law of Motion??",  # Duplicate
        correct_answer="Law of Inertia",
        explanation="Objects maintain velocity unless acted on by net force.",
        difficulty="easy",
        bloom_level="remember",
        quality_score=Decimal("0.80"),
    )

    duplicates = await detect_assessment_duplicates([q1, q2], threshold=0.90)
    assert len(duplicates) == 1
    assert duplicates[0].similarity_score == 1.0

    questions_map = {q1_id: q1, q2_id: q2}
    keep_ids, discard_ids = resolve_duplicate_conflicts(duplicates, questions_map)

    assert keep_ids == {q1_id}
    assert discard_ids == {q2_id}


# ------------------------------------------------------------------------------
# 3. Evaluation Agent Single Question Acceptance & Decision Logic
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluation_accept_high_quality_question() -> None:
    """Verify evaluator returns ACCEPT for high scoring, fully grounded question."""
    user_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    bp_id = uuid.uuid4()

    chunk = DocumentChunk(
        id=chunk_id,
        document_id=uuid.uuid4(),
        user_id=user_id,
        chunk_index=0,
        content="Mitochondria produce ATP through oxidative phosphorylation.",
        page_start=2,
    )

    bp = QuestionBlueprint(
        id=bp_id,
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="mcq_single",
        difficulty="medium",
        bloom_level="understand",
        source_chunk_ids=[chunk_id],
    )

    q = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        blueprint_id=bp_id,
        user_id=user_id,
        question_type="mcq_single",
        question_text="What is the main biochemical output of mitochondria?",
        options=[
            {"key": "A", "text": "ATP"},
            {"key": "B", "text": "Glucose"},
            {"key": "C", "text": "DNA"},
            {"key": "D", "text": "Lipids"},
        ],
        correct_answer="A",
        explanation="Mitochondria produce ATP via cellular respiration.",
        topic="Cell Biology",
        difficulty="medium",
        bloom_level="understand",
        source_chunk_ids=[chunk_id],
        source_pages=[2],
        supporting_evidence={"source_chunk_ids": [str(chunk_id)]},
        status="draft",
    )

    fake_output = LLMEvaluationOutput(
        question_id=str(q.id),
        scores=MetricScores(
            correctness=0.98,
            groundedness=0.96,
            relevance=0.95,
            clarity=0.92,
            grammar=0.95,
            answerability=0.95,
            difficulty_alignment=0.90,
            bloom_alignment=0.92,
            distractor_quality=0.90,
            duplication_risk=0.0,
            overall_quality=0.94,
        ),
        decision="ACCEPT",
        strengths=["Clear stem", "High factual grounding"],
        issues=[],
        recommendations=[],
        rationale="Excellent question matching all criteria.",
    )

    fake_llm = FakeLLMProvider(scripted_responses=[fake_output.model_dump()])
    agent = EvaluationAgent(llm_provider=fake_llm)

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    eval_rec, out = await agent.evaluate_single_question(
        mock_session,
        question=q,
        blueprint=bp,
        available_chunks=[chunk],
        user_id=user_id,
    )

    assert out.decision == "ACCEPT"
    assert eval_rec.decision == "ACCEPT"
    assert q.status == "approved"
    assert float(q.quality_score or 0) >= 0.85


# ------------------------------------------------------------------------------
# 4. Refinement Loop Test
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_evaluation_refine_and_repair_loop() -> None:
    """Verify recoverable question receives REFINE, gets updated, and passes re-evaluation."""
    user_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    assessment_id = uuid.uuid4()

    chunk = DocumentChunk(
        id=chunk_id,
        document_id=uuid.uuid4(),
        user_id=user_id,
        chunk_index=0,
        content="The speed of light in vacuum is approximately 300,000 km/s.",
        page_start=1,
    )

    q = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        blueprint_id=uuid.uuid4(),
        user_id=user_id,
        question_type="short_answer",
        question_text="What is light speed?",  # Slightly ambiguous stem
        options=None,
        correct_answer="300,000 km/s",
        explanation="Light travels at 300,000 km/s in vacuum.",
        topic="Physics",
        difficulty="easy",
        bloom_level="remember",
        source_chunk_ids=[chunk_id],
        source_pages=[1],
        status="draft",
        version=1,
        generation_attempts=1,
    )

    # Initial evaluation: REFINE
    initial_eval = LLMEvaluationOutput(
        question_id=str(q.id),
        scores=MetricScores(
            correctness=0.90,
            groundedness=0.90,
            relevance=0.85,
            clarity=0.65,  # Recoverable clarity flaw
            grammar=0.80,
            answerability=0.75,
            difficulty_alignment=0.80,
            bloom_alignment=0.80,
            distractor_quality=1.0,
            duplication_risk=0.0,
            overall_quality=0.78,
        ),
        decision="REFINE",
        issues=["Stem is too informal and lacks medium specification (vacuum)."],
        recommendations=["Rephrase stem to: 'What is the approximate speed of light in a vacuum?'"],
        rationale="Good concept but stem needs precision.",
    )

    # Refined question response
    refined_item = GeneratedQuestionItem(
        blueprint_id=q.blueprint_id or uuid.uuid4(),
        question_type="short_answer",
        question_text="What is the approximate speed of light in a vacuum?",
        options=None,
        correct_answer="300,000 km/s",
        explanation="Light in a vacuum travels at approximately 300,000 km/s.",
        topic="Physics",
        difficulty="easy",
        bloom_level="remember",
        supporting_evidence=SupportingEvidence(
            source_chunk_ids=[chunk_id],
            verbatim_excerpt="The speed of light in vacuum is approximately 300,000 km/s.",
            page_numbers=[1],
            rationale="Defines speed of light.",
        ),
    )

    # Re-evaluation: ACCEPT
    re_eval = LLMEvaluationOutput(
        question_id=str(q.id),
        scores=MetricScores(
            correctness=0.98,
            groundedness=0.98,
            relevance=0.95,
            clarity=0.95,
            grammar=0.95,
            answerability=0.95,
            difficulty_alignment=0.90,
            bloom_alignment=0.90,
            distractor_quality=1.0,
            duplication_risk=0.0,
            overall_quality=0.96,
        ),
        decision="ACCEPT",
        strengths=["Clear stem with vacuum context"],
        issues=[],
        recommendations=[],
        rationale="Refinement successfully fixed stem clarity.",
    )

    call_count = 0

    async def fake_complete_structured(messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        usage = LLMUsage(provider="fake", model="fake-model")
        if call_count == 1:
            return initial_eval, usage
        elif call_count == 2:
            return refined_item, usage
        else:
            return re_eval, usage

    fake_llm = MagicMock()
    fake_llm.complete_structured = AsyncMock(side_effect=fake_complete_structured)

    agent = EvaluationAgent(llm_provider=fake_llm)
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    # 1. Initial Eval
    _, out1 = await agent.evaluate_single_question(
        mock_session, question=q, available_chunks=[chunk], user_id=user_id
    )
    assert out1.decision == "REFINE"
    assert q.status == "flagged"

    # 2. Refinement pass
    refined_q, eval2 = await agent.refine_single_question(
        mock_session,
        question=q,
        available_chunks=[chunk],
        evaluator_issues=out1.issues,
        evaluator_recommendations=out1.recommendations,
        user_id=user_id,
    )

    assert refined_q.version == 2
    assert refined_q.question_text == "What is the approximate speed of light in a vacuum?"
    assert eval2.decision == "ACCEPT"
    assert refined_q.status == "approved"


# ------------------------------------------------------------------------------
# 5. Full Assessment Orchestration & Replacement Blueprint Test
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_assessment_evaluation_and_replacement_blueprint() -> None:
    """Verify failed candidate exhaustion triggers replacement blueprint to preserve count."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    chunk_id = uuid.uuid4()
    bp1_id = uuid.uuid4()

    mock_assessment = Assessment(
        id=assessment_id,
        user_id=user_id,
        document_id=doc_id,
        name="Physics Exam",
        configuration={"total_questions": 1},
        status="generating",
    )

    mock_chunk = DocumentChunk(
        id=chunk_id,
        document_id=doc_id,
        user_id=user_id,
        chunk_index=0,
        content="Gravity causes objects to accelerate downward at 9.8 m/s^2.",
        page_start=1,
    )

    bp1 = QuestionBlueprint(
        id=bp1_id,
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="short_answer",
        difficulty="medium",
        bloom_level="understand",
        source_chunk_ids=[chunk_id],
        status="planned",
        sequence_number=1,
    )

    q1 = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        blueprint_id=bp1_id,
        user_id=user_id,
        question_type="short_answer",
        question_text="Unusable hallucinated statement",
        options=None,
        correct_answer="Unknown",
        explanation="None",
        difficulty="medium",
        bloom_level="understand",
        source_chunk_ids=[chunk_id],
        source_pages=[1],
        status="draft",
        version=1,
        generation_attempts=1,
        created_at=datetime.now(UTC),
    )

    # Initial Eval: REGENERATE (hallucinated)
    regen_eval = LLMEvaluationOutput(
        question_id=str(q1.id),
        scores=MetricScores(
            correctness=0.20,
            groundedness=0.10,
            overall_quality=0.20,
        ),
        decision="REGENERATE",
        issues=["Completely ungrounded"],
        recommendations=["Regenerate from source context"],
    )

    # Replacement Question generated
    rep_item = GeneratedQuestionItem(
        blueprint_id=uuid.uuid4(),
        question_type="short_answer",
        question_text="What is the standard acceleration due to Earth's gravity?",
        options=None,
        correct_answer="9.8 m/s^2",
        explanation="Earth's gravity produces 9.8 m/s^2 acceleration.",
        topic="Physics",
        difficulty="medium",
        bloom_level="understand",
        supporting_evidence=SupportingEvidence(
            source_chunk_ids=[chunk_id],
            verbatim_excerpt="Gravity causes objects to accelerate downward at 9.8 m/s^2.",
            page_numbers=[1],
            rationale="States gravitational acceleration.",
        ),
    )

    accept_eval = LLMEvaluationOutput(
        scores=MetricScores(
            correctness=0.98,
            groundedness=0.98,
            overall_quality=0.95,
        ),
        decision="ACCEPT",
        strengths=["Factually grounded"],
    )

    call_count = 0

    async def fake_eval_structured(messages, response_model, **kwargs):
        nonlocal call_count
        call_count += 1
        usage = LLMUsage(provider="fake", model="fake-model")
        if call_count <= 2:
            return regen_eval, usage
        else:
            return accept_eval, usage

    fake_llm = MagicMock()
    fake_llm.complete_structured = AsyncMock(side_effect=fake_eval_structured)

    agent = EvaluationAgent(llm_provider=fake_llm)
    # Configure 1 max regeneration attempt to quickly trigger replacement blueprint
    agent.settings.EVALUATION_MAX_REGENERATION_ATTEMPTS = 1

    # Mock DB Session
    mock_session = AsyncMock()
    mock_session.add = MagicMock()

    async def fake_execute(stmt):
        mock_result = MagicMock()
        stmt_str = str(stmt)
        if "FROM assessments" in stmt_str:
            mock_result.scalar_one_or_none.return_value = mock_assessment
            mock_result.scalars.return_value.all.return_value = [mock_assessment]
        elif "FROM document_chunks" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [mock_chunk]
        elif "FROM question_blueprints" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [bp1]
        elif "FROM topics" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [Topic(id=uuid.uuid4(), document_id=doc_id, user_id=user_id, name="Mechanics")]
        elif "FROM concepts" in stmt_str:
            mock_result.scalars.return_value.all.return_value = [Concept(id=uuid.uuid4(), document_id=doc_id, user_id=user_id, name="Gravity")]
        elif "FROM questions" in stmt_str:
            # First query returns initial question, subsequent returns replacement
            if "status != :status_1" in stmt_str:
                mock_result.scalars.return_value.all.return_value = [q1]
            elif "status = :status_1" in stmt_str:
                # approved questions query
                mock_result.scalars.return_value.all.return_value = [q1]
            else:
                mock_result.scalars.return_value.all.return_value = [q1]
        return mock_result

    mock_session.execute = AsyncMock(side_effect=fake_execute)

    # Mock generation agent batch generation
    async def fake_gen_batch(*args, **kwargs):
        rep_q = Question(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            blueprint_id=bp1_id,
            user_id=user_id,
            question_type="short_answer",
            question_text=rep_item.question_text,
            correct_answer=rep_item.correct_answer,
            explanation=rep_item.explanation,
            difficulty="medium",
            bloom_level="understand",
            source_chunk_ids=[chunk_id],
            source_pages=[1],
            status="draft",
            created_at=datetime.now(UTC),
        )
        return [rep_q], []

    agent.generation_agent.generate_batch_questions = AsyncMock(side_effect=fake_gen_batch)

    summary = await agent.evaluate_and_refine_assessment(
        mock_session,
        assessment_id=assessment_id,
        user_id=user_id,
    )

    assert summary.assessment_id == assessment_id
    assert mock_assessment.progress == Decimal("100.00")
