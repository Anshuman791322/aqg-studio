# Phase 00 Handoff: Repository Contract & Architecture Specification

## 1. Phase Summary
- **Phase ID**: `00-repository-contract`
- **Phase Name**: Repository Contract, Architecture Specification & Structural Foundation
- **Execution Date**: 2026-08-21
- **Status**: **COMPLETED**

---

## 2. Scope of Phase 00
The scope of Phase 00 is to establish the permanent architectural contract, governance rules, technical specifications, and repository structure for **AQG Studio**. This phase locks in the multi-agent design, technology stack, security boundaries, database models, and execution roadmap across all subsequent phases (Phases 01 through 14).

---

## 3. Deliverables Produced

1. **Governance & AI Directives**:
   - `AGENTS.md`: Mandatory operational rules for Codex and AI assistants (research first, inspect codebase, complete implementations without placeholders, zero secrets, monolithic FastAPI + Next.js architecture, deterministic-first boundary, free-tier guardrails).
2. **Core System Documentation**:
   - `docs/PROJECT_SPEC.md`: Product mission, target personas, supported formats (PDF, DOCX, PPTX, TXT), explicit rejection of `.doc`, explicit deferral of scanned PDF OCR, assessment dimensions (MCQ, True/False, Short Answer, Descriptive), Bloom taxonomy levels, and MVP limits.
   - `docs/ARCHITECTURE.md`: Detailed 6-agent LangGraph workflow specification, multi-provider LLM fallback gateway (OpenRouter -> NVIDIA), modular monolith design, and locked tech stack.
   - `docs/API_CONTRACT.md`: Complete REST and Server-Sent Events (SSE) OpenAPI endpoints, request/response payloads, error envelopes, and event streaming schemas.
   - `docs/DATA_MODEL.md`: Relational and vector schema definition (PostgreSQL + `pgvector`), table specifications, indexes, foreign keys, and Row-Level Security (RLS) policies.
   - `docs/SECURITY.md`: Secret isolation protocols, JWT signature verification, file upload defense (magic bytes, MIME validation, zip bomb limits), prompt-injection quarantine (`<untrusted_document_content>`), and audit logging.
   - `docs/DEPLOYMENT.md`: Infrastructure setup guide for Vercel, Render, and Supabase free tier, environment variable matrix, and CI/CD pipelines.
   - `docs/PHASE_STATUS.md`: Full roadmap tracker spanning Phases 0 through 14 with status, verification commands, and risk assessments.
3. **Repository Scaffold & Automation**:
   - `README.md`: System overview, multi-agent diagram, tech stack, and developer instructions.
   - `.gitignore`: Production-grade ignore rules covering Python, Node.js, Next.js, virtualenvs, local storage, secrets, and IDEs.
   - `.editorconfig`: Cross-editor formatting rules.
   - `Makefile`: Standardized automation commands (`install`, `dev`, `test`, `lint`, `typecheck`, `format`, `verify`).
   - `.env.example`: Comprehensive environment template for root, backend, and frontend.
   - `supabase/migrations/20260821000000_initial_schema.sql`: Foundational SQL migration.
   - Scaffolds for `frontend/` and `backend/`.

---

## 4. Explicit Non-Goals for Phase 00
- **No Premature Feature Implementation**: Application routes, UI components, and agent execution logic are deliberately omitted in Phase 00 to establish the contract first.
- **No Mock or Fake Production Credentials**: No API keys or mock database credentials were written into repository files.
- **No Distributed Microservices**: No Docker Compose microservice clusters or message broker infrastructure.
- **No Paid Cloud Infrastructure**: No reliance on paid vector databases or external paid hosting tiers.

---

## 5. Acceptance Criteria Checklist

| Acceptance Criterion | Verification Method | Status |
| :--- | :--- | :--- |
| All required folders (`docs/`, `docs/phases/`, `frontend/`, `backend/`, `supabase/migrations/`) exist | Recursive directory inspection | **PASSED** |
| All required documentation files are written and internally consistent | Cross-reference validation | **PASSED** |
| `AGENTS.md` contains all mandated operational rules | Content review | **PASSED** |
| `PROJECT_SPEC.md` covers formats, rejection of `.doc`, deferral of OCR, and MVP limits | Content review | **PASSED** |
| `ARCHITECTURE.md` defines 6 agents, LangGraph orchestration, and locked stack | Content review | **PASSED** |
| No secrets, API keys, or production credentials are committed | Regex / Ripgrep security scan | **PASSED** |
| No premature full application features implemented | Codebase inspection | **PASSED** |
| README clearly explains execution discipline for future phases | Content review | **PASSED** |

---

## 6. Verification Evidence & Command Logs

### Command 1: Secret Scanner Guard
- **Command**: `grep_search` across `aqg-studio/` for potential private keys, real tokens, or passwords.
- **Result**: Zero secret matches found. All templates strictly use placeholder keys in `.env.example`.

### Command 2: Directory Structure Verification
- **Target**: `c:\Users\anshu\Downloads\Codex\aqg-studio`
- **Result**: All required files, configs, documentation, and directories verified present.

---

## 7. Next Steps: Phase 01 Transition
Phase 01 will establish the active project scaffolding:
1. Initialize FastAPI backend structure with Pydantic v2 schemas and initial health check route.
2. Initialize Next.js 15 App Router frontend with Tailwind CSS and base layout.
3. Configure GitHub Actions CI workflow for automated linting, typechecking, and tests.
