"""LLM subsystem module exports."""

from app.llm.base import LLMProvider
from app.llm.errors import (
    LLMAllProvidersFailedError,
    LLMAuthenticationError,
    LLMBudgetExceededError,
    LLMConnectionError,
    LLMError,
    LLMInvalidInputError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMTransientError,
)
from app.llm.factory import create_llm_gateway, get_llm_gateway
from app.llm.fake import FakeLLMProvider
from app.llm.fallback import FallbackLLMGateway
from app.llm.nvidia import NVIDIAProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.schemas import (
    ChatMessage,
    ChatResponse,
    LLMUsage,
    ProviderCapabilities,
)

__all__ = [
    "LLMProvider",
    "ChatMessage",
    "ChatResponse",
    "LLMUsage",
    "ProviderCapabilities",
    "OpenRouterProvider",
    "NVIDIAProvider",
    "FakeLLMProvider",
    "FallbackLLMGateway",
    "create_llm_gateway",
    "get_llm_gateway",
    "LLMError",
    "LLMAuthenticationError",
    "LLMInvalidInputError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMConnectionError",
    "LLMTransientError",
    "LLMStructuredOutputError",
    "LLMBudgetExceededError",
    "LLMAllProvidersFailedError",
]
