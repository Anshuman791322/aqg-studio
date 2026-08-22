# AQG Studio - Release Candidate Checklist (v1.0.0-RC)

This document provides the mandatory pre-flight verification gates and deployment validation checks for the AQG Studio Release Candidate.

---

## 1. Automated Verification Gates

- [x] **Backend Unit & Integration Tests**: 175/175 passing (`pytest -v`)
- [x] **Deterministic End-to-End Pipeline**: Complete 10-step lifecycle verified (`test_end_to_end_pipeline.py`)
- [x] **Backend Strict Type Checking**: 0 Mypy errors across 108 source files (`mypy app`)
- [x] **Backend Linting & Formatting**: 0 Ruff errors (`ruff check .`)
- [x] **Deployment Smoke Tests**: 8/8 automated smoke tests passing (`python scripts/smoke_test.py`)
- [x] **Frontend Unit & Component Tests**: 18/18 Jest tests passing (`npm test`)
- [x] **Frontend Strict Type Checking**: 0 TypeScript errors (`npm run typecheck`)
- [x] **Frontend Linting**: 0 ESLint errors (`npm run lint`)
- [x] **Frontend Production Build**: 11 static and dynamic routes compiled successfully (`npm run build`)

---

## 2. Security & Compliance Checklist

- [x] **User Data Isolation**: Every SQL query strictly scoped with `WHERE user_id = :user_id`.
- [x] **Storage Sandboxing**: All document and export paths enforce `{user_id}/{document_id}/...` with directory traversal protection.
- [x] **JWT Authentication**: Backend verifies HMAC-SHA256 signatures against `SUPABASE_JWT_SECRET` with `aud` and `exp` validation.
- [x] **OWASP Security Headers**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, CSP, and HSTS headers injected.
- [x] **Burst Rate Limiting**: In-memory sliding-window limiter (120 req/min) returning 429 and `Retry-After`.
- [x] **PostgreSQL Atomic Quotas**: Daily assessment generation limit (10/day) and question count limit (50/assessment) enforced.
- [x] **Decompression Bomb Defenses**: Zip magic-byte checks, 1,000-entry limit, 200MB size ceiling, and 100:1 ratio cap before parsing.
- [x] **Secret Sanitization**: Zero API keys or user passwords logged to stdout; automated regex redaction.
- [x] **Prompt Injection Hardening**: All raw document texts wrapped in untrusted `<document_content>` boundary tags.

---

## 3. Deployment Configuration Verification

- [x] **Render Web Service Blueprint**: `render.yaml` configured with Python 3.12, dynamic `$PORT`, and health probe `/health/live`.
- [x] **Vercel Frontend Configuration**: `frontend/vercel.json` configured for Next.js App Router.
- [x] **Supabase Migrations**: Ordered migrations (`01`, `02`, `03`) verified with RLS enabled on all 13 tables.
- [x] **Zero Persistent Disk Dependency**: All state persisted in Supabase; workers recover transparently across restarts.
- [x] **Zero Paid Services**: Operates entirely within Vercel Hobby, Render Free Web Service, and Supabase Free Tier.

---

## 4. Manual Cloud Verification Steps

When deploying to live cloud instances:
1. **Supabase**:
   - Apply SQL migrations in numerical order.
   - Verify `user-documents` and `generated-exports` storage buckets are created and set to private.
   - Enable Email or OAuth sign-in providers in Supabase Auth.
2. **Render**:
   - Create Web Service from `render.yaml`.
   - Set environment variables (`DATABASE_URL`, `SUPABASE_JWT_SECRET`, `OPENROUTER_API_KEY`, `NVIDIA_API_KEY`).
3. **Vercel**:
   - Import `frontend/` directory.
   - Set `NEXT_PUBLIC_BACKEND_URL`, `NEXT_PUBLIC_SUPABASE_URL`, and `NEXT_PUBLIC_SUPABASE_ANON_KEY`.
4. **Smoke Test**:
   - Execute `BACKEND_URL=https://<your-render-app>.onrender.com python scripts/smoke_test.py`.

---

## 5. Release Candidate Verdict

**Status**: **READY FOR RELEASE (RC-1)**
