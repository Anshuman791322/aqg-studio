# AQG Studio - Authoritative Repository Instructions

## 1. Project Overview & Operational Context
**AQG Studio** is an enterprise-grade, multi-agent automated question-generation platform. It transforms uploaded educational and learning materials (PDF, DOCX, PPTX, TXT) into pedagogically sound, source-grounded assessments (MCQ, True/False, Short Answer, Descriptive) with automated evaluation, quality scorecards, and multi-format exports.

The system is architected as a **single modular FastAPI backend service** and a **single Next.js frontend SPA/SSR application**. The six specialized agents (Document Processing, Knowledge Analysis, Question Planning, Question Generation, Evaluation & Refinement, Output & Reporting) are internal Python modules coordinated deterministically using **LangGraph**, not independent microservices.

---

## 2. Mandatory Rules for Codex & Future AI Tasks

All AI coding assistants, automated agents, and contributors working on this repository must strictly adhere to the following rules without exception:

### 2.1 Pre-Execution Research & Context Loading
- **Read Authoritative Documents First**: Always read `AGENTS.md`, `docs/PROJECT_SPEC.md`, `docs/ARCHITECTURE.md`, `docs/API_CONTRACT.md`, `docs/DATA_MODEL.md`, and relevant phase documentation in `docs/phases/` before designing or modifying code.
- **Inspect Before Assuming**: Inspect existing files and directory state prior to proposing or implementing changes. Never guess file names, import paths, database schema fields, or dependency versions.
- **Continuous Execution**: Follow through from plan creation to implementation, automated testing, type validation, and documentation. Never terminate an execution cycle after merely drafting a plan or leaving placeholder code.
- **Autonomous Progress**: Make reasonable, robust implementation choices consistent with the architectural contract when not blocked.

### 2.2 Repository & Code Integrity
- **Preserve Unrelated Work**: Do not overwrite or delete existing projects, scripts, or unrelated user files in the workspace.
- **Non-Destructive Operations**: Strictly avoid destructive Git operations (e.g., `git reset --hard`, `git clean -fdx`, `git checkout -- .` on root without precise targeting).
- **Zero Placeholder Tolerance**: Banned patterns include `// TODO`, `/* implement here */`, `pass  # add logic later`, `...`, and truncated code blocks. All code must be complete, functional, and typed.

### 2.3 Secrets, Security & Data Handling
- **No Secrets in Code**: Never commit API keys, database connection strings, passwords, JWT secrets, service-role keys, or OAuth credentials.
- **Environment Configuration**: Reference configuration values via environment variables. Document all variables exclusively in `.env.example` files with descriptive types and zero real secrets.
- **Untrusted Document Boundary**: Treat all user-uploaded documents and text as **untrusted data**. Never interpolate raw document text into system prompt instructions. Always isolate document text within explicit structured tags (e.g., `<untrusted_document_content>`) to prevent prompt-injection exploits.
- **Strict Input & Output Validation**: Validate all incoming HTTP payloads and all LLM response payloads against strict Pydantic v2 (backend) and Zod/TypeScript (frontend) schemas. Reject ungrounded, malformed, or out-of-schema responses deterministically.

### 2.4 System Architecture & Technology Constraints
- **Single Backend Service**: The backend must remain a single FastAPI service. Do not introduce microservices, distributed message brokers (Kafka/RabbitMQ), Celery workers, or Redis caches unless explicitly revised in an architectural amendment.
- **Single Frontend Application**: Next.js App Router (TypeScript + Tailwind CSS).
- **Deterministic vs. Generative Boundary**:
  - Use deterministic Python code for file parsing, text extraction, page/slide segmentation, chunking, word/token counting, quota enforcement, JSON schema validation, and export formatting.
  - Reserve LLMs strictly for knowledge extraction, difficulty assessment, question drafting, distractor synthesis, rubric generation, and refinement loops.
- **Provider Resilience & Fallback**: All LLM calls must support graceful fallback (Primary: OpenRouter; Fallback: NVIDIA NIM / API). If the primary provider fails (rate limit, outage, invalid token), the system must seamlessly fall back to the secondary provider without dropping the job.
- **Zero-Cost & Free-Tier Strictness**: Never introduce dependencies or infrastructure requirements that necessitate a paid cloud plan. The stack is locked to Supabase Free Tier (Postgres + pgvector + Auth + Storage), Vercel Free Tier (Frontend), and Render Free Tier (FastAPI Backend).

### 2.5 Verification & Phase Gate Discipline
- **Mandatory Quality Gates**: Before marking any phase or task as complete, execute all relevant verification commands:
  - Backend: `pytest`, `ruff check`, `mypy --strict`
  - Frontend: `npm run lint`, `npm run typecheck`, `npm run build`
  - Database: Verification of migration scripts against schema definitions
- **Handoff Documentation**: After completing any phase:
  1. Update `docs/PHASE_STATUS.md` with phase status, completion date, verification commands executed, and unresolved risks.
  2. Create or update the detailed phase handoff document in `docs/phases/<phase_number>-<phase_name>.md`.
  3. Record the exact commands executed and their output logs.

---

## 3. Technology Stack Summary
| Layer | Technology | Primary Role |
| :--- | :--- | :--- |
| **Frontend** | Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS, Lucide Icons | Responsive UI, Document Upload, Interactive Blueprint Builder, Question Review Studio, Export Hub |
| **Backend** | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 (async), LangGraph | REST API, SSE streaming, document extraction, multi-agent orchestration, RAG retrieval |
| **Database** | PostgreSQL 15+ (Supabase) with `pgvector` | Relational tables, embeddings storage, cosine vector search, Row-Level Security (RLS) |
| **Auth & Storage** | Supabase Auth (JWT) & Supabase Storage (Private S3 buckets) | Secure user authentication, document file storage, export artifact storage |
| **Primary LLM** | OpenRouter (`anthropic/claude-3.5-sonnet`, `meta-llama/llama-3.3-70b-instruct`) | Core reasoning, question planning, generation, evaluation |
| **Fallback LLM** | NVIDIA NIM API (`meta/llama-3.3-70b-instruct`, `mistralai/mixtral-8x22b-instruct`) | Automatic fallback upon provider failure or rate limit |
| **Deployment** | Vercel (Frontend), Render Web Service (Backend), Supabase Cloud (Database) | Production hosting within 100% free/community tier limits |

---

## 4. Multi-Agent Pipeline Topology
The system executes a deterministic 6-agent workflow:
```
[User Document Upload]
        │
        ▼
1. Document Processing Agent (Deterministic extraction, text cleanup, slide/page metadata tagging, chunking)
        │
        ▼
2. Knowledge Retrieval & Analysis Agent (Key concept extraction, topic clustering, prerequisite mapping)
        │
        ▼
3. Question Planning Agent (Assessment blueprint creation: Bloom levels, difficulty distribution, question type quotas)
        │
        ▼
[Per-Blueprint Chunk Retrieval via pgvector Cosine Search]
        │
        ▼
4. Question Generation Agent (Prompt construction, structured JSON generation with citations & distractors)
        │
        ▼
5. Evaluation & Refinement Agent (Automated 5-metric scoring: Groundedness, Clarity, Bloom alignment, Distractor quality, Bias)
        │ ── (Loop back to Generation if score < threshold, max 2 retries)
        ▼
6. Output & Report Agent (Quality scorecard calculation, assessment bundling, multi-format export compilation)
        │
        ▼
[Human-in-the-Loop Review Studio & Export Center]
```

---

## 5. Development Commands Reference
- `make install` - Install frontend and backend dependencies
- `make dev` - Launch local FastAPI backend and Next.js frontend concurrently
- `make test` - Run full backend and frontend automated test suites
- `make lint` - Run ruff, eslint, and prettier checks
- `make typecheck` - Run mypy (Python) and tsc (TypeScript) strict checks
- `make verify` - Run full lint, typecheck, test, and build suite before committing
