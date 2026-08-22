/**
 * Standard API response and error types matching backend schemas.
 */

export interface ApiErrorDetail {
  field?: string | null;
  issue: string;
}

export interface ApiErrorPayload {
  code: string;
  message: string;
  details?: ApiErrorDetail[];
}

export interface ApiMetaPayload {
  timestamp: string;
  request_id?: string | null;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  meta: ApiMetaPayload;
}

export interface ApiErrorResponse {
  success: false;
  error: ApiErrorPayload;
  meta: ApiMetaPayload;
}

export interface HealthStatus {
  status: "ok" | "ready" | "error";
  database?: string;
  environment?: string;
}

export interface VersionInfo {
  name: string;
  version: string;
  api_version: string;
  environment: string;
  status: string;
}

// -----------------------------------------------------------------------------
// Document Types
// -----------------------------------------------------------------------------
export interface DocumentData {
  id: string;
  user_id: string;
  original_filename: string;
  storage_path: string;
  mime_type: string;
  size_bytes: number;
  checksum?: string | null;
  status: "pending" | "queued" | "processing" | "ready" | "failed" | "needs_ocr";
  page_count: number;
  word_count: number;
  language: string;
  metadata?: Record<string, unknown>;
  error_code?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DocumentChunkData {
  id: string;
  document_id: string;
  chunk_index: number;
  chapter?: string | null;
  section?: string | null;
  page_start?: number | null;
  page_end?: number | null;
  content: string;
  token_count: number;
  content_hash?: string | null;
  metadata?: Record<string, unknown>;
}

export interface ConceptData {
  id: string;
  topic_id: string;
  name: string;
  definition: string;
  difficulty: "easy" | "medium" | "hard";
  metadata?: Record<string, unknown>;
}

export interface TopicData {
  id: string;
  document_id: string;
  name: string;
  description?: string | null;
  importance_score: number;
  concepts: ConceptData[];
  metadata?: Record<string, unknown>;
}

export interface LearningObjectiveData {
  bloom_level: "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";
  description: string;
  source_chunk_ids: string[];
}

export interface KeyFactData {
  fact: string;
  importance_score: number;
  source_chunk_ids: string[];
}

export interface DocumentAnalysisData {
  document_id: string;
  summary: string;
  estimated_difficulty: "easy" | "medium" | "hard";
  topics: TopicData[];
  learning_objectives: LearningObjectiveData[];
  key_facts: KeyFactData[];
}

export interface DocumentInitiateRequest {
  original_filename: string;
  declared_mime_type: string;
  size_bytes: number;
}

export interface DocumentInitiateResponse {
  document_id: string;
  storage_path: string;
  upload_bucket: string;
}

// -----------------------------------------------------------------------------
// Assessment Types
// -----------------------------------------------------------------------------
export interface AssessmentConfiguration {
  total_questions?: number;
  topic_ids?: string[];
  question_type_distribution?: Record<string, number>;
  difficulty_distribution?: Record<string, number>;
  bloom_distribution?: Record<string, number>;
  custom_instructions?: string;
  include_answers?: boolean;
  include_explanations?: boolean;
  include_source_references?: boolean;
}

export interface AssessmentMetrics {
  total_questions?: number;
  accepted_questions?: number;
  rejected_questions?: number;
  average_quality_score?: number;
  regeneration_count?: number;
  type_distribution?: Record<string, number>;
  difficulty_distribution?: Record<string, number>;
  bloom_distribution?: Record<string, number>;
  topic_coverage?: Record<string, number>;
}

export interface AssessmentData {
  id: string;
  user_id: string;
  document_id: string;
  name: string;
  status: "draft" | "queued" | "running" | "ready" | "failed" | "cancelled";
  progress: number;
  configuration?: AssessmentConfiguration;
  metrics?: AssessmentMetrics;
  created_at: string;
  updated_at: string;
}

export interface QuestionBlueprintData {
  id: string;
  sequence_number: number;
  topic_id?: string | null;
  topic_name?: string | null;
  concept_id?: string | null;
  concept_name?: string | null;
  question_type: "mcq_single" | "mcq_multi" | "true_false" | "short_answer" | "descriptive";
  difficulty: "easy" | "medium" | "hard";
  bloom_level: "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";
  learning_objective: string;
  source_chunk_ids: string[];
  status: string;
}

export interface AssessmentBlueprintResponseData {
  assessment_id: string;
  document_id: string;
  name: string;
  total_questions: number;
  status: string;
  configuration?: Record<string, unknown>;
  blueprints: QuestionBlueprintData[];
}

export interface AssessmentCreateRequest {
  document_id: string;
  name: string;
  total_questions: number;
  topic_ids?: string[];
  question_type_distribution?: Record<string, number>;
  difficulty_distribution?: Record<string, number>;
  bloom_distribution?: Record<string, number>;
  custom_instructions?: string;
  include_answers?: boolean;
  include_explanations?: boolean;
  include_source_references?: boolean;
}

// -----------------------------------------------------------------------------
// Question & Evaluation Types
// -----------------------------------------------------------------------------
export interface QuestionOptionData {
  key: string;
  text: string;
  rationale?: string;
}

export interface SupportingEvidenceData {
  direct_quote: string;
  chunk_id: string;
  page_number?: number;
  relevance_score?: number;
}

export interface EvaluationFeedbackData {
  strengths?: string[];
  critique?: string;
  recommendations?: string[];
  dimension_scores?: Record<string, number>;
}

export interface EvaluationData {
  id: string;
  question_id: string;
  user_id: string;
  correctness_score?: number | null;
  grounding_score?: number | null;
  clarity_score?: number | null;
  relevance_score?: number | null;
  difficulty_score?: number | null;
  bloom_alignment_score?: number | null;
  distractor_quality_score?: number | null;
  duplication_score?: number | null;
  overall_quality_score: number;
  decision: "PASS" | "REVISE" | "FAIL" | "ACCEPT" | "REFINE" | "REGENERATE";
  feedback?: EvaluationFeedbackData;
  created_at: string;
}

export interface QuestionData {
  id: string;
  assessment_id: string;
  blueprint_id?: string | null;
  user_id: string;
  question_type: "mcq_single" | "mcq_multi" | "true_false" | "short_answer" | "descriptive";
  question_text: string;
  options?: QuestionOptionData[] | null;
  correct_answer?: string | null;
  explanation?: string | null;
  difficulty: "easy" | "medium" | "hard";
  bloom_level: "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";
  quality_score?: number | null;
  status: "draft" | "approved" | "rejected" | "flagged";
  metadata?: {
    topic?: string;
    concept?: string;
    source_chunk_ids?: string[];
    source_pages?: number[];
    supporting_evidence?: SupportingEvidenceData;
  };
  version: number;
  created_at: string;
  updated_at: string;
  evaluations?: EvaluationData[];
}

export interface QuestionUpdateRequest {
  question_text?: string;
  options?: QuestionOptionData[];
  correct_answer?: string;
  explanation?: string;
  difficulty?: "easy" | "medium" | "hard";
  bloom_level?: "remember" | "understand" | "apply" | "analyze" | "evaluate" | "create";
  status?: "draft" | "approved" | "rejected" | "flagged";
}

// -----------------------------------------------------------------------------
// Job & Polling Types
// -----------------------------------------------------------------------------
export interface JobStatusData {
  job_id: string;
  resource_type: "document" | "assessment" | "export";
  resource_id: string;
  job_type: string;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  current_step?: string | null;
  accepted_questions?: number | null;
  target_questions?: number | null;
  attempts: number;
  max_attempts: number;
  error_code?: string | null;
  error_message?: string | null;
  state?: Record<string, unknown>;
  created_at?: string | null;
  updated_at?: string | null;
}

// -----------------------------------------------------------------------------
// Export & Report Types
// -----------------------------------------------------------------------------
export interface ExportConfiguration {
  include_answers?: boolean;
  include_explanations?: boolean;
  include_source_references?: boolean;
  include_quality_scores?: boolean;
  shuffle_questions?: boolean;
  shuffle_mcq_options?: boolean;
  separate_answer_key?: boolean;
  seed?: number | null;
  custom_title?: string | null;
  custom_instructions?: string | null;
}

export interface ExportCreateRequest {
  assessment_id?: string;
  format: "pdf" | "docx" | "moodle_xml" | "gift" | "qti_2_1" | "json" | "csv";
  configuration?: ExportConfiguration;
}

export interface ExportData {
  id: string;
  assessment_id: string;
  user_id?: string;
  format: "pdf" | "docx" | "moodle_xml" | "gift" | "qti_2_1" | "json" | "csv";
  storage_path: string;
  configuration?: ExportConfiguration;
  status: "pending" | "completed" | "failed";
  file_size_bytes?: number | null;
  download_url?: string | null;
  created_at: string;
  updated_at: string;
}

export interface DistributionCount {
  count: number;
  percentage: number;
}

export interface TopicCoverageItem {
  topic_name: string;
  question_count: number;
  is_covered: boolean;
  importance_score: number;
}

export interface PedagogicalQualityMetrics {
  total_requested: number;
  total_generated: number;
  total_accepted: number;
  total_rejected: number;
  total_flagged: number;
  total_draft: number;
  approval_rate: number;
  average_overall_quality: number;
  average_groundedness: number;
  average_correctness: number;
  average_clarity: number;
  average_distractor_quality: number;
  number_refined: number;
  number_regenerated: number;
  duplicate_count: number;
  failed_blueprints: number;
  estimated_provider_requests?: number;
  estimated_total_tokens?: number;
}

export interface AssessmentReportData {
  assessment_id: string;
  document_id: string;
  assessment_name: string;
  document_filename: string;
  status: string;
  created_at: string;
  updated_at: string;
  metrics: PedagogicalQualityMetrics;
  question_type_distribution: Record<string, DistributionCount>;
  difficulty_distribution: Record<string, DistributionCount>;
  bloom_distribution: Record<string, DistributionCount>;
  topic_coverage: TopicCoverageItem[];
  available_exports: ExportData[];
}

