import io
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import fitz
import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.db.session import get_db
from app.main import app
from app.models.entities import Document

client = TestClient(app)

TEST_SECRET = "dev-insecure-supabase-jwt-secret-for-offline-testing-32bytes!"


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Ensure clean dependency overrides for every test."""
    yield
    app.dependency_overrides.clear()


def create_auth_header(user_id: uuid.UUID) -> dict[str, str]:
    """Helper to generate valid authorization header for a test user."""
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": str(user_id),
            "email": f"user_{user_id.hex[:8]}@example.com",
            "role": "authenticated",
            "aud": "authenticated",
            "iat": now,
            "exp": now + 3600,
        },
        TEST_SECRET,
        algorithm="HS256",
    )
    return {"Authorization": f"Bearer {token}"}


# ------------------------------------------------------------------------------
# Ingestion Initiation Tests
# ------------------------------------------------------------------------------
def test_initiate_upload_valid_pdf() -> None:
    """Verify initiate upload creates document record and returns private storage path."""
    user_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    payload = {
        "original_filename": "Quantum_Mechanics_Ch1.pdf",
        "declared_mime_type": "application/pdf",
        "size_bytes": 1024 * 1024,
    }

    response = client.post("/api/v1/documents/initiate", json=payload, headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "document_id" in data["data"]
    assert "storage_path" in data["data"]
    assert str(user_id) in data["data"]["storage_path"]
    assert "quantum_mechanics_ch1.pdf" in data["data"]["storage_path"].lower()


def test_initiate_upload_rejects_legacy_doc() -> None:
    """Verify initiate upload rejects legacy .doc with explanatory message."""
    user_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    payload = {
        "original_filename": "Lecture_1998.doc",
        "declared_mime_type": "application/msword",
        "size_bytes": 50000,
    }

    response = client.post("/api/v1/documents/initiate", json=payload, headers=headers)
    assert response.status_code == 422

    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "UNSUPPORTED_LEGACY_DOC"
    assert ".docx or .pdf" in data["error"]["message"]


def test_initiate_upload_rejects_oversized_file() -> None:
    """Verify initiate upload rejects files exceeding max size limit (50MB)."""
    user_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    payload = {
        "original_filename": "Massive_Textbook.pdf",
        "declared_mime_type": "application/pdf",
        "size_bytes": 100 * 1024 * 1024,  # 100MB
    }

    response = client.post("/api/v1/documents/initiate", json=payload, headers=headers)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_initiate_upload_unauthenticated_returns_401() -> None:
    """Verify unauthenticated initiate request returns 401."""
    payload = {
        "original_filename": "Notes.pdf",
        "declared_mime_type": "application/pdf",
        "size_bytes": 1000,
    }
    response = client.post("/api/v1/documents/initiate", json=payload)
    assert response.status_code == 401


# ------------------------------------------------------------------------------
# Document Processing Endpoint Tests
# ------------------------------------------------------------------------------
def test_process_document_text_file() -> None:
    """Verify process endpoint enqueues a document processing job and returns JobStatusResponse."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    raw_text = (
        "# Introduction to Deep Learning\n\n"
        "Deep learning is a subset of machine learning based on artificial neural networks. "
        "Convolutional neural networks excel in computer vision tasks."
    )
    file_bytes = raw_text.encode("utf-8")

    mock_doc = Document(
        id=doc_id,
        user_id=user_id,
        original_filename="lecture_deep_learning.md",
        storage_path=f"{user_id}/{doc_id}/lecture_deep_learning.md",
        mime_type="text/markdown",
        size_bytes=len(file_bytes),
        status="pending",
    )

    mock_job = MagicMock()
    mock_job.id = uuid.uuid4()
    mock_job.user_id = user_id
    mock_job.resource_type = "document"
    mock_job.resource_id = doc_id
    mock_job.job_type = "document_processing"
    mock_job.status = "queued"
    mock_job.progress = 0.0
    mock_job.current_step = None
    mock_job.attempts = 0
    mock_job.max_attempts = 3
    mock_job.error_code = None
    mock_job.error_message = None
    mock_job.state = {}
    mock_job.created_at = None
    mock_job.updated_at = None

    mock_session = AsyncMock()

    async def override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = override_get_db

    with (
        patch("app.api.v1.endpoints.documents.document_repo.get_by_id", new_callable=AsyncMock) as mock_get,
        patch("app.api.v1.endpoints.documents.job_runner.enqueue_job", new_callable=AsyncMock) as mock_enqueue,
    ):
        mock_get.return_value = mock_doc
        mock_enqueue.return_value = mock_job

        response = client.post(
            f"/api/v1/documents/{doc_id}/process",
            files={"file": ("lecture_deep_learning.md", io.BytesIO(file_bytes), "text/markdown")},
            headers=headers,
        )
        assert response.status_code == 200

        data = response.json()
        assert data["success"] is True
        assert data["data"]["resource_id"] == str(doc_id)
        assert data["data"]["resource_type"] == "document"
        assert data["data"]["job_type"] == "document_processing"
        assert data["data"]["status"] == "queued"
        assert data["data"]["progress"] == 0.0


def test_process_scanned_pdf_flags_needs_ocr() -> None:
    """Verify document parser flags needs_ocr when PDF lacks extractable text."""
    # In-memory empty/scanned-like PDF
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.write()
    doc.close()

    from app.services.parsers.pdf import PDFDocumentParser
    parser = PDFDocumentParser()
    parsed_doc = parser.parse(pdf_bytes, "scanned_assignment.pdf")

    assert parsed_doc.is_scanned is True
    assert parsed_doc.error_code == "NEEDS_OCR"


def test_list_documents_endpoint() -> None:
    """Verify GET /api/v1/documents returns list response."""
    user_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    response = client.get("/api/v1/documents", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert isinstance(response.json()["data"], list)


def test_delete_document_endpoint() -> None:
    """Verify DELETE /api/v1/documents/{id} endpoint works."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    response = client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["deleted"] is True
