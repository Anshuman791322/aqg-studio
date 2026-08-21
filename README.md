# AQG Studio

> **Multi-Agent Automated Question-Generation System**  
> Grounded, pedagogically calibrated assessments generated from educational material (PDF, DOCX, PPTX, TXT) with automated self-evaluation, hallucination defense, and human-in-the-loop review.

---

## 1. Overview
**AQG Studio** is an enterprise-grade automated assessment engineering platform designed for educators, corporate trainers, certification bodies, and instructional designers. Instead of naive single-shot question generation, AQG Studio deploys a **deterministic 6-agent pipeline orchestrated via LangGraph**:

1. **Document Processing Agent**: Parses documents into structured content trees with page/slide metadata, tables, and sections.
2. **Knowledge Retrieval & Analysis Agent**: Extracts core topics, concept dependencies, and conceptual difficulty.
3. **Question Planning Agent**: Synthesizes a balanced assessment blueprint conforming to Bloom’s Taxonomy and target difficulty tiers.
4. **Question Generation Agent**: Executes vector-grounded RAG retrieval per blueprint item to generate questions with distractors and explanations.
5. **Evaluation & Refinement Agent**: Evaluates generated questions across 5 pedagogical dimensions (groundedness, ambiguity, distractor plausibility, Bloom alignment, bias) and iterates if criteria are not met.
6. **Output & Report Agent**: Bundles finalized assessments, computes quality scorecards, and prepares exports for LMS systems (Moodle XML, GIFT, QTI 2.1, PDF, DOCX, JSON, CSV).

---

## 2. Technology Stack & Constraints

The stack is strictly designed to operate on **community / zero-cost free tiers** with high performance and zero distributed microservice complexity:

- **Frontend**: Next.js 15 (App Router), React 19, TypeScript (Strict), Tailwind CSS, Lucide Icons, Radix UI, `@supabase/ssr`.
- **Backend**: FastAPI, Python 3.12, Pydantic v2, SQLAlchemy 2.0 (async), LangGraph, `python-jose`.
- **Database & Storage**: PostgreSQL 15+ hosted on Supabase Free Tier, `pgvector` for vector similarity search, Supabase Auth, Supabase Storage (Private S3 buckets).
- **Primary LLM**: OpenRouter API (`anthropic/claude-3.5-sonnet`, `meta-llama/llama-3.3-70b-instruct`).
- **Fallback LLM**: NVIDIA NIM API (`meta/llama-3.3-70b-instruct`, `mistralai/mixtral-8x22b-instruct`).
- **Embeddings**: `fastembed` (local ONNX CPU embeddings, e.g., BAAI/bge-small-en-v1.5) or OpenRouter embedding endpoints.
- **Hosting**: Vercel Free Tier (Frontend), Render Web Service Free Tier (Backend).

---

## 3. Directory Layout

```
aqg-studio/
├── AGENTS.md                  # Authoritative instructions for Codex and AI agents
├── README.md                  # System overview and getting started guide
├── .gitignore                 # Production-grade gitignore
├── .editorconfig              # Code style formatting rules
├── .env.example               # Root environment variable template
├── Makefile                   # Standardized development automation commands
├── .github/
│   └── workflows/
│       └── ci.yml             # GitHub Actions CI workflow (Python & Node)
│
├── frontend/                  # Next.js 15 App Router Frontend Application
│   ├── .env.example           # Public client environment template
│   ├── README.md              # Frontend module guide
│   ├── package.json           # Next.js + React 19 dependencies
│   ├── tsconfig.json          # Strict TypeScript configuration
│   ├── tailwind.config.ts     # Tailwind design system configuration
│   ├── eslint.config.mjs      # Flat ESLint configuration
│   ├── middleware.ts          # Route protection and session refresh middleware
│   ├── app/                   # App Router pages (Landing, Auth, Dashboard, Layout, 404)
│   ├── components/            # Reusable UI components (Navbar, Footer)
│   ├── lib/                   # Supabase SSR clients, API client, Zod env validator
│   └── types/                 # TypeScript type definitions (API, Assessment)
│
├── backend/                   # FastAPI Python 3.12 Backend Application
│   ├── .env.example           # Backend environment template (Zero secrets)
│   ├── README.md              # Backend module guide
│   ├── pyproject.toml         # Python project configuration & tool settings
│   ├── requirements.txt       # Production dependencies
│   ├── app/
│   │   ├── main.py            # FastAPI entrypoint, middlewares & exception handlers
│   │   ├── api/v1/            # API v1 routes (version, auth, me)
│   │   ├── core/              # Config, Logging, Errors, JWT Auth dependencies
│   │   ├── db/                # SQLAlchemy 2.0 async engine & sessionmaker
│   │   ├── models/            # SQLAlchemy ORM entities (13 tables)
│   │   ├── repositories/      # User-scoped database repository layer
│   │   ├── schemas/           # Pydantic schemas (common, auth)
│   │   └── services/          # Storage path security & business services
│   └── tests/                 # Pytest test suite (Health, Version, Auth, Models, Repos, Isolation)
│
├── supabase/                  # Supabase Database Migrations & Seed Data
│   └── migrations/
│       ├── 20260821000001_extensions_and_helpers.sql
│       ├── 20260821000002_core_schema.sql
│       └── 20260821000003_storage_and_rls.sql
│
└── docs/                      # Authoritative Technical Specifications
    ├── PROJECT_SPEC.md        # Product requirements, supported formats, MVP limits
    ├── ARCHITECTURE.md        # Multi-agent architecture, state graph, fallback strategy
    ├── API_CONTRACT.md        # REST & SSE OpenAPI specification
    ├── DATA_MODEL.md          # PostgreSQL relational schema, indexes, RLS policies
    ├── SECURITY.md            # Secret management, prompt-injection defense, JWT verification
    ├── DEPLOYMENT.md          # Deployment guide for Vercel, Render, and Supabase
    ├── PHASE_STATUS.md        # Comprehensive tracker for Phases 0 through 14
    └── phases/                # Granular phase handoff deliverables
        ├── 00-repository-contract.md
        ├── 01-foundation.md
        ├── 02-supabase-schema.md
        └── 03-authentication.md
```

---

## 4. Phase Roadmap & Verified Milestones

| Phase | Milestone | Description | Status |
| :--- | :--- | :--- | :--- |
| **00** | **Repository Contract** | Permanent project contract, specifications, locked stack | **Completed** |
| **01** | **Application Foundation**| FastAPI backend & Next.js 15 frontend foundations, strict typing, tests | **Completed** |
| **02** | **Supabase & RLS** | PostgreSQL schema, pgvector, storage buckets, RLS security policies | **Completed** |
| **03** | **User Authentication** | Supabase Auth, Next.js cookie sessions, JWT verification, dashboard shell | **Completed** |
| **04** | **Document Processing Engine**| Parsers for PDF, DOCX, PPTX, TXT with structural chunking | **Completed** |
| **05** | **Model Provider Gateway** | OpenRouter & NVIDIA fallback, 1-shot repair, zero-leak logging | **Completed** |
| **06** | **Knowledge Retrieval & RAG** | Vector embeddings, hybrid retrieval, map-and-reduce knowledge analysis | **Completed** |
| **07** | **Question Planning Agent** | Blueprint generation, Bloom taxonomy matrix, quota planning | **Completed** |
| **08** | **Question Generation Agent** | Grounded question generation with OpenRouter + NVIDIA fallback| **Completed** |
| **09** | **Evaluation & Refinement** | 5-metric automated quality grading & iterative revision loop | Ready |

| **10** | **Output & Report Agent** | Quality scorecard, hallucination index, assessment bundler | Planned |
| **11** | **Human Review Studio** | Interactive UI for editing, approving, and refining items | Planned |
| **12** | **Multi-Format Export** | Export to PDF, DOCX, Moodle XML, GIFT, QTI 2.1, JSON, CSV | Planned |
| **13** | **Frontend UI & Dashboard** | Complete Next.js dashboard, upload wizard, live SSE logs | Planned |
| **14** | **End-to-End Testing & Deploy**| Integration tests, benchmark suite, Vercel & Render staging deploy | Planned |

---

## 5. Getting Started & Verification Commands

### Prerequisites
- Node.js 20+ and npm 10+
- Python 3.12+
- Supabase account (Free Tier) or local Supabase CLI

### Setup & Local Development
```bash
cd aqg-studio

# 1. Install dependencies
make install-backend
make install-frontend

# 2. Run backend and frontend automated tests
make test-backend
make test-frontend

# 3. Run linting & strict type checking
make lint
make typecheck

# 4. Build production packages
make build

# 5. Start development servers
# Terminal 1 (FastAPI on :8000):
make dev-backend
# Terminal 2 (Next.js on :3000):
make dev-frontend
```
