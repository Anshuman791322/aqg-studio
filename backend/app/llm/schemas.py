"""Data schemas and types for LLM requests, responses, usage, and capabilities."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

RoleType = Literal["system", "user", "assistant", "tool"]


class ChatMessage(BaseModel):
    """Normalized chat message."""

    model_config = ConfigDict(extra="ignore")

    role: RoleType
    content: str
    name: str | None = None


class LLMUsage(BaseModel):
    """Normalized token usage and execution telemetry."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    model: str
    latency_ms: float = 0.0
    request_id: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """Normalized chat completion response."""

    model_config = ConfigDict(extra="ignore")

    content: str
    usage: LLMUsage
    finish_reason: str | None = "stop"
    raw_response: dict[str, Any] | None = None


class ProviderCapabilities(BaseModel):
    """Declared capabilities and constraints for a model provider."""

    model_config = ConfigDict(extra="ignore")

    supports_structured_output: bool = False
    supports_tools: bool = False
    supports_embeddings: bool = False
    max_context_tokens: int = 8192
