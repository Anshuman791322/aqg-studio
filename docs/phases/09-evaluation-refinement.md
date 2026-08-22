# Phase 9 Handoff: Evaluation & Refinement Agent

## Summary of Implementation
Phase 9 delivers the complete **Evaluation & Refinement Agent** (Agent 5), providing deterministic validation, 10-dimensional pedagogical quality scoring, automated multi-pass refinement, grounded regeneration with context refreshment, replacement blueprint generation for attempt exhaustion, and duplicate detection:

1. **Deterministic Rule Validation (`backend/app/evaluation/deterministic.py`)**:
   - `validate_question_deterministic`:
     - Checks existence and character boundaries (10 <= length <= 2000).
     - Validates `source_chunk_ids` against document chunk IDs to prevent hallucinated chunk citations.
     - Single-Select MCQ: exactly 4 options, unique keys (`A, B, C, D`), unique option texts, single correct answer matching a valid key, bans lazy phrases ("All/None of the above/these", "Both A and B").
     - Multi-Select MCQ: at least 4 options, at least 2 correct keys.
     - True/False: boolean answers (`True`/`False` or case-insensitive string equivalents).
     - Short Answer: concise answers (<= 500 characters).
     - Descriptive: presence of rubric or key concept points.
     - Blueprint attribute alignment (question type, difficulty, Bloom level).
     - Exact normalized duplicate question prevention.

2. **Structured Pedagogical Evaluation (`backend/app/evaluation/schemas.py` & `backend/app/prompts/evaluation.py`)**:
   - Scores 10 pedagogical dimensions (0.0 to 1.0):
     - `correctness`: Factual accuracy according to source chunks.
     - `groundedness`: Hallucination defense (strict factual provenance).
     - `relevance`: Alignment to target concept and learning objective.
     - `clarity`: Unambiguous, concise stem and options.
     - `grammar`: Linguistic correctness and punctuation.
     - `answerability`: Answerable strictly from provided text.
     - `difficulty_alignment`: Matches easy/medium/hard tier.
     - `bloom_alignment`: Matches intended Bloom cognitive taxonomy level.
     - `distractor_quality`: Plausible, non-lazy, distinct options for MCQs (1.0 for non-MCQs).
     - `duplication_risk`: Risk of duplicating another item in the assessment.
     - `overall_quality`: Composite score.
   - Decision engine thresholds:
     - `ACCEPT`: `overall_quality >= 0.85`, `correctness >= 0.90`, `groundedness >= 0.90`, `duplication_risk <= 0.30`.
     - `REFINE`: Recoverable issues (minor stem clarity, distractor adjustment, grammar polish) with `overall_quality >= 0.60`, `groundedness >= 0.70`.
     - `REGENERATE`: Critical flaws, ungrounded claims, or hallucinated facts.

3. **Iterative Refinement & Prompt Boundary (`backend/app/prompts/refinement.py`)**:
   - Targeted repair loop passing evaluator critique and recommendations to the model.
   - Anti-injection security fencing isolating `<document_context>`, `<original_question>`, and `<evaluator_feedback>`.
   - Strictly prevents refinement from introducing external unsupported facts.
   - Re-evaluates refined candidate immediately.

4. **Regeneration & Replacement Blueprints (`backend/app/agents/evaluation_agent.py`)**:
   - `regenerate_single_question`: Discards failed candidates, runs fresh RAG retrieval, and generates fresh items with failure rationale.
   - `create_replacement_blueprint`: When regeneration attempts exhaust (`EVALUATION_MAX_REGENERATION_ATTEMPTS = 2`), creates a replacement blueprint with matching difficulty/Bloom parameters from document concepts to maintain the requested assessment question quota.

5. **Duplicate Detection & Control (`backend/app/evaluation/duplication.py`)**:
   - Normalized exact matching (stripping punctuation and whitespace).
   - Lexical Jaccard token overlap similarity.
   - Vector embedding cosine similarity.
   - Conflict resolution keeping higher-quality candidates and triggering regeneration/replacement for duplicates.

6. **API Endpoints (`backend/app/api/v1/endpoints/questions.py` & `assessments.py`)**:
   - `POST /api/v1/assessments/{assessment_id}/evaluate`: Runs assessment evaluation and refinement workflow.
   - `POST /api/v1/questions/{question_id}/evaluate`: Single question evaluation scorecard.
   - `POST /api/v1/questions/{question_id}/refine`: Single question targeted refinement pass.
   - `GET /api/v1/questions/{question_id}/evaluations`: List historical evaluation audit scorecards.

---

## Verification & Quality Gates
- **Unit & Integration Tests**: 142 backend tests passing (`pytest` including deterministic rules, duplicate conflict resolution, acceptance scoring, refinement loops, attempt exhaustion, replacement blueprint creation, and cross-user isolation).
- **Static Analysis & Types**: Ruff (`0` errors), mypy (`0` errors across 89 source files).
- **Frontend Quality Gate**: ESLint (`0` warnings/errors), TypeScript strict typecheck (`0` errors), Next.js 15 production build compiling 9 routes.
