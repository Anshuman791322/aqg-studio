"""Tests for private storage path construction and validation services."""

import uuid

from app.services.storage import (
    build_document_storage_path,
    build_export_storage_path,
    sanitize_filename,
    validate_storage_path,
)


def test_sanitize_filename_removes_traversal() -> None:
    """Verify filename sanitizer strips path traversal elements."""
    assert sanitize_filename("../../../etc/passwd") == "passwd"
    assert sanitize_filename("..\\..\\windows\\system32.dll") == "system32.dll"
    assert sanitize_filename("lecture 1: biology notes!.pdf") == "lecture_1__biology_notes_.pdf"
    assert sanitize_filename("   ") == "unnamed_document"


def test_build_document_storage_path() -> None:
    """Verify document storage path follows {user_id}/{document_id}/{filename} format."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()
    path = build_document_storage_path(
        user_id=user_id,
        document_id=doc_id,
        filename="Physics 101.pdf",
    )
    assert path == f"{user_id}/{doc_id}/Physics_101.pdf"


def test_build_export_storage_path() -> None:
    """Verify export storage path format."""
    user_id = uuid.uuid4()
    assessment_id = uuid.uuid4()
    export_id = uuid.uuid4()
    path = build_export_storage_path(
        user_id=user_id,
        assessment_id=assessment_id,
        export_id=export_id,
        extension=".xml",
    )
    assert path == f"{user_id}/{assessment_id}/{export_id}.xml"


def test_validate_storage_path_accepts_valid_user_path() -> None:
    """Verify validate_storage_path returns True for correctly scoped paths."""
    user_id = uuid.uuid4()
    valid_path = f"{user_id}/doc_123/notes.pdf"
    assert validate_storage_path(valid_path, user_id) is True


def test_validate_storage_path_rejects_cross_tenant_access() -> None:
    """Verify validate_storage_path rejects paths belonging to another user ID."""
    victim_user_id = uuid.uuid4()
    attacker_user_id = uuid.uuid4()

    victim_path = f"{victim_user_id}/private_exam/exam.pdf"
    assert validate_storage_path(victim_path, attacker_user_id) is False


def test_validate_storage_path_rejects_path_traversal() -> None:
    """Verify validate_storage_path rejects paths with directory traversal sequences."""
    user_id = uuid.uuid4()
    assert validate_storage_path(f"{user_id}/../other_user/data.pdf", user_id) is False
    assert validate_storage_path(f"{user_id}/..\\data.pdf", user_id) is False
    assert validate_storage_path("", user_id) is False


async def test_supabase_storage_rest_operations_mocked() -> None:
    """Verify upload, download, delete, and sign URL storage methods with mock HTTP responses."""
    from unittest.mock import AsyncMock, patch

    from app.services.storage import (
        create_signed_download_url,
        delete_file_from_storage,
        download_file_from_storage,
        upload_file_to_storage,
    )

    with (
        patch("app.services.storage.get_storage_base_url", return_value="https://test.supabase.co/storage/v1"),
        patch("app.services.storage.get_storage_headers", return_value={"Authorization": "Bearer mock"}),
    ):
        mock_upload_resp = AsyncMock(status_code=200)
        mock_download_resp = AsyncMock(status_code=200, content=b"mock-binary-data")
        mock_delete_resp = AsyncMock(status_code=200)
        mock_sign_resp = AsyncMock(status_code=200, json=lambda: {"signedURL": "/object/sign/url123"})

        with patch("httpx.AsyncClient.post", side_effect=[mock_upload_resp, mock_sign_resp]), \
             patch("httpx.AsyncClient.get", return_value=mock_download_resp), \
             patch("httpx.AsyncClient.request", return_value=mock_delete_resp):

            # 1. Test upload
            uploaded = await upload_file_to_storage("generated-exports", "user/ass/exp.pdf", b"data")
            assert uploaded is True

            # 2. Test download
            downloaded = await download_file_from_storage("generated-exports", "user/ass/exp.pdf")
            assert downloaded == b"mock-binary-data"

            # 3. Test signed URL
            signed_url = await create_signed_download_url("generated-exports", "user/ass/exp.pdf")
            assert signed_url == "https://test.supabase.co/storage/v1/object/sign/url123"

            # 4. Test delete
            deleted = await delete_file_from_storage("generated-exports", "user/ass/exp.pdf")
            assert deleted is True

