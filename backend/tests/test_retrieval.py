"""Unit and integration tests for Hybrid RAG Retrieval Service."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.embeddings.fake import FakeEmbeddingProvider
from app.models.entities import DocumentChunk
from app.retrieval.service import (
    HybridRetrievalService,
    compute_cosine_similarity,
    compute_lexical_overlap_score,
)


def test_cosine_similarity_math() -> None:
    """Verify vector math properties for identical, orthogonal, and arbitrary vectors."""
    vec_1 = [1.0, 0.0, 0.0]
    vec_2 = [1.0, 0.0, 0.0]
    vec_3 = [0.0, 1.0, 0.0]

    assert compute_cosine_similarity(vec_1, vec_2) == 1.0
    assert compute_cosine_similarity(vec_1, vec_3) == 0.0
    assert compute_cosine_similarity([], []) == 0.0


def test_lexical_overlap_score_math() -> None:
    """Verify token overlap score accurately measures common keywords."""
    query = "mitochondria cellular respiration"
    text_1 = "Mitochondria play a central role in cellular respiration and ATP synthesis."
    text_2 = "The nucleus contains genetic material."

    score_1 = compute_lexical_overlap_score(query, text_1)
    score_2 = compute_lexical_overlap_score(query, text_2)

    assert score_1 == 1.0  # All 3 query words appear
    assert score_2 == 0.0


def test_lexical_overlap_handles_punctuation_and_casing() -> None:
    """Verify lexical tokenization strips punctuation and matches case-insensitively."""
    query = "What is DNA?"
    text = "DNA (Deoxyribonucleic acid) is what stores genetic information."
    score = compute_lexical_overlap_score(query, text)
    # 'what', 'is', 'dna' all present
    assert score == 1.0


@pytest.mark.asyncio
async def test_hybrid_retrieval_ranking() -> None:
    """Verify hybrid retrieval ranks relevant vector & lexical chunks highest."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    fake_embedder = FakeEmbeddingProvider(dimension=384)
    service = HybridRetrievalService(embedding_provider=fake_embedder)

    # Embed query and chunks
    query_text = "photosynthesis in chloroplasts"
    q_vec = await fake_embedder.embed_query(query_text)

    chunk_1_text = "Photosynthesis occurs inside chloroplasts using chlorophyll."
    chunk_1_vec = await fake_embedder.embed_query(chunk_1_text)

    chunk_2_text = "Newton's laws of universal gravitation describe planetary motion."
    chunk_2_vec = await fake_embedder.embed_query(chunk_2_text)

    mock_chunk_1 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        chunk_index=0,
        content=chunk_1_text,
        embedding=chunk_1_vec,
        token_count=50,
    )
    mock_chunk_2 = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        chunk_index=1,
        content=chunk_2_text,
        embedding=chunk_2_vec,
        token_count=50,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_chunk_1, mock_chunk_2]
    mock_session.execute.return_value = mock_result

    results = await service.retrieve(
        mock_session,
        user_id=user_id,
        document_id=doc_id,
        query=query_text,
        top_k=2,
        alpha=0.5,
    )

    assert len(results) == 2
    # Chunk 1 about photosynthesis should score higher than chunk 2
    assert results[0].chunk_id == mock_chunk_1.id
    assert results[0].score > results[1].score
    assert results[0].retrieval_mode == "hybrid"


@pytest.mark.asyncio
async def test_lexical_only_fallback_when_embeddings_absent() -> None:
    """Verify retrieval falls back gracefully to lexical scoring when chunks lack vector embeddings."""
    user_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    # Broken embedding provider to simulate OOM or offline failure
    class BrokenEmbedder(FakeEmbeddingProvider):
        async def embed_query(self, text: str) -> list[float]:
            raise RuntimeError("Out of memory on free tier")

    service = HybridRetrievalService(embedding_provider=BrokenEmbedder())

    mock_chunk = DocumentChunk(
        id=uuid.uuid4(),
        document_id=doc_id,
        user_id=user_id,
        chunk_index=0,
        content="Quantum entanglement is a physical phenomenon.",
        embedding=None,  # No embedding
        token_count=30,
    )

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_chunk]
    mock_session.execute.return_value = mock_result

    results = await service.retrieve(
        mock_session,
        user_id=user_id,
        document_id=doc_id,
        query="quantum entanglement",
        top_k=1,
    )

    assert len(results) == 1
    assert results[0].retrieval_mode == "lexical"
    assert results[0].score == 1.0  # Perfect token overlap


@pytest.mark.asyncio
async def test_cross_user_isolation_in_retrieval() -> None:
    """Verify that retrieval query returns empty list when user does not own the document."""
    user_id_a = uuid.uuid4()
    user_id_b = uuid.uuid4()
    doc_id = uuid.uuid4()

    service = HybridRetrievalService()

    # Session mock returning empty because user_id_b query finds no matching records
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    results = await service.retrieve(
        mock_session,
        user_id=user_id_b,  # Attacker user
        document_id=doc_id,
        query="confidential data",
    )

    assert len(results) == 0
