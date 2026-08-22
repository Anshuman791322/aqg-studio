# AQG Studio - System Architecture & Engineering Design

## 1. Architectural Philosophy & Principles
AQG Studio is built as a **cohesive, modular monolith** comprising a single Next.js frontend application and a single FastAPI backend service. Rather than incurring the operational complexity and network latency of distributed microservices, the 6 specialized agents in AQG Studio are implemented as cleanly decoupled Python modules orchestrated through a stateful **LangGraph** execution graph.

### Core Architectural Tenets:
1. **Deterministic Foundations, Generative Intelligence**: Parsing, validation, chunking, math, counting, and format compliance are handled strictly by deterministic Python code. Generative LLMs are utilized solely for semantic analysis, creative item generation, and qualitative evaluation.
2. **Zero Paid Cloud Dependencies**: The system operates exclusively within free/community cloud tiers: Supabase (Postgres + pgvector + Auth + Storage), Vercel (Frontend), and Render (Backend).
3. **Resilient Multi-Provider Fallback**: If OpenRouter encounters rate limits, network outages, or model unavailability, the LangGraph execution runtime dynamically fails over to the NVIDIA NIM API with identical structured schema guarantees.
4. **Transparent Provenance**: Every artifact generated is anchored to deterministic document chunk IDs with verbatim source citations.

---

## 2. Global System Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT / FRONTEND LAYER                            │
│                                                                             │
│   Next.js 15 (App Router) + TypeScript + Tailwind CSS                       │
│   - Document Upload & Extraction Viewer                                     │
│   - Interactive Blueprint Generator & Distribution Matrix                   │
│   - Real-Time Generation Streamer (Server-Sent Events)                      │
│   - Question Review Studio (Side-by-Side Source Citation Inspector)         │
│   - Multi-Format Export Center (PDF, DOCX, Moodle, QTI, JSON, CSV)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / WSS / SSE
                                       │ (Supabase JWT Bearer Auth)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                          FASTAPI BACKEND SERVICE                            │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      API Routing & Validation                       │   │
│   │  /api/v1/auth   /api/v1/documents   /api/v1/blueprints   /api/v1/job│   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      │                                      │
│   ┌──────────────────────────────────▼──────────────────────────────────┐   │
│   │              LangGraph Multi-Agent Orchestration Core               │   │
│   │                                                                     │   │
│   │  [1. Doc Processing] ──► [2. Knowledge Analysis] ──► [3. Planning] │   │
│   │                                                          │          │   │
│   │  [6. Output & Report] ◄── [5. Eval & Refine] ◄── [4. Generation] ◄┘  │   │
│   └─────────────────┬─────────────────────────────────┬─────────────────┘   │
│                     │                                 │                     │
│   ┌─────────────────▼──────────────┐   ┌──────────────▼─────────────────┐   │
│   │  LLM Provider Fallback Gateway │   │   Deterministic Engines        │   │
│   │  - Primary: OpenRouter         │   │   - PyMuPDF / python-docx      │   │
│   │  - Fallback: NVIDIA NIM API    │   │   - fastembed (BGE-small ONNX) │   │
│   └────────────────────────────────┘   └────────────────────────────────┘   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ SQLAlchemy 2.0 (asyncpg)
                                       │ Supabase Storage API
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPABASE MANAGED CLOUD PLATFORM                          │
│                                                                             │
│   - PostgreSQL 15+ with pgvector Extension (Vector Similarity Search)       │
│   - Supabase Auth (JWT verification & User Profiles)                        │
│   - Supabase Storage (Private encrypted buckets for uploaded docs & exports)│
│   - Row Level Security (RLS) enforcing strict multi-tenant isolation        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The 6-Agent Sequential Pipeline Specification

The multi-agent workflow is modeled as a LangGraph `StateGraph` passing a typed `AssessmentJobState` payload across nodes.

```
                  ┌──────────────────────────────┐
                  │ 1. Document Processing Agent │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 2. Knowledge Analysis Agent  │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 3. Question Planning Agent   │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ pgvector RAG Chunk Retrieval │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 4. Question Generation Agent │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
        ┌─────────┤ 5. Evaluation & Refine Agent │◄────────┐
        │         └──────────────┬───────────────┘         │ (Iterative Refine)
        │                        │                         │ (Max 2 Attempts)
        │ (Passed Scorecard)     │ (Failed Scorecard)      │
        │                        └─────────────────────────┘
        ▼
┌──────────────────────────────┐
│ 6. Output & Report Agent     │
└──────────────┬───────────────┘
               │
               ▼
[Final Assessment Bundle + Quality Scorecard]
```

### Agent 1: Document Processing Agent
- **Purpose**: Ingests raw files (PDF, DOCX, PPTX, TXT), strips artifacts, normalizes typography, detects scanned image PDFs (deferring OCR), segments text by section/page/slide, and produces token-bounded chunks.
- **Implementation**: Pure deterministic Python (`pypdf`, `pymupdf`, `python-docx`, `python-pptx`, `tiktoken`).
- **Output**: Array of `DocumentChunk` records with character offsets, page/slide indices, and compute-ready text embeddings.

### Agent 2: Knowledge Retrieval & Analysis Agent
- **Purpose**: Analyzes the structural chunks to extract key concepts, domain vocabulary, conceptual dependencies, and topic distribution.
- **Implementation**: LLM semantic analyzer utilizing few-shot prompts with strict JSON schema outputs.
- **Output**: `KnowledgeMap` object containing prioritized topics, subtopics, prerequisite relationships, and difficulty indicators.

### Agent 3: Question Planning Agent
- **Purpose**: Formulates an assessment blueprint matching user specifications (target count, question types, difficulty ratio, Bloom taxonomy distribution).
- **Implementation**: Hybrid deterministic planner + LLM constraint solver. The deterministic module calculates exact quotas, while the LLM maps each question slot to a specific topic and cognitive objective.
- **Output**: `AssessmentBlueprint` containing individual `QuestionPlanItem` definitions.

### Agent 4: Question Generation Agent
- **Purpose**: Generates high-fidelity questions for each `QuestionPlanItem`. Executes cosine similarity queries against `pgvector` to isolate the 3–5 most relevant document chunks, constructs an anti-injection prompt, and generates structured JSON question objects.
- **Implementation**: Prompt-engineered LLM generator with Pydantic output parsing, citations, distractor rationales, and rubric definitions.
- **Output**: Draft `GeneratedQuestion` records with full provenance links.

### Agent 5: Evaluation & Refinement Agent
- **Purpose**: Implements an automated adversarial critique, scoring, and refinement loop.
- **Deterministic Validation**: Fast non-LLM checks for required fields, character bounds, source chunk ID provenance against document chunks, single-select MCQ rules (4 options, unique keys/texts, single correct answer, ban on lazy phrases), boolean formats, and exact normalized duplicate prevention.
- **Pedagogical Evaluation**: Evaluates candidate questions across 10 dimensions (correctness, groundedness, relevance, clarity, grammar, answerability, difficulty alignment, Bloom alignment, distractor quality, duplication risk, overall quality).
- **Decision Engine**:
  - `ACCEPT`: high quality scores (overall >= 0.85, correctness >= 0.90, groundedness >= 0.90, duplication_risk <= 0.30) and zero critical flaws.
  - `REFINE`: recoverable flaws (minor stem ambiguity, distractor tweak, grammar polish) routed to LLM Refinement Prompt preserving source boundaries.
  - `REGENERATE`: fatal flaws, ungrounded claims, or hallucinated facts routed to fresh item generation.
- **Attempt Bounding & Replacement Blueprints**: Refinement and regeneration passes are bounded (`EVALUATION_MAX_REFINEMENT_ATTEMPTS = 2`, `EVALUATION_MAX_REGENERATION_ATTEMPTS = 2`). If attempts exhaust, replacement blueprints are deterministically generated to maintain the requested question quota.
- **Duplicate Control**: Exact normalized matching, lexical Jaccard similarity, and vector cosine embedding similarity identify peer duplicates and keep higher-quality candidates.
- **Output**: Fully verified questions, persisted `Evaluation` scorecards, and `AssessmentEvaluationSummary`.

### Agent 6: Output & Report Agent
- **Purpose**: Computes global assessment statistics, calculates overall quality scores, estimates assessment completion time, flags human-review recommendations, and compiles export packages.
- **Implementation**: Deterministic Python report aggregator and export builder.
- **Output**: Finalized assessment bundle, PDF/DOCX templates, and LMS-compatible export payloads.

---

## 4. LangGraph State Management & PostgreSQL Background Job Runner

To operate reliably on Render free-tier instances (which may sleep, cycle, or restart), all long-running asynchronous workflows are managed as compiled **LangGraph** state graphs executed by an in-process **PostgreSQL-backed Job Runner** (`PostgresJobRunner`).

### 4.1 Compact Typed Graph States

State dictionaries store lightweight identifiers, bounds, step pointers, and metric counters rather than large raw texts or embedding arrays:

```python
class DocumentGraphState(TypedDict, total=False):
    document_id: str
    user_id: str
    raw_bytes: bytes | None
    storage_path: str | None
    mime_type: str | None
    page_count: int
    word_count: int
    language: str
    chunk_ids: list[str]
    topic_ids: list[str]
    current_step: str
    progress: float
    error_code: str | None
    error_message: str | None

class AssessmentGraphState(TypedDict, total=False):
    assessment_id: str
    document_id: str
    user_id: str
    target_questions: int
    blueprint_ids: list[str]
    generated_question_ids: list[str]
    accepted_question_ids: list[str]
    failed_question_ids: list[str]
    replacement_blueprint_ids: list[str]
    replacement_count: int
    current_step: str
    progress: float
    average_quality_score: float
    error_code: str | None
    error_message: str | None
```

### 4.2 Compiled Workflows

1. **Document Processing Workflow (7 Nodes)**:
   ```
   START
   ──► validate_document
   ──► extract_document
   ──► clean_and_chunk
   ──► store_chunks
   ──► create_embeddings
   ──► analyze_knowledge
   ──► finalize_document
   ──► END
   ```

2. **Assessment Generation & Refinement Workflow (10 Nodes)**:
   ```
   START
   ──► load_assessment
   ──► create_or_load_blueprints
   ──► retrieve_and_generate_batches
   ──► evaluate_batches
   ──► route_failed_questions
   ──► refine_or_regenerate
   ──► deduplicate
   ──► verify_requested_count
   ──► calculate_metrics
   ──► finalize_assessment
   ──► END
   ```

### 4.3 PostgreSQL Job Runner (`PostgresJobRunner`)

- **Brokerless In-Process Architecture**: Pure Python + async SQLAlchemy running inside the FastAPI lifespan without Celery, Redis, Temporal, or external queues.
- **Transactional Claiming**: Atomically claims the next pending job using `SELECT ... WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED`, preventing race conditions across concurrent workers.
- **Heartbeat & Liveness**: Periodically touches `jobs.heartbeat_at` every 15 seconds during graph execution.
- **Startup Crash Recovery**: On application boot (`job_runner.start()`), detects orphaned running jobs with expired heartbeats and transitions them back to `queued` state with preserved progress checkpoints.
- **Node Idempotency & Resumability**: Every graph node checks if its respective database entities already exist before performing expensive extraction or LLM invocations, resuming execution from the last persisted checkpoint.
- **Graceful Shutdown & Cancellation**: Watches an `asyncio.Event` stop signal and checks for active job cancellation before each node execution.

---

## 5. LLM Provider Fallback Gateway & Structured Output

To guarantee 99.9% pipeline reliability without relying on single-vendor uptime, all LLM calls are routed through a provider gateway (`backend/app/llm/`):

```
                      ┌────────────────────────────┐
                      │    LLM Gateway Request     │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │  Primary Provider:         │
                      │  OpenRouter API            │
                      │  (openrouter/free)         │
                      └─────────────┬──────────────┘
                                    │
                       Success? ────┼──── Transient Error (429/5xx) / Timeout / NetError
                      │             │     (Retry with Jittered Exponential Backoff)
                      ▼             ▼
             [Return Result]  ┌────────────────────────────┐
                              │  Fallback Provider:        │
                              │  NVIDIA NIM API            │
                              │  (meta/llama-3.3-70b)      │
                              └─────────────┬──────────────┘
                                            │
                               Success? ────┼──── Error
                              │             │
                              ▼             ▼
                     [Return Result]  [Raise LLMAllProvidersFailedError]
```

### Structured Output & Controlled 1-Pass Repair
1. The engine constructs a strict JSON Schema definition embedded in system instructions.
2. The initial response is extracted, harmless Markdown fences (````json ... ````) are stripped, and content is parsed into Pydantic models.
3. If schema validation fails, a controlled repair prompt feeds the exact validation error back to the model for a single corrective pass.
4. If validation succeeds, typed domain entities are returned; if repair fails, typed `LLMStructuredOutputError` is raised.

---

## 6. Locked Technology Stack & Zero-Cost Constraints

| Category | Approved Standard | Prohibited Technologies |
| :--- | :--- | :--- |
| **Frontend** | Next.js 15 App Router, TypeScript, Tailwind CSS | Pages router, Vue, Angular, Svelte |
| **Backend** | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 | Flask, Django, Express.js (for AQG Studio backend) |
| **Agent Orchestration**| LangGraph | AutoGen, CrewAI, raw monolithic spaghetti loops |
| **Database** | Supabase PostgreSQL + `pgvector` extension | Paid Pinecone, Weaviate, Qdrant, Milvus |
| **Task Execution** | FastAPI BackgroundTasks / Async IO coroutines | Redis, Celery, RabbitMQ, Kafka, Kubernetes |
| **File Storage** | Supabase Storage (Private S3) | AWS S3 paid buckets, GCP Cloud Storage paid |
| **Hosting** | Vercel (Frontend Free), Render (Backend Free) | AWS EC2, GCP GKE, Azure Kubernetes |
