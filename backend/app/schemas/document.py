"""Pydantic schemas for document ingestion, status, and chunk extraction."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DocumentInitiateRequest(BaseModel):
    """Payload for initiating a private document upload."""

    original_filename: str = Field(..., min_length=1, max_length=255)
    declared_mime_type: str = Field(default="application/pdf", min_length=1)
    size_bytes: int = Field(..., gt=0, description="File size in bytes")


class DocumentInitiateResponse(BaseModel):
    """Response containing created document ID and target storage path."""

    document_id: uuid.UUID
    storage_path: str
    upload_bucket: str = "source-documents"


class DocumentCompleteRequest(BaseModel):
    """Payload to confirm upload completion."""

    document_id: uuid.UUID | None = None


class DocumentResponseData(BaseModel):
    """Document metadata and status representation."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    original_filename: str
    storage_path: str
    mime_type: str
    size_bytes: int
    checksum: str | None = None
    status: str
    page_count: int | None = None
    word_count: int | None = None
    language: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("metadata", mode="before")
    @classmethod
    def coerce_none_metadata(cls, v: Any) -> dict[str, Any]:
        if v is None or not isinstance(v, dict):
            return {}
        return v


class DocumentChunkData(BaseModel):
    """Structured document chunk representation."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_start: int
    page_end: int
    section: str | None = None
    chapter: str | None = None
    token_count: int
    char_count: int
    content_hash: str
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_")

    @field_validator("metadata", mode="before")
    @classmethod
    def coerce_none_metadata(cls, v: Any) -> dict[str, Any]:
        if v is None or not isinstance(v, dict):
            return {}
        return v
