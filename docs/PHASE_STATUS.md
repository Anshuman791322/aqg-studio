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
| **05** | **Chunking, Embeddings & pgvector RAG** | READY | Pending | Cosine vector search benchmarks, token window chunk tests |
| **06** | **Knowledge Retrieval & Analysis Agent** | PLANNED | Pending | Concept extraction tests, topic hierarchy JSON validation |
| **07** | **Question Planning & Blueprint Agent** | PLANNED | Pending | Blueprint quota math verification, Bloom distribution checks |
| **08** | **Question Generation & Fallback Gateway** | PLANNED | Pending | OpenRouter + NVIDIA fallback failover integration tests |
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
  - **Backend**:
    - Signature-verified Supabase JWT verification (`verify_supabase_jwt`) with strict expiration, audience, subject UUID, algorithm, and prefix normalization.
    - Typed `CurrentUser` dependency injected into FastAPI endpoints.
    - Authenticated endpoint `GET /api/v1/auth/me` (and `/api/v1/me`) returning user profile and quota metrics.
    - Body `user_id` tampering protection across repository operations.
  - **Frontend**:
    - Supabase browser and server client utilities with Next.js App Router cookie sessions.
    - Next.js middleware for route protection (`/dashboard`) and safe `returnUrl` redirects.
    - Auth routes: `/auth/sign-in`, `/auth/sign-up`, `/auth/callback`, `/auth/sign-out`.
    - Protected dashboard shell displaying user profile, quotas, and module actions.
    - API client auto-attaching current access token.
- **Verification**: 56/56 tests passed, Next.js 15 build clean.

---

### Phase 04: Document Processing & Parsing Engine
- **Status**: **COMPLETED & VERIFIED** (2026-08-21)
- **Scope**:
  - **Deterministic Parsers**:
    - PyMuPDF (`PDFDocumentParser`): page extraction, repeated running header/footer deduplication, scanned PDF heuristic detection (`needs_ocr` status when text density < 60 chars/page), password-encrypted PDF handling.
    - `python-docx` (`DOCXDocumentParser`): heading hierarchy parsing, table extraction, zip bomb defense, legacy `.doc` rejection with actionable conversion message.
    - `python-pptx` (`PPTXDocumentParser`): slide title extraction, shape and table text extraction, speaker notes extraction, slide-to-page indexing.
    - Plain text / Markdown (`TXTDocumentParser`): multi-encoding support (UTF-8, Latin-1, CP1252), Markdown header structure extraction.
  - **Linguistic Utilities & Cleaners**:
    - Whitespace and control-character normalization.
    - Conservative dehyphenation.
    - Stopword frequency language detection across English, Spanish, French, German, Italian, Portuguese, and Hindi.
    - Token estimation via `tiktoken` (`cl100k_base`) with character-ratio fallback.
    - SHA-256 checksum calculation.
  - **Hierarchical Chunker**:
    - Target window 600–900 tokens, max 1,200 tokens, ~10% overlap (~75 tokens).
    - Heading and paragraph boundary awareness.
    - Non-empty guarantees, deterministic 0-indexed chunking, SHA-256 chunk content hash.
  - **API Endpoints & Orchestration**:
    - `POST /api/v1/documents/initiate`: Limits & format validation, creates document record, returns private storage path `<user_id>/<document_id>/<sanitized_filename>`.
    - `POST /api/v1/documents/{document_id}/complete`: Confirms upload and marks document queued.
    - `POST /api/v1/documents/{document_id}/process`: Deterministic processing service idempotently replacing chunks and setting status.
    - `GET /api/v1/documents`, `GET /api/v1/documents/{id}`, `DELETE /api/v1/documents/{id}`, `GET /api/v1/documents/{id}/chunks`.
- **Verification Commands Run**:
  - `python -m pytest -v tests/` (77/77 tests passed)
  - `python -m ruff check .` (0 lint errors across 46 source files)
  - `python -m mypy app` (Strict type checking passed on 46 source files)
  - `npx eslint .` (0 frontend lint errors)
  - `npx tsc --noEmit` (0 frontend type errors)
  - `npm test` (0 failures)
  - `npm run build` (Next.js production build succeeded with 9 static & dynamic routes compiled)
- **Verdict**: **PHASE PASSED**
