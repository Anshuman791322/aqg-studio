/**
 * Domain types for Question Generation, Blueprints, and Pedagogical Taxonomies.
 */

export type QuestionType =
  | "mcq_single"
  | "mcq_multi"
  | "true_false"
  | "short_answer"
  | "descriptive";

export type DifficultyLevel = "easy" | "medium" | "hard";

export type BloomLevel =
  | "remember"
  | "understand"
  | "apply"
  | "analyze"
  | "evaluate"
  | "create";

export type DocumentFileType = "pdf" | "docx" | "pptx" | "txt" | "md";

export interface QuestionOption {
  id: string;
  text: string;
  is_correct: boolean;
  rationale?: string;
}

export interface QuestionCitation {
  chunk_id: string;
  page_number?: number | null;
  slide_number?: number | null;
  verbatim_quote: string;
}

export interface GeneratedQuestionItem {
  id: string;
  type: QuestionType;
  difficulty: DifficultyLevel;
  bloom_level: BloomLevel;
  stem: string;
  options?: QuestionOption[];
  correct_answer: string;
  explanation: string;
  primary_citation: QuestionCitation;
  status: "DRAFT" | "PENDING_REVIEW" | "APPROVED" | "REJECTED" | "FLAGGED";
  quality_score?: number;
}
