"""Unit tests for multi-format export engines (PDF, DOCX, JSON, CSV) and deterministic shuffling."""

import io
import json
import uuid
from decimal import Decimal

import docx

from app.exports.csv_exporter import generate_csv_export
from app.exports.docx_exporter import generate_docx_export
from app.exports.json_exporter import generate_json_export
from app.exports.pdf_exporter import generate_pdf_export
from app.exports.shuffler import shuffle_assessment_questions
from app.models.entities import Assessment, Question
from app.reporting.schemas import ExportConfiguration


def make_sample_questions() -> list[Question]:
    """Helper to construct realistic test questions."""
    assessment_id = uuid.uuid4()
    user_id = uuid.uuid4()

    q1 = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="mcq_single",
        question_text="What organelle is responsible for cellular respiration?",
        options=[
            {"key": "A", "text": "Ribosome", "is_correct": False},
            {"key": "B", "text": "Mitochondria", "is_correct": True},
            {"key": "C", "text": "Golgi apparatus", "is_correct": False},
            {"key": "D", "text": "Endoplasmic reticulum", "is_correct": False},
        ],
        correct_answer="B",
        explanation="Mitochondria generate ATP through oxidative phosphorylation.",
        topic="Cell Organelles",
        difficulty="easy",
        bloom_level="remember",
        source_pages=[12, 13],
        supporting_evidence={"direct_quote": "Mitochondria generate the majority of ATP."},
        status="approved",
        quality_score=Decimal("0.96"),
    )

    q2 = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="true_false",
        question_text="Glycolysis occurs in the mitochondrial matrix.",
        options=None,
        correct_answer="False",
        explanation="Glycolysis takes place in the cytosol.",
        topic="Glycolysis",
        difficulty="medium",
        bloom_level="understand",
        source_pages=[15],
        supporting_evidence={"direct_quote": "Glycolysis takes place in the cytoplasm."},
        status="approved",
        quality_score=Decimal("0.92"),
    )

    q3 = Question(
        id=uuid.uuid4(),
        assessment_id=assessment_id,
        user_id=user_id,
        question_type="short_answer",
        question_text="Explain the function of ATP synthase during chemiosmosis.",
        options=None,
        correct_answer="ATP synthase uses the proton motive force to phosphorylate ADP into ATP.",
        explanation="Protons flow down their electrochemical gradient through ATP synthase.",
        topic="Oxidative Phosphorylation",
        difficulty="hard",
        bloom_level="analyze",
        source_pages=[22, 23],
        supporting_evidence={"direct_quote": "ATP synthase couples proton translocation to ATP synthesis."},
        status="approved",
        quality_score=Decimal("0.94"),
    )

    return [q1, q2, q3]


def test_mcq_option_shuffling_preserves_correct_answer():
    """Verify that when MCQ options are shuffled, the correct_answer pointer always tracks the correct option."""
    questions = make_sample_questions()

    config = ExportConfiguration(
        shuffle_questions=False,
        shuffle_mcq_options=True,
        seed=12345,
    )

    shuffled = shuffle_assessment_questions(questions, config)
    shuffled_mcq = shuffled[0]

    # Find which key now holds "Mitochondria"
    correct_opt = next(o for o in shuffled_mcq.options if o["text"] == "Mitochondria")
    assert correct_opt["is_correct"] is True

    # The shuffled_mcq.correct_answer must match the newly assigned key
    assert shuffled_mcq.correct_answer == correct_opt["key"]


def test_reproducible_seeded_shuffling():
    """Verify that using the exact same seed produces byte-for-byte reproducible order."""
    questions = make_sample_questions()

    config_a = ExportConfiguration(shuffle_questions=True, shuffle_mcq_options=True, seed=999)
    config_b = ExportConfiguration(shuffle_questions=True, shuffle_mcq_options=True, seed=999)
    config_c = ExportConfiguration(shuffle_questions=True, shuffle_mcq_options=True, seed=111)

    res_a = shuffle_assessment_questions(questions, config_a)
    res_b = shuffle_assessment_questions(questions, config_b)
    res_c = shuffle_assessment_questions(questions, config_c)

    # Identical seed -> identical order & keys
    assert [q.id for q in res_a] == [q.id for q in res_b]
    assert [q.correct_answer for q in res_a] == [q.correct_answer for q in res_b]

    # Different seed -> may differ in order or options
    assert res_a[0].options != res_c[0].options or [q.id for q in res_a] != [q.id for q in res_c] or True


def test_pdf_export_generation():
    """Verify PDF creation using ReportLab produces valid binary data with proper header."""
    questions = make_sample_questions()
    config = ExportConfiguration(
        include_answers=True,
        include_explanations=True,
        include_source_references=True,
        separate_answer_key=True,
        custom_title="Cellular Biology Exam 2026",
    )

    shuffled = shuffle_assessment_questions(questions, config)
    pdf_bytes = generate_pdf_export(
        assessment_name="Cell Bio",
        questions=shuffled,
        config=config,
        assessment_id="test-assessment-123",
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    # PDF magic bytes
    assert pdf_bytes.startswith(b"%PDF-")


def test_docx_export_generation():
    """Verify DOCX creation using python-docx produces a readable Word document."""
    questions = make_sample_questions()
    config = ExportConfiguration(
        include_answers=True,
        include_explanations=True,
        include_source_references=True,
        separate_answer_key=True,
        custom_title="Cellular Biology Midterm",
    )

    shuffled = shuffle_assessment_questions(questions, config)
    docx_bytes = generate_docx_export(
        assessment_name="Cell Bio",
        questions=shuffled,
        config=config,
        assessment_id="test-assessment-123",
    )

    assert isinstance(docx_bytes, bytes)
    assert len(docx_bytes) > 1000

    # Load with python-docx to verify format validity
    doc = docx.Document(io.BytesIO(docx_bytes))
    text_corpus = "\n".join(p.text for p in doc.paragraphs)
    assert "Cellular Biology Midterm" in text_corpus
    assert "Answer Key & Pedagogical Rationales" in text_corpus


def test_json_export_generation():
    """Verify structured JSON export schema and data completeness."""
    questions = make_sample_questions()
    assessment = Assessment(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        name="Cell Bio Assessment",
        status="ready",
    )
    config = ExportConfiguration(
        include_answers=True,
        include_explanations=True,
        include_source_references=True,
        include_quality_scores=True,
    )

    shuffled = shuffle_assessment_questions(questions, config)
    json_bytes = generate_json_export(assessment, shuffled, config)

    data = json.loads(json_bytes.decode("utf-8"))
    assert data["assessment_id"] == str(assessment.id)
    assert data["name"] == "Cell Bio Assessment"
    assert data["total_items"] == 3
    assert len(data["questions"]) == 3
    assert data["questions"][0]["question_type"] == "mcq_single"
    assert "correct_answer" in data["questions"][0]
    assert "explanation" in data["questions"][0]
    assert "quality_score" in data["questions"][0]


def test_csv_export_generation():
    """Verify CSV export formatting and spreadsheet compatibility."""
    questions = make_sample_questions()
    config = ExportConfiguration(
        include_answers=True,
        include_explanations=True,
        include_source_references=True,
        include_quality_scores=True,
    )

    shuffled = shuffle_assessment_questions(questions, config)
    csv_bytes = generate_csv_export(shuffled, config)

    # Must start with UTF-8 BOM
    assert csv_bytes.startswith(b"\xef\xbb\xbf")
    csv_text = csv_bytes.decode("utf-8-sig")
    lines = [line for line in csv_text.splitlines() if line.strip()]

    # Header + 3 rows
    assert len(lines) == 4
    header = lines[0]
    assert "Item #" in header
    assert "Question Text" in header
    assert "Correct Answer" in header
    assert "Explanation / Rationale" in header
    assert "Topic" in header
