"""Evaluation and refinement package exports."""

from app.evaluation.deterministic import (
    BANNED_MCQ_PHRASES,
    normalize_stem,
    validate_question_deterministic,
)
from app.evaluation.duplication import (
    DuplicateMatch,
    compute_jaccard_similarity,
    compute_vector_cosine_similarity,
    detect_assessment_duplicates,
    is_exact_normalized_duplicate,
    normalize_text,
    resolve_duplicate_conflicts,
)
from app.evaluation.schemas import (
    AssessmentEvaluationSummary,
    DeterministicCheckResult,
    EvaluationDecision,
    EvaluationResponseData,
    LLMEvaluationOutput,
    MetricScores,
    QuestionWithEvaluationsData,
    RefinementRequest,
)

__all__ = [
    "AssessmentEvaluationSummary",
    "BANNED_MCQ_PHRASES",
    "DeterministicCheckResult",
    "DuplicateMatch",
    "EvaluationDecision",
    "EvaluationResponseData",
    "LLMEvaluationOutput",
    "MetricScores",
    "QuestionWithEvaluationsData",
    "RefinementRequest",
    "compute_jaccard_similarity",
    "compute_vector_cosine_similarity",
    "detect_assessment_duplicates",
    "is_exact_normalized_duplicate",
    "normalize_stem",
    "normalize_text",
    "resolve_duplicate_conflicts",
    "validate_question_deterministic",
]
