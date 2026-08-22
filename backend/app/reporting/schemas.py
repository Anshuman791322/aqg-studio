"""Pydantic schemas for assessment reporting, pedagogical metrics, and exports."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ExportConfiguration(BaseModel):
    """Configuration options for assessment file export."""

    model_config = ConfigDict(extra="ignore")

    include_answers: bool = Field(
        default=True,
        description="Whether to include correct answer indicators/keys.",
    )
    include_explanations: bool = Field(
        default=True,
        description="Whether to include detailed explanations/rationales.",
    )
    include_source_references: bool = Field(
        default=True,
        description="Whether to include source chunk and page citations.",
    )
    include_quality_scores: bool = Field(
        default=False,
        description="Whether to render quality scorecards and evaluation metrics.",
    )
    shuffle_questions: bool = Field(
        default=False,
        description="Whether to deterministically randomize question order.",
    )
    shuffle_mcq_options: bool = Field(
        default=False,
        description="Whether to deterministically randomize MCQ distractor positions.",
    )
    separate_answer_key: bool = Field(
        default=True,
        description="Whether to place answers and explanations in a dedicated section at the end.",
    )
    seed: int | None = Field(
        default=None,
        description="Optional deterministic integer seed for reproducible shuffling.",
    )
    custom_title: str | None = Field(
        default=None,
        max_length=200,
        description="Optional custom title overriding the assessment name in export document.",
    )
    custom_instructions: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional custom instructions to display at the top of the test paper.",
    )


class ExportCreateRequest(BaseModel):
    """Request schema for creating an export file package."""

    model_config = ConfigDict(extra="forbid")

    format: str = Field(
        ...,
        description="Export file format: 'pdf', 'docx', 'json', 'csv', 'moodle_xml', 'gift', 'qti_2_1'.",
        pattern=r"^(pdf|docx|json|csv|moodle_xml|gift|qti_2_1)$",
    )
    configuration: ExportConfiguration = Field(
        default_factory=ExportConfiguration,
        description="Fine-grained export formatting and content options.",
    )


class ExportResponse(BaseModel):
    """Response schema for an export package record."""

    id: uuid.UUID
    assessment_id: uuid.UUID
    user_id: uuid.UUID
    format: str
    storage_path: str
    configuration: dict[str, Any]
    status: str
    file_size_bytes: int | None = None
    download_url: str | None = None
    created_at: datetime
    updated_at: datetime


class ExportDownloadResponse(BaseModel):
    """Response schema for generating a secure short-lived export download URL."""

    export_id: uuid.UUID
    assessment_id: uuid.UUID
    format: str
    filename: str
    download_url: str
    expires_in_seconds: int = 3600


class DistributionCount(BaseModel):
    """Count and percentage share for a distribution category."""

    count: int
    percentage: float = Field(
        ..., ge=0.0, le=100.0, description="Percentage share (0.0 to 100.0)."
    )


class TopicCoverageItem(BaseModel):
    """Topic coverage analysis item."""

    topic_name: str
    question_count: int
    is_covered: bool
    importance_score: float = 1.0


class PedagogicalQualityMetrics(BaseModel):
    """Aggregated pedagogical evaluation metrics for an assessment."""

    total_requested: int
    total_generated: int
    total_accepted: int
    total_rejected: int
    total_flagged: int
    total_draft: int
    approval_rate: float = Field(..., ge=0.0, le=100.0)
    average_overall_quality: float = Field(..., ge=0.0, le=1.0)
    average_groundedness: float = Field(..., ge=0.0, le=1.0)
    average_correctness: float = Field(..., ge=0.0, le=1.0)
    average_clarity: float = Field(..., ge=0.0, le=1.0)
    average_distractor_quality: float = Field(..., ge=0.0, le=1.0)
    number_refined: int
    number_regenerated: int
    duplicate_count: int
    failed_blueprints: int
    estimated_provider_requests: int = 0
    estimated_total_tokens: int = 0


class AssessmentReportResponse(BaseModel):
    """Comprehensive analytics and pedagogical quality report for an assessment."""

    assessment_id: uuid.UUID
    document_id: uuid.UUID
    assessment_name: str
    document_filename: str
    status: str
    created_at: datetime
    updated_at: datetime
    metrics: PedagogicalQualityMetrics
    question_type_distribution: dict[str, DistributionCount]
    difficulty_distribution: dict[str, DistributionCount]
    bloom_distribution: dict[str, DistributionCount]
    topic_coverage: list[TopicCoverageItem]
    available_exports: list[ExportResponse] = Field(default_factory=list)
