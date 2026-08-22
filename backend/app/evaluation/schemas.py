"""Pydantic schemas for Question Evaluation, Refinement, and Pedagogical Quality Scoring."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

EvaluationDecision = Literal["ACCEPT", "REFINE", "REGENERATE"]


class MetricScores(BaseModel):
    """Normalized 10-dimensional pedagogical quality scoring breakdown (0.0 to 1.0)."""

    correctness: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Factual correctness and accuracy of the question and answer key based strictly on source text.",
    )
    groundedness: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Degree to which every premise and detail is strictly derived from supplied source chunks (hallucination defense).",
    )
    relevance: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Relevance of the question to the targeted topic, concept, and learning objective.",
    )
    clarity: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Clarity, readability, and lack of ambiguity in the question stem and options.",
    )
    grammar: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Linguistic correctness, formatting, punctuation, and typographical quality.",
    )
    answerability: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Whether a student can definitively answer the question using only the provided context without external trivia.",
    )
    difficulty_alignment: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Alignment with the requested difficulty tier (easy, medium, hard).",
    )
    bloom_alignment: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Alignment with the requested Bloom taxonomy cognitive level (remember, understand, apply, analyze, evaluate, create).",
    )
    distractor_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Plausibility, mutual exclusivity, and lack of giveaway cues for MCQ distractors (1.0 for non-MCQ).",
    )
    duplication_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Risk of duplicating another item in the assessment (0.0 = completely unique, 1.0 = exact duplicate).",
    )
    overall_quality: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Composite overall quality score from 0.0 to 1.0.",
    )


class LLMEvaluationOutput(BaseModel):
    """Structured output returned by the LLM Question Evaluator."""

    question_id: str | None = Field(
        default=None,
        description="Stringified UUID of the evaluated question.",
    )
    scores: MetricScores = Field(
        default_factory=MetricScores,
        description="Detailed dimensional scores.",
    )
    decision: EvaluationDecision = Field(
        default="ACCEPT",
        description="Final action recommendation: ACCEPT, REFINE, or REGENERATE.",
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Specific pedagogical strengths identified in the question.",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Defects or shortcomings requiring correction or regeneration.",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Actionable improvement recommendations for the refinement agent.",
    )
    rationale: str = Field(
        default="",
        description="Comprehensive summary explanation of the evaluation decision.",
    )


class DeterministicCheckResult(BaseModel):
    """Results from fast non-LLM rule and constraint checks."""

    is_valid: bool = True
    critical_failure: bool = False
    issues: list[str] = Field(default_factory=list)
    rule_violations: list[str] = Field(default_factory=list)


class RefinementRequest(BaseModel):
    """Request payload for manual or targeted question refinement."""

    target_issues: list[str] = Field(
        default_factory=list,
        description="Specific defects or weaknesses to remedy.",
    )
    custom_instructions: str | None = Field(
        default=None,
        max_length=500,
        description="Optional user guidance for rephrasing or adjusting the question.",
    )


class EvaluationResponseData(BaseModel):
    """API representation of an Evaluation record."""

    id: uuid.UUID
    question_id: uuid.UUID
    correctness_score: float | None = None
    grounding_score: float | None = None
    clarity_score: float | None = None
    relevance_score: float | None = None
    difficulty_score: float | None = None
    bloom_alignment_score: float | None = None
    distractor_quality_score: float | None = None
    duplication_score: float | None = None
    overall_quality_score: float
    decision: str
    feedback: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class QuestionWithEvaluationsData(BaseModel):
    """Question representation paired with historical evaluation audit cards."""

    id: uuid.UUID
    assessment_id: uuid.UUID
    blueprint_id: uuid.UUID | None = None
    question_type: str
    question_text: str
    options: list[dict[str, Any]] | None = None
    correct_answer: Any
    explanation: str
    topic: str | None = None
    difficulty: str
    bloom_level: str
    source_chunk_ids: list[uuid.UUID] = Field(default_factory=list)
    source_pages: list[int] = Field(default_factory=list)
    supporting_evidence: dict[str, Any] = Field(default_factory=dict)
    status: str
    version: int = 1
    generation_attempts: int = 1
    quality_score: float | None = None
    created_at: datetime | None = None
    evaluations: list[EvaluationResponseData] = Field(default_factory=list)


class AssessmentEvaluationSummary(BaseModel):
    """Comprehensive evaluation and refinement summary for an assessment."""

    assessment_id: uuid.UUID
    total_questions: int
    accepted_count: int
    refined_count: int
    regenerated_count: int
    failed_count: int
    average_quality_score: float
    status: str
    questions: list[QuestionWithEvaluationsData]
