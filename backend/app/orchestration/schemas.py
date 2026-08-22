"""Pydantic schemas and TypedDict state models for LangGraph workflows and PostgreSQL background jobs."""

import uuid
from datetime import datetime
from typing import Any, TypedDict

from pydantic import BaseModel, Field


class DocumentGraphState(TypedDict, total=False):
    """Typed state dictionary for Document Ingestion, Parsing, Chunking, and Knowledge Analysis workflow."""

    document_id: str
    user_id: str
    job_id: str | None
    filename: str
    storage_path: str
    mime_type: str | None
    raw_bytes: bytes | None
    page_count: int
    word_count: int
    chunk_ids: list[str]
    topic_ids: list[str]
    current_step: str
    progress: float
    error_code: str | None
    error_message: str | None


class AssessmentGraphState(TypedDict, total=False):
    """Typed state dictionary for Blueprint Planning, Generation, Evaluation, Refinement, and Dedup workflow."""

    assessment_id: str
    document_id: str
    user_id: str
    job_id: str | None
    target_questions: int
    blueprint_ids: list[str]
    generated_question_ids: list[str]
    accepted_question_ids: list[str]
    rejected_question_ids: list[str]
    replacement_count: int
    average_quality_score: float
    current_step: str
    progress: float
    error_code: str | None
    error_message: str | None


class JobStatusResponse(BaseModel):
    """Unified status payload representing background execution state."""

    job_id: uuid.UUID
    resource_type: str
    resource_id: uuid.UUID
    job_type: str
    status: str
    progress: float = Field(ge=0.0, le=100.0)
    current_step: str | None = None
    accepted_questions: int = 0
    target_questions: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    locked_at: datetime | None = None
    heartbeat_at: datetime | None = None
    state: dict[str, Any] = Field(default_factory=dict)
