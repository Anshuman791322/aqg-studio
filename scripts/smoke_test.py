from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import AsyncMock, patch

# Ensure backend directory is in python path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient

from app.core.auth import CurrentUser, get_current_user
from app.core.config import get_settings
from app.core.quota import burst_rate_limiter, quota_service
from app.db.session import get_db
from app.main import app
from app.models.entities import Assessment, Document, LLMUsageDaily
from app.services.parsers.docx import DOCXDocumentParser
from app.services.parsers.pdf import PDFDocumentParser
from app.services.parsers.pptx import PPTXDocumentParser
from app.services.storage import (
    build_document_storage_path,
    build_export_storage_path,
    validate_storage_path,
)

settings = get_settings()
client = TestClient(app)


class DeploymentSmokeTests(unittest.TestCase):
    """End-to-end deployment readiness smoke tests."""

    def setUp(self) -> None:
        burst_rate_limiter.reset()
        app.dependency_overrides.clear()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        burst_rate_limiter.reset()

    def test_01_liveness_probe(self) -> None:
        """Verify /health/live returns 200 OK with status: ok."""
        res = client.get("/health/live")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ok")

    def test_02_readiness_probe(self) -> None:
        """Verify /health/ready returns 200 OK without calling external paid APIs."""
        res = client.get("/health/ready")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data.get("status"), "ready")
        self.assertIn("database", data)

    def test_03_security_headers_injected(self) -> None:
        """Verify OWASP-recommended security headers are injected into HTTP responses."""
        res = client.get("/health/live")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "DENY")
        self.assertEqual(res.headers.get("X-XSS-Protection"), "1; mode=block")
        self.assertEqual(res.headers.get("Referrer-Policy"), "strict-origin-when-cross-origin")
        self.assertIn("X-Correlation-ID", res.headers)

    def test_04_auth_guard_rejection(self) -> None:
        """Verify protected endpoints strictly reject unauthenticated requests with 401."""
        unauthenticated_routes = [
            ("GET", "/api/v1/auth/me"),
            ("GET", "/api/v1/documents"),
            ("GET", "/api/v1/assessments"),
            ("POST", "/api/v1/assessments"),
        ]
        for method, route in unauthenticated_routes:
            if method == "GET":
                res = client.get(route)
            else:
                res = client.post(route, json={})
            self.assertEqual(
                res.status_code,
                401,
                f"Expected 401 for unauthenticated request to {method} {route}, got {res.status_code}",
            )
            self.assertFalse(res.json().get("success"))

    def test_05_storage_path_isolation(self) -> None:
        """Verify storage paths strictly enforce user-id sandboxing and prevent traversal."""
        user_a = uuid.uuid4()
        user_b = uuid.uuid4()
        doc_id = uuid.uuid4()
        exp_id = uuid.uuid4()

        doc_path = build_document_storage_path(user_a, doc_id, "notes.pdf")
        self.assertTrue(validate_storage_path(doc_path, user_a))
        self.assertFalse(validate_storage_path(doc_path, user_b))

        exp_path = build_export_storage_path(user_a, doc_id, exp_id, "pdf")
        self.assertTrue(validate_storage_path(exp_path, user_a))
        self.assertFalse(validate_storage_path(exp_path, user_b))

        # Path traversal sequences rejected
        self.assertFalse(validate_storage_path(f"{user_a}/../{user_b}/exploit.pdf", user_a))

    def test_06_parser_signature_and_decompression_defenses(self) -> None:
        """Verify binary parser defenses against invalid signatures and corrupted headers."""
        pdf_parser = PDFDocumentParser()
        fake_pdf = pdf_parser.parse(b"NOT_A_PDF_FILE", "fake.pdf")
        self.assertEqual(fake_pdf.error_code, "INVALID_FILE_SIGNATURE")

        docx_parser = DOCXDocumentParser()
        fake_docx = docx_parser.parse(b"NOT_A_ZIP_ARCHIVE", "fake.docx")
        self.assertEqual(fake_docx.error_code, "INVALID_FILE_SIGNATURE")

        pptx_parser = PPTXDocumentParser()
        fake_pptx = pptx_parser.parse(b"NOT_A_PPTX_ARCHIVE", "fake.pptx")
        self.assertEqual(fake_pptx.error_code, "INVALID_FILE_SIGNATURE")

    def test_07_burst_rate_limiter_burst_rejection(self) -> None:
        """Verify burst rate limiter rejects rapid bursts exceeding limit with 429."""
        burst_rate_limiter.reset()
        test_ip = "192.168.1.100"

        # Simulate requests up to limit
        for _ in range(settings.BURST_RATE_LIMIT_PER_MINUTE):
            allowed, _, _ = burst_rate_limiter.is_allowed(f"ip_{test_ip}")
            self.assertTrue(allowed)

        # Next request must be throttled
        allowed, retry_after, _ = burst_rate_limiter.is_allowed(f"ip_{test_ip}")
        self.assertFalse(allowed)
        self.assertGreater(retry_after, 0)

    def test_08_daily_quota_atomic_enforcement(self) -> None:
        """Verify daily assessment creation quota rejects requests beyond MAX_ASSESSMENTS_PER_DAY."""
        user_id = uuid.uuid4()
        mock_db = AsyncMock()

        # Simulate user having reached daily quota
        mock_usage = LLMUsageDaily(
            user_id=user_id,
            assessments_created=settings.MAX_ASSESSMENTS_PER_DAY,
            request_count=50,
            input_tokens=1000,
            output_tokens=500,
        )

        with patch("app.core.quota.usage_repo.get_or_create_today", new=AsyncMock(return_value=mock_usage)):
            with self.assertRaises(Exception) as ctx:
                import asyncio
                asyncio.run(quota_service.check_and_increment_assessment_quota(mock_db, user_id))

            self.assertEqual(ctx.exception.code, "DAILY_QUOTA_EXCEEDED")
            self.assertEqual(ctx.exception.status_code, 429)


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(DeploymentSmokeTests)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    if not result.wasSuccessful():
        sys.exit(1)
    print("\n[SMOKE TEST PASSED] All 8 deployment health, security, and quota smoke tests succeeded.")
