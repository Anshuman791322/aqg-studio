"""Knowledge Retrieval & Analysis Agent for structured semantic parsing and pedagogical mapping."""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.knowledge.merger import consolidate_knowledge_batches, sanitize_batch_analysis
from app.knowledge.schemas import KnowledgeAnalysis, KnowledgeBatchAnalysis
from app.llm.base import LLMProvider
from app.llm.factory import get_llm_gateway
from app.llm.schemas import ChatMessage
from app.models.entities import Concept, Document, DocumentChunk, LearningObjective, Topic
from app.prompts.knowledge import (
    KNOWLEDGE_EXTRACTION_SYSTEM_PROMPT,
    build_knowledge_batch_user_prompt,
)

logger = get_logger("aqg.agents.knowledge")


class KnowledgeAnalysisAgent:
    """Agent responsible for analyzing document chunks and constructing structured pedagogical knowledge models."""

    def __init__(self, llm_provider: LLMProvider | None = None) -> None:
        self.llm = llm_provider or get_llm_gateway()

    def _create_chunk_batches(
        self, chunks: list[DocumentChunk], max_tokens_per_batch: int = 2500
    ) -> list[list[DocumentChunk]]:
        """Partition document chunks into bounded token batches."""
        if not chunks:
            return []

        batches: list[list[DocumentChunk]] = []
        current_batch: list[DocumentChunk] = []
        current_tokens = 0

        for chunk in chunks:
            chunk_tokens = chunk.token_count or len(chunk.content.split())
            if current_batch and (current_tokens + chunk_tokens > max_tokens_per_batch):
                batches.append(current_batch)
                current_batch = [chunk]
                current_tokens = chunk_tokens
            else:
                current_batch.append(chunk)
                current_tokens += chunk_tokens

        if current_batch:
            batches.append(current_batch)

        return batches

    async def analyze_document(
        self,
        session: AsyncSession,
        *,
        document_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> KnowledgeAnalysis:
        """Run map-and-reduce knowledge analysis over document chunks and persist results."""
        logger.info(
            "Beginning knowledge analysis for document",
            extra={"document_id": str(document_id), "user_id": str(user_id)},
        )

        # 1. Fetch document and chunks scoped by user_id
        doc_stmt = select(Document).where(
            Document.id == document_id, Document.user_id == user_id
        )
        doc_res = await session.execute(doc_stmt)
        document = doc_res.scalar_one_or_none()
        if not document:
            raise ValueError(f"Document {document_id} not found for user {user_id}")

        chunks_stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.document_id == document_id,
                DocumentChunk.user_id == user_id,
            )
            .order_by(DocumentChunk.chunk_index.asc())
        )
        chunks_res = await session.execute(chunks_stmt)
        chunks = list(chunks_res.scalars().all())

        if not chunks:
            raise ValueError(f"Document {document_id} has no processed chunks to analyze.")

        # 2. Partition chunks into bounded analysis batches
        batches = self._create_chunk_batches(chunks)
        batch_results: list[KnowledgeBatchAnalysis] = []
        accumulated_metadata: dict[str, Any] = {
            "provider": self.llm.provider_name,
            "batches_count": len(batches),
            "total_chunks": len(chunks),
        }

        # 3. Map Phase: Extract knowledge from each chunk batch
        for b_idx, batch in enumerate(batches):
            batch_valid_ids = {c.id for c in batch}
            chunk_dicts = [
                {
                    "id": c.id,
                    "chunk_index": c.chunk_index,
                    "section": c.section,
                    "content": c.content,
                }
                for c in batch
            ]

            user_prompt = build_knowledge_batch_user_prompt(chunk_dicts)
            messages = [
                ChatMessage(role="system", content=KNOWLEDGE_EXTRACTION_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ]

            logger.info(
                f"Analyzing batch {b_idx + 1}/{len(batches)} ({len(batch)} chunks)",
                extra={"document_id": str(document_id), "batch_index": b_idx},
            )

            raw_batch_analysis, usage = await self.llm.complete_structured(
                messages,
                response_model=KnowledgeBatchAnalysis,
                temperature=0.2,
            )

            # 4. Sanitize extracted chunk IDs against batch boundaries
            sanitized_batch = sanitize_batch_analysis(raw_batch_analysis, batch_valid_ids)
            batch_results.append(sanitized_batch)

        # 5. Reduce Phase: Consolidate topics, concepts, facts, and objectives
        consolidated = consolidate_knowledge_batches(
            document_id=document_id,
            batches=batch_results,
            provider_metadata=accumulated_metadata,
        )

        # 6. Idempotent Persistence: Clean old records and persist new knowledge model
        await session.execute(
            delete(Topic).where(
                Topic.document_id == document_id, Topic.user_id == user_id
            )
        )
        await session.execute(
            delete(LearningObjective).where(
                LearningObjective.document_id == document_id,
                LearningObjective.user_id == user_id,
            )
        )

        # Persist Topics & Concepts
        topic_name_to_id: dict[str, uuid.UUID] = {}
        for t_schema in consolidated.topics:
            topic_entity = Topic(
                id=uuid.uuid4(),
                document_id=document_id,
                user_id=user_id,
                name=t_schema.name,
                description=t_schema.description,
                importance_score=Decimal(str(round(t_schema.importance_score, 2))),
                metadata_={
                    "order_index": t_schema.order_index,
                    "source_chunk_ids": [str(cid) for cid in t_schema.source_chunk_ids],
                },
            )
            session.add(topic_entity)
            await session.flush()
            topic_name_to_id[t_schema.name.lower().strip()] = topic_entity.id

            for c_schema in t_schema.concepts:
                concept_entity = Concept(
                    id=uuid.uuid4(),
                    topic_id=topic_entity.id,
                    document_id=document_id,
                    user_id=user_id,
                    name=c_schema.name,
                    definition=c_schema.definition,
                    difficulty=c_schema.difficulty,
                    metadata_={
                        "importance_score": c_schema.importance_score,
                        "source_chunk_ids": [str(cid) for cid in c_schema.source_chunk_ids],
                    },
                )
                session.add(concept_entity)

        # Persist Learning Objectives
        for o_schema in consolidated.learning_objectives:
            linked_topic_id = (
                topic_name_to_id.get(o_schema.topic_name.lower().strip())
                if o_schema.topic_name
                else None
            )
            obj_entity = LearningObjective(
                id=uuid.uuid4(),
                document_id=document_id,
                topic_id=linked_topic_id,
                user_id=user_id,
                bloom_level=o_schema.bloom_level,
                description=o_schema.description,
                metadata_={"source_chunk_ids": [str(cid) for cid in o_schema.source_chunk_ids]},
            )
            session.add(obj_entity)

        # Update Document Metadata
        doc_meta = dict(document.metadata_ or {})
        doc_meta["knowledge_analysis"] = {
            "summary": consolidated.summary,
            "total_topics": consolidated.total_topics,
            "total_concepts": consolidated.total_concepts,
            "total_objectives": consolidated.total_objectives,
            "analysis_version": consolidated.analysis_version,
            "provider_metadata": consolidated.provider_metadata,
        }
        document.metadata_ = doc_meta

        await session.commit()

        logger.info(
            "Knowledge analysis successfully completed and persisted",
            extra={
                "document_id": str(document_id),
                "topics_count": consolidated.total_topics,
                "concepts_count": consolidated.total_concepts,
                "objectives_count": consolidated.total_objectives,
            },
        )

        return consolidated
