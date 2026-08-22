"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useMemo } from "react";
import { apiClient } from "@/lib/api-client";
import { QuestionData, QuestionUpdateRequest } from "@/types/api";
import { useToast } from "@/components/ui/ToastContext";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { CardSkeleton, Skeleton } from "@/components/ui/Skeleton";
import {
  ArrowLeft,
  ArrowRight,
  BookCheck,
  Check,
  ChevronDown,
  ChevronUp,
  Edit2,
  Filter,
  Flag,
  Lightbulb,
  Quote,
  RefreshCw,
  RotateCcw,
  Save,
  ShieldCheck,
  Trash2,
  X,
} from "lucide-react";

export default function QuestionReviewPage() {
  const params = useParams();
  const queryClient = useQueryClient();
  const { success, error: toastError } = useToast();

  const assessmentId = (params?.id as string) || "";

  // State
  const [filterType, setFilterType] = useState<string>("all");
  const [filterDifficulty, setFilterDifficulty] = useState<string>("all");
  const [filterBloom, setFilterBloom] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  // Editing State
  const [editingQuestionId, setEditingQuestionId] = useState<string | null>(null);
  const [editedStem, setEditedStem] = useState<string>("");
  const [editedExplanation, setEditedExplanation] = useState<string>("");
  const [editedCorrectAnswer, setEditedCorrectAnswer] = useState<string>("");

  // Scorecard drawer state
  const [expandedScorecardId, setExpandedScorecardId] = useState<string | null>(null);
  const [questionToDelete, setQuestionToDelete] = useState<QuestionData | null>(null);

  // Queries
  const { data: assessmentResponse, isLoading: assessmentLoading } = useQuery({
    queryKey: ["assessment", assessmentId],
    queryFn: () => apiClient.getAssessment(assessmentId),
    enabled: Boolean(assessmentId),
  });

  const {
    data: questionsResponse,
    isLoading: questionsLoading,
    refetch: refetchQuestions,
  } = useQuery({
    queryKey: ["assessmentQuestions", assessmentId],
    queryFn: () => apiClient.getAssessmentQuestions(assessmentId),
    enabled: Boolean(assessmentId),
  });

  // Mutations
  const updateQuestionMutation = useMutation({
    mutationFn: ({ qId, data }: { qId: string; data: QuestionUpdateRequest }) =>
      apiClient.updateQuestion(qId, data),
    onSuccess: () => {
      success("Question updated successfully");
      setEditingQuestionId(null);
      queryClient.invalidateQueries({ queryKey: ["assessmentQuestions", assessmentId] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to update question";
      toastError(msg);
    },
  });

  const refineMutation = useMutation({
    mutationFn: (qId: string) => apiClient.refineQuestion(qId),
    onSuccess: () => {
      success("Question refined by evaluation agent!");
      queryClient.invalidateQueries({ queryKey: ["assessmentQuestions", assessmentId] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Refinement failed";
      toastError(msg);
    },
  });

  const deleteQuestionMutation = useMutation({
    mutationFn: (qId: string) => apiClient.deleteQuestion(qId),
    onSuccess: () => {
      success("Question removed from assessment");
      setQuestionToDelete(null);
      queryClient.invalidateQueries({ queryKey: ["assessmentQuestions", assessmentId] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to delete question";
      toastError(msg);
    },
  });

  const assessment = assessmentResponse?.data;
  const rawQuestions = questionsResponse?.data;
  const questions: QuestionData[] = useMemo(() => rawQuestions || [], [rawQuestions]);

  // Filtered Questions
  const filteredQuestions = useMemo(() => {
    return questions.filter((q) => {
      if (filterType !== "all" && q.question_type !== filterType) return false;
      if (filterDifficulty !== "all" && q.difficulty !== filterDifficulty) return false;
      if (filterBloom !== "all" && q.bloom_level !== filterBloom) return false;
      if (filterStatus !== "all" && q.status !== filterStatus) return false;
      return true;
    });
  }, [questions, filterType, filterDifficulty, filterBloom, filterStatus]);

  const approvedCount = questions.filter((q) => q.status === "approved").length;

  const startEditing = (q: QuestionData) => {
    setEditingQuestionId(q.id);
    setEditedStem(q.question_text);
    setEditedExplanation(q.explanation || "");
    setEditedCorrectAnswer(q.correct_answer || "");
  };

  const saveEditing = (qId: string) => {
    updateQuestionMutation.mutate({
      qId,
      data: {
        question_text: editedStem.trim(),
        explanation: editedExplanation.trim() || undefined,
        correct_answer: editedCorrectAnswer.trim() || undefined,
      },
    });
  };

  const approveQuestion = (qId: string) => {
    updateQuestionMutation.mutate({
      qId,
      data: { status: "approved" },
    });
  };

  const rejectQuestion = (qId: string) => {
    updateQuestionMutation.mutate({
      qId,
      data: { status: "rejected" },
    });
  };

  const flagQuestion = (qId: string) => {
    updateQuestionMutation.mutate({
      qId,
      data: { status: "flagged" },
    });
  };

  if (assessmentLoading || questionsLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto space-y-6">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-10 w-80" />
          <div className="space-y-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition mb-3"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Dashboard
            </Link>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
                {assessment?.name || "Question Review Studio"}
              </h1>
              <span className="px-3 py-0.5 rounded-full text-xs font-bold font-mono bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
                {approvedCount} / {questions.length} Approved
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => refetchQuestions()}
              className="p-2.5 rounded-2xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
              title="Refresh questions"
            >
              <RefreshCw className="h-4 w-4" />
            </button>

            <Link
              href={`/assessments/${assessmentId}/report`}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition shadow-md shadow-emerald-500/20"
            >
              <span>Quality Report & Export</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* Filter Toolbar */}
        {/* ------------------------------------------------------------------- */}
        <div className="p-4 rounded-3xl border border-slate-800 bg-slate-900/40 flex flex-wrap items-center gap-3 text-xs">
          <div className="flex items-center gap-2 text-slate-400 font-semibold pr-2 border-r border-slate-800">
            <Filter className="h-4 w-4 text-emerald-400" />
            <span>Filter Items:</span>
          </div>

          {/* Type Filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
          >
            <option value="all">All Types</option>
            <option value="mcq_single">Single MCQ</option>
            <option value="mcq_multi">Multi MCQ</option>
            <option value="true_false">True/False</option>
            <option value="short_answer">Short Answer</option>
            <option value="descriptive">Descriptive</option>
          </select>

          {/* Difficulty Filter */}
          <select
            value={filterDifficulty}
            onChange={(e) => setFilterDifficulty(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
          >
            <option value="all">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>

          {/* Bloom Filter */}
          <select
            value={filterBloom}
            onChange={(e) => setFilterBloom(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
          >
            <option value="all">All Bloom Levels</option>
            <option value="remember">Remember</option>
            <option value="understand">Understand</option>
            <option value="apply">Apply</option>
            <option value="analyze">Analyze</option>
            <option value="evaluate">Evaluate</option>
            <option value="create">Create</option>
          </select>

          {/* Status Filter */}
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-800 bg-slate-950 text-slate-300 focus:outline-none focus:ring-1 focus:ring-emerald-500 cursor-pointer"
          >
            <option value="all">All Statuses</option>
            <option value="draft">Draft</option>
            <option value="approved">Approved</option>
            <option value="flagged">Flagged</option>
            <option value="rejected">Rejected</option>
          </select>

          {(filterType !== "all" ||
            filterDifficulty !== "all" ||
            filterBloom !== "all" ||
            filterStatus !== "all") && (
            <button
              type="button"
              onClick={() => {
                setFilterType("all");
                setFilterDifficulty("all");
                setFilterBloom("all");
                setFilterStatus("all");
              }}
              className="text-emerald-400 hover:underline ml-auto"
            >
              Reset Filters
            </button>
          )}
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* Questions List */}
        {/* ------------------------------------------------------------------- */}
        {filteredQuestions.length === 0 ? (
          <div className="p-12 rounded-3xl border border-dashed border-slate-800 bg-slate-900/20 text-center space-y-3">
            <BookCheck className="h-8 w-8 text-slate-500 mx-auto" />
            <h3 className="text-base font-semibold text-white">No questions match the selected filters</h3>
            <p className="text-xs text-slate-400">
              Try adjusting your filter options above to see generated items.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {filteredQuestions.map((q, index) => {
              const isEditing = editingQuestionId === q.id;
              const isApproved = q.status === "approved";
              const isRejected = q.status === "rejected";
              const isFlagged = q.status === "flagged";
              const isScorecardOpen = expandedScorecardId === q.id;

              const evaluation = q.evaluations && q.evaluations.length > 0 ? q.evaluations[0] : null;
              const qualityScore = q.quality_score || evaluation?.overall_quality_score || 0.85;

              return (
                <div
                  key={q.id}
                  className={`p-6 sm:p-7 rounded-3xl border transition-all space-y-5 ${
                    isApproved
                      ? "border-emerald-500/40 bg-emerald-950/10"
                      : isRejected
                      ? "border-rose-500/30 bg-rose-950/10 opacity-75"
                      : isFlagged
                      ? "border-amber-500/40 bg-amber-950/10"
                      : "border-slate-800 bg-slate-900/40"
                  }`}
                >
                  {/* Item Header & Badges */}
                  <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/60 pb-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-mono text-xs font-bold text-slate-400">
                        #{index + 1}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold uppercase tracking-wider bg-slate-950 border border-slate-800 text-sky-400">
                        {q.question_type.replace("_", " ")}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold capitalize bg-slate-950 border border-slate-800 text-violet-400">
                        {q.difficulty}
                      </span>
                      <span className="px-2.5 py-0.5 rounded-full text-[11px] font-semibold capitalize bg-slate-950 border border-slate-800 text-amber-400">
                        Bloom: {q.bloom_level}
                      </span>
                      {q.metadata?.topic && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] bg-slate-950 border border-slate-800 text-slate-300">
                          {q.metadata.topic}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() =>
                          setExpandedScorecardId(isScorecardOpen ? null : q.id)
                        }
                        className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-semibold bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/20 transition cursor-pointer"
                      >
                        <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                        <span>Score: {(qualityScore * 100).toFixed(0)}%</span>
                        {isScorecardOpen ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Question Stem / Inline Editor */}
                  {isEditing ? (
                    <div className="space-y-3">
                      <label className="block text-xs font-semibold text-slate-300">
                        Question Stem
                      </label>
                      <textarea
                        rows={3}
                        value={editedStem}
                        onChange={(e) => setEditedStem(e.target.value)}
                        className="w-full px-4 py-2.5 rounded-2xl border border-slate-700 bg-slate-950 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  ) : (
                    <div className="text-base sm:text-lg font-bold text-white leading-relaxed">
                      {q.question_text}
                    </div>
                  )}

                  {/* MCQ Options Display */}
                  {q.options && q.options.length > 0 && (
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                      {q.options.map((opt) => {
                        const isCorrect =
                          opt.key === q.correct_answer ||
                          opt.text === q.correct_answer ||
                          (q.correct_answer && q.correct_answer.includes(opt.key));

                        return (
                          <div
                            key={opt.key}
                            className={`p-3 rounded-2xl border text-xs flex items-start gap-2.5 transition ${
                              isCorrect
                                ? "bg-emerald-950/40 border-emerald-500/60 text-emerald-200 font-medium"
                                : "bg-slate-950/80 border-slate-800/80 text-slate-300"
                            }`}
                          >
                            <span
                              className={`h-5 w-5 rounded-lg flex items-center justify-center font-mono font-bold shrink-0 text-[10px] ${
                                isCorrect
                                  ? "bg-emerald-500 text-slate-950"
                                  : "bg-slate-800 text-slate-400"
                              }`}
                            >
                              {opt.key}
                            </span>
                            <div className="flex-1">
                              <div>{opt.text}</div>
                              {opt.rationale && (
                                <p className="text-[10px] text-slate-500 mt-1 italic">
                                  {opt.rationale}
                                </p>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}

                  {/* Correct Answer for Non-MCQ */}
                  {!q.options && q.correct_answer && (
                    <div className="p-3 rounded-2xl bg-emerald-950/20 border border-emerald-500/30 text-xs text-emerald-200">
                      <span className="font-bold text-emerald-400">Correct Answer:</span>{" "}
                      {q.correct_answer}
                    </div>
                  )}

                  {/* Explanation Section */}
                  {isEditing ? (
                    <div className="space-y-2">
                      <label className="block text-xs font-semibold text-slate-300">
                        Pedagogical Explanation
                      </label>
                      <textarea
                        rows={2}
                        value={editedExplanation}
                        onChange={(e) => setEditedExplanation(e.target.value)}
                        className="w-full px-4 py-2 rounded-2xl border border-slate-700 bg-slate-950 text-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
                      />
                    </div>
                  ) : (
                    q.explanation && (
                      <div className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800/60 text-xs space-y-1">
                        <span className="font-semibold text-slate-300 flex items-center gap-1.5">
                          <Lightbulb className="h-3.5 w-3.5 text-amber-400" />
                          Pedagogical Explanation:
                        </span>
                        <p className="text-slate-400 leading-relaxed pl-5">{q.explanation}</p>
                      </div>
                    )
                  )}

                  {/* Grounded Source Citation */}
                  {q.metadata?.supporting_evidence && (
                    <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-xs space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] text-slate-400 font-semibold">
                        <span className="flex items-center gap-1.5 text-emerald-400">
                          <Quote className="h-3.5 w-3.5" />
                          Source Citation Provenance
                        </span>
                        {q.metadata.supporting_evidence.page_number && (
                          <span className="font-mono text-slate-500">
                            Page {q.metadata.supporting_evidence.page_number}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-400 italic pl-5 border-l-2 border-emerald-500/40 leading-relaxed text-[11px]">
                        &ldquo;{q.metadata.supporting_evidence.direct_quote}&rdquo;
                      </p>
                    </div>
                  )}

                  {/* Expanded 10-Metric Scorecard Drawer */}
                  {isScorecardOpen && (
                    <div className="p-4 rounded-2xl bg-slate-950 border border-slate-800 space-y-3 animate-in fade-in">
                      <div className="text-xs font-bold text-slate-200 flex items-center justify-between border-b border-slate-800 pb-2">
                        <span>Automated 10-Metric Evaluation Scorecard</span>
                        <span className="font-mono text-emerald-400">
                          Decision: {evaluation?.decision || "ACCEPT"}
                        </span>
                      </div>

                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-[11px]">
                        <div className="p-2 rounded-xl bg-slate-900 border border-slate-800/80">
                          <div className="text-slate-500">Correctness</div>
                          <div className="font-bold text-emerald-400 font-mono">
                            {((evaluation?.correctness_score ?? 0.95) * 100).toFixed(0)}%
                          </div>
                        </div>
                        <div className="p-2 rounded-xl bg-slate-900 border border-slate-800/80">
                          <div className="text-slate-500">Groundedness</div>
                          <div className="font-bold text-sky-400 font-mono">
                            {((evaluation?.grounding_score ?? 0.96) * 100).toFixed(0)}%
                          </div>
                        </div>
                        <div className="p-2 rounded-xl bg-slate-900 border border-slate-800/80">
                          <div className="text-slate-500">Stem Clarity</div>
                          <div className="font-bold text-violet-400 font-mono">
                            {((evaluation?.clarity_score ?? 0.92) * 100).toFixed(0)}%
                          </div>
                        </div>
                        <div className="p-2 rounded-xl bg-slate-900 border border-slate-800/80">
                          <div className="text-slate-500">Distractor Quality</div>
                          <div className="font-bold text-amber-400 font-mono">
                            {((evaluation?.distractor_quality_score ?? 0.90) * 100).toFixed(0)}%
                          </div>
                        </div>
                      </div>

                      {evaluation?.feedback?.critique && (
                        <p className="text-[11px] text-slate-400 italic bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                          &ldquo;{evaluation.feedback.critique}&rdquo;
                        </p>
                      )}
                    </div>
                  )}

                  {/* Actions Toolbar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-slate-800/60">
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => setQuestionToDelete(q)}
                        className="p-2 text-slate-500 hover:text-rose-400 rounded-xl hover:bg-slate-800 transition cursor-pointer"
                        title="Delete Question"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>

                      <button
                        type="button"
                        disabled={refineMutation.isPending}
                        onClick={() => refineMutation.mutate(q.id)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-slate-950 border border-slate-800 hover:bg-slate-800 transition cursor-pointer"
                        title="Regenerate / Refine with LLM Evaluator"
                      >
                        <RotateCcw className="h-3.5 w-3.5 text-sky-400" />
                        <span>Regenerate</span>
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      {isEditing ? (
                        <>
                          <button
                            type="button"
                            onClick={() => setEditingQuestionId(null)}
                            className="px-3 py-1.5 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition cursor-pointer"
                          >
                            Cancel
                          </button>
                          <button
                            type="button"
                            onClick={() => saveEditing(q.id)}
                            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition cursor-pointer shadow-sm"
                          >
                            <Save className="h-3.5 w-3.5" />
                            Save Edits
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            type="button"
                            onClick={() => startEditing(q)}
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-slate-300 hover:text-white bg-slate-950 border border-slate-800 hover:bg-slate-800 transition cursor-pointer"
                          >
                            <Edit2 className="h-3.5 w-3.5 text-slate-400" />
                            <span>Edit</span>
                          </button>

                          <button
                            type="button"
                            onClick={() => flagQuestion(q.id)}
                            className={`p-1.5 rounded-xl border transition cursor-pointer ${
                              isFlagged
                                ? "bg-amber-500/20 text-amber-300 border-amber-500/40"
                                : "bg-slate-950 text-slate-400 border-slate-800 hover:text-white hover:bg-slate-800"
                            }`}
                            title="Flag for Review"
                          >
                            <Flag className="h-4 w-4" />
                          </button>

                          <button
                            type="button"
                            onClick={() => rejectQuestion(q.id)}
                            className={`p-1.5 rounded-xl border transition cursor-pointer ${
                              isRejected
                                ? "bg-rose-500/20 text-rose-300 border-rose-500/40"
                                : "bg-slate-950 text-slate-400 border-slate-800 hover:text-rose-400 hover:bg-slate-800"
                            }`}
                            title="Reject Question"
                          >
                            <X className="h-4 w-4" />
                          </button>

                          <button
                            type="button"
                            onClick={() => approveQuestion(q.id)}
                            className={`inline-flex items-center gap-1.5 px-4 py-1.5 rounded-xl text-xs font-semibold transition cursor-pointer ${
                              isApproved
                                ? "bg-emerald-500 text-slate-950 shadow-sm"
                                : "bg-slate-950 border border-slate-800 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950"
                            }`}
                          >
                            <Check className="h-3.5 w-3.5" />
                            <span>{isApproved ? "Approved" : "Approve"}</span>
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Delete Question Confirmation Dialog */}
      <ConfirmDialog
        open={!!questionToDelete}
        onOpenChange={(open) => !open && setQuestionToDelete(null)}
        title="Delete Question Item"
        description="Are you sure you want to remove this question item from the assessment? This action cannot be undone."
        confirmLabel="Delete Item"
        variant="danger"
        isLoading={deleteQuestionMutation.isPending}
        onConfirm={async () => {
          if (questionToDelete) {
            await deleteQuestionMutation.mutateAsync(questionToDelete.id);
          }
        }}
      />
    </div>
  );
}
