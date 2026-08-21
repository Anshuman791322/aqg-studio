"""Typed exceptions for LLM providers, retries, and fallback handling."""

from typing import Any


class LLMError(Exception):
    """Base class for all LLM-related errors."""

    def __init__(
        self,
        message: str,
        provider: str | None = None,
        model: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.provider = provider
        self.model = model
        self.details = details or {}


class LLMAuthenticationError(LLMError):
    """Authentication or authorization failure (HTTP 401/403)."""
    pass


class LLMInvalidInputError(LLMError):
    """Invalid input payload or unsupported parameters (HTTP 400/422). Non-retryable."""
    pass


class LLMRateLimitError(LLMError):
    """Rate limit or quota exhausted (HTTP 429). Retryable with backoff."""
    pass


class LLMTimeoutError(LLMError):
    """Request timed out waiting for provider response. Retryable / Fallback eligible."""
    pass


class LLMConnectionError(LLMError):
    """Network connection failure or socket error. Retryable / Fallback eligible."""
    pass


class LLMTransientError(LLMError):
    """Transient server error (HTTP 500/502/503/504). Retryable / Fallback eligible."""
    pass


class LLMStructuredOutputError(LLMError):
    """Model output failed schema validation after repair attempt."""

    def __init__(
        self,
        message: str,
        raw_output: str,
        provider: str | None = None,
        model: str | None = None,
        validation_errors: list[str] | None = None,
    ) -> None:
        super().__init__(message, provider=provider, model=model)
        self.raw_output = raw_output
        self.validation_errors = validation_errors or []


class LLMBudgetExceededError(LLMError):
    """Application request or token budget exhausted."""
    pass


class LLMAllProvidersFailedError(LLMError):
    """All configured LLM providers in fallback chain failed."""

    def __init__(
        self,
        message: str,
        attempted_providers: list[str],
        errors: list[Exception],
    ) -> None:
        super().__init__(message)
        self.attempted_providers = attempted_providers
        self.errors = errors
