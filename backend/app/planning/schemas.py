"""Pydantic schemas for Assessment creation, configuration, and QuestionBlueprints."""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

QuestionType = Literal["mcq", "mcq_single", "mcq_multi", "true_false", "short_answer", "descriptive"]
DifficultyLevel = Literal["easy", "medium", "hard"]
BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]


class AssessmentCreateRequest(BaseModel):
    """Payload for creating an assessment and generating question blueprints."""

    model_config = ConfigDict(extra="ignore")

    document_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=200)
    total_questions: int = Field(default=10, ge=1, le=50)
    topic_ids: list[uuid.UUID] | None = None
    question_type_distribution: dict[str, float] | None = Field(
        default=None,
        description="Distribution of question types in percentages or weights (e.g. {'mcq': 60, 'short_answer': 40})",
    )
    difficulty_distribution: dict[str, float] | None = Field(
        default=None,
        description="Distribution of difficulty levels (e.g. {'easy': 30, 'medium': 50, 'hard': 20})",
    )
    bloom_distribution: dict[str, float] | None = Field(
        default=None,
        description="Distribution of Bloom taxonomy cognitive levels (e.g. {'remember': 30, 'understand': 40, 'apply': 30})",
    )
    custom_instructions: str | None = Field(
        default=None,
        max_length=1000,
        description="Optional assessment instructions or focus directives.",
    )
    include_answers: bool = True
    include_explanations: bool = True
    include_source_references: bool = True


class QuestionBlueprintItemSchema(BaseModel):
    """Individual question design item in an assessment blueprint."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID | None = None
    sequence_number: int = Field(..., ge=1)
    topic_id: uuid.UUID | None = None
    topic_name: str | None = None
    concept_id: uuid.UUID | None = None
    concept_name: str | None = None
    question_type: str
    difficulty: DifficultyLevel
    bloom_level: BloomLevel
    learning_objective: str
    source_chunk_ids: list[uuid.UUID] = Field(default_factory=list)
    rationale: str = ""
    status: str = "planned"


class AssessmentResponseData(BaseModel):
    """Response schema for Assessment summary entity."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    document_id: uuid.UUID
    name: str
    total_questions: int
    configuration: dict[str, Any]
    status: str
    progress: float
    metrics: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AssessmentBlueprintResponse(BaseModel):
    """Response schema containing an assessment and its full question blueprint."""

    model_config = ConfigDict(extra="ignore")

    assessment_id: uuid.UUID
    document_id: uuid.UUID
    name: str
    total_questions: int
    status: str
    configuration: dict[str, Any]
    blueprints: list[QuestionBlueprintItemSchema]


class PlanningSlotRefinementItem(BaseModel):
    """Structured LLM output for refining a single blueprint slot."""

    model_config = ConfigDict(extra="ignore")

    sequence_number: int
    learning_objective: str
    rationale: str
    source_chunk_ids: list[uuid.UUID] = Field(default_factory=list)


class PlanningRefinementOutput(BaseModel):
    """Structured LLM output response for full blueprint slot refinement."""

    model_config = ConfigDict(extra="ignore")

    items: list[PlanningSlotRefinementItem]

