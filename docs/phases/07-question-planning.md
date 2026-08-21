# Phase 7 Handoff: Question Planning Agent & Assessment Blueprint Generation

## Summary of Implementation
Phase 7 delivers the **Question Planning Agent**, deterministic Largest Remainder quota allocator, assessment creation workflows, and question blueprint schemas without prematurely generating question wording:

1. **Strict Assessment & Planning Schemas (`backend/app/planning/schemas.py`)**:
   - `AssessmentCreateRequest`: Validates `document_id`, `name`, `total_questions` (1..50), optional `topic_ids`, `question_type_distribution`, `difficulty_distribution`, `bloom_distribution`, `custom_instructions` (max 1000 chars), `include_answers`, `include_explanations`, `include_source_references`.
   - `QuestionBlueprintItemSchema`: `sequence_number`, `topic_id`, `topic_name`, `concept_id`, `concept_name`, `question_type`, `difficulty`, `bloom_level`, `learning_objective`, `source_chunk_ids`, `rationale`, `status`.
   - `PlanningSlotRefinementItem` & `PlanningRefinementOutput`: Pydantic structured output models for LLM refinement.
   - `AssessmentResponseData`: Serialized assessment summary model.
   - `AssessmentBlueprintResponse`: Combined assessment and blueprint collection response.

2. **Deterministic Quota Allocator (`backend/app/planning/allocator.py`)**:
   - `largest_remainder_distribution`: Hamilton-Hare largest-remainder quota calculator guaranteeing exact integer sums matching `total_questions`.
   - `build_blueprint_slots`: Generates skeleton blueprint slots balancing question types, difficulties, Bloom cognitive levels, and topics weighted by importance and concept coverage.

3. **Question Planning Agent (`backend/app/agents/planning_agent.py`)**:
   - `QuestionPlanningAgent.create_assessment_with_blueprint(...)`:
     - Verifies document ownership and topic/concept availability.
     - Runs deterministic slot allocation before any LLM call.
     - Uses structured LLM prompt (`PLANNING_AGENT_SYSTEM_PROMPT` in `prompts/planning.py`) to refine learning objectives, assign pedagogical rationales, and verify chunk provenance while strictly forbidding question generation.
     - Provides deterministic fallback synthesis if LLM refinement is offline or fails.
     - Persists `Assessment` (status `'draft'`) and `QuestionBlueprint` (status `'planned'`) records inside an atomic transaction.

4. **Assessment REST Endpoints (`backend/app/api/v1/endpoints/assessments.py`)**:
   - `POST /api/v1/assessments`: Creates assessment and designs blueprints.
   - `GET /api/v1/assessments`: Lists authenticated user's assessments.
   - `GET /api/v1/assessments/{id}`: Retrieves single assessment summary.
   - `GET /api/v1/assessments/{id}/blueprint`: Retrieves blueprint design items in sequence order.
   - `DELETE /api/v1/assessments/{id}`: Deletes assessment and cascades to blueprints/questions.

---

## Verification & Quality Gates
- **Unit & Integration Tests**: 113 backend tests passing (`pytest` including quota math, slot allocation, prompt injection protection, cross-user isolation, and endpoint tests).
- **Static Analysis & Types**: Ruff (`0` errors), mypy (`0` errors across 77 source files).
- **Frontend Verification**: ESLint (`0` warnings/errors), TypeScript strict typecheck (`0` errors), Jest, and Next.js 15 production build compiling 9 routes.
