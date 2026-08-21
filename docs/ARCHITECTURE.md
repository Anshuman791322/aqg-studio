# AQG Studio - System Architecture & Engineering Design

## 1. Architectural Philosophy & Principles
AQG Studio is built as a **cohesive, modular monolith** comprising a single Next.js frontend application and a single FastAPI backend service. Rather than incurring the operational complexity and network latency of distributed microservices, the 6 specialized agents in AQG Studio are implemented as cleanly decoupled Python modules orchestrated through a stateful **LangGraph** execution graph.

### Core Architectural Tenets:
1. **Deterministic Foundations, Generative Intelligence**: Parsing, validation, chunking, math, counting, and format compliance are handled strictly by deterministic Python code. Generative LLMs are utilized solely for semantic analysis, creative item generation, and qualitative evaluation.
2. **Zero Paid Cloud Dependencies**: The system operates exclusively within free/community cloud tiers: Supabase (Postgres + pgvector + Auth + Storage), Vercel (Frontend), and Render (Backend).
3. **Resilient Multi-Provider Fallback**: If OpenRouter encounters rate limits, network outages, or model unavailability, the LangGraph execution runtime dynamically fails over to the NVIDIA NIM API with identical structured schema guarantees.
4. **Transparent Provenance**: Every artifact generated is anchored to deterministic document chunk IDs with verbatim source citations.

---

## 2. Global System Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLIENT / FRONTEND LAYER                            │
│                                                                             │
│   Next.js 15 (App Router) + TypeScript + Tailwind CSS                       │
│   - Document Upload & Extraction Viewer                                     │
│   - Interactive Blueprint Generator & Distribution Matrix                   │
│   - Real-Time Generation Streamer (Server-Sent Events)                      │
│   - Question Review Studio (Side-by-Side Source Citation Inspector)         │
│   - Multi-Format Export Center (PDF, DOCX, Moodle, QTI, JSON, CSV)          │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ HTTPS / WSS / SSE
                                       │ (Supabase JWT Bearer Auth)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                          FASTAPI BACKEND SERVICE                            │
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                      API Routing & Validation                       │   │
│   │  /api/v1/auth   /api/v1/documents   /api/v1/blueprints   /api/v1/job│   │
│   └──────────────────────────────────┬──────────────────────────────────┘   │
│                                      │                                      │
│   ┌──────────────────────────────────▼──────────────────────────────────┐   │
│   │              LangGraph Multi-Agent Orchestration Core               │   │
│   │                                                                     │   │
│   │  [1. Doc Processing] ──► [2. Knowledge Analysis] ──► [3. Planning] │   │
│   │                                                          │          │   │
│   │  [6. Output & Report] ◄── [5. Eval & Refine] ◄── [4. Generation] ◄┘  │   │
│   └─────────────────┬─────────────────────────────────┬─────────────────┘   │
│                     │                                 │                     │
│   ┌─────────────────▼──────────────┐   ┌──────────────▼─────────────────┐   │
│   │  LLM Provider Fallback Gateway │   │   Deterministic Engines        │   │
│   │  - Primary: OpenRouter         │   │   - PyMuPDF / python-docx      │   │
│   │  - Fallback: NVIDIA NIM API    │   │   - fastembed (BGE-small ONNX) │   │
│   └────────────────────────────────┘   └────────────────────────────────┘   │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ SQLAlchemy 2.0 (asyncpg)
                                       │ Supabase Storage API
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    SUPABASE MANAGED CLOUD PLATFORM                          │
│                                                                             │
│   - PostgreSQL 15+ with pgvector Extension (Vector Similarity Search)       │
│   - Supabase Auth (JWT verification & User Profiles)                        │
│   - Supabase Storage (Private encrypted buckets for uploaded docs & exports)│
│   - Row Level Security (RLS) enforcing strict multi-tenant isolation        │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The 6-Agent Sequential Pipeline Specification

The multi-agent workflow is modeled as a LangGraph `StateGraph` passing a typed `AssessmentJobState` payload across nodes.

```
                  ┌──────────────────────────────┐
                  │ 1. Document Processing Agent │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 2. Knowledge Analysis Agent  │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 3. Question Planning Agent   │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ pgvector RAG Chunk Retrieval │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 4. Question Generation Agent │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
        ┌─────────┤ 5. Evaluation & Refine Agent │◄────────┐
        │         └──────────────┬───────────────┘         │ (Iterative Refine)
        │                        │                         │ (Max 2 Attempts)
        │ (Passed Scorecard)     │ (Failed Scorecard)      │
        │                        └─────────────────────────┘
        ▼
┌──────────────────────────────┐
│ 6. Output & Report Agent     │
└──────────────┬───────────────┘
               │
               ▼
[Final Assessment Bundle + Quality Scorecard]
```

### Agent 1: Document Processing Agent
- **Purpose**: Ingests raw files (PDF, DOCX, PPTX, TXT), strips artifacts, normalizes typography, detects scanned image PDFs (deferring OCR), segments text by section/page/slide, and produces token-bounded chunks.
- **Implementation**: Pure deterministic Python (`pypdf`, `pymupdf`, `python-docx`, `python-pptx`, `tiktoken`).
- **Output**: Array of `DocumentChunk` records with character offsets, page/slide indices, and compute-ready text embeddings.

### Agent 2: Knowledge Retrieval & Analysis Agent
- **Purpose**: Analyzes the structural chunks to extract key concepts, domain vocabulary, conceptual dependencies, and topic distribution.
- **Implementation**: LLM semantic analyzer utilizing few-shot prompts with strict JSON schema outputs.
- **Output**: `KnowledgeMap` object containing prioritized topics, subtopics, prerequisite relationships, and difficulty indicators.

### Agent 3: Question Planning Agent
- **Purpose**: Formulates an assessment blueprint matching user specifications (target count, question types, difficulty ratio, Bloom taxonomy distribution).
- **Implementation**: Hybrid deterministic planner + LLM constraint solver. The deterministic module calculates exact quotas, while the LLM maps each question slot to a specific topic and cognitive objective.
- **Output**: `AssessmentBlueprint` containing individual `QuestionPlanItem` definitions.

### Agent 4: Question Generation Agent
- **Purpose**: Generates high-fidelity questions for each `QuestionPlanItem`. Executes cosine similarity queries against `pgvector` to isolate the 3–5 most relevant document chunks, constructs an anti-injection prompt, and generates structured JSON question objects.
- **Implementation**: Prompt-engineered LLM generator with Pydantic output parsing, citations, distractor rationales, and rubric definitions.
- **Output**: Draft `GeneratedQuestion` records with full provenance links.

### Agent 5: Evaluation & Refinement Agent
- **Purpose**: Implements an adversarial critique loop. Evaluates every drafted question across 5 dimensions:
  1. *Factual Groundedness* (checks against retrieved chunks; flags unsupported claims).
  2. *Stem Clarity* (identifies ambiguity or grammatical issues).
  3. *Distractor Plausibility* (ensures options are realistic and mutually exclusive).
  4. *Bloom Alignment* (verifies cognitive verbs match question task).
  5. *Fairness & Tone* (screens for unwanted bias).
- **Refinement Loop**: If a question scores < 4.0/5.0 aggregate or fails groundedness, the agent crafts targeted feedback annotations and routes the item back to Agent 4 for a regenerative pass (capped at 2 iterations).
- **Output**: Verified questions and comprehensive `QuestionEvaluationReport`.

### Agent 6: Output & Report Agent
- **Purpose**: Computes global assessment statistics, calculates overall quality scores, estimates assessment completion time, flags human-review recommendations, and compiles export packages.
- **Implementation**: Deterministic Python report aggregator and export builder.
- **Output**: Finalized assessment bundle, PDF/DOCX templates, and LMS-compatible export payloads.

---

## 4. LangGraph State Management

The core generation pipeline maintains an immutable state across all 6 agent nodes:

```python
from typing import TypedDict, List, Dict, Any, Optional

class AssessmentJobState(TypedDict):
    job_id: str
    user_id: str
    document_id: str
    raw_file_path: str
    file_type: str
    
    # Agent 1 Outputs
    total_pages: int
    is_scanned_pdf: bool
    chunks: List[Dict[str, Any]]
    
    # Agent 2 Outputs
    knowledge_map: Dict[str, Any]
    extracted_topics: List[str]
    
    # Agent 3 Outputs
    blueprint_id: str
    question_plans: List[Dict[str, Any]]
    
    # Agent 4 & 5 Outputs
    draft_questions: List[Dict[str, Any]]
    evaluated_questions: List[Dict[str, Any]]
    refinement_iterations: Dict[str, int]
    
    # Agent 6 Outputs
    final_scorecard: Dict[str, Any]
    export_manifest: Dict[str, Any]
    status: str
    error: Optional[str]
```

---

## 5. LLM Provider Fallback Gateway

To guarantee 99.9% pipeline reliability without relying on single-vendor uptime, all LLM calls are routed through a provider gateway:

```
                      ┌────────────────────────────┐
                      │    LLM Gateway Request     │
                      └─────────────┬──────────────┘
                                    │
                                    ▼
                      ┌────────────────────────────┐
                      │  Primary Provider:         │
                      │  OpenRouter API            │
                      │  (Claude-3.5 / Llama-3.3)  │
                      └─────────────┬──────────────┘
                                    │
                       Success? ────┼──── Error / Rate Limit (429/5xx) / Timeout
                      │             │
                      ▼             ▼
             [Return Result]  ┌────────────────────────────┐
                              │  Fallback Provider:        │
                              │  NVIDIA NIM API            │
                              │  (Llama-3.3-70B-Instruct)  │
                              └─────────────┬──────────────┘
                                            │
                               Success? ────┼──── Error
                              │             │
                              ▼             ▼
                     [Return Result]  [Raise Typed FallbackException]
```

---

## 6. Locked Technology Stack & Zero-Cost Constraints

| Category | Approved Standard | Prohibited Technologies |
| :--- | :--- | :--- |
| **Frontend** | Next.js 15 App Router, TypeScript, Tailwind CSS | Pages router, Vue, Angular, Svelte |
| **Backend** | FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 | Flask, Django, Express.js (for AQG Studio backend) |
| **Agent Orchestration**| LangGraph | AutoGen, CrewAI, raw monolithic spaghetti loops |
| **Database** | Supabase PostgreSQL + `pgvector` extension | Paid Pinecone, Weaviate, Qdrant, Milvus |
| **Task Execution** | FastAPI BackgroundTasks / Async IO coroutines | Redis, Celery, RabbitMQ, Kafka, Kubernetes |
| **File Storage** | Supabase Storage (Private S3) | AWS S3 paid buckets, GCP Cloud Storage paid |
| **Hosting** | Vercel (Frontend Free), Render (Backend Free) | AWS EC2, GCP GKE, Azure Kubernetes |
