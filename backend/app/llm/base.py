"""Abstract base provider interface for language models."""

from abc import ABC, abstractmethod
from typing import TypeVar

from pydantic import BaseModel

from app.llm.schemas import ChatMessage, ChatResponse, LLMUsage, ProviderCapabilities

T = TypeVar("T", bound=BaseModel)


class LLMProvider(ABC):
    """Abstract interface all LLM providers must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Identifier name for this provider (e.g. 'openrouter', 'nvidia', 'fake')."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model identifier string."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declared operational capabilities for this provider/model."""
        pass

    @abstractmethod
    async def complete_chat(
        self,
        messages: list[ChatMessage],
        *,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        timeout: float | None = None,
    ) -> ChatResponse:
        """Generate a chat completion response from the provider."""
        pass

    @abstractmethod
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
        """Generate a validated structured Pydantic object from the provider."""
        pass
