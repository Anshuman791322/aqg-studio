# AQG Studio - Phase Status & Execution Roadmap (Phases 0–14)

This document tracks the verified completion status, deliverables, verification commands, and open risks for every phase in the AQG Studio development lifecycle.

---

## Global Phase Status Dashboard

| Phase | Name | Status | Completed Date | Verified Quality Gate |
| :--- | :--- | :--- | :--- | :--- |
| **00** | **Repository Contract & Architecture** | **COMPLETED** | 2026-08-21 | File & docs consistency, zero-secrets scan, contract verification |
| **01** | **Environment & Project Foundations** | **COMPLETED** | 2026-08-21 | 14 backend tests passing, mypy strict, ruff lint, Next.js 15 build |
| **02** | **Supabase Schema, Migrations & RLS** | **COMPLETED** | 2026-08-21 | 44 backend tests passing (models, repositories, storage, isolation), RLS SQL |
| **03** | **User Authentication & Authorization** | **COMPLETED (REMEDIATED)** | 2026-08-21 | 56 backend tests passing (JWT signatures, expiration, aud, sub, body tampering), Next.js SSR Auth & Dashboard |
| **04** | **Document Processing & Parsing Engine** | **COMPLETED** | 2026-08-21 | 77 backend tests passing (PDF/DOCX/PPTX/TXT parsers, header removal, scanned PDF detection, chunking 600-900 tokens, 10% overlap, lifecycle endpoints), Next.js 15 build |
| **05** | **Model Provider Abstraction & Gateway** | **COMPLETED** | 2026-08-21 | 87 backend tests passing (OpenRouter, NVIDIA NIM, fake provider, structured output with 1-shot repair, jittered backoff, fallback failover, request budgeting, zero-leak logging) |
| **06** | **Chunking, Embeddings & pgvector RAG** | READY | Pending | Cosine vector search benchmarks, token window chunk tests |
| **07** | **Knowledge Retrieval & Analysis Agent** | PLANNED | Pending | Concept extraction tests, topic hierarchy JSON validation |
| **08** | **Question Planning & Blueprint Agent** | PLANNED | Pending | Blueprint quota math verification, Bloom distribution checks |
| **09** | **Question Generation & Fallback Gateway** | PLANNED | Pending | OpenRouter + NVIDIA fallback failover integration tests |
| **10** | **Evaluation & Refinement Agent** | PLANNED | Pending | 5-metric scoring tests, iterative refinement loop test |
| **11** | **Output & Quality Report Agent** | PLANNED | Pending | Scorecard calculation tests, hallucination rate metrics |
| **12** | **Human-in-the-Loop Review Workflows** | PLANNED | Pending | Question approval/rejection/editing endpoint tests |
| **13** | **Multi-Format Export Engine** | PLANNED | Pending | PDF, DOCX, Moodle XML, GIFT, QTI 2.1 exporter compliance tests |
| **14** | **Next.js Frontend & Studio Dashboard** | PLANNED | Pending | End-to-end UI rendering, SSE live streaming, review studio |

---

## Detailed Phase Breakdown

### Phase 00: Repository Contract & Architecture
- **Status**: **COMPLETED** (2026-08-21)
- **Scope**: Repository structure, `AGENTS.md` instructions, project specification, multi-agent architecture, API contracts, data models, security threat models, zero-cost deployment guides.
- **Verification**: Zero-secrets check, file structure validation.

---

### Phase 01: Environment & Project Foundations
- **Status**: **COMPLETED** (2026-08-21)
- **Scope**: FastAPI core foundation (Pydantic Settings, correlation IDs, structured logging, standardized error envelopes, CORS, `/health/live`, `/health/ready`, `/api/v1/version`), Next.js 15 landing page and layout, CI workflow.
- **Verification**: 14/14 backend tests passed, Ruff/mypy clean, Next.js build clean.

---

### Phase 02: Supabase Schema, Migrations & RLS
- **Status**: **COMPLETED** (2026-08-21)
- **Scope**: Ordered SQL migrations (extensions, 13 core tables, full-text GIN index, 384-d vector HNSW index, private storage buckets, storage RLS, table RLS), SQLAlchemy 2.0 ORM entities, user-scoped repositories, private storage path security.
- **Verification**: 44/44 backend tests passed (including 10 multi-tenant isolation tests), Ruff/mypy clean.

---

### Phase 03: User Authentication & Authorization
- **Status**: **COMPLETED (REMEDIATED & VERIFIED)** (2026-08-21)
- **Scope**:
  - **Backend**: Signature-verified Supabase JWT verification (`verify_supabase_jwt`), `CurrentUser` dependency, `GET /api/v1/auth/me`.
  - **Frontend**: Supabase browser and server SSR clients, route protection middleware (`/dashboard`), auth routes (`/auth/sign-in`, `/auth/sign-up`, `/auth/callback`, `/auth/sign-out`), protected dashboard.
- **Verification**: 56/56 tests passed, Next.js 15 build clean.

---

### Phase 04: Document Processing & Parsing Engine
- **Status**: **COMPLETED & VERIFIED** (2026-08-21)
- **Scope**: Deterministic parsers for PDF (header/footer removal, scanned PDF detection), DOCX (headings, tables, zip bomb defense), PPTX (slides, notes), TXT/MD; linguistic cleaner; hierarchical semantic chunker (600–900 tokens, 10% overlap); document endpoints (`/api/v1/documents/*`).
- **Verification**: 77/77 tests passed, Next.js 15 build clean.

---

### Phase 05: Model Provider Abstraction & Gateway
- **Status**: **COMPLETED & VERIFIED** (2026-08-21)
- **Scope**:
  - **Provider Abstractions**: `LLMProvider` base protocol, `OpenRouterProvider` (`openrouter/free`), `NVIDIAProvider` (`meta/llama-3.3-70b-instruct`), `FakeLLMProvider` for offline test mocking.
  - **Fallback Gateway**: `FallbackLLMGateway` supporting sequential failover (`LLM_PROVIDER_ORDER`), exponential backoff with random jitter, non-retryable short circuits on `LLMInvalidInputError`, rate limit / timeout / 5xx retries, and application-level request budget protection (`LLM_MAX_DAILY_REQUEST_BUDGET`).
  - **Structured Generation Pipeline**: Works on arbitrary models without requiring native JSON mode; cleans markdown code fences, validates against Pydantic models, and executes at most 1 controlled repair pass before raising `LLMStructuredOutputError`.
  - **Zero-Leak Logging**: Absolute redaction of API keys, source text, and sensitive prompts from all log outputs.
- **Verification Commands Run**:
  - `python -m pytest -v tests/` (87/87 tests passed)
  - `python -m ruff check .` (0 lint errors across 54 source files)
  - `python -m mypy app` (Strict type checking passed on 54 source files)
  - `npx eslint .` (0 frontend lint errors)
  - `npx tsc --noEmit` (0 frontend type errors)
  - `npm test` (0 failures)
  - `npm run build` (Next.js production build succeeded with 9 static & dynamic routes compiled)
- **Verdict**: **PHASE PASSED**
