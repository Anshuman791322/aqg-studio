"""Deterministic fake LLM provider for unit and integration testing."""

import json
from collections import deque
from typing import Any, TypeVar

from pydantic import BaseModel

from app.llm.base import LLMProvider
from app.llm.schemas import ChatMessage, ChatResponse, LLMUsage, ProviderCapabilities
from app.llm.structured import execute_structured_workflow

T = TypeVar("T", bound=BaseModel)


class FakeLLMProvider(LLMProvider):
    """Deterministic, scriptable LLM Provider for testing and local offline execution."""

    def __init__(
        self,
        provider_name: str = "fake",
        default_model: str = "fake-model-v1",
        scripted_responses: list[str | dict[str, Any] | Exception] | None = None,
        capabilities: ProviderCapabilities | None = None,
    ) -> None:
        self._provider_name = provider_name
        self._default_model = default_model
        self._queue: deque[str | dict[str, Any] | Exception] = deque(
            scripted_responses or ["Hello! This is a scripted response from FakeLLMProvider."]
        )
        self._capabilities = capabilities or ProviderCapabilities(
            supports_structured_output=True,
            supports_tools=True,
            supports_embeddings=True,
            max_context_tokens=32768,
        )
        self.call_history: list[dict[str, Any]] = []

    @property
    def provider_name(self) -> str:
        return self._provider_name

    @property
    def default_model(self) -> str:
        return self._default_model

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._capabilities

    def add_response(self, response: str | dict[str, Any] | Exception) -> None:
        """Enqueue a scripted response or exception."""
        self._queue.append(response)

    def set_responses(self, responses: list[str | dict[str, Any] | Exception]) -> None:
        """Replace scripted response queue."""
        self._queue = deque(responses)

    async def complete_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> ChatResponse:
        """Pop and return the next scripted response or raise configured exception."""
        target_model = model or self._default_model
        self.call_history.append({
            "messages": messages,
            "model": target_model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": timeout,
        })

        if not self._queue:
            # Default fallback when queue is exhausted
            content = "Default scripted response."
        else:
            item = self._queue.popleft()
            if isinstance(item, Exception):
                raise item
            content = json.dumps(item) if isinstance(item, dict) else str(item)

        usage = LLMUsage(
            provider=self._provider_name,
            model=target_model,
            latency_ms=15.0,
            request_id=f"fake_req_{len(self.call_history)}",
            input_tokens=sum(len(m.content.split()) for m in messages),
            output_tokens=len(content.split()),
            total_tokens=sum(len(m.content.split()) for m in messages) + len(content.split()),
        )

        return ChatResponse(
            content=content,
            usage=usage,
            finish_reason="stop",
            raw_response={"fake": True, "model": target_model},
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
        """Execute structured completion against fake provider with schema validation."""
        return await execute_structured_workflow(
            chat_completer=self.complete_chat,
            messages=messages,
            response_model=response_model,
            model=model or self._default_model,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            supports_native_json=self._capabilities.supports_structured_output,
            provider_name=self._provider_name,
        )
