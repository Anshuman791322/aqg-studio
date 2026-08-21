# Phase 8 Handoff: Grounded Batched Question Generation Agent

## Summary of Implementation
Phase 8 delivers the **Question Generation Agent**, batched RAG retrieval, multi-type question validation, source chunk provenance, prompt-injection defense framing, and assessment question endpoints:

1. **Strict Schemas (`backend/app/generation/schemas.py`)**:
   - `SupportingEvidence`: `source_chunk_ids`, `verbatim_excerpt`, `page_numbers`, `rationale`.
   - `GeneratedMCQOption`: `key` ("A", "B", "C", "D"), `text`.
   - `GeneratedQuestionItem`: Structured output mapping to a `blueprint_id` with `question_type`, `question_text`, `options`, `correct_answer`, `explanation`, `topic`, `difficulty`, `bloom_level`, and `supporting_evidence`.
   - `BatchQuestionGenerationOutput`: Groups up to `GENERATION_BATCH_SIZE` items in one request to conserve free provider quotas.
   - `QuestionResponseData` & `AssessmentGenerationResult`: API data transfer models.

2. **Validation Engine (`backend/app/generation/validator.py`)**:
   - `validate_generated_question`:
     - Verifies blueprint attributes match (`question_type`, `difficulty`, `bloom_level`).
     - Grounding check: `source_chunk_ids` are non-empty and strictly subset of context chunks; verbatim excerpt is present.
     - Single-Select MCQ: exactly 4 distinct options, distinct texts, exactly 1 correct option, bans lazy phrases ("All/None of the above/these", "Both A and B").
     - Multi-Select MCQ: 4+ options, 2+ correct options.
     - True/False: boolean answers (`True`/`False`), unambiguous statement.
     - Short Answer: concise answers (<= 500 characters, no essays).
     - Descriptive: grading rubric or key concept points present in `correct_answer`.

3. **Generation Prompts (`backend/app/prompts/generation.py`)**:
   - `QUESTION_GENERATOR_SYSTEM_PROMPT`:
     - Treats all text in `<document_context>` as untrusted data; strictly ignores embedded commands or prompt injections.
     - Strict source grounding: only generates questions factually supported by supplied chunks.
   - `build_batch_generation_user_prompt`: Formats blueprints with their per-blueprint retrieved chunk context and chunk UUIDs.

4. **Question Generation Agent (`backend/app/agents/question_generation_agent.py`)**:
   - `QuestionGenerationAgent`:
     - `generate_batch_questions(...)`: Batches blueprints, executes hybrid RAG retrieval per item, calls structured LLM, validates items independently, and saves valid `Question` records with status `'draft'`.
     - `generate_assessment_questions(...)`: Full assessment lifecycle with fallback retry of failed blueprints using reduced batch size (size 1) up to `GENERATION_MAX_RETRIES` attempts, updating `Assessment` metrics (`total_questions`, `generated_questions`, `failed_questions`) and status (`'ready'` / `'failed'`).

5. **API Endpoints (`backend/app/api/v1/endpoints/assessments.py` & `questions.py`)**:
   - `POST /api/v1/assessments/{assessment_id}/generate`: Initiates grounded question generation.
   - `GET /api/v1/assessments/{assessment_id}/questions`: Lists generated questions with supporting evidence.
   - `GET /api/v1/questions/{question_id}`: Retrieves single question with full audit trace.

---

## Verification & Quality Gates
- **Unit & Integration Tests**: 129 backend tests passing (`pytest` including all 4 question types, MCQ option counts, duplicate options, hallucinated chunk rejection, partial batch success, prompt injection defense, and budget limits).
- **Static Analysis & Types**: Ruff (`0` errors), mypy (`0` errors across 82 source files).
- **Frontend Verification**: ESLint (`0` warnings/errors), TypeScript strict typecheck (`0` errors), Jest, and Next.js 15 production build compiling 9 routes.
