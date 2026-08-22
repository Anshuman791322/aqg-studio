"""Tests for in-memory burst rate limiting and PostgreSQL quota manager."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.core.config import get_settings
from app.core.errors import AppException, ValidationException
from app.core.quota import BurstRateLimiter, quota_service
from app.models.entities import LLMUsageDaily

settings = get_settings()


def test_burst_rate_limiter_sliding_window() -> None:
    """Verify in-memory sliding window allows normal traffic and blocks bursts."""
    limiter = BurstRateLimiter(limit=5, window_seconds=10)
    key = "test_user_1"

    # First 5 requests must succeed
    for _ in range(5):
        allowed, retry_after, remaining = limiter.is_allowed(key)
        assert allowed is True
        assert retry_after == 0

    # 6th request must be rejected
    allowed, retry_after, remaining = limiter.is_allowed(key)
    assert allowed is False
    assert retry_after > 0
    assert remaining == 0

    # Distinct user is unaffected
    allowed_other, _, _ = limiter.is_allowed("test_user_2")
    assert allowed_other is True


def test_quota_service_validate_question_count() -> None:
    """Verify per-assessment question bound validation."""
    quota_service.validate_question_count(10)
    quota_service.validate_question_count(settings.MAX_QUESTIONS_PER_ASSESSMENT)

    with pytest.raises(ValidationException) as exc_info_zero:
        quota_service.validate_question_count(0)
    assert exc_info_zero.value.code == "INVALID_QUESTION_COUNT"

    with pytest.raises(ValidationException) as exc_info_excess:
        quota_service.validate_question_count(settings.MAX_QUESTIONS_PER_ASSESSMENT + 1)
    assert exc_info_excess.value.code == "QUESTION_LIMIT_EXCEEDED"


@pytest.mark.asyncio
async def test_quota_service_daily_assessment_increment_success() -> None:
    """Verify check_and_increment_assessment_quota increments count when under limit."""
    user_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_usage = LLMUsageDaily(
        user_id=user_id,
        assessments_created=2,
        request_count=10,
        input_tokens=500,
        output_tokens=250,
    )

    with patch("app.core.quota.usage_repo.get_or_create_today", new=AsyncMock(return_value=mock_usage)):
        updated = await quota_service.check_and_increment_assessment_quota(mock_session, user_id)
        assert updated.assessments_created == 3
        mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_quota_service_daily_assessment_limit_exceeded() -> None:
    """Verify check_and_increment_assessment_quota raises 429 when limit reached."""
    user_id = uuid.uuid4()
    mock_session = AsyncMock()

    mock_usage = LLMUsageDaily(
        user_id=user_id,
        assessments_created=settings.MAX_ASSESSMENTS_PER_DAY,
        request_count=100,
        input_tokens=10000,
        output_tokens=5000,
    )

    with patch("app.core.quota.usage_repo.get_or_create_today", new=AsyncMock(return_value=mock_usage)):
        with pytest.raises(AppException) as exc_info:
            await quota_service.check_and_increment_assessment_quota(mock_session, user_id)

        assert exc_info.value.status_code == 429
        assert exc_info.value.code == "DAILY_QUOTA_EXCEEDED"
        assert exc_info.value.details is not None
        assert exc_info.value.details[0].field == "quota"
