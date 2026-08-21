"""Deterministic quota and distribution allocator using Largest Remainder Method."""

import math

from app.models.entities import Concept, Topic

DEFAULT_QUESTION_TYPE_DISTRIBUTION: dict[str, float] = {
    "mcq_single": 0.6,
    "short_answer": 0.4,
}

DEFAULT_DIFFICULTY_DISTRIBUTION: dict[str, float] = {
    "easy": 0.3,
    "medium": 0.5,
    "hard": 0.2,
}

DEFAULT_BLOOM_DISTRIBUTION: dict[str, float] = {
    "remember": 0.2,
    "understand": 0.3,
    "apply": 0.3,
    "analyze": 0.2,
}

NORMALIZE_QUESTION_TYPE_MAP: dict[str, str] = {
    "mcq": "mcq_single",
    "mcq_single": "mcq_single",
    "mcq_multi": "mcq_multi",
    "true_false": "true_false",
    "short_answer": "short_answer",
    "descriptive": "descriptive",
}


def largest_remainder_distribution(
    total_count: int,
    weights: dict[str, float],
    default_fallback: dict[str, float] | None = None,
) -> dict[str, int]:
    """Calculate exact integer allocations totaling total_count using Hamilton-Hare Largest Remainder method."""
    if total_count <= 0:
        return {}

    # 1. Clean and filter weights
    cleaned: dict[str, float] = {
        k: float(v) for k, v in weights.items() if v > 0.0
    }
    if not cleaned:
        cleaned = dict(default_fallback or DEFAULT_DIFFICULTY_DISTRIBUTION)

    total_weight = sum(cleaned.values())
    if total_weight <= 0.0:
        cleaned = dict(default_fallback or DEFAULT_DIFFICULTY_DISTRIBUTION)
        total_weight = sum(cleaned.values())

    # 2. Normalize weights
    normalized = {k: v / total_weight for k, v in cleaned.items()}

    # 3. Exact allocations & initial floor values
    exact = {k: total_count * weight for k, weight in normalized.items()}
    floors = {k: int(math.floor(val)) for k, val in exact.items()}
    remainders = {k: val - floors[k] for k, val in exact.items()}

    allocated_so_far = sum(floors.values())
    deficit = total_count - allocated_so_far

    # 4. Sort by remainder descending, then key alphabetically for stability
    sorted_by_remainder = sorted(
        remainders.keys(),
        key=lambda k: (remainders[k], k),
        reverse=True,
    )

    allocations = dict(floors)
    for i in range(deficit):
        target_key = sorted_by_remainder[i % len(sorted_by_remainder)]
        allocations[target_key] += 1

    return allocations


class SlotSkeleton:
    """Design container for a single question blueprint slot."""

    def __init__(
        self,
        sequence_number: int,
        topic: Topic,
        concept: Concept | None,
        question_type: str,
        difficulty: str,
        bloom_level: str,
    ) -> None:
        self.sequence_number = sequence_number
        self.topic = topic
        self.concept = concept
        self.question_type = question_type
        self.difficulty = difficulty
        self.bloom_level = bloom_level


def build_blueprint_slots(
    *,
    total_questions: int,
    topics: list[Topic],
    type_distribution: dict[str, float] | None = None,
    difficulty_distribution: dict[str, float] | None = None,
    bloom_distribution: dict[str, float] | None = None,
) -> list[SlotSkeleton]:
    """Deterministically allocate attributes across total_questions slots."""
    if not topics:
        raise ValueError("Cannot build blueprint slots without at least one topic.")

    # 1. Normalize and compute question type allocation
    raw_type_dist = type_distribution or DEFAULT_QUESTION_TYPE_DISTRIBUTION
    normalized_type_weights: dict[str, float] = {}
    for k, v in raw_type_dist.items():
        canonical_k = NORMALIZE_QUESTION_TYPE_MAP.get(k.lower(), k.lower())
        normalized_type_weights[canonical_k] = (
            normalized_type_weights.get(canonical_k, 0.0) + float(v)
        )

    type_counts = largest_remainder_distribution(
        total_questions,
        normalized_type_weights,
        DEFAULT_QUESTION_TYPE_DISTRIBUTION,
    )

    # 2. Compute difficulty allocation
    diff_counts = largest_remainder_distribution(
        total_questions,
        difficulty_distribution or DEFAULT_DIFFICULTY_DISTRIBUTION,
        DEFAULT_DIFFICULTY_DISTRIBUTION,
    )

    # 3. Compute Bloom cognitive level allocation
    bloom_counts = largest_remainder_distribution(
        total_questions,
        bloom_distribution or DEFAULT_BLOOM_DISTRIBUTION,
        DEFAULT_BLOOM_DISTRIBUTION,
    )

    # 4. Compute Topic allocation weighted by importance and concept coverage
    topic_weights: dict[str, float] = {}
    topic_lookup: dict[str, Topic] = {}
    for t in topics:
        t_id_str = str(t.id)
        topic_lookup[t_id_str] = t
        base_importance = float(t.importance_score) if t.importance_score else 0.5
        concepts_bonus = 1.0 + (0.2 * len(t.concepts))
        topic_weights[t_id_str] = max(0.1, base_importance * concepts_bonus)

    topic_counts = largest_remainder_distribution(
        total_questions,
        topic_weights,
    )

    # 5. Expand individual attribute pools
    type_pool: list[str] = []
    for q_type, count in type_counts.items():
        type_pool.extend([q_type] * count)

    diff_pool: list[str] = []
    for diff, count in diff_counts.items():
        diff_pool.extend([diff] * count)

    bloom_pool: list[str] = []
    for bloom, count in bloom_counts.items():
        bloom_pool.extend([bloom] * count)

    topic_slot_list: list[Topic] = []
    for t_id_str, count in topic_counts.items():
        topic_obj = topic_lookup[t_id_str]
        topic_slot_list.extend([topic_obj] * count)

    # 6. Assemble slots with stable round-robin concept assignment
    slots: list[SlotSkeleton] = []
    for seq in range(1, total_questions + 1):
        idx = seq - 1
        curr_topic = topic_slot_list[idx]
        assigned_concept: Concept | None = None
        if curr_topic.concepts:
            concept_idx = idx % len(curr_topic.concepts)
            assigned_concept = curr_topic.concepts[concept_idx]

        slot = SlotSkeleton(
            sequence_number=seq,
            topic=curr_topic,
            concept=assigned_concept,
            question_type=type_pool[idx],
            difficulty=diff_pool[idx],
            bloom_level=bloom_pool[idx],
        )
        slots.append(slot)

    return slots
