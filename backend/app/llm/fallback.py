"""Fallback LLM gateway with backoff, jitter, request budgeting, and multi-provider failover."""

import asyncio
import random
from typing import TypeVar

from pydantic import BaseModel

from app.core.logging import get_logger
from app.llm.base import LLMProvider
from app.llm.errors import (
    LLMAllProvidersFailedError,
    LLMAuthenticationError,
    LLMBudgetExceededError,
    LLMConnectionError,
    LLMError,
    LLMInvalidInputError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMTransientError,
)
from app.llm.schemas import ChatMessage, ChatResponse, LLMUsage, ProviderCapabilities

logger = get_logger("aqg.llm.fallback")
T = TypeVar("T", bound=BaseModel)


class FallbackLLMGateway(LLMProvider):
    """Orchestrates an ordered list of LLM providers with automatic retry, backoff, and failover."""

    def __init__(
        self,
        providers: list[LLMProvider],
        *,
        max_retries_per_provider: int = 2,
        base_backoff_seconds: float = 0.5,
        max_backoff_seconds: float = 5.0,
        max_request_budget: int = 1000,
    ) -> None:
        if not providers:
            raise ValueError("FallbackLLMGateway requires at least one LLMProvider.")
        self.providers = providers
        self.max_retries_per_provider = max_retries_per_provider
        self.base_backoff_seconds = base_backoff_seconds
        self.max_backoff_seconds = max_backoff_seconds
        self.max_request_budget = max_request_budget
        self._request_counter = 0

    @property
    def provider_name(self) -> str:
        return f"gateway[{','.join(p.provider_name for p in self.providers)}]"

    @property
    def default_model(self) -> str:
        return self.providers[0].default_model

    @property
    def capabilities(self) -> ProviderCapabilities:
        # Gateway provides capabilities of the primary provider
        return self.providers[0].capabilities

    def _check_and_increment_budget(self) -> None:
        """Check application-level request budget."""
        if self._request_counter >= self.max_request_budget:
            raise LLMBudgetExceededError(
                message=f"Application LLM request budget ({self.max_request_budget}) exceeded."
            )
        self._request_counter += 1

    def reset_budget(self) -> None:
        """Reset request counter."""
        self._request_counter = 0

    async def _calculate_backoff_delay(self, attempt: int) -> float:
        """Compute exponential backoff delay with random jitter."""
        exponential = self.base_backoff_seconds * (2 ** attempt)
        jitter = random.uniform(0.05, 0.25)
        delay = min(exponential + jitter, self.max_backoff_seconds)
        return delay

    async def complete_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> ChatResponse:
        """Attempt chat completion across configured providers in sequence with retries."""
        self._check_and_increment_budget()

        attempted_providers: list[str] = []
        collected_errors: list[Exception] = []

        for p_idx, provider in enumerate(self.providers):
            attempted_providers.append(provider.provider_name)

            for attempt in range(self.max_retries_per_provider + 1):
                try:
                    logger.info(
                        "Executing chat completion with provider",
                        extra={
                            "provider": provider.provider_name,
                            "attempt": attempt + 1,
                            "is_fallback": p_idx > 0,
                        },
                    )
                    return await provider.complete_chat(
                        messages,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                    )
                except LLMInvalidInputError as non_retryable:
                    # Invalid payload error is fatal and must not be retried or failed over
                    logger.error(
                        "Non-retryable invalid input error from provider",
                        extra={"provider": provider.provider_name, "error": str(non_retryable)},
                    )
                    raise non_retryable
                except LLMAuthenticationError as auth_err:
                    # Authentication failure cannot be solved with retry on the same provider;
                    # skip immediately to the next provider in the fallback chain
                    logger.warning(
                        "Provider authentication failed, skipping to next provider",
                        extra={"provider": provider.provider_name, "error": str(auth_err)},
                    )
                    collected_errors.append(auth_err)
                    break
                except (LLMRateLimitError, LLMTimeoutError, LLMConnectionError, LLMTransientError, LLMError) as err:
                    collected_errors.append(err)
                    if attempt < self.max_retries_per_provider:
                        delay = await self._calculate_backoff_delay(attempt)
                        logger.warning(
                            "Transient provider failure, retrying with backoff",
                            extra={
                                "provider": provider.provider_name,
                                "attempt": attempt + 1,
                                "delay_s": round(delay, 2),
                                "error": str(err)[:200],
                            },
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.warning(
                            "Provider exhausted maximum retries, falling back to next provider",
                            extra={
                                "failed_provider": provider.provider_name,
                                "next_provider": (
                                    self.providers[p_idx + 1].provider_name
                                    if p_idx + 1 < len(self.providers)
                                    else "None"
                                ),
                            },
                        )

        raise LLMAllProvidersFailedError(
            message=f"All {len(attempted_providers)} configured LLM providers failed.",
            attempted_providers=attempted_providers,
            errors=collected_errors,
        )

    async def complete_structured(
        self,
        messages: list[ChatMessage],
        response_model: type[T],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> tuple[T, LLMUsage]:
        """Attempt structured completion across configured providers in sequence with retries."""
        self._check_and_increment_budget()

        attempted_providers: list[str] = []
        collected_errors: list[Exception] = []

        for p_idx, provider in enumerate(self.providers):
            attempted_providers.append(provider.provider_name)

            for attempt in range(self.max_retries_per_provider + 1):
                try:
                    logger.info(
                        "Executing structured completion with provider",
                        extra={
                            "provider": provider.provider_name,
                            "attempt": attempt + 1,
                            "is_fallback": p_idx > 0,
                            "schema": response_model.__name__,
                        },
                    )
                    return await provider.complete_structured(
                        messages,
                        response_model,
                        model=model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        timeout=timeout,
                    )
                except LLMInvalidInputError as non_retryable:
                    raise non_retryable
                except LLMAuthenticationError as auth_err:
                    collected_errors.append(auth_err)
                    break
                except Exception as err:
                    collected_errors.append(err)
                    if attempt < self.max_retries_per_provider:
                        delay = await self._calculate_backoff_delay(attempt)
                        await asyncio.sleep(delay)
                    else:
                        break

        raise LLMAllProvidersFailedError(
            message=f"All {len(attempted_providers)} configured LLM providers failed for structured output.",
            attempted_providers=attempted_providers,
            errors=collected_errors,
        )
