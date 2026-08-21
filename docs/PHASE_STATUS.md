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
| **06** | **Knowledge Retrieval, Embeddings & RAG** | **COMPLETED** | 2026-08-21 | 101 backend tests passing (Map-and-reduce knowledge extraction, anti-injection prompt boundary, topic/concept deduplication, FastEmbed & NVIDIA embeddings, hybrid vector/lexical retrieval) |
| **07** | **Question Planning & Blueprint Agent** | **COMPLETED** | 2026-08-21 | 113 backend tests passing (Hamilton-Hare Largest Remainder Method, deterministic slot allocation, no question text in blueprints, assessment REST endpoints) |
| **08** | **Question Generation & Fallback Gateway** | READY | Pending | OpenRouter + NVIDIA fallback failover integration tests |
| **09** | **Evaluation & Refinement Agent** | PLANNED | Pending | 5-metric scoring tests, iterative refinement loop test |
| **10** | **Output & Quality Report Agent** | PLANNED | Pending | Scorecard calculation tests, hallucination rate metrics |
| **11** | **Human-in-the-Loop Review Workflows** | PLANNED | Pending | Question approval/rejection/editing endpoint tests |
| **12** | **Multi-Format Export Engine** | PLANNED | Pending | PDF, DOCX, Moodle XML, GIFT, QTI 2.1 exporter compliance tests |
| **13** | **Next.js Frontend & Studio Dashboard** | PLANNED | Pending | End-to-end UI rendering, SSE live streaming, review studio |
| **14** | **End-to-End Testing & Deployment** | PLANNED | Pending | Integration test suite, Vercel & Render staging deploy |

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
- **Verification**: 87/87 tests passed, Next.js 15 build clean.

---

### Phase 06: Knowledge Retrieval, Embeddings & RAG
- **Status**: **COMPLETED & VERIFIED** (2026-08-21)
- **Scope**:
  - **Knowledge Extraction Agent**: Map-and-reduce workflow grouping chunks into bounded token batches, enforcing prompt-injection defenses and strict source citations, sanitizing hallucinated chunk IDs, and merging topics and concepts deterministically.
  - **Embeddings Subsystem**: `EmbeddingProvider` abstraction with lazy-loaded `FastEmbedProvider` (384-d `BAAI/bge-small-en-v1.5`), `NVIDIAEmbeddingProvider`, and deterministic `FakeEmbeddingProvider`.
  - **Hybrid RAG Retrieval**: User- and document-scoped hybrid vector/lexical retrieval with weighted scoring, cosine similarity, lexical overlap, and database search migration function (`match_document_chunks_hybrid`).
  - **API Endpoints**: `POST /api/v1/documents/{id}/analyze`, `GET /api/v1/documents/{id}/analysis`, `POST /api/v1/documents/{id}/retrieve`.
- **Verification**: 101/101 tests passed, Next.js 15 build clean.

---

### Phase 07: Question Planning & Blueprint Agent
- **Status**: **COMPLETED & VERIFIED** (2026-08-21)
- **Scope**:
  - **Deterministic Allocation**: Hamilton-Hare Largest Remainder Method distributing exact integer question counts across types, difficulties, Bloom levels, and topics without LLM math hallucination.
  - **Question Planning Agent**: Structured design pipeline assigning topics, concepts, Bloom taxonomy objectives, chunk citations, and pedagogic rationales without writing premature question wording.
  - **Assessment Endpoints**: `POST /api/v1/assessments`, `GET /api/v1/assessments`, `GET /api/v1/assessments/{id}`, `GET /api/v1/assessments/{id}/blueprint`, `DELETE /api/v1/assessments/{id}`.
- **Verification Commands Run**:
  - `python -m pytest -v tests/` (113/113 tests passed)
  - `python -m ruff check .` (0 lint errors across 77 source files)
  - `python -m mypy app` (Strict type checking passed on 77 source files)
  - `npx eslint .` (0 frontend lint errors)
  - `npx tsc --noEmit` (0 frontend type errors)
  - `npm test` (0 failures)
  - `npm run build` (Next.js production build succeeded with 9 static & dynamic routes compiled)
- **Verdict**: **PHASE PASSED**
