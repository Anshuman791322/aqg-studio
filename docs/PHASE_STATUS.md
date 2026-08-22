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
| **07** | **Question Planning & Blueprint Agent** | **COMPLETED** | 2026-08-21 | 117 backend tests passing (Hamilton-Hare Largest Remainder Method, deterministic slot allocation, no question text in blueprints, assessment REST endpoints) |
| **08** | **Question Generation & Fallback Gateway** | **COMPLETED** | 2026-08-21 | 129 backend tests passing (Batched generation, per-blueprint RAG, multi-type validation, prompt injection defense, draft persistence) |
| **09** | **Evaluation & Refinement Agent** | **COMPLETED** | 2026-08-22 | 142 backend tests passing (10-metric scoring, deterministic validation, iterative refinement loop, regeneration, replacement blueprints, duplicate control) |
| **10** | **LangGraph Orchestration & Job Runner** | **COMPLETED** | 2026-08-22 | 152 backend tests passing (7-node document workflow, 10-node assessment workflow, PostgreSQL SKIP LOCKED runner, heartbeat, crash recovery, resumability, queue/status/cancel APIs) |
| **11** | **Authenticated Studio Web Interface** | **COMPLETED** | 2026-08-22 | 12 frontend tests passing (auth guards, upload validation, live distribution matrix, polling tracker, question review studio), Next.js 15 build (11 routes compiled), full TypeScript & ESLint clean |
| **12** | **Multi-Format Export Engine & Output Agent** | **COMPLETED** | 2026-08-22 | 170 backend tests passing, PDF/DOCX/JSON/CSV exporters, seeded shuffling, scorecard analytics |
| **13** | **Production Hardening & Deployment** | **COMPLETED** | 2026-08-22 | 174 backend tests passing, 8/8 smoke tests passing, rate limits, atomic quotas, OWASP headers, Render & Vercel deploy specs |
| **14** | **Full Audit & Release-Candidate Prep** | **COMPLETED** | 2026-08-22 | 175 backend tests passing, full deterministic pipeline E2E test, zero lint/type errors, RC documentation suite |


---

### Phase 14: Full Repository Audit, Remediation, and Release Candidate Preparation
- **Status**: **COMPLETED & VERIFIED** (2026-08-22)
- **Scope**:
  - **Full 17-Dimension Audit**: Security, isolation, authentication, RLS, storage paths, parsers, fallback gateway, prompt injection, knowledge analysis, Hamilton-Hare allocator, generation schema, evaluation loops, job idempotency, frontend workflows, export pipelines, zero-cost deployment, documentation sync.
  - **Remediation**: Added structured warning logging to profile retrieval exception fallbacks.
  - **Deterministic End-to-End Test**: `backend/tests/test_end_to_end_pipeline.py` verifying document ingestion, chunking, embeddings, 10-question blueprint planning, question generation, evaluation, scorecard report, JSON/PDF/DOCX/CSV exports, and cross-user tenant isolation.
  - **Release Candidate Documentation Suite**: Added `docs/RELEASE_CHECKLIST.md`, `docs/KNOWN_LIMITATIONS.md`, `docs/DEMO_GUIDE.md`, and `docs/phases/14-final-audit.md`.
- **Verification Commands Run**:
  - `python scripts/smoke_test.py` (8/8 smoke tests passed)
  - `python -m pytest -v tests/test_end_to_end_pipeline.py` (1/1 passed in 0.20s)
  - `python -m pytest -v` (175/175 backend tests passed)
  - `python -m ruff check .` (0 lint errors across 108 source files)
  - `python -m mypy app` (0 type errors across 108 source files)
  - `npm test` (18/18 frontend tests passed)
  - `npm run typecheck` (0 TypeScript type errors)
  - `npm run lint` (0 ESLint errors)
  - `npm run build` (Next.js production build succeeded with 11 routes compiled)
- **Verdict**: **RELEASE CANDIDATE READY (RC-1)**



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
- **Verification**: 117/117 tests passed, Next.js 15 build clean.

---

### Phase 08: Question Generation & Fallback Gateway
- **Status**: **COMPLETED & VERIFIED** (2026-08-21)
- **Scope**:
  - **Grounded Generation Agent**: Batched question generation for `mcq_single`, `mcq_multi`, `true_false`, `short_answer`, and `descriptive` question types with per-blueprint hybrid RAG retrieval.
  - **Validation Engine**: Independent per-item validation enforcing exact 4-option MCQ constraints, distinct options, ban on lazy distractors, correct answer alignment, and strict source chunk citation subsets.
  - **Resilient Batch Handling**: Partial batch success isolation, individual retry fallback for failed blueprint items with reduced batch size, and prompt-injection defense tags.
  - **Endpoints**: `POST /api/v1/assessments/{id}/generate`, `GET /api/v1/assessments/{id}/questions`, `GET /api/v1/questions/{id}`.
- **Verification Commands Run**:
  - `python -m pytest -v tests/` (129/129 tests passed)
  - `python -m ruff check .` (0 lint errors across 82 source files)
  - `python -m mypy app` (Strict type checking passed on 82 source files)
  - `npx eslint .` (0 frontend lint errors)
  - `npx tsc --noEmit` (0 frontend type errors)
  - `npm test` (0 failures)
  - `npm run build` (Next.js production build succeeded with 9 static & dynamic routes compiled)
- **Verdict**: **PHASE PASSED**

---

### Phase 09: Evaluation & Refinement Agent
- **Status**: **COMPLETED & VERIFIED** (2026-08-22)
- **Scope**:
  - **Deterministic Validator**: Fast non-LLM rule checks (required fields, stem length, source chunk ID validation against document chunks, MCQ 4-option count/keys/texts/banned phrases, boolean answers, duplicate stems).
  - **Structured LLM Evaluation**: 10-dimensional scoring (correctness, groundedness, relevance, clarity, grammar, answerability, difficulty alignment, Bloom alignment, distractor quality, duplication risk, overall quality).
  - **Decision Engine**: ACCEPT (high quality), REFINE (recoverable flaws), REGENERATE (factual/hallucination failure).
  - **Refinement Loop**: Iterative targeted repairs adhering to evaluator critique while strictly preserving factual source chunk boundaries (up to `EVALUATION_MAX_REFINEMENT_ATTEMPTS = 2`).
  - **Regeneration Loop & Replacement Blueprints**: Regeneration with failure reasons; if attempts exhaust, generates replacement blueprints from document concepts to maintain requested question quota.
  - **Duplicate Control**: Exact normalized matching, lexical Jaccard similarity, and vector cosine embedding similarity to detect and eliminate duplicate questions within an assessment.
  - **Audit Persistence**: Scorecards stored in `evaluations` table with full metric fidelity.
  - **Endpoints**: `POST /api/v1/assessments/{id}/evaluate`, `POST /api/v1/questions/{id}/evaluate`, `POST /api/v1/questions/{id}/refine`, `GET /api/v1/questions/{id}/evaluations`.
- **Verification Commands Run**:
  - `python -m pytest -v` (142/142 tests passed)
  - `python -m ruff check .` (0 lint errors across 89 source files)
  - `python -m mypy app` (Strict type checking passed on 89 source files)
  - `npm run lint` (0 frontend lint errors)
  - `npm run typecheck` (0 frontend TypeScript errors)
  - `npm run build` (Next.js production build succeeded with 9 static & dynamic routes compiled)
- **Verdict**: **PHASE PASSED**

---

### Phase 10: LangGraph Orchestration & Job Runner
- **Status**: **COMPLETED & VERIFIED** (2026-08-22)
- **Scope**:
  - **7-Node Document Workflow**: `validate_document` -> `extract_document` -> `clean_and_chunk` -> `store_chunks` -> `create_embeddings` -> `analyze_knowledge` -> `finalize_document`.
  - **10-Node Assessment Workflow**: `load_assessment` -> `create_or_load_blueprints` -> `retrieve_and_generate_batches` -> `evaluate_batches` -> `route_failed_questions` -> `refine_or_regenerate` -> `deduplicate` -> `verify_requested_count` -> `calculate_metrics` -> `finalize_assessment`.
  - **PostgreSQL Background Job Runner**: In-process `PostgresJobRunner` claiming jobs transactionally via `SELECT ... FOR UPDATE SKIP LOCKED`, background heartbeat task, crash recovery of stale jobs (`recover_stale_running_jobs`), node idempotency, and graceful shutdown.
  - **FastAPI Lifespan Integration**: Runner boots and halts with the FastAPI server process.
  - **Queue-Based REST API**: `POST /api/v1/documents/{id}/process`, `GET /api/v1/documents/{id}/status`, `POST /api/v1/assessments/{id}/generate`, `GET /api/v1/assessments/{id}/status`, `POST /api/v1/assessments/{id}/cancel`.
- **Verification Commands Run**:
  - `python -m pytest -v` (152/152 tests passed across 24 test suites)
  - `python -m ruff check .` (0 lint errors across 94 source files)
  - `python -m mypy app` (Strict type checking passed on 94 source files)
  - `npm run lint` (0 frontend lint errors)
  - `npm run typecheck` (0 frontend TypeScript errors)
  - `npm run build` (Next.js production build succeeded with 9 static & dynamic routes compiled)
- **Verdict**: **PHASE PASSED**

---

### Phase 11: Authenticated Studio Web Interface
- **Status**: **COMPLETED & VERIFIED** (2026-08-22)
- **Scope**:
  - **8 Key User Routes**: `/` (Public landing), `/dashboard` (Workspace overview), `/documents/new` (Drag-and-drop ingestion), `/documents/[id]` (Knowledge map & chunk inspector), `/assessments/new` (Live distribution matrix), `/assessments/[id]/progress` (Status polling & 6-stage tracker), `/assessments/[id]/review` (Question review studio with inline edit & citations), `/assessments/[id]/report` (Cognitive depth analytics & LMS export center).
  - **State & Networking**: Complete typed `apiClient` with Supabase JWT bearer injection, TanStack Query provider, `ToastProvider` accessible notifications, and `@radix-ui/react-dialog` confirmation modals.
  - **Component Quality**: High-contrast dark theme, accessible loading skeletons, visible focus states, no key leaks, and WCAG AA compliance.
- **Verification Commands Run**:
  - `npm test` (18/18 frontend component & integration tests passed across 8 test suites)
  - `npm run typecheck` (0 TypeScript type errors)
  - `npm run lint` (0 ESLint errors)
  - `npm run build` (Next.js production build succeeded with 11 static & dynamic routes compiled)
  - `python -m pytest -v` (152/152 backend tests passed)
  - `python -m ruff check .` (0 backend lint errors)
  - `python -m mypy app` (0 backend type errors)
- **Verdict**: **PHASE PASSED**

---

### Phase 12: Output & Report Agent, Assessment Analytics, and Secure Exports
- **Status**: **COMPLETED & VERIFIED** (2026-08-22)
- **Scope**:
  - **Deterministic Analytics Engine**: `calculate_assessment_report()` aggregating overall quality, groundedness, correctness, clarity, distractor quality, refinement/regeneration passes, and topic/taxonomy balance.
  - **Multi-Format Export Pipelines**: Pure-Python ReportLab PDF with two-pass `NumberedCanvas` headers/footers, `python-docx` Word packages, formatted JSON schema, and UTF-8 BOM CSV for spreadsheets.
  - **Seeded Shuffling**: Reproducible item reordering and MCQ option shuffling with synchronized `correct_answer` pointer updates.
  - **Secure Storage & Download**: Private `generated-exports` storage at `<user_id>/<assessment_id>/<export_id>.<extension>` with ownership verification and download streaming.
  - **REST Endpoints**: `POST /api/v1/assessments/{id}/exports`, `GET /api/v1/assessments/{id}/exports`, `GET /api/v1/exports/{id}/download`, `DELETE /api/v1/exports/{id}`, `GET /api/v1/assessments/{id}/report`.
- **Verification Commands Run**:
  - `python -m pytest -v tests/test_output_report_agent.py tests/test_exports.py tests/test_export_endpoints.py` (17/17 passed)
  - `python -m pytest -v` (170/170 backend tests passed)
  - `python -m ruff check .` (0 lint errors)
  - `python -m mypy app` (0 type errors across 106 source files)
  - `npm test` (18/18 frontend component & integration tests passed across 8 suites)
  - `npm run typecheck` (0 TypeScript type errors)
  - `npm run lint` (0 ESLint errors)
  - `npm run build` (Next.js production build succeeded with 11 static & dynamic routes compiled)
- **Verdict**: **PHASE PASSED**

---

### Phase 13: Production Hardening and Zero-Cost Deployment Preparation
- **Status**: **COMPLETED & VERIFIED** (2026-08-22)
- **Scope**:
  - **Security Hardening**: Binary file signature checks (`%PDF-`, `PK\x03\x04`), archive decompression bomb caps (1,000 entries, 200MB expansion, 100:1 ratio), and user-scoped path sandboxing.
  - **OWASP Security Headers**: `nosniff`, `DENY`, `1; mode=block`, `strict-origin-when-cross-origin`, CSP, and HSTS.
  - **Burst Rate Limiting**: In-memory sliding window rate limiter tracking 120 req/min with `429 Too Many Requests` and `Retry-After` header.
  - **Atomic Quotas**: PostgreSQL-backed daily assessment limit (`MAX_ASSESSMENTS_PER_DAY: 10`) and question ceiling (`MAX_QUESTIONS_PER_ASSESSMENT: 50`) without Redis.
  - **Observability**: Structured JSON logging in production with secret redaction filter for Bearer tokens, passwords, and upstream API keys.
  - **Cascading Cleanup**: Automatic removal of remote Supabase Storage files on document and assessment deletion.
  - **Deployment Specifications**: `render.yaml` blueprint for Render free-tier web service and `frontend/vercel.json` for Vercel.
  - **Automated Smoke Test Suite**: 8 end-to-end checks in `scripts/smoke_test.py` running entirely offline.
- **Verification Commands Run**:
  - `python scripts/smoke_test.py` (8/8 smoke tests passed)
  - `python -m pytest -v` (174/174 backend tests passed)
  - `python -m ruff check .` (0 lint errors across 107 source files)
  - `python -m mypy app` (0 type errors across 107 source files)
  - `npm test` (18/18 frontend tests passed)
  - `npm run typecheck` (0 TypeScript type errors)
  - `npm run lint` (0 ESLint errors)
  - `npm run build` (Next.js production build succeeded with 11 routes compiled)
- **Verdict**: **PHASE PASSED**





