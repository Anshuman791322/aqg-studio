# Phase 6 Handoff: Knowledge Retrieval & Analysis Agent, Embeddings & Hybrid RAG

## Summary of Implementation
Phase 6 delivers the **Knowledge Retrieval & Analysis Agent**, multi-provider embedding subsystem, and user-scoped hybrid vector/lexical search for AQG Studio:

1. **Strict Knowledge Schemas (`backend/app/knowledge/schemas.py`)**:
   - `ConceptSchema`: `name`, `definition`, `importance_score` (0.0–1.0), `difficulty`, `source_chunk_ids` (must be >= 1).
   - `TopicSchema`: `name`, `description`, `importance_score`, `order_index`, `concepts`, `source_chunk_ids`.
   - `LearningObjectiveSchema`: `bloom_level` ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create'), `description`, `topic_name`, `source_chunk_ids`.
   - `KeyFactSchema`: `fact`, `importance_score`, `source_chunk_ids`.
   - `KnowledgeBatchAnalysis`: Structured output schema for chunk batch extractions.
   - `KnowledgeAnalysis`: Consolidated document-level pedagogical representation.

2. **Map-and-Reduce Knowledge Agent (`backend/app/agents/knowledge_agent.py`, `merger.py`)**:
   - Chunks partitioned into bounded token batches (~2,500 tokens).
   - LLM extraction prompt enforces anti-injection defenses (`<document_content>` boundaries, ignoring embedded instructions, strict source citations).
   - Sanitizer removes hallucinated chunk IDs outside batch boundaries.
   - Deterministic merger fuses equivalent topics and concepts, takes highest importance scores, and consolidates learning objectives.
   - Idempotent database persistence in PostgreSQL (`topics`, `concepts`, `learning_objectives`, and `document.metadata_`).

3. **Multi-Provider Embedding Abstraction (`backend/app/embeddings/`)**:
   - `EmbeddingProvider` abstract interface.
   - `FastEmbedProvider`: Lazy-loaded local ONNX embeddings (`BAAI/bge-small-en-v1.5`, 384 dimensions) with graceful low-memory fallbacks.
   - `NVIDIAEmbeddingProvider`: Client for NVIDIA NIM embeddings (`https://integrate.api.nvidia.com/v1/embeddings`).
   - `FakeEmbeddingProvider`: Deterministic unit vector provider based on text SHA-256 for unit tests.

4. **Hybrid RAG Retrieval Service (`backend/app/retrieval/`) & PostgreSQL Function**:
   - `HybridRetrievalService.retrieve(...)`: Scopes queries strictly to `user_id` and `document_id`.
   - Weighted score combining cosine vector similarity and lexical token overlap: `score = alpha * sim + (1 - alpha) * lex`.
   - Lexical fallback when embeddings are absent or unavailable.
   - Supabase migration `20260821000004_hybrid_search_function.sql` for native database execution.

5. **API Endpoints (`backend/app/api/v1/endpoints/documents.py`)**:
   - `POST /api/v1/documents/{id}/analyze`: Runs knowledge extraction agent and persists topics/concepts/objectives.
   - `GET /api/v1/documents/{id}/analysis`: Retrieves persisted pedagogical knowledge graph.
   - `POST /api/v1/documents/{id}/retrieve`: Publicly accessible, user-isolated chunk retrieval endpoint.

---

## Test Verification
- **Unit & Integration Tests**: 98 backend tests passing (`pytest` including 11 Knowledge Agent and Retrieval tests).
- **Static Analysis & Types**: Ruff (`0` errors), mypy (`0` errors across 63 source files).
- **Frontend Verification**: ESLint (`0` warnings/errors), TypeScript strict typecheck (`0` errors), Jest, and Next.js 15 production build compiling 9 routes.
