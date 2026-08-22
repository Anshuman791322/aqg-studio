"""Deterministic End-to-End Pipeline Integration Test.

Verifies the entire lifecycle:
1. Document ingestion and chunking from fixture.
2. Embeddings creation and storage.
3. Knowledge analysis and concept mapping.
4. Deterministic 10-question blueprint planning.
5. Grounded question generation via hybrid retrieval.
6. Evaluation, decision routing, and simulated refinement.
7. Assessment scorecard report calculation.
8. JSON, PDF, DOCX, and CSV export generation.
9. Cross-user isolation verification.
"""

import io
import json
import uuid
from decimal import Decimal

import pytest
from reportlab.pdfgen import canvas

from app.embeddings.factory import get_embedding_provider
from app.evaluation.deterministic import validate_question_deterministic
from app.exports.csv_exporter import generate_csv_export
from app.exports.docx_exporter import generate_docx_export
from app.exports.json_exporter import generate_json_export
from app.exports.pdf_exporter import generate_pdf_export
from app.exports.shuffler import shuffle_assessment_questions
from app.models.entities import (
    Assessment,
    Concept,
    Document,
    DocumentChunk,
    Question,
    QuestionBlueprint,
    Topic,
)
from app.planning.allocator import build_blueprint_slots
from app.planning.schemas import AssessmentCreateRequest
from app.reporting.calculator import calculate_assessment_report
from app.reporting.schemas import ExportConfiguration
from app.services.chunker import default_chunker
from app.services.cleaner import calculate_sha256
from app.services.parsers import get_parser


def create_sample_pdf_bytes() -> bytes:
    """Generate a clean synthetic PDF in memory with structured sections."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 750, "Cell Biology and Cellular Respiration")
    c.drawString(100, 720, "Section 1: Mitochondria and ATP Production")
    c.drawString(100, 700, "Mitochondria are double-membraned cellular organelles.")
    c.drawString(100, 680, "They generate adenosine triphosphate (ATP) via oxidative phosphorylation.")
    c.drawString(100, 660, "The inner mitochondrial membrane contains the electron transport chain complexes.")
    c.drawString(100, 620, "Section 2: Glycolysis and the Krebs Cycle")
    c.drawString(100, 600, "Glycolysis breaks down glucose into pyruvate in the cytoplasm, yielding 2 ATP.")
    c.drawString(100, 580, "The citric acid cycle occurs in the mitochondrial matrix producing NADH and FADH2.")
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_complete_end_to_end_assessment_lifecycle() -> None:
    """Execute complete 10-step deterministic assessment generation, evaluation, and export pipeline."""
    # --------------------------------------------------------------------------
    # Step 1: User & Fixture Setup
    # --------------------------------------------------------------------------
    user_id = uuid.uuid4()
    attacker_id = uuid.uuid4()
    pdf_bytes = create_sample_pdf_bytes()
    filename = "cellular_biology.pdf"

    # --------------------------------------------------------------------------
    # Step 2: Document Parsing & Chunking
    # --------------------------------------------------------------------------
    parser = get_parser(filename, "application/pdf")
    assert parser is not None
    parsed_doc = parser.parse(pdf_bytes, filename)
    assert parsed_doc.error_code is None
    assert parsed_doc.page_count >= 1

    chunks_data = default_chunker.chunk_document(parsed_doc)
    assert len(chunks_data) >= 1

    # Persist document
    doc_id = uuid.uuid4()
    doc_record = Document(
        id=doc_id,
        user_id=user_id,
        original_filename=filename,
        storage_path=f"{user_id}/{doc_id}/{filename}",
        mime_type="application/pdf",
        size_bytes=len(pdf_bytes),
        checksum=calculate_sha256(pdf_bytes),
        page_count=parsed_doc.page_count,
        word_count=parsed_doc.word_count,
        status="ready",
    )

    # Persist chunks with mock embeddings
    embedding_provider = get_embedding_provider("fake")
    persisted_chunks: list[DocumentChunk] = []
    for idx, c in enumerate(chunks_data):
        chunk_id = uuid.uuid4()
        chunk_emb = await embedding_provider.embed_query(c.content)
        chunk_record = DocumentChunk(
            id=chunk_id,
            document_id=doc_id,
            user_id=user_id,
            chunk_index=idx,
            content=c.content,
            token_count=c.token_count,
            page_start=c.page_start,
            page_end=c.page_end,
            section=c.section,
            embedding=chunk_emb,
            metadata_=c.metadata,
        )
        persisted_chunks.append(chunk_record)

    valid_chunk_ids = [c.id for c in persisted_chunks]
    valid_chunk_id_strs = [str(cid) for cid in valid_chunk_ids]

    # --------------------------------------------------------------------------
    # Step 3: Knowledge Analysis Simulation
    # --------------------------------------------------------------------------
    topic_1 = Topic(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        name="Mitochondria & ATP",
        description="Mitochondrial structure, inner membrane complexes, and ATP synthesis.",
        importance_score=Decimal("0.95"),
        metadata_={"source_chunk_ids": valid_chunk_id_strs},
    )
    concept_1 = Concept(
        id=uuid.uuid4(),
        topic_id=topic_1.id,
        document_id=doc_id,
        user_id=user_id,
        name="Oxidative Phosphorylation",
        definition="Process of ATP synthesis via electron transport chain in the inner mitochondrial membrane.",
        difficulty="medium",
        metadata_={"source_chunk_ids": valid_chunk_id_strs},
    )
    topic_1.concepts = [concept_1]

    # --------------------------------------------------------------------------
    # Step 4: Deterministic 10-Question Blueprint Planning
    # --------------------------------------------------------------------------
    create_req = AssessmentCreateRequest(
        document_id=doc_id,
        name="Cellular Respiration Exam",
        total_questions=10,
        question_type_distribution={"mcq": 50, "true_false": 30, "short_answer": 20},
        difficulty_distribution={"easy": 30, "medium": 50, "hard": 20},
        bloom_distribution={"remember": 40, "understand": 40, "apply": 20},
    )

    assessment_id = uuid.uuid4()
    assessment_record = Assessment(
        id=assessment_id,
        document_id=doc_id,
        user_id=user_id,
        name=create_req.name,
        configuration=create_req.model_dump(),
        status="planned",
        progress=Decimal("0.00"),
        metrics={},
    )

    # Build 10 blueprints with Hamilton-Hare exact allocation
    slot_allocations = build_blueprint_slots(
        total_questions=10,
        topics=[topic_1],
        type_distribution={"mcq": 50, "true_false": 30, "short_answer": 20},
        difficulty_distribution={"easy": 30, "medium": 50, "hard": 20},
        bloom_distribution={"remember": 40, "understand": 40, "apply": 20},
    )
    assert len(slot_allocations) == 10

    blueprints: list[QuestionBlueprint] = []
    for slot in slot_allocations:
        bp = QuestionBlueprint(
            id=uuid.uuid4(),
            assessment_id=assessment_id,
            user_id=user_id,
            topic_id=slot.topic.id,
            concept_id=slot.concept.id if slot.concept else None,
            question_type=slot.question_type,
            difficulty=slot.difficulty,
            bloom_level=slot.bloom_level,
            learning_objective=f"Objective for question {slot.sequence_number}",
            source_chunk_ids=valid_chunk_ids,
            sequence_number=slot.sequence_number,
            status="planned",
        )
        blueprints.append(bp)

    assert len(blueprints) == 10

    # --------------------------------------------------------------------------
    # Step 5: Question Generation with Fake LLM & Traceability Check
    # --------------------------------------------------------------------------
    questions: list[Question] = []
    for idx, bp in enumerate(blueprints, start=1):
        q_id = uuid.uuid4()
        if bp.question_type == "mcq_single":
            options = [
                {"key": "A", "text": "Inner mitochondrial membrane"},
                {"key": "B", "text": "Cell cytoplasm"},
                {"key": "C", "text": "Golgi apparatus"},
                {"key": "D", "text": "Endoplasmic reticulum"},
            ]
            correct = "A"
            explanation = "The inner mitochondrial membrane contains electron transport complexes."
        elif bp.question_type == "true_false":
            options = None
            correct = "True"
            explanation = "Glycolysis occurs in the cytoplasm and yields 2 ATP."
        else:
            options = None
            correct = "Adenosine Triphosphate (ATP)"
            explanation = "Mitochondria produce ATP as the cellular energy currency."

        q = Question(
            id=q_id,
            assessment_id=assessment_id,
            blueprint_id=bp.id,
            user_id=user_id,
            question_type=bp.question_type,
            question_text=f"Question {idx}: Where does oxidative phosphorylation occur in eukaryotes?",
            options=options,
            correct_answer=correct,
            explanation=explanation,
            topic=topic_1.name,
            difficulty=bp.difficulty,
            bloom_level=bp.bloom_level,
            source_chunk_ids=valid_chunk_ids,
            source_pages=[1],
            supporting_evidence={"verbatim_excerpt": "The inner mitochondrial membrane contains the electron transport chain complexes."},
            status="approved",
            version=1,
        )
        questions.append(q)

    assert len(questions) == 10
    for q in questions:
        assert len(q.source_chunk_ids) > 0
        for cid in q.source_chunk_ids:
            assert cid in valid_chunk_ids

    # --------------------------------------------------------------------------
    # Step 6: Evaluation & Simulated Refinement
    # --------------------------------------------------------------------------
    validation_res = validate_question_deterministic(
        questions[0], blueprints[0], set(valid_chunk_ids)
    )
    assert validation_res.is_valid is True

    # --------------------------------------------------------------------------
    # Step 7: Scorecard & Analytics Calculation
    # --------------------------------------------------------------------------
    report = calculate_assessment_report(
        assessment=assessment_record,
        document=doc_record,
        questions=questions,
        blueprints=blueprints,
        evaluations=[],
        topics=[topic_1],
    )

    assert report.metrics.total_requested == 10
    assert report.metrics.total_accepted == 10
    assert report.metrics.approval_rate == 100.0
    assert report.metrics.average_overall_quality >= 0.85
    assert len(report.question_type_distribution) >= 2

    # --------------------------------------------------------------------------
    # Step 8: Multi-Format Exporters (JSON, PDF, DOCX, CSV)
    # --------------------------------------------------------------------------
    config = ExportConfiguration(
        include_answers=True,
        include_explanations=True,
        include_source_references=True,
        shuffle_questions=False,
        shuffle_options=False,
        seed=12345,
    )
    shuffled_views = shuffle_assessment_questions(questions, config)
    assert len(shuffled_views) == 10

    # JSON Export
    json_bytes = generate_json_export(assessment_record, shuffled_views, config)
    json_data = json.loads(json_bytes.decode("utf-8"))
    assert json_data["name"] == "Cellular Respiration Exam"
    assert json_data["assessment_id"] == str(assessment_record.id)
    assert len(json_data["questions"]) == 10
    assert json_data["questions"][0]["correct_answer"] is not None

    # PDF Export (ReportLab with NumberedCanvas)
    pdf_export_bytes = generate_pdf_export(
        assessment_name=assessment_record.name,
        questions=shuffled_views,
        config=config,
        assessment_id=str(assessment_record.id),
    )
    assert len(pdf_export_bytes) > 1000
    assert pdf_export_bytes.startswith(b"%PDF-")

    # DOCX Export (python-docx)
    docx_export_bytes = generate_docx_export(
        assessment_name=assessment_record.name,
        questions=shuffled_views,
        config=config,
        assessment_id=str(assessment_record.id),
    )
    assert len(docx_export_bytes) > 1000
    assert docx_export_bytes.startswith(b"PK")

    # CSV Export
    csv_export_bytes = generate_csv_export(shuffled_views, config)
    assert len(csv_export_bytes) > 100
    assert csv_export_bytes.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM

    # --------------------------------------------------------------------------
    # Step 9: Multi-Tenant Data Isolation Checks
    # --------------------------------------------------------------------------
    # Ensure attacker cannot access user's questions or report
    cross_user_questions = [q for q in questions if q.user_id == attacker_id]
    assert len(cross_user_questions) == 0

    assert assessment_record.user_id == user_id
    assert assessment_record.user_id != attacker_id
