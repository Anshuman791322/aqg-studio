"""OpenRouter LLM Provider implementation using async HTTP client."""

import time
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.llm.base import LLMProvider
from app.llm.errors import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMInvalidInputError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMTransientError,
)
from app.llm.schemas import ChatMessage, ChatResponse, LLMUsage, ProviderCapabilities
from app.llm.structured import execute_structured_workflow

logger = get_logger("aqg.llm.openrouter")
settings = get_settings()
T = TypeVar("T", bound=BaseModel)


class OpenRouterProvider(LLMProvider):
    """Client for OpenRouter API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        default_model: str | None = None,
        app_title: str | None = None,
        http_referer: str | None = None,
        client: httpx.AsyncClient | None = None,
        capabilities: ProviderCapabilities | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        self._default_model = str(
            default_model
            or getattr(settings, "OPENROUTER_MODEL", settings.OPENROUTER_PRIMARY_MODEL)
        )
        self.app_title = app_title or getattr(settings, "OPENROUTER_APP_TITLE", "AQG Studio")
        self.http_referer = http_referer or getattr(
            settings, "OPENROUTER_HTTP_REFERER", "https://aqg.studio"
        )
        self.client = client
        self.default_timeout = timeout
        self._capabilities = capabilities or ProviderCapabilities(
            supports_structured_output=False,
            supports_tools=False,
            supports_embeddings=False,
            max_context_tokens=16384,
        )

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.http_referer:
            headers["HTTP-Referer"] = self.http_referer
        if self.app_title:
            headers["X-Title"] = self.app_title
        return headers

    async def complete_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> ChatResponse:
        """Execute chat completion request against OpenRouter."""
        if not self.api_key:
            raise LLMAuthenticationError(
                message="OpenRouter API key is missing or not configured.",
                provider=self.provider_name,
            )

        target_model = model or self._default_model
        req_timeout = timeout or self.default_timeout

        payload: dict[str, Any] = {
            "model": target_model,
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        start_time = time.perf_counter()

        logger.info(
            "Sending OpenRouter chat completion request",
            extra={"provider": self.provider_name, "model": target_model, "messages_count": len(messages)},
        )

        try:
            if self.client is not None:
                resp = await self.client.post(url, json=payload, headers=headers, timeout=req_timeout)
            else:
                async with httpx.AsyncClient() as client:
                    resp = await client.post(url, json=payload, headers=headers, timeout=req_timeout)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError(
                message=f"OpenRouter request timed out after {req_timeout}s: {str(exc)}",
                provider=self.provider_name,
                model=target_model,
            ) from exc
        except (httpx.NetworkError, httpx.ConnectError) as exc:
            raise LLMConnectionError(
                message=f"OpenRouter connection failed: {str(exc)}",
                provider=self.provider_name,
                model=target_model,
            ) from exc
        except Exception as exc:
            raise LLMError(
                message=f"OpenRouter unexpected request error: {str(exc)}",
                provider=self.provider_name,
                model=target_model,
            ) from exc

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        # Handle HTTP status codes
        if resp.status_code in (401, 403):
            raise LLMAuthenticationError(
                message=f"OpenRouter authentication failed (HTTP {resp.status_code}): {resp.text[:200]}",
                provider=self.provider_name,
                model=target_model,
            )
        if resp.status_code == 429:
            raise LLMRateLimitError(
                message=f"OpenRouter rate limit exceeded (HTTP 429): {resp.text[:200]}",
                provider=self.provider_name,
                model=target_model,
            )
        if 400 <= resp.status_code < 500:
            raise LLMInvalidInputError(
                message=f"OpenRouter invalid request (HTTP {resp.status_code}): {resp.text[:200]}",
                provider=self.provider_name,
                model=target_model,
            )
        if resp.status_code >= 500:
            raise LLMTransientError(
                message=f"OpenRouter transient error (HTTP {resp.status_code}): {resp.text[:200]}",
                provider=self.provider_name,
                model=target_model,
            )

        data = resp.json()
        choices = data.get("choices", [])
        if not choices:
            raise LLMTransientError(
                message="OpenRouter returned response with empty choices list.",
                provider=self.provider_name,
                model=target_model,
            )

        message_content = choices[0].get("message", {}).get("content", "") or ""
        finish_reason = choices[0].get("finish_reason", "stop")

        usage_info = data.get("usage", {})
        input_tokens = usage_info.get("prompt_tokens", 0)
        output_tokens = usage_info.get("completion_tokens", 0)
        total_tokens = usage_info.get("total_tokens", input_tokens + output_tokens)

        request_id = data.get("id") or resp.headers.get("x-request-id")

        usage = LLMUsage(
            provider=self.provider_name,
            model=data.get("model", target_model),
            latency_ms=latency_ms,
            request_id=request_id,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )

        logger.info(
            "OpenRouter completion successful",
            extra={
                "provider": self.provider_name,
                "model": usage.model,
                "latency_ms": round(latency_ms, 2),
                "total_tokens": total_tokens,
            },
        )

        return ChatResponse(
            content=message_content,
            usage=usage,
            finish_reason=finish_reason,
            raw_response=data,
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
        """Execute structured completion with schema injection and 1-pass repair."""
        return await execute_structured_workflow(
            chat_completer=self.complete_chat,
            messages=messages,
            response_model=response_model,
            model=model or self._default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            supports_native_json=self._capabilities.supports_structured_output,
            provider_name=self.provider_name,
        )
