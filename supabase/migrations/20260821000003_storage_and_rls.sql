-- ==============================================================================
-- AQG Studio Migration 03: Private Storage Buckets & Row Level Security (RLS)
-- File: 20260821000003_storage_and_rls.sql
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. Private Storage Buckets Initialization
-- ------------------------------------------------------------------------------
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES 
    ('source-documents', 'source-documents', false, 52428800, ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/vnd.openxmlformats-officedocument.presentationml.presentation', 'text/plain', 'text/markdown']),
    ('generated-exports', 'generated-exports', false, 52428800, ARRAY['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/zip', 'application/xml', 'text/plain', 'text/csv', 'application/json'])
ON CONFLICT (id) DO NOTHING;

-- ------------------------------------------------------------------------------
-- 2. Storage Row-Level Security Policies (storage.objects)
-- ------------------------------------------------------------------------------
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to view their own uploaded files
CREATE POLICY "Users can view own storage objects"
ON storage.objects FOR SELECT
TO authenticated
USING (
    bucket_id IN ('source-documents', 'generated-exports')
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to upload to their own user-scoped directory
CREATE POLICY "Users can upload to own storage directory"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (
    bucket_id IN ('source-documents', 'generated-exports')
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to update their own files
CREATE POLICY "Users can update own storage objects"
ON storage.objects FOR UPDATE
TO authenticated
USING (
    bucket_id IN ('source-documents', 'generated-exports')
    AND (storage.foldername(name))[1] = auth.uid()::text
)
WITH CHECK (
    bucket_id IN ('source-documents', 'generated-exports')
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Allow authenticated users to delete their own files
CREATE POLICY "Users can delete own storage objects"
ON storage.objects FOR DELETE
TO authenticated
USING (
    bucket_id IN ('source-documents', 'generated-exports')
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- ------------------------------------------------------------------------------
-- 3. Application Tables Row-Level Security (RLS)
-- ------------------------------------------------------------------------------

-- Enable RLS on all application tables
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.topics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.concepts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.learning_objectives ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.question_blueprints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.questions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.evaluations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.exports ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.llm_usage_daily ENABLE ROW LEVEL SECURITY;

-- 3.1 Profiles RLS Policies (Primary key 'id' equals auth.uid())
CREATE POLICY "Profiles select policy" ON public.profiles FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY "Profiles insert policy" ON public.profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
CREATE POLICY "Profiles update policy" ON public.profiles FOR UPDATE TO authenticated USING (auth.uid() = id) WITH CHECK (auth.uid() = id);
CREATE POLICY "Profiles delete policy" ON public.profiles FOR DELETE TO authenticated USING (auth.uid() = id);

-- 3.2 Documents RLS Policies
CREATE POLICY "Documents select policy" ON public.documents FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Documents insert policy" ON public.documents FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Documents update policy" ON public.documents FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Documents delete policy" ON public.documents FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.3 Document Chunks RLS Policies
CREATE POLICY "Document chunks select policy" ON public.document_chunks FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Document chunks insert policy" ON public.document_chunks FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Document chunks update policy" ON public.document_chunks FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Document chunks delete policy" ON public.document_chunks FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.4 Topics RLS Policies
CREATE POLICY "Topics select policy" ON public.topics FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Topics insert policy" ON public.topics FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Topics update policy" ON public.topics FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Topics delete policy" ON public.topics FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.5 Concepts RLS Policies
CREATE POLICY "Concepts select policy" ON public.concepts FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Concepts insert policy" ON public.concepts FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Concepts update policy" ON public.concepts FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Concepts delete policy" ON public.concepts FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.6 Learning Objectives RLS Policies
CREATE POLICY "Learning objectives select policy" ON public.learning_objectives FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Learning objectives insert policy" ON public.learning_objectives FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Learning objectives update policy" ON public.learning_objectives FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Learning objectives delete policy" ON public.learning_objectives FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.7 Assessments RLS Policies
CREATE POLICY "Assessments select policy" ON public.assessments FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Assessments insert policy" ON public.assessments FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Assessments update policy" ON public.assessments FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Assessments delete policy" ON public.assessments FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.8 Question Blueprints RLS Policies
CREATE POLICY "Question blueprints select policy" ON public.question_blueprints FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Question blueprints insert policy" ON public.question_blueprints FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Question blueprints update policy" ON public.question_blueprints FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Question blueprints delete policy" ON public.question_blueprints FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.9 Questions RLS Policies
CREATE POLICY "Questions select policy" ON public.questions FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Questions insert policy" ON public.questions FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Questions update policy" ON public.questions FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Questions delete policy" ON public.questions FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.10 Evaluations RLS Policies
CREATE POLICY "Evaluations select policy" ON public.evaluations FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Evaluations insert policy" ON public.evaluations FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Evaluations update policy" ON public.evaluations FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Evaluations delete policy" ON public.evaluations FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.11 Jobs RLS Policies
CREATE POLICY "Jobs select policy" ON public.jobs FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Jobs insert policy" ON public.jobs FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Jobs update policy" ON public.jobs FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Jobs delete policy" ON public.jobs FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.12 Exports RLS Policies
CREATE POLICY "Exports select policy" ON public.exports FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Exports insert policy" ON public.exports FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Exports update policy" ON public.exports FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Exports delete policy" ON public.exports FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- 3.13 LLM Usage Daily RLS Policies
CREATE POLICY "LLM usage select policy" ON public.llm_usage_daily FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "LLM usage insert policy" ON public.llm_usage_daily FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "LLM usage update policy" ON public.llm_usage_daily FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY "LLM usage delete policy" ON public.llm_usage_daily FOR DELETE TO authenticated USING (auth.uid() = user_id);
