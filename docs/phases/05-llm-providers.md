# Phase 5 Handoff: Model Provider Abstraction (OpenRouter & NVIDIA NIM)

## Summary of Implementation
Phase 5 delivers the multi-provider LLM gateway and structured generation subsystem for AQG Studio:

1. **Provider Abstraction Architecture (`backend/app/llm/`)**:
   - `LLMProvider` abstract base interface defining normalized `complete_chat(...)` and `complete_structured(...)` contracts.
   - `OpenRouterProvider`: Asynchronous client for OpenRouter (`https://openrouter.ai/api/v1`), configurable models (`OPENROUTER_MODEL`, default `openrouter/free`), custom HTTP-Referer, and X-Title headers.
   - `NVIDIAProvider`: Asynchronous client for NVIDIA NIM (`https://integrate.api.nvidia.com/v1`), dynamic model configuration (`NVIDIA_MODEL`, default `meta/llama-3.3-70b-instruct`).
   - `FakeLLMProvider`: Deterministic, scriptable LLM provider for zero-cost offline testing, failure simulation, and local mocking.

2. **Robust Fallback Gateway (`FallbackLLMGateway`)**:
   - Multi-provider sequential failover (`LLM_PROVIDER_ORDER=openrouter,nvidia`).
   - Exponential backoff with random jitter (`base_backoff=0.5s`, `max_backoff=5.0s`, `max_retries=2` per provider).
   - Automatic retry and failover on `LLMTimeoutError`, `LLMConnectionError`, `LLMRateLimitError` (HTTP 429), and `LLMTransientError` (HTTP 5xx).
   - Immediate skipping without backoff loops for permanent `LLMAuthenticationError` (401/403).
   - Fatal short-circuiting on `LLMInvalidInputError` (HTTP 400/422) and `LLMBudgetExceededError`.
   - Application-level request budget protection (`LLM_MAX_DAILY_REQUEST_BUDGET`).

3. **Structured Output Pipeline & 1-Pass Repair (`structured.py`)**:
   - Works across all free and commercial models without assuming native JSON schema support.
   - Strips harmless Markdown code fences (````json ... ````).
   - JSON parsing and strict Pydantic validation against arbitrary schema models.
   - Executes at most **one controlled repair pass** feeding validation errors back to the model.
   - Raises typed `LLMStructuredOutputError` on unrecoverable output.

4. **Security & Zero-Leakage Logging**:
   - API keys and auth tokens are server-side only (`OPENROUTER_API_KEY`, `NVIDIA_API_KEY`) and never exposed to the frontend.
   - Logger records only safe telemetry: provider name, model, latency (ms), token counts, and request IDs.
   - Full prompts, user source text, and authorization tokens are strictly redacted from logs.

---

## Test Verification
- **Unit & Integration Tests**: 87 backend tests passing (`pytest` including 10 LLM provider and gateway tests).
- **Static Analysis & Types**: Ruff (`0` errors), mypy (`0` errors across 54 source files).
- **Frontend Verification**: ESLint (`0` warnings/errors), TypeScript strict typecheck (`0` errors), Jest, and Next.js 15 production build compiling 9 routes.
