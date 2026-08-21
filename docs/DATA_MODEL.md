# AQG Studio - Database Schema & Data Model Specification

## 1. Architectural Philosophy & Engine
- **Target RDBMS**: PostgreSQL 15+ (Hosted on Supabase Free Tier)
- **Primary Extensions**:
  - `pgcrypto`: For cryptographic primitives and UUID generation (`gen_random_uuid()`).
  - `vector`: `pgvector` extension for 384-dimensional dense vector similarity search (`BAAI/bge-small-en-v1.5` embeddings).
- **Primary Key Standard**: `UUID` across all tables.
- **Timestamp Standard**: `TIMESTAMPTZ` in UTC across all tables with automated `handle_updated_at()` trigger.
- **Schema Management**: Pure Supabase SQL migrations under `supabase/migrations/`.
  - *Note*: SQLAlchemy models map to these tables but must **never** run `Base.metadata.create_all()` in production.

---

## 2. Migration Execution Order
1. `supabase/migrations/20260821000001_extensions_and_helpers.sql`: Enables `pgcrypto`, `vector`, and creates `handle_updated_at()` trigger function.
2. `supabase/migrations/20260821000002_core_schema.sql`: DDL for all 13 core relational & vector tables, check constraints, GIN full-text search indexes, HNSW cosine vector indexes, and `updated_at` triggers.
3. `supabase/migrations/20260821000003_storage_and_rls.sql`: Creates private storage buckets (`source-documents`, `generated-exports`) and establishes multi-tenant Row Level Security (RLS) policies across all tables and storage objects.

---

## 3. Relational Table Definitions

### 3.1 `profiles`
Extends `auth.users` with application profile data.
```sql
CREATE TABLE public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.2 `documents`
Uploaded educational resources (PDF, DOCX, PPTX, TXT).
```sql
CREATE TABLE public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    original_filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL,
    checksum TEXT,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'parsed', 'failed', 'ocr_deferred')),
    page_count INT NOT NULL DEFAULT 0,
    word_count INT NOT NULL DEFAULT 0,
    language TEXT NOT NULL DEFAULT 'en',
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.3 `document_chunks`
Extracted document segments with 384-d vector embeddings and full-text search.
```sql
CREATE TABLE public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chapter TEXT,
    section TEXT,
    page_start INT,
    page_end INT,
    content TEXT NOT NULL,
    token_count INT NOT NULL,
    content_hash TEXT,
    embedding vector(384),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    fts TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_document_chunks_index UNIQUE (document_id, chunk_index)
);
```

### 3.4 `topics`
Core domain topics extracted from the document.
```sql
CREATE TABLE public.topics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    importance_score NUMERIC(3,2) DEFAULT 1.00,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.5 `concepts`
Key conceptual definitions under extracted topics.
```sql
CREATE TABLE public.concepts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    topic_id UUID NOT NULL REFERENCES public.topics(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    definition TEXT,
    difficulty TEXT CHECK (difficulty IN ('easy', 'medium', 'hard')),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.6 `learning_objectives`
Target pedagogical learning outcomes aligned with Bloom's Taxonomy.
```sql
CREATE TABLE public.learning_objectives (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES public.topics(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    bloom_level TEXT NOT NULL CHECK (bloom_level IN ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create')),
    description TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.7 `assessments`
Assessment configurations and generation sessions.
```sql
CREATE TABLE public.assessments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'generating', 'evaluating', 'ready', 'failed')),
    progress NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.8 `question_blueprints`
Planning matrix specifying difficulty, Bloom level, and source chunks for each item.
```sql
CREATE TABLE public.question_blueprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES public.assessments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    topic_id UUID REFERENCES public.topics(id) ON DELETE SET NULL,
    concept_id UUID REFERENCES public.concepts(id) ON DELETE SET NULL,
    question_type TEXT NOT NULL CHECK (question_type IN ('mcq_single', 'mcq_multi', 'true_false', 'short_answer', 'descriptive')),
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    bloom_level TEXT NOT NULL CHECK (bloom_level IN ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create')),
    learning_objective TEXT,
    source_chunk_ids UUID[] DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned', 'generating', 'generated', 'failed')),
    sequence_number INT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.9 `questions`
Generated and reviewed assessment items with rationale and citations.
```sql
CREATE TABLE public.questions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES public.assessments(id) ON DELETE CASCADE,
    blueprint_id UUID REFERENCES public.question_blueprints(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    question_type TEXT NOT NULL CHECK (question_type IN ('mcq_single', 'mcq_multi', 'true_false', 'short_answer', 'descriptive')),
    question_text TEXT NOT NULL,
    options JSONB,
    correct_answer JSONB NOT NULL,
    explanation TEXT NOT NULL,
    topic TEXT,
    difficulty TEXT NOT NULL CHECK (difficulty IN ('easy', 'medium', 'hard')),
    bloom_level TEXT NOT NULL CHECK (bloom_level IN ('remember', 'understand', 'apply', 'analyze', 'evaluate', 'create')),
    source_chunk_ids UUID[] DEFAULT '{}',
    source_pages INTEGER[] DEFAULT '{}',
    supporting_evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'pending_review', 'approved', 'rejected', 'flagged')),
    version INT NOT NULL DEFAULT 1,
    generation_attempts INT NOT NULL DEFAULT 1,
    quality_score NUMERIC(3,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.10 `evaluations`
Automated pedagogical quality scorecards across 5 core dimensions.
```sql
CREATE TABLE public.evaluations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    question_id UUID NOT NULL REFERENCES public.questions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    correctness_score NUMERIC(3,2),
    grounding_score NUMERIC(3,2),
    clarity_score NUMERIC(3,2),
    relevance_score NUMERIC(3,2),
    difficulty_score NUMERIC(3,2),
    bloom_alignment_score NUMERIC(3,2),
    distractor_quality_score NUMERIC(3,2),
    duplication_score NUMERIC(3,2),
    overall_quality_score NUMERIC(3,2) NOT NULL,
    decision TEXT NOT NULL CHECK (decision IN ('PASS', 'REVISE', 'FAIL')),
    feedback JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.11 `jobs`
Background job queue and execution state tracking.
```sql
CREATE TABLE public.jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    resource_type TEXT NOT NULL CHECK (resource_type IN ('document', 'assessment', 'export')),
    resource_id UUID NOT NULL,
    job_type TEXT NOT NULL CHECK (job_type IN ('document_processing', 'knowledge_analysis', 'question_planning', 'question_generation', 'question_evaluation', 'export_generation')),
    status TEXT NOT NULL DEFAULT 'queued' CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled')),
    progress NUMERIC(5,2) NOT NULL DEFAULT 0.00,
    current_step TEXT,
    attempts INT NOT NULL DEFAULT 0,
    state JSONB NOT NULL DEFAULT '{}'::jsonb,
    locked_at TIMESTAMPTZ,
    heartbeat_at TIMESTAMPTZ,
    error_code TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.12 `exports`
Generated export packages (PDF, DOCX, Moodle XML, GIFT, QTI 2.1, JSON, CSV).
```sql
CREATE TABLE public.exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    assessment_id UUID NOT NULL REFERENCES public.assessments(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    format TEXT NOT NULL CHECK (format IN ('pdf', 'docx', 'moodle_xml', 'gift', 'qti_2_1', 'json', 'csv')),
    storage_path TEXT NOT NULL,
    configuration JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    file_size_bytes BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);
```

### 3.13 `llm_usage_daily`
Daily token quota and assessment creation rate-limiting tracking.
```sql
CREATE TABLE public.llm_usage_daily (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    usage_date DATE NOT NULL DEFAULT ((now() AT TIME ZONE 'utc')::date),
    request_count INT NOT NULL DEFAULT 0,
    input_tokens INT NOT NULL DEFAULT 0,
    output_tokens INT NOT NULL DEFAULT 0,
    assessments_created INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    CONSTRAINT uq_llm_usage_daily UNIQUE (user_id, usage_date)
);
```

---

## 4. Storage Buckets & Storage Policies
- **`source-documents`**: Private bucket (`public = false`) for raw PDFs, DOCX, PPTX, TXT.
- **`generated-exports`**: Private bucket (`public = false`) for generated export bundles.
- **Path Isolation**:
  `storage_path` format: `{user_id}/{resource_id}/{filename}`.
  Storage RLS policy enforces `(storage.foldername(name))[1] = auth.uid()::text`.
