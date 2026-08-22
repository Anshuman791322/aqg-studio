# Phase 10 Handoff: LangGraph Orchestration, PostgreSQL Job Runner & Resumability

## 1. Executive Summary

Phase 10 transitions AQG Studio from synchronous, transient agent endpoints to a production-grade, stateful background execution architecture. By coupling compiled **LangGraph** workflows with an in-process, database-backed **PostgreSQL Job Runner** (`PostgresJobRunner`), AQG Studio achieves robust crash recovery, zero ephemeral memory state, transactional concurrency control (`SELECT FOR UPDATE SKIP LOCKED`), and checkpointed step resumability without introducing external brokers (Redis, Celery, Temporal, or Kubernetes).

---

## 2. Deliverables & Components

### 2.1 Schemas & Compact State (`backend/app/orchestration/schemas.py`)
- `DocumentGraphState(TypedDict)`: Lightweight graph state for the 7-node document pipeline tracking `document_id`, `user_id`, step pointers, and entity ID collections.
- `AssessmentGraphState(TypedDict)`: Lightweight graph state for the 10-node assessment pipeline tracking `assessment_id`, `document_id`, blueprint IDs, accepted question IDs, replacement counters, and quality metrics.
- `JobStatusResponse(BaseModel)`: Standardized polling response payload containing `job_id`, `resource_type`, `resource_id`, `job_type`, `status`, `progress` (0.0–100.0), `current_step`, `accepted_questions`, `target_questions`, `attempts`, `error_code`, `error_message`, and UTC timestamps.

### 2.2 Document Processing Workflow (`backend/app/orchestration/document_flow.py`)
Compiled 7-node LangGraph pipeline:
1. `validate_document`: Validates document existence, status, format, and storage path.
2. `extract_document`: Deterministically extracts text, slides, sections, and metadata across PDF, DOCX, PPTX, and TXT/MD.
3. `clean_and_chunk`: Cleans text and splits into token-bounded semantic chunks (600–900 tokens, 10% overlap).
4. `store_chunks`: Persists chunks idempotently to PostgreSQL (`document_chunks` table).
5. `create_embeddings`: Computes 384-dimensional vector embeddings and updates chunks.
6. `analyze_knowledge`: Executes bounded map-and-reduce knowledge analysis, extracting domain topics and concepts.
7. `finalize_document`: Updates document status to `ready` with 100% progress.

### 2.3 Assessment Generation Workflow (`backend/app/orchestration/assessment_flow.py`)
Compiled 10-node LangGraph pipeline:
1. `load_assessment`: Validates assessment record and underlying document readiness.
2. `create_or_load_blueprints`: Loads existing blueprints or deterministically plans new blueprints with Hamilton-Hare Largest Remainder slot allocation.
3. `retrieve_and_generate_batches`: Performs per-blueprint hybrid RAG retrieval and batched question generation (`GENERATION_BATCH_SIZE = 5`).
4. `evaluate_batches`: Executes 10-metric pedagogical scoring and deterministic rule validation.
5. `route_failed_questions`: Isolates accepted questions from items requiring refinement or regeneration.
6. `refine_or_regenerate`: Executes bounded refinement passes (max 2) and regenerates questions with failure context.
7. `deduplicate`: Applies exact normalized matching, lexical Jaccard similarity, and vector cosine distance to eliminate peer duplicates.
8. `verify_requested_count`: Checks accepted count against target quota; generates replacement blueprints from document concepts if needed.
9. `calculate_metrics`: Computes overall quality scores, accepted counts, and distribution statistics.
10. `finalize_assessment`: Updates assessment status to `ready` with 100% progress and commits metrics.

### 2.4 In-Process PostgreSQL Job Runner (`backend/app/orchestration/runner.py`)
- **Single-Worker Concurrency**: Runs purely inside the FastAPI process with default concurrency of 1.
- **Transactional Claiming**: Atomically claims next queued job using `SELECT ... WHERE status = 'queued' ORDER BY created_at ASC LIMIT 1 FOR UPDATE SKIP LOCKED`.
- **Heartbeat Tracking**: Dedicated background heartbeat task updates `jobs.heartbeat_at` every 15 seconds during active graph execution.
- **Startup Crash Recovery**: `recover_stale_running_jobs` detects orphaned `running` jobs on boot (e.g., after Render container cycling) and returns them to `queued` state with preserved progress checkpoints.
- **Idempotent Resumability**: Graph nodes check database entities before re-running operations, allowing recovered jobs to resume without repeating completed expensive steps.
- **Cancellation & Graceful Shutdown**: Listens to an `asyncio.Event` stop signal and checks for active job cancellation before executing each node.

### 2.5 Lifespan Integration (`backend/app/main.py`)
- `await job_runner.start()` executed in FastAPI lifespan on application startup.
- `await job_runner.stop()` executed in FastAPI lifespan on application shutdown.

### 2.6 Queue-Based API Endpoints
- `POST /api/v1/documents/{document_id}/process`: Enqueues document processing job, returns `JobStatusResponse`.
- `GET /api/v1/documents/{document_id}/status`: Polls document processing job status.
- `POST /api/v1/assessments/{assessment_id}/generate`: Enqueues question generation job, returns `JobStatusResponse`.
- `GET /api/v1/assessments/{assessment_id}/status`: Polls assessment generation progress and question counts.
- `POST /api/v1/assessments/{assessment_id}/cancel`: Aborts active generation job.

---

## 3. Quality Verification & Test Matrix

### 3.1 Backend Test Suite
- **Total Tests**: **152 passing tests** across 24 test suites (`pytest`).
- **New Integration Suites**:
  - `backend/tests/test_orchestration.py` (5 tests): Full 7-node document flow, full 10-node assessment flow, transactional claim `SKIP LOCKED`, duplicate enqueue prevention, startup crash recovery, job cancellation.
  - `backend/tests/test_job_endpoints.py` (5 tests): Document process/status APIs, assessment generate/status/cancel APIs, unauthenticated checks, cross-tenant isolation.
- **Type Checking**: Strict `mypy app` passing with 0 errors across 94 source files.
- **Linting**: `ruff check .` passing with 0 errors.

### 3.2 Frontend Build & Types
- `tsc --noEmit`: 0 errors.
- `eslint .`: 0 errors.
- `next build`: Successfully compiled 9 static and dynamic routes.

---

## 4. Verification Commands Executed

```bash
# Backend verification
cd backend
python -m ruff check .
python -m mypy app
python -m pytest -v

# Frontend verification
cd ../frontend
npm run typecheck
npm run lint
npm run build
```

---

## 5. Handoff Status & Next Phase

Phase 10 is **COMPLETED & VERIFIED**. All queue-based background orchestration requirements are satisfied. The codebase is ready for **Phase 11: Human-in-the-Loop Review Workflows** (interactive question editing, approval, rejection, and manual refinement passes).
