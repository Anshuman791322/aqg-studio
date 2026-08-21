"""Hybrid Vector & Lexical RAG Retrieval Service."""

import math
import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider
from app.embeddings.factory import get_embedding_provider
from app.models.entities import DocumentChunk
from app.retrieval.schemas import RetrievedChunk

logger = get_logger("aqg.retrieval.service")


def compute_lexical_overlap_score(query: str, content: str) -> float:
    """Compute normalized token overlap score between query and chunk content."""
    q_words = set(query.lower().split())
    if not q_words:
        return 0.0
    c_words = set(content.lower().split())
    if not c_words:
        return 0.0
    intersection = q_words.intersection(c_words)
    return len(intersection) / len(q_words)


def compute_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


class HybridRetrievalService:
    """Service orchestrating vector cosine search, PostgreSQL full-text ranking, and hybrid fusion."""

    def __init__(self, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def retrieve(
        self,
        session: AsyncSession,
        *,
        user_id: uuid.UUID,
        document_id: uuid.UUID,
        query: str,
        top_k: int = 5,
        section_filter: str | None = None,
        alpha: float = 0.5,
    ) -> list[RetrievedChunk]:
        """Execute scoped hybrid retrieval over document chunks."""
        logger.info(
            "Executing hybrid retrieval query",
            extra={
                "user_id": str(user_id),
                "document_id": str(document_id),
                "top_k": top_k,
                "alpha": alpha,
                "query_len": len(query),
            },
        )

        # 1. Fetch chunks strictly scoped to user_id and document_id
        stmt = (
            select(DocumentChunk)
            .where(
                DocumentChunk.user_id == user_id,
                DocumentChunk.document_id == document_id,
            )
        )
        if section_filter:
            stmt = stmt.where(DocumentChunk.section == section_filter)

        chunks_res = await session.execute(stmt)
        chunks: Sequence[DocumentChunk] = chunks_res.scalars().all()

        if not chunks:
            return []

        # 2. Generate query vector embedding if available
        query_vector: list[float] | None = None
        retrieval_mode = "hybrid"

        try:
            query_vector = await self.embedding_provider.embed_query(query)
        except Exception as e:
            logger.warning(
                f"Embedding generation failed ({str(e)}), falling back to lexical-only retrieval.",
                extra={"document_id": str(document_id)},
            )
            retrieval_mode = "lexical"

        scored_results: list[RetrievedChunk] = []

        for chunk in chunks:
            sim = 0.0
            if query_vector is not None and chunk.embedding is not None:
                sim = compute_cosine_similarity(query_vector, list(chunk.embedding))

            lex = compute_lexical_overlap_score(query, chunk.content)

            if query_vector is not None and chunk.embedding is not None:
                final_score = (alpha * sim) + ((1.0 - alpha) * lex)
                mode = "hybrid"
            else:
                final_score = lex
                mode = "lexical"

            scored_results.append(
                RetrievedChunk(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    section=chunk.section,
                    chapter=chunk.chapter,
                    token_count=chunk.token_count,
                    similarity=round(sim, 4),
                    lexical_rank=round(lex, 4),
                    score=round(final_score, 4),
                    retrieval_mode=mode,
                )
            )

        # Sort by score descending, then chunk_index ascending
        scored_results.sort(key=lambda r: (r.score, -r.chunk_index), reverse=True)
        return scored_results[:top_k]
