"""Pydantic schemas for Knowledge Analysis and extraction."""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

BloomLevel = Literal["remember", "understand", "apply", "analyze", "evaluate", "create"]
DifficultyLevel = Literal["easy", "medium", "hard"]


class ConceptSchema(BaseModel):
    """Extracted pedagogical concept definition."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=200)
    definition: str = Field(..., min_length=5)
    importance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    difficulty: DifficultyLevel = Field(default="medium")
    source_chunk_ids: list[uuid.UUID] = Field(..., min_length=1)


class KeyFactSchema(BaseModel):
    """Extracted key fact, definition, or formula."""

    model_config = ConfigDict(extra="ignore")

    fact: str = Field(..., min_length=5)
    importance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    source_chunk_ids: list[uuid.UUID] = Field(..., min_length=1)


class TopicSchema(BaseModel):
    """Extracted topic and associated concepts."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    importance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    order_index: int = Field(default=0, ge=0)
    concepts: list[ConceptSchema] = Field(default_factory=list)
    source_chunk_ids: list[uuid.UUID] = Field(..., min_length=1)


class LearningObjectiveSchema(BaseModel):
    """Extracted learning objective aligned with Bloom's taxonomy."""

    model_config = ConfigDict(extra="ignore")

    bloom_level: BloomLevel
    description: str = Field(..., min_length=10)
    topic_name: str | None = None
    source_chunk_ids: list[uuid.UUID] = Field(..., min_length=1)


class KnowledgeBatchAnalysis(BaseModel):
    """Raw structured extraction response from LLM for a chunk batch."""

    model_config = ConfigDict(extra="ignore")

    topics: list[TopicSchema] = Field(default_factory=list)
    key_facts: list[KeyFactSchema] = Field(default_factory=list)
    learning_objectives: list[LearningObjectiveSchema] = Field(default_factory=list)


class KnowledgeAnalysis(BaseModel):
    """Consolidated document-level knowledge analysis representation."""

    model_config = ConfigDict(extra="ignore")

    document_id: uuid.UUID
    analysis_version: str = "1.0.0"
    summary: str = ""
    estimated_difficulty: DifficultyLevel = "medium"
    topics: list[TopicSchema] = Field(default_factory=list)
    learning_objectives: list[LearningObjectiveSchema] = Field(default_factory=list)
    key_facts: list[KeyFactSchema] = Field(default_factory=list)
    total_topics: int = 0
    total_concepts: int = 0
    total_objectives: int = 0
    provider_metadata: dict[str, Any] = Field(default_factory=dict)
