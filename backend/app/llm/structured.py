"""Structured output parser, JSON repair mechanism, and schema validator."""

import json
import re
from collections.abc import Callable, Coroutine
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.logging import get_logger
from app.llm.errors import LLMStructuredOutputError
from app.llm.schemas import ChatMessage, ChatResponse, LLMUsage

logger = get_logger("aqg.llm.structured")
T = TypeVar("T", bound=BaseModel)

# Regex to strip markdown code blocks
JSON_BLOCK_REGEX = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def strip_markdown_fences(text: str) -> str:
    """Strip harmless markdown code fences enclosing JSON content."""
    trimmed = text.strip()
    match = JSON_BLOCK_REGEX.search(trimmed)
    if match:
        return match.group(1).strip()

    # If starts with ``` and ends with ```, strip them
    if trimmed.startswith("```") and trimmed.endswith("```"):
        lines = trimmed.split("\n")
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()

    return trimmed


def extract_json_candidate(text: str) -> str:
    """Extract candidate JSON substring from freeform text."""
    cleaned = strip_markdown_fences(text)
    # Check for direct object or array
    if (cleaned.startswith("{") and cleaned.endswith("}")) or (
        cleaned.startswith("[") and cleaned.endswith("]")
    ):
        return cleaned

    # Search for first { to last }
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return cleaned[first_brace : last_brace + 1]

    return cleaned


def build_structured_system_prompt(response_model: type[BaseModel]) -> str:
    """Generate explicit schema instruction for models lacking native JSON schema support."""
    schema_json = json.dumps(response_model.model_json_schema(), indent=2)
    return (
        "You must respond with valid, parseable JSON matching the following JSON Schema.\n"
        "Do not include explanations, thinking, or commentary outside the JSON object.\n"
        f"JSON Schema:\n{schema_json}"
    )


async def execute_structured_workflow(
    chat_completer: Callable[..., Coroutine[Any, Any, ChatResponse]],
    messages: list[ChatMessage],
    response_model: type[T],
    *,
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int | None = None,
    timeout: float | None = None,
    supports_native_json: bool = False,
    provider_name: str = "llm",
) -> tuple[T, LLMUsage]:
    """Execute chat completion and validate against Pydantic schema with at most one repair attempt."""
    prepared_messages = list(messages)
    schema_instruction = build_structured_system_prompt(response_model)

    # Append JSON schema instructions to ensure free/fallback models adhere to format
    if prepared_messages and prepared_messages[0].role == "system":
        existing_sys = prepared_messages[0].content
        prepared_messages[0] = ChatMessage(
            role="system",
            content=f"{existing_sys}\n\n{schema_instruction}",
        )
    else:
        prepared_messages.insert(0, ChatMessage(role="system", content=schema_instruction))

    # Initial completion pass
    initial_resp = await chat_completer(
        prepared_messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    raw_content = initial_resp.content
    total_usage = initial_resp.usage

    try:
        candidate_json = extract_json_candidate(raw_content)
        parsed_data = json.loads(candidate_json)
        validated_instance = response_model.model_validate(parsed_data)
        return validated_instance, total_usage
    except (json.JSONDecodeError, ValidationError) as initial_err:
        err_msg = str(initial_err)
        logger.warning(
            "Initial structured output parsing failed, executing controlled repair pass",
            extra={"provider": provider_name, "error": err_msg[:200]},
        )

    # Controlled Repair Pass (At most 1 attempt)
    repair_prompt = (
        f"Your previous response failed validation with error: {err_msg[:300]}.\n"
        f"Previous response was:\n{raw_content[:800]}\n\n"
        f"Please repair the response and return ONLY valid JSON matching the schema:\n"
        f"{schema_instruction}"
    )

    repair_messages = list(prepared_messages)
    repair_messages.append(ChatMessage(role="assistant", content=raw_content))
    repair_messages.append(ChatMessage(role="user", content=repair_prompt))

    repair_resp = await chat_completer(
        repair_messages,
        model=model,
        temperature=0.1,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    repair_content = repair_resp.content

    # Accumulate token usage
    total_usage.input_tokens += repair_resp.usage.input_tokens
    total_usage.output_tokens += repair_resp.usage.output_tokens
    total_usage.total_tokens += repair_resp.usage.total_tokens
    total_usage.latency_ms += repair_resp.usage.latency_ms

    try:
        repaired_candidate = extract_json_candidate(repair_content)
        repaired_data = json.loads(repaired_candidate)
        validated_instance = response_model.model_validate(repaired_data)
        return validated_instance, total_usage
    except (json.JSONDecodeError, ValidationError) as second_err:
        logger.error(
            "Structured output repair pass failed schema validation",
            extra={"provider": provider_name, "error": str(second_err)[:200]},
        )
        raise LLMStructuredOutputError(
            message=f"Model failed structured validation after repair: {str(second_err)}",
            raw_output=repair_content,
            provider=provider_name,
            model=model or total_usage.model,
            validation_errors=[str(second_err)],
        ) from second_err
