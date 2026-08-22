"""In-memory burst rate limiting and PostgreSQL-backed atomic quota management."""

import threading
import time as time_module
import uuid
from collections import defaultdict
from datetime import UTC, datetime, time, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.errors import AppException, ErrorDetail, ValidationException
from app.core.logging import get_logger
from app.models.entities import LLMUsageDaily
from app.repositories.usage import usage_repo

logger = get_logger("app.core.quota")
settings = get_settings()


class BurstRateLimiter:
    """Thread-safe in-memory sliding window rate limiter for burst mitigation without Redis."""

    def __init__(self, limit: int = 120, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> tuple[bool, int, int]:
        """Check if request is allowed under rate limit.

        Returns:
            tuple of (is_allowed: bool, retry_after_seconds: int, remaining_requests: int)
        """
        now = time_module.time()
        window_start = now - self.window_seconds

        with self._lock:
            # Prune timestamps older than window
            timestamps = [t for t in self._requests[key] if t > window_start]

            if len(timestamps) >= self.limit:
                oldest = timestamps[0]
                retry_after = max(1, int(oldest + self.window_seconds - now))
                self._requests[key] = timestamps
                return False, retry_after, 0

            timestamps.append(now)
            self._requests[key] = timestamps
            remaining = max(0, self.limit - len(timestamps))
            return True, 0, remaining

    def reset(self) -> None:
        """Reset rate limiter state (useful for test isolation)."""
        with self._lock:
            self._requests.clear()


# Global burst rate limiter instance
burst_rate_limiter = BurstRateLimiter(
    limit=settings.BURST_RATE_LIMIT_PER_MINUTE,
    window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS,
)


def _get_seconds_until_midnight_utc() -> int:
    """Compute number of seconds remaining until the next UTC midnight."""
    now = datetime.now(UTC)
    tomorrow = now.date() + timedelta(days=1)
    midnight = datetime.combine(tomorrow, time.min, tzinfo=UTC)
    return max(1, int((midnight - now).total_seconds()))


class QuotaService:
    """PostgreSQL-backed daily assessment and token quota manager."""

    @staticmethod
    def validate_question_count(count: int) -> None:
        """Enforce per-assessment question generation limits."""
        if count <= 0:
            raise ValidationException(
                message="Total questions must be at least 1.",
                code="INVALID_QUESTION_COUNT",
            )
        if count > settings.MAX_QUESTIONS_PER_ASSESSMENT:
            raise ValidationException(
                message=(
                    f"Assessment requested {count} questions, exceeding the maximum allowed "
                    f"limit of {settings.MAX_QUESTIONS_PER_ASSESSMENT} questions per assessment."
                ),
                code="QUESTION_LIMIT_EXCEEDED",
            )

    @staticmethod
    async def check_and_increment_assessment_quota(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> LLMUsageDaily:
        """Atomically verify and increment daily assessment creation quota in PostgreSQL."""
        usage = await usage_repo.get_or_create_today(session, user_id=user_id)

        if usage.assessments_created >= settings.MAX_ASSESSMENTS_PER_DAY:
            retry_after = _get_seconds_until_midnight_utc()
            logger.warning(
                f"User {user_id} exceeded daily assessment quota ({usage.assessments_created}/{settings.MAX_ASSESSMENTS_PER_DAY})"
            )
            raise AppException(
                code="DAILY_QUOTA_EXCEEDED",
                message=(
                    f"Daily limit of {settings.MAX_ASSESSMENTS_PER_DAY} assessments reached. "
                    "Please try again tomorrow when your daily quota resets."
                ),
                status_code=429,
                details=[ErrorDetail(field="quota", issue=f"Retry after {retry_after} seconds.")],
            )

        usage.assessments_created += 1
        await session.flush()
        return usage

    @staticmethod
    async def get_user_quota_summary(
        session: AsyncSession,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Retrieve user's active quota and today's consumption metrics."""
        usage = await usage_repo.get_or_create_today(session, user_id=user_id)
        return {
            "max_assessments_per_day": settings.MAX_ASSESSMENTS_PER_DAY,
            "assessments_created_today": usage.assessments_created,
            "assessments_remaining_today": max(
                0, settings.MAX_ASSESSMENTS_PER_DAY - usage.assessments_created
            ),
            "max_questions_per_assessment": settings.MAX_QUESTIONS_PER_ASSESSMENT,
            "total_requests_today": usage.request_count,
            "input_tokens_today": usage.input_tokens,
            "output_tokens_today": usage.output_tokens,
            "resets_in_seconds": _get_seconds_until_midnight_utc(),
        }


quota_service = QuotaService()
