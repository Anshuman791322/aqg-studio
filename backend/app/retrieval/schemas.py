"""Schemas for RAG chunk retrieval and hybrid search."""

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RetrievalMode = Literal["hybrid", "vector", "lexical"]


class RetrievedChunk(BaseModel):
    """Normalized retrieved document chunk with relevance scoring."""

    model_config = ConfigDict(extra="ignore")

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    chunk_index: int
    content: str
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    chapter: str | None = None
    token_count: int = 0
    similarity: float = 0.0
    lexical_rank: float = 0.0
    score: float = 0.0
    retrieval_mode: RetrievalMode = "hybrid"


class RetrievalRequest(BaseModel):
    """Payload for retrieving document chunks."""

    model_config = ConfigDict(extra="ignore")

    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    section_filter: str | None = None
    alpha: float = Field(default=0.5, ge=0.0, le=1.0)


class RetrievalResponse(BaseModel):
    """Response envelope for chunk retrieval."""

    model_config = ConfigDict(extra="ignore")

    document_id: uuid.UUID
    query: str
    total_retrieved: int
    chunks: list[RetrievedChunk]
