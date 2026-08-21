"""Integration tests for document ingestion API endpoints, lifecycle, and tenant isolation."""

import io
import time
import uuid

import fitz
from fastapi.testclient import TestClient
from jose import jwt

from app.main import app

client = TestClient(app)

TEST_SECRET = "dev-insecure-supabase-jwt-secret-for-offline-testing-32bytes!"


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
    """Verify process endpoint parses uploaded text content and returns ready document."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    raw_text = (
        "# Introduction to Deep Learning\n\n"
        "Deep learning is a subset of machine learning based on artificial neural networks. "
        "Convolutional neural networks excel in computer vision tasks."
    )
    file_bytes = raw_text.encode("utf-8")

    response = client.post(
        f"/api/v1/documents/{doc_id}/process",
        files={"file": ("lecture_deep_learning.md", io.BytesIO(file_bytes), "text/markdown")},
        headers=headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["id"] == str(doc_id)
    assert data["data"]["status"] == "ready"
    assert data["data"]["word_count"] > 10
    assert data["data"]["checksum"] is not None


def test_process_scanned_pdf_flags_needs_ocr() -> None:
    """Verify process endpoint sets status to needs_ocr when PDF lacks extractable text."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    headers = create_auth_header(user_id)

    # In-memory empty/scanned-like PDF
    doc = fitz.open()
    doc.new_page()
    pdf_bytes = doc.write()
    doc.close()

    response = client.post(
        f"/api/v1/documents/{doc_id}/process",
        files={"file": ("scanned_assignment.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"]["status"] == "needs_ocr"
    assert data["data"]["error_code"] == "NEEDS_OCR"


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
