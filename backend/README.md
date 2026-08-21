# AQG Studio - Backend Application

## Overview
This directory contains the FastAPI Python 3.12 backend service for AQG Studio. It orchestrates the 6 specialized agents via LangGraph and exposes REST and Server-Sent Events (SSE) APIs for the Next.js frontend.

## Architecture & Agent Modules
- `app/api/`: REST & SSE API route handlers (Auth, Documents, Blueprints, Jobs, Questions, Exports).
- `app/core/`: Application settings, security dependencies, Supabase JWT verification.
- `app/db/`: SQLAlchemy 2.0 async engine, base model, session lifecycle management.
- `app/agents/`:
  - `document_processing/`: Deterministic PDF, DOCX, PPTX, TXT parsers and chunkers.
  - `knowledge_analysis/`: Topic modeling, concept extraction, and prerequisite mapping.
  - `question_planning/`: Assessment blueprint generation and Bloom taxonomy quota mapping.
  - `question_generation/`: Vector-grounded question generator with OpenRouter + NVIDIA fallback.
  - `evaluation_refinement/`: Adversarial 5-metric pedagogical grader and iterative refiner.
  - `output_reporting/`: Quality scorecards and multi-format exporters (Moodle, QTI, PDF, DOCX).
- `app/graph/`: LangGraph `StateGraph` definition and state transition logic.

## Development Scripts
- `uvicorn app.main:app --reload --port 8000`: Run local development server
- `pytest tests/`: Run automated test suite
- `ruff check .`: Run code linter
- `mypy app/`: Run static type checking
