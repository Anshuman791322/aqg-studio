"""Pydantic schemas for Question Generation Agent and batch outputs."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SupportingEvidence(BaseModel):
    """Grounding evidence and verbatim excerpt from source document chunks."""

    model_config = ConfigDict(extra="ignore")

    source_chunk_ids: list[uuid.UUID] = Field(
        default_factory=list,
        description="UUIDs of the source document chunks supporting this question.",
    )
    verbatim_excerpt: str = Field(
        ...,
        min_length=5,
        description="Verbatim sentence or phrase from the source chunk text.",
    )
    page_numbers: list[int] = Field(
        default_factory=list,
        description="Source document page numbers if applicable.",
    )
    rationale: str = Field(
        default="",
        description="Short rationale explaining how the evidence justifies the question and answer key.",
    )


class GeneratedMCQOption(BaseModel):
    """An option item for multiple-choice questions."""

    model_config = ConfigDict(extra="ignore")

    key: str = Field(..., description="Option identifier (e.g. 'A', 'B', 'C', 'D').")
    text: str = Field(..., min_length=1, description="Option wording.")


class GeneratedQuestionItem(BaseModel):
    """Structured LLM output for a single generated question matching a blueprint."""

    model_config = ConfigDict(extra="ignore")

    blueprint_id: uuid.UUID = Field(
        ..., description="UUID of the QuestionBlueprint this item realizes."
    )
    question_type: str = Field(
        ..., description="Question type ('mcq_single', 'mcq_multi', 'true_false', 'short_answer', 'descriptive')."
    )
    question_text: str = Field(
        ..., min_length=10, description="Clear, unambiguous question stem or prompt."
    )
    options: list[GeneratedMCQOption] | None = Field(
        default=None,
        description="List of exactly 4 options for single-select MCQ, or 4+ for multi-select MCQ.",
    )
    correct_answer: Any = Field(
        ...,
        description="Answer key. For MCQ: option key ('A') or text; for TF: boolean; for short answer: concise string; for descriptive: rubric points.",
    )
    explanation: str = Field(
        ...,
        min_length=10,
        description="Concise pedagogical explanation justifying why the answer is correct and why distractors are incorrect.",
    )
    topic: str = Field(..., description="Topic name.")
    difficulty: str = Field(..., description="Difficulty tier ('easy', 'medium', 'hard').")
    bloom_level: str = Field(
        ...,
        description="Bloom taxonomy level ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create').",
    )
    supporting_evidence: SupportingEvidence = Field(
        ..., description="Grounding source chunks and verbatim excerpt."
    )


class BatchQuestionGenerationOutput(BaseModel):
    """Structured LLM response for a batch of generated questions."""

    model_config = ConfigDict(extra="ignore")

    questions: list[GeneratedQuestionItem] = Field(
        default_factory=list,
        description="List of generated questions corresponding to requested blueprint batch.",
    )


class QuestionResponseData(BaseModel):
    """Response model for a persisted Question entity."""

    model_config = ConfigDict(extra="ignore")

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
    status: str = "draft"
    version: int = 1
    created_at: datetime | None = None


class AssessmentGenerationResult(BaseModel):
    """Result summary for an assessment question generation job."""

    model_config = ConfigDict(extra="ignore")

    assessment_id: uuid.UUID
    total_blueprints: int
    generated_questions: int
    failed_blueprints: int
    status: str
    questions: list[QuestionResponseData] = Field(default_factory=list)
