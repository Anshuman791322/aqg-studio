# AQG Studio - Deployment & Infrastructure Guide

## 1. Zero-Cost Free-Tier Architecture
AQG Studio is architected to operate with zero infrastructure expenses by composing free-tier services:

- **Frontend**: Vercel Free Tier (Next.js 15 App Router Edge/Serverless)
- **Backend API**: Render Web Service Free Tier (FastAPI + Python 3.12/3.13)
- **Database & Storage**: Supabase Free Tier (PostgreSQL 15+, pgvector, Auth, Private Storage Buckets)
- **LLM Gateway**: OpenRouter Free Tier (`anthropic/claude-3.5-sonnet`, `meta-llama/llama-3.3-70b-instruct`) with failover to NVIDIA NIM Free Tier.

---

## 2. Supabase Setup & Migration Guide

### 2.1 Supabase Project Provisioning
1. Create a free project at [supabase.com](https://supabase.com).
2. Copy the database connection string (`DATABASE_URL`), API URL (`SUPABASE_URL`), Anon Key (`SUPABASE_ANON_KEY`), and Service Role Key (`SUPABASE_SERVICE_ROLE_KEY`).

### 2.2 Applying SQL Migrations to a Fresh Supabase Project

#### Option A: Supabase CLI (Recommended)
```bash
# Link project
npx supabase link --project-ref <your-project-ref>

# Apply all ordered migrations in supabase/migrations/
npx supabase db push
```

#### Option B: Supabase SQL Editor (Manual)
Run the migration files in exact numerical order in the Supabase Dashboard SQL Editor:
1. `supabase/migrations/20260821000001_extensions_and_helpers.sql`
2. `supabase/migrations/20260821000002_core_schema.sql`
3. `supabase/migrations/20260821000003_storage_and_rls.sql`

### 2.3 Verifying Migration Success
Run the following SQL check in the Supabase SQL editor:
```sql
-- 1. Check extensions
SELECT extname, extversion FROM pg_extension WHERE extname IN ('pgcrypto', 'vector');

-- 2. Check table count
SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';
-- Expected: 13 tables

-- 3. Check storage buckets
SELECT id, name, public FROM storage.buckets WHERE id IN ('source-documents', 'generated-exports');
-- Expected: 2 private buckets

-- 4. Check RLS enablement
SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';
-- Expected: rowsecurity = true for all tables
```

---

## 3. Environment Configuration

### Backend Environment Variables (`backend/.env`)
```bash
ENVIRONMENT=production
DEBUG=false
API_V1_STR=/api/v1
PROJECT_NAME="AQG Studio Backend"

DATABASE_URL=postgresql+asyncpg://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
DATABASE_ECHO=false

SUPABASE_URL=https://[REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=[SECRET_SERVICE_ROLE_KEY]

OPENROUTER_API_KEY=sk-or-v1-...
NVIDIA_NIM_API_KEY=nvapi-...

BACKEND_CORS_ORIGINS=["https://aqg-studio.vercel.app"]
```

### Frontend Environment Variables (`frontend/.env.local`)
```bash
NEXT_PUBLIC_API_URL=https://aqg-studio-api.onrender.com
NEXT_PUBLIC_SUPABASE_URL=https://[REF].supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGci...
NEXT_PUBLIC_APP_NAME="AQG Studio"
```
