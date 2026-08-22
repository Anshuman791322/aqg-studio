"""Duplicate detection and resolution engine (exact normalized, lexical Jaccard, embedding cosine)."""

import math
import re
import uuid
from typing import Literal

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.embeddings.base import EmbeddingProvider
from app.models.entities import Question

logger = get_logger("aqg.evaluation.duplication")

PUNCT_REGEX = re.compile(r"[^\w\s]", re.UNICODE)
WORD_REGEX = re.compile(r"\w+", re.UNICODE)


class DuplicateMatch(BaseModel):
    """Pairwise duplicate detection result."""

    question_id: uuid.UUID
    duplicate_with_id: uuid.UUID
    similarity_score: float = Field(ge=0.0, le=1.0)
    match_type: Literal["exact_normalized", "lexical_jaccard", "embedding_cosine"]


def normalize_text(text: str) -> str:
    """Normalize text into lowercased token sequence without punctuation."""
    if not text:
        return ""
    cleaned = PUNCT_REGEX.sub(" ", text.lower())
    return " ".join(cleaned.split())


def is_exact_normalized_duplicate(text1: str, text2: str) -> bool:
    """Return True if both strings normalize to identical token sequences."""
    n1 = normalize_text(text1)
    n2 = normalize_text(text2)
    return bool(n1 and n2 and n1 == n2)


def compute_jaccard_similarity(text1: str, text2: str) -> float:
    """Compute Jaccard token overlap between two strings (0.0 to 1.0)."""
    words1 = set(WORD_REGEX.findall(text1.lower()))
    words2 = set(WORD_REGEX.findall(text2.lower()))
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    if not union:
        return 0.0
    return len(intersection) / len(union)


def compute_vector_cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


async def detect_assessment_duplicates(
    questions: list[Question],
    threshold: float = 0.90,
    embedding_provider: EmbeddingProvider | None = None,
) -> list[DuplicateMatch]:
    """Scan all question pairs in an assessment for exact, lexical, or semantic duplication."""
    if len(questions) < 2:
        return []

    duplicates: list[DuplicateMatch] = []
    seen_pairs: set[tuple[uuid.UUID, uuid.UUID]] = set()

    # Pre-embed question texts if embedding provider is supplied
    embeddings_map: dict[uuid.UUID, list[float]] = {}
    if embedding_provider is not None:
        try:
            texts = [q.question_text for q in questions]
            vectors = await embedding_provider.embed_texts(texts)
            for q, vec in zip(questions, vectors, strict=True):
                embeddings_map[q.id] = vec
        except Exception as exc:
            logger.warning(
                f"Embedding generation for duplicate detection failed ({exc}); falling back to lexical matching."
            )

    for i in range(len(questions)):
        for j in range(i + 1, len(questions)):
            q1 = questions[i]
            q2 = questions[j]

            pair_key = (min(q1.id, q2.id), max(q1.id, q2.id))
            if pair_key in seen_pairs:
                continue

            # 1. Exact Normalized Check
            if is_exact_normalized_duplicate(q1.question_text, q2.question_text):
                seen_pairs.add(pair_key)
                duplicates.append(
                    DuplicateMatch(
                        question_id=q1.id,
                        duplicate_with_id=q2.id,
                        similarity_score=1.0,
                        match_type="exact_normalized",
                    )
                )
                continue

            # 2. Lexical Jaccard Similarity
            jaccard_score = compute_jaccard_similarity(q1.question_text, q2.question_text)
            if jaccard_score >= threshold:
                seen_pairs.add(pair_key)
                duplicates.append(
                    DuplicateMatch(
                        question_id=q1.id,
                        duplicate_with_id=q2.id,
                        similarity_score=round(jaccard_score, 4),
                        match_type="lexical_jaccard",
                    )
                )
                continue

            # 3. Embedding Cosine Similarity
            vec1 = embeddings_map.get(q1.id)
            vec2 = embeddings_map.get(q2.id)
            if vec1 and vec2:
                cos_sim = compute_vector_cosine_similarity(vec1, vec2)
                if cos_sim >= threshold:
                    seen_pairs.add(pair_key)
                    duplicates.append(
                        DuplicateMatch(
                            question_id=q1.id,
                            duplicate_with_id=q2.id,
                            similarity_score=round(cos_sim, 4),
                            match_type="embedding_cosine",
                        )
                    )

    return duplicates


def resolve_duplicate_conflicts(
    duplicates: list[DuplicateMatch],
    questions_by_id: dict[uuid.UUID, Question],
) -> tuple[set[uuid.UUID], set[uuid.UUID]]:
    """Determine which duplicate questions to keep and which to discard/regenerate based on quality score."""
    keep_ids: set[uuid.UUID] = set()
    discard_ids: set[uuid.UUID] = set()

    for match in duplicates:
        q1 = questions_by_id.get(match.question_id)
        q2 = questions_by_id.get(match.duplicate_with_id)

        if not q1 or not q2:
            continue

        score1 = float(q1.quality_score or 0.0)
        score2 = float(q2.quality_score or 0.0)

        # Retain the candidate with higher quality score
        if score1 > score2:
            winner = q1.id
            loser = q2.id
        elif score2 > score1:
            winner = q2.id
            loser = q1.id
        else:
            # Tie breaker: earlier creation time or stable id
            if q1.created_at <= q2.created_at:
                winner = q1.id
                loser = q2.id
            else:
                winner = q2.id
                loser = q1.id

        if loser not in keep_ids:
            discard_ids.add(loser)
        keep_ids.add(winner)

    return keep_ids, discard_ids
