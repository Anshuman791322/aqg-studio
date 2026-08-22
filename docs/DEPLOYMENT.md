# AQG Studio - Deployment & Infrastructure Guide

## 1. Zero-Cost Free-Tier Architecture
AQG Studio is architected to operate with zero infrastructure expenses by composing free-tier services:

- **Frontend**: Vercel Free Tier (Next.js 15 App Router)
- **Backend API**: Render Web Service Free Tier (FastAPI + Python 3.12, zero-disk dependency)
- **Database & Storage**: Supabase Free Tier (PostgreSQL 15+, pgvector, Auth, Private Storage Buckets)
- **LLM Gateway**: OpenRouter Free Tier with failover to NVIDIA NIM Free Tier.

---

## 2. Environment Variables Matrix

| Variable | Target | Scope | Local Value | Production Example | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `ENVIRONMENT` | Backend | Secret | `development` | `production` | Runtime mode (`production` activates JSON logging & HSTS) |
| `PORT` | Backend | System | `8000` | Dynamic `$PORT` | Bound port for Uvicorn |
| `LOG_LEVEL` | Backend | Secret | `DEBUG` | `INFO` | Logging threshold |
| `LOG_FORMAT` | Backend | Secret | `text` | `json` | `json` produces structured single-line logs |
| `BACKEND_CORS_ORIGINS` | Backend | Secret | `["http://localhost:3000"]` | `["https://aqg-studio.vercel.app"]` | Allowed CORS origins list |
| `DATABASE_URL` | Backend | Secret | `postgresql+asyncpg://...` | `postgresql+asyncpg://...` | Supabase connection string (use Transaction pooler for serverless) |
| `SUPABASE_JWT_SECRET` | Backend | Secret | `your-jwt-secret` | `supa-jwt-secret...` | Verifies incoming user auth tokens |
| `NEXT_PUBLIC_SUPABASE_URL` | Backend/Frontend | Public | `http://127.0.0.1:54321` | `https://[ref].supabase.co` | Supabase project endpoint |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Backend/Frontend | Public | `eyJh...` | `eyJh...` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Secret | `eyJh...` | `eyJh...` | Supabase administrative key (never in frontend) |
| `SUPABASE_STORAGE_BUCKET_DOCUMENTS` | Backend | Config | `user-documents` | `user-documents` | Bucket for original uploaded files |
| `SUPABASE_STORAGE_BUCKET_EXPORTS` | Backend | Config | `generated-exports` | `generated-exports` | Bucket for exported PDFs, DOCX, etc. |
| `OPENROUTER_API_KEY` | Backend | Secret | `sk-or-v1-...` | `sk-or-v1-...` | Primary LLM gateway API key |
| `NVIDIA_API_KEY` | Backend | Secret | `nvapi-...` | `nvapi-...` | Fallback LLM gateway API key |
| `BURST_RATE_LIMIT_PER_MINUTE` | Backend | Config | `120` | `120` | In-memory burst rate limit per client token/IP |
| `MAX_ASSESSMENTS_PER_DAY` | Backend | Config | `10` | `10` | Daily assessment quota per user |
| `MAX_QUESTIONS_PER_ASSESSMENT` | Backend | Config | `50` | `50` | Maximum question count per assessment |
| `NEXT_PUBLIC_BACKEND_URL` | Frontend | Public | `http://localhost:8000` | `https://aqg-studio-backend.onrender.com` | FastAPI backend URL for client API requests |

---

## 3. Supabase Setup & Migration Guide

### 3.1 Supabase Project Provisioning
1. Create a free project at [supabase.com](https://supabase.com).
2. Copy the database connection string (`DATABASE_URL`), API URL (`SUPABASE_URL`), Anon Key (`SUPABASE_ANON_KEY`), and Service Role Key (`SUPABASE_SERVICE_ROLE_KEY`).

### 3.2 Applying SQL Migrations in Numerical Order
Execute migrations via Supabase CLI or SQL Editor:
1. `supabase/migrations/20260821000001_extensions_and_helpers.sql`
2. `supabase/migrations/20260821000002_core_schema.sql`
3. `supabase/migrations/20260821000003_storage_and_rls.sql`

### 3.3 Storage Buckets Creation
Ensure two **private** storage buckets exist:
1. `user-documents` (private, max file size 50MB, MIME types: PDF, DOCX, PPTX, TXT).
2. `generated-exports` (private, max file size 50MB).

### 3.4 Low-Connection Environment Guidance
Supabase free tier provides a limited number of direct database connections (typically 15-60). 
- Use the **Transaction Pooler** connection string (port `6543`) with `pgbouncer=true` if scaling multiple backend workers.
- The default connection pool size in `backend/app/db/session.py` is configured with `pool_size=5` and `max_overflow=10` to avoid connection exhaustion.

---

## 4. Backend Deployment on Render Free Web Service

1. Create a new **Web Service** on [render.com](https://render.com) connected to this repository.
2. Select the repository root or use the included `render.yaml` blueprint.
3. Configuration settings:
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Health Check Path**: `/health/live`
   - **Instance Type**: Free
4. Populate environment variables from the Matrix above.

### Render Cold Starts & Background Resiliency
- Render free instances spin down after 15 minutes of inactivity. The first incoming request may take 30-50 seconds to wake up the service.
- **In-Process PostgreSQL Job Runner**: `PostgresJobRunner` executes inside the FastAPI process lifespan.
- **Startup Crash Recovery**: When Render spins up or restarts, `recover_stale_running_jobs` scans for stale jobs and re-queues them automatically.
- **Resumable Checkpoints**: Every LangGraph step commits progress to PostgreSQL, so resumed jobs do not re-run finished work.

---

## 5. Frontend Deployment on Vercel

1. Import the repository into [vercel.com](https://vercel.com).
2. Configuration settings:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `next build`
   - **Output Directory**: `.next`
   - **Install Command**: `npm install`
3. Populate Environment Variables:
   - `NEXT_PUBLIC_BACKEND_URL`: `https://aqg-studio-backend.onrender.com`
   - `NEXT_PUBLIC_SUPABASE_URL`: `https://[ref].supabase.co`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `eyJh...`
4. Deploy.

---

## 6. Deployment Verification & Smoke Testing

Run the automated deployment smoke test script against any environment:

```bash
# Run against local backend
python scripts/smoke_test.py

# Or verify deployed backend
BACKEND_URL=https://aqg-studio-backend.onrender.com python scripts/smoke_test.py
```

### Smoke Test Suite Checks:
1. `/health/live` returns 200 OK with `status: "ok"`.
2. `/health/ready` returns 200 OK with database connection status without calling paid AI APIs.
3. OWASP security headers (`nosniff`, `DENY`, `strict-origin-when-cross-origin`, CSP) are present.
4. Protected API endpoints return 401 Unauthorized when requested without a valid token.
5. Storage path sandboxing and directory traversal defenses pass.
6. File parser signatures and decompression bomb caps reject corrupted archives.
7. In-memory burst rate limiting returns 429 and `Retry-After`.
8. PostgreSQL atomic quota enforcement returns 429 when daily assessment limit is exceeded.
