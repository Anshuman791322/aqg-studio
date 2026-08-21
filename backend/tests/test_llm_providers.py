"""Unit and integration tests for LLM providers, structured output repair, and fallback gateway."""

import json
import logging

import httpx
import pytest
from pydantic import BaseModel, Field

from app.llm.errors import (
    LLMAllProvidersFailedError,
    LLMBudgetExceededError,
    LLMConnectionError,
    LLMRateLimitError,
    LLMStructuredOutputError,
    LLMTimeoutError,
    LLMTransientError,
)
from app.llm.fake import FakeLLMProvider
from app.llm.fallback import FallbackLLMGateway
from app.llm.nvidia import NVIDIAProvider
from app.llm.openrouter import OpenRouterProvider
from app.llm.schemas import ChatMessage


# Test schema for structured output
class SampleQuestionSchema(BaseModel):
    stem: str
    options: list[str] = Field(..., min_length=2)
    correct_answer: str
    bloom_level: str


# ------------------------------------------------------------------------------
# 1. OpenRouter Request Construction & Response
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_openrouter_request_construction_and_success() -> None:
    """Verify OpenRouter correctly constructs headers, payload, and extracts usage."""
    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        data = json.loads(request.content.decode("utf-8"))
        assert data["model"] == "openrouter/free"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Hello OpenRouter"

        response_body = {
            "id": "gen_12345",
            "model": "openrouter/free",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "Hello human!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        }
        return httpx.Response(200, json=response_body)

    mock_transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        provider = OpenRouterProvider(
            api_key="sk-or-v1-mock-secret-key-12345",
            base_url="https://openrouter.ai/api/v1",
            default_model="openrouter/free",
            app_title="AQG Studio Unit Test",
            http_referer="https://aqg.studio/test",
            client=client,
        )

        resp = await provider.complete_chat(
            [ChatMessage(role="user", content="Hello OpenRouter")]
        )

        assert resp.content == "Hello human!"
        assert resp.usage.provider == "openrouter"
        assert resp.usage.total_tokens == 15
        assert resp.usage.request_id == "gen_12345"

        # Verify request headers
        req = captured_requests[0]
        assert req.headers["Authorization"] == "Bearer sk-or-v1-mock-secret-key-12345"
        assert req.headers["HTTP-Referer"] == "https://aqg.studio/test"
        assert req.headers["X-Title"] == "AQG Studio Unit Test"


# ------------------------------------------------------------------------------
# 2. NVIDIA Request Construction & Response
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_nvidia_request_construction_and_success() -> None:
    """Verify NVIDIA provider correctly constructs headers and extracts usage."""
    captured_requests: list[httpx.Request] = []

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured_requests.append(request)
        response_body = {
            "id": "nv_req_9876",
            "model": "meta/llama-3.3-70b-instruct",
            "choices": [
                {
                    "message": {"role": "assistant", "content": "NVIDIA NIM response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 20,
                "completion_tokens": 10,
                "total_tokens": 30,
            },
        }
        return httpx.Response(200, json=response_body)

    mock_transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        provider = NVIDIAProvider(
            api_key="nvapi-mock-secret-key-67890",
            base_url="https://integrate.api.nvidia.com/v1",
            default_model="meta/llama-3.3-70b-instruct",
            client=client,
        )

        resp = await provider.complete_chat([ChatMessage(role="user", content="Test NVIDIA")])

        assert resp.content == "NVIDIA NIM response"
        assert resp.usage.provider == "nvidia"
        assert resp.usage.total_tokens == 30

        req = captured_requests[0]
        assert req.headers["Authorization"] == "Bearer nvapi-mock-secret-key-67890"


# ------------------------------------------------------------------------------
# 3. Successful Structured Response & Markdown Fences
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_structured_response_with_markdown_fences() -> None:
    """Verify JSON with surrounding markdown code fences is cleaned and parsed."""
    fenced_payload = (
        "```json\n"
        "{\n"
        '  "stem": "What is the capital of France?",\n'
        '  "options": ["Paris", "London", "Berlin", "Madrid"],\n'
        '  "correct_answer": "Paris",\n'
        '  "bloom_level": "Remember"\n'
        "}\n"
        "```"
    )
    fake_provider = FakeLLMProvider(scripted_responses=[fenced_payload])

    res, usage = await fake_provider.complete_structured(
        [ChatMessage(role="user", content="Generate question")],
        response_model=SampleQuestionSchema,
    )

    assert isinstance(res, SampleQuestionSchema)
    assert res.stem == "What is the capital of France?"
    assert res.correct_answer == "Paris"
    assert len(res.options) == 4
    assert usage.provider == "fake"


# ------------------------------------------------------------------------------
# 4. Controlled 1-Pass Repair Attempt
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_structured_response_one_repair_attempt_success() -> None:
    """Verify that when initial output is invalid, exactly 1 repair attempt executes and succeeds."""
    # Attempt 1: Invalid JSON (missing options list)
    invalid_json = '{"stem": "What is DNA?", "correct_answer": "Deoxyribonucleic acid"}'
    # Attempt 2 (Repair): Valid JSON
    valid_json = (
        "{\n"
        '  "stem": "What is DNA?",\n'
        '  "options": ["Deoxyribonucleic acid", "Ribonucleic acid", "Protein", "Lipid"],\n'
        '  "correct_answer": "Deoxyribonucleic acid",\n'
        '  "bloom_level": "Understand"\n'
        "}"
    )

    fake_provider = FakeLLMProvider(scripted_responses=[invalid_json, valid_json])

    res, usage = await fake_provider.complete_structured(
        [ChatMessage(role="user", content="Generate question")],
        response_model=SampleQuestionSchema,
    )

    assert isinstance(res, SampleQuestionSchema)
    assert res.stem == "What is DNA?"
    assert len(fake_provider.call_history) == 2


@pytest.mark.asyncio
async def test_structured_response_repair_failure_raises_typed_error() -> None:
    """Verify that if repair attempt also fails, LLMStructuredOutputError is raised."""
    bad_json_1 = "This is not JSON at all."
    bad_json_2 = '{"invalid": "still missing fields"}'

    fake_provider = FakeLLMProvider(scripted_responses=[bad_json_1, bad_json_2])

    with pytest.raises(LLMStructuredOutputError) as exc_info:
        await fake_provider.complete_structured(
            [ChatMessage(role="user", content="Generate question")],
            response_model=SampleQuestionSchema,
        )

    assert "failed structured validation" in str(exc_info.value)
    assert len(fake_provider.call_history) == 2


# ------------------------------------------------------------------------------
# 5. Timeout & Rate-Limit Retries with Backoff
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_retry_on_rate_limit_success() -> None:
    """Verify gateway retries on rate limit (429) with backoff and succeeds on attempt 2."""
    provider = FakeLLMProvider(
        provider_name="test_rate_limit_provider",
        scripted_responses=[
            LLMRateLimitError("Rate limit exceeded 429", provider="test_rate_limit_provider"),
            "Successful response after rate limit recovery.",
        ],
    )
    gateway = FallbackLLMGateway(
        providers=[provider],
        max_retries_per_provider=2,
        base_backoff_seconds=0.01,
        max_backoff_seconds=0.05,
    )

    resp = await gateway.complete_chat([ChatMessage(role="user", content="Test backoff")])
    assert resp.content == "Successful response after rate limit recovery."
    assert len(provider.call_history) == 2


# ------------------------------------------------------------------------------
# 6. Primary-Provider Failure Followed by Fallback Success
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_fallback_to_secondary_provider() -> None:
    """Verify gateway fails over to secondary provider when primary fails."""
    primary = FakeLLMProvider(
        provider_name="primary_openrouter",
        scripted_responses=[
            LLMTransientError("500 Internal Server Error", provider="primary_openrouter"),
            LLMTransientError("500 Internal Server Error", provider="primary_openrouter"),
            LLMTransientError("500 Internal Server Error", provider="primary_openrouter"),
        ],
    )
    secondary = FakeLLMProvider(
        provider_name="secondary_nvidia",
        scripted_responses=["Response from secondary NVIDIA NIM provider."],
    )

    gateway = FallbackLLMGateway(
        providers=[primary, secondary],
        max_retries_per_provider=2,
        base_backoff_seconds=0.01,
    )

    resp = await gateway.complete_chat([ChatMessage(role="user", content="Test failover")])
    assert resp.content == "Response from secondary NVIDIA NIM provider."
    assert resp.usage.provider == "secondary_nvidia"
    assert len(primary.call_history) == 3
    assert len(secondary.call_history) == 1


# ------------------------------------------------------------------------------
# 7. All Providers Fail Raises LLMAllProvidersFailedError
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_all_providers_fail() -> None:
    """Verify LLMAllProvidersFailedError is raised when all providers in chain fail."""
    primary = FakeLLMProvider(
        provider_name="primary",
        scripted_responses=[
            LLMTimeoutError("Timeout", provider="primary"),
            LLMTimeoutError("Timeout", provider="primary"),
        ],
    )
    secondary = FakeLLMProvider(
        provider_name="secondary",
        scripted_responses=[
            LLMConnectionError("Connection Refused", provider="secondary"),
            LLMConnectionError("Connection Refused", provider="secondary"),
        ],
    )

    gateway = FallbackLLMGateway(
        providers=[primary, secondary],
        max_retries_per_provider=1,
        base_backoff_seconds=0.01,
    )

    with pytest.raises(LLMAllProvidersFailedError) as exc_info:
        await gateway.complete_chat([ChatMessage(role="user", content="Test all fail")])

    assert "primary" in exc_info.value.attempted_providers
    assert "secondary" in exc_info.value.attempted_providers


# ------------------------------------------------------------------------------
# 8. Request Budget Exhaustion
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_gateway_request_budget_exhaustion() -> None:
    """Verify gateway raises LLMBudgetExceededError when request budget is exhausted."""
    provider = FakeLLMProvider(scripted_responses=["Response 1", "Response 2", "Response 3"])
    gateway = FallbackLLMGateway(
        providers=[provider],
        max_request_budget=2,
        base_backoff_seconds=0.01,
    )

    # 1st request ok
    await gateway.complete_chat([ChatMessage(role="user", content="Req 1")])
    # 2nd request ok
    await gateway.complete_chat([ChatMessage(role="user", content="Req 2")])

    # 3rd request must raise LLMBudgetExceededError
    with pytest.raises(LLMBudgetExceededError) as exc_info:
        await gateway.complete_chat([ChatMessage(role="user", content="Req 3")])

    assert "budget (2) exceeded" in str(exc_info.value)


# ------------------------------------------------------------------------------
# 9. Secret Redaction & Logging Safety
# ------------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_secrets_and_prompt_redacted_from_logs(caplog: pytest.LogCaptureFixture) -> None:
    """Verify API keys and user source documents are never written to logger records."""
    secret_key = "sk-super-secret-production-token-99999"
    sensitive_prompt = "TOP SECRET SOURCE DOCUMENT: Proprietary Examination Notes"

    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "id": "gen_secret_test",
                "model": "openrouter/free",
                "choices": [{"message": {"role": "assistant", "content": "Clean answer"}}],
                "usage": {"total_tokens": 10},
            },
        )

    mock_transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=mock_transport) as client:
        provider = OpenRouterProvider(
            api_key=secret_key,
            client=client,
        )

        with caplog.at_level(logging.INFO):
            await provider.complete_chat([ChatMessage(role="user", content=sensitive_prompt)])

        log_text = caplog.text
        # Verify secret key NEVER appears anywhere in log records
        assert secret_key not in log_text
        # Verify sensitive document prompt text NEVER appears in log records
        assert sensitive_prompt not in log_text
        assert "TOP SECRET" not in log_text
