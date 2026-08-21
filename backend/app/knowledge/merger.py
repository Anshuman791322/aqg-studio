"""Deterministic consolidation, deduplication, and reduction for knowledge extraction."""

import uuid
from collections.abc import Sequence
from typing import Any

from app.knowledge.schemas import (
    ConceptSchema,
    KeyFactSchema,
    KnowledgeAnalysis,
    KnowledgeBatchAnalysis,
    LearningObjectiveSchema,
    TopicSchema,
)


def filter_valid_chunk_ids(
    source_ids: list[uuid.UUID], valid_ids: set[uuid.UUID]
) -> list[uuid.UUID]:
    """Filter out hallucinated or out-of-batch chunk UUIDs."""
    return [cid for cid in source_ids if cid in valid_ids]


def sanitize_batch_analysis(
    batch: KnowledgeBatchAnalysis, valid_chunk_ids: set[uuid.UUID]
) -> KnowledgeBatchAnalysis:
    """Validate and sanitize all source chunk IDs in a batch extraction."""
    sanitized_topics: list[TopicSchema] = []
    for topic in batch.topics:
        valid_t_ids = filter_valid_chunk_ids(topic.source_chunk_ids, valid_chunk_ids)
        if not valid_t_ids:
            # If topic itself has no valid IDs, try to inherit from its concepts
            inherited_ids = set()
            for c in topic.concepts:
                inherited_ids.update(filter_valid_chunk_ids(c.source_chunk_ids, valid_chunk_ids))
            valid_t_ids = list(inherited_ids)

        if not valid_t_ids:
            continue

        sanitized_concepts: list[ConceptSchema] = []
        for concept in topic.concepts:
            valid_c_ids = filter_valid_chunk_ids(concept.source_chunk_ids, valid_chunk_ids)
            if not valid_c_ids:
                # Inherit from parent topic if valid
                valid_c_ids = list(valid_t_ids)
            sanitized_concepts.append(
                ConceptSchema(
                    name=concept.name.strip(),
                    definition=concept.definition.strip(),
                    importance_score=max(0.0, min(1.0, concept.importance_score)),
                    difficulty=concept.difficulty,
                    source_chunk_ids=valid_c_ids,
                )
            )

        sanitized_topics.append(
            TopicSchema(
                name=topic.name.strip(),
                description=topic.description.strip() if topic.description else None,
                importance_score=max(0.0, min(1.0, topic.importance_score)),
                order_index=topic.order_index,
                concepts=sanitized_concepts,
                source_chunk_ids=valid_t_ids,
            )
        )

    sanitized_objectives: list[LearningObjectiveSchema] = []
    for obj in batch.learning_objectives:
        valid_o_ids = filter_valid_chunk_ids(obj.source_chunk_ids, valid_chunk_ids)
        if valid_o_ids:
            sanitized_objectives.append(
                LearningObjectiveSchema(
                    bloom_level=obj.bloom_level,
                    description=obj.description.strip(),
                    topic_name=obj.topic_name.strip() if obj.topic_name else None,
                    source_chunk_ids=valid_o_ids,
                )
            )

    sanitized_facts: list[KeyFactSchema] = []
    for fact in batch.key_facts:
        valid_f_ids = filter_valid_chunk_ids(fact.source_chunk_ids, valid_chunk_ids)
        if valid_f_ids:
            sanitized_facts.append(
                KeyFactSchema(
                    fact=fact.fact.strip(),
                    importance_score=max(0.0, min(1.0, fact.importance_score)),
                    source_chunk_ids=valid_f_ids,
                )
            )

    return KnowledgeBatchAnalysis(
        topics=sanitized_topics,
        learning_objectives=sanitized_objectives,
        key_facts=sanitized_facts,
    )


def consolidate_knowledge_batches(
    document_id: uuid.UUID,
    batches: Sequence[KnowledgeBatchAnalysis],
    provider_metadata: dict[str, str | int | float | None] | None = None,
) -> KnowledgeAnalysis:
    """Consolidate multiple batch extractions into a single coherent KnowledgeAnalysis."""
    topic_map: dict[str, dict[str, Any]] = {}
    objective_map: dict[tuple[str, str], LearningObjectiveSchema] = {}
    fact_map: dict[str, KeyFactSchema] = {}

    order_counter = 0

    for batch in batches:
        for topic in batch.topics:
            norm_key = topic.name.lower().strip()
            if norm_key not in topic_map:
                topic_map[norm_key] = {
                    "name": topic.name.strip(),
                    "description": topic.description,
                    "importance_score": topic.importance_score,
                    "order_index": order_counter,
                    "source_chunk_ids": set(topic.source_chunk_ids),
                    "concepts": {},
                }
                order_counter += 1
            else:
                existing = topic_map[norm_key]
                existing["importance_score"] = max(
                    existing["importance_score"], topic.importance_score
                )
                existing["source_chunk_ids"].update(topic.source_chunk_ids)
                if not existing["description"] and topic.description:
                    existing["description"] = topic.description

            # Merge concepts under topic
            concept_store = topic_map[norm_key]["concepts"]
            for concept in topic.concepts:
                c_norm_key = concept.name.lower().strip()
                if c_norm_key not in concept_store:
                    concept_store[c_norm_key] = {
                        "name": concept.name.strip(),
                        "definition": concept.definition.strip(),
                        "importance_score": concept.importance_score,
                        "difficulty": concept.difficulty,
                        "source_chunk_ids": set(concept.source_chunk_ids),
                    }
                else:
                    c_existing = concept_store[c_norm_key]
                    c_existing["importance_score"] = max(
                        c_existing["importance_score"], concept.importance_score
                    )
                    c_existing["source_chunk_ids"].update(concept.source_chunk_ids)
                    if len(concept.definition) > len(c_existing["definition"]):
                        c_existing["definition"] = concept.definition.strip()

        for obj in batch.learning_objectives:
            obj_key = (obj.bloom_level, obj.description.lower().strip())
            if obj_key not in objective_map:
                objective_map[obj_key] = obj
            else:
                merged_ids = set(objective_map[obj_key].source_chunk_ids).union(
                    obj.source_chunk_ids
                )
                objective_map[obj_key].source_chunk_ids = list(merged_ids)

        for fact in batch.key_facts:
            f_key = fact.fact.lower().strip()
            if f_key not in fact_map:
                fact_map[f_key] = fact
            else:
                merged_ids = set(fact_map[f_key].source_chunk_ids).union(fact.source_chunk_ids)
                fact_map[f_key].source_chunk_ids = list(merged_ids)
                fact_map[f_key].importance_score = max(
                    fact_map[f_key].importance_score, fact.importance_score
                )

    # Reassemble topics
    final_topics: list[TopicSchema] = []
    total_concepts = 0

    for t_data in sorted(topic_map.values(), key=lambda x: x["order_index"]):
        concepts_list: list[ConceptSchema] = []
        for c_data in t_data["concepts"].values():
            concepts_list.append(
                ConceptSchema(
                    name=c_data["name"],
                    definition=c_data["definition"],
                    importance_score=c_data["importance_score"],
                    difficulty=c_data["difficulty"],
                    source_chunk_ids=sorted(c_data["source_chunk_ids"]),
                )
            )
        total_concepts += len(concepts_list)

        final_topics.append(
            TopicSchema(
                name=t_data["name"],
                description=t_data["description"],
                importance_score=t_data["importance_score"],
                order_index=t_data["order_index"],
                concepts=concepts_list,
                source_chunk_ids=sorted(t_data["source_chunk_ids"]),
            )
        )

    final_objectives = list(objective_map.values())
    final_facts = list(fact_map.values())

    # Build summary
    summary = (
        f"Document analyzed into {len(final_topics)} core pedagogical topics, "
        f"{total_concepts} distinct concepts, and {len(final_objectives)} learning objectives."
    )

    return KnowledgeAnalysis(
        document_id=document_id,
        analysis_version="1.0.0",
        summary=summary,
        estimated_difficulty="medium",
        topics=final_topics,
        learning_objectives=final_objectives,
        key_facts=final_facts,
        total_topics=len(final_topics),
        total_concepts=total_concepts,
        total_objectives=len(final_objectives),
        provider_metadata=provider_metadata or {},
    )
