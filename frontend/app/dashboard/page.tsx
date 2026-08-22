"use client";

import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiClient, UserProfileData } from "@/lib/api-client";
import { DocumentData, AssessmentData } from "@/types/api";
import { useToast } from "@/components/ui/ToastContext";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { CardSkeleton } from "@/components/ui/Skeleton";
import {
  ArrowRight,
  BookOpen,
  FileText,
  FileUp,
  Layers,
  LogOut,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
  User,
  Zap,
} from "lucide-react";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const { success, error: toastError } = useToast();

  const [documentToDelete, setDocumentToDelete] = useState<DocumentData | null>(null);
  const [assessmentToDelete, setAssessmentToDelete] = useState<AssessmentData | null>(null);

  // Queries
  const { data: profileResponse } = useQuery({
    queryKey: ["authMe"],
    queryFn: () => apiClient.getAuthMe(),
    retry: false,
  });

  const {
    data: documentsResponse,
    isLoading: docsLoading,
    refetch: refetchDocs,
  } = useQuery({
    queryKey: ["documents"],
    queryFn: () => apiClient.listDocuments({ limit: 10 }),
  });

  const {
    data: assessmentsResponse,
    isLoading: assessmentsLoading,
    refetch: refetchAssessments,
  } = useQuery({
    queryKey: ["assessments"],
    queryFn: () => apiClient.listAssessments(),
  });

  // Mutations
  const deleteDocMutation = useMutation({
    mutationFn: (docId: string) => apiClient.deleteDocument(docId),
    onSuccess: () => {
      success("Document deleted successfully");
      setDocumentToDelete(null);
      queryClient.invalidateQueries({ queryKey: ["documents"] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to delete document";
      toastError(msg);
    },
  });

  const deleteAssessmentMutation = useMutation({
    mutationFn: (assessmentId: string) => apiClient.deleteAssessment(assessmentId),
    onSuccess: () => {
      success("Assessment deleted successfully");
      setAssessmentToDelete(null);
      queryClient.invalidateQueries({ queryKey: ["assessments"] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to delete assessment";
      toastError(msg);
    },
  });

  const userProfile: UserProfileData | undefined = profileResponse?.data;
  const documents: DocumentData[] = documentsResponse?.data || [];
  const assessments: AssessmentData[] = assessmentsResponse?.data || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Dashboard Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="h-9 w-9 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:bg-emerald-500 group-hover:text-slate-950 transition-all">
                <BookOpen className="h-5 w-5" />
              </div>
              <span className="font-bold text-lg tracking-tight text-white">AQG Studio</span>
            </Link>
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-800/40">
              Workspace
            </span>
          </div>

          <div className="flex items-center gap-3 sm:gap-4">
            <div className="hidden sm:flex items-center gap-2 text-xs text-slate-400 bg-slate-900 px-3.5 py-1.5 rounded-2xl border border-slate-800">
              <User className="h-3.5 w-3.5 text-emerald-400" />
              <span className="font-medium text-slate-200">
                {userProfile?.display_name || userProfile?.email || "User"}
              </span>
            </div>
            <form action="/auth/sign-out" method="post">
              <button
                type="submit"
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-2xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 border border-slate-800 transition-all cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Sign Out</span>
              </button>
            </form>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
        {/* Welcome & Quota Banner */}
        <div className="p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-emerald-950/40 via-slate-900/40 to-slate-900/20 border border-emerald-500/20 relative overflow-hidden flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2 max-w-2xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <Sparkles className="h-3.5 w-3.5" />
              Educator Studio
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Welcome back, {userProfile?.display_name || "Educator"}
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">
              Ingest textbooks and lecture slides to generate Bloom-calibrated assessments with automated evaluation and LMS package exports.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Link
              href="/documents/new"
              className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 shadow-md shadow-emerald-500/20"
            >
              <FileUp className="h-4 w-4" />
              Upload Document
            </Link>
            <Link
              href="/assessments/new"
              className="inline-flex items-center gap-2 rounded-2xl border border-slate-700 bg-slate-900 px-5 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-800 hover:text-white"
            >
              <Plus className="h-4 w-4 text-emerald-400" />
              New Assessment
            </Link>
          </div>
        </div>

        {/* Quota & Usage Metrics Strip */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Daily Requests
              </span>
              <Zap className="h-4 w-4 text-emerald-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {userProfile?.quota.today_requests || 0} / 500
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Community tier request budget</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Source Documents
              </span>
              <FileText className="h-4 w-4 text-sky-400" />
            </div>
            <div className="text-2xl font-bold text-white">{documents.length}</div>
            <p className="text-[11px] text-slate-500 mt-1">Ingested & indexed in pgvector</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Assessments Created
              </span>
              <Layers className="h-4 w-4 text-violet-400" />
            </div>
            <div className="text-2xl font-bold text-white">{assessments.length}</div>
            <p className="text-[11px] text-slate-500 mt-1">Pedagogical question sets</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Tokens Processed
              </span>
              <Sparkles className="h-4 w-4 text-amber-400" />
            </div>
            <div className="text-2xl font-bold text-white">
              {(userProfile?.quota.today_input_tokens || 0) +
                (userProfile?.quota.today_output_tokens || 0)}
            </div>
            <p className="text-[11px] text-slate-500 mt-1">Today&apos;s cognitive payload</p>
          </div>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* Section 1: Recent Documents */}
        {/* ------------------------------------------------------------------- */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Source Learning Materials
              </h2>
              <p className="text-xs text-slate-400">
                Uploaded PDFs, DOCX, PPTX, and notes indexed for semantic retrieval
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => refetchDocs()}
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
                title="Refresh documents"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
              <Link
                href="/documents/new"
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
              >
                <span>Upload New</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>

          {docsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : documents.length === 0 ? (
            /* Empty State for Documents */
            <div className="p-10 rounded-3xl border border-dashed border-slate-800 bg-slate-900/20 text-center space-y-4">
              <div className="h-12 w-12 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 mx-auto flex items-center justify-center">
                <FileUp className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-white">No documents uploaded yet</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Upload your textbook chapters, lecture slides, or syllabus notes to begin question generation.
                </p>
              </div>
              <Link
                href="/documents/new"
                className="inline-flex items-center gap-2 rounded-2xl bg-emerald-500 px-5 py-2.5 text-xs font-semibold text-slate-950 hover:bg-emerald-400 transition"
              >
                <FileUp className="h-3.5 w-3.5" />
                Upload Your First Document
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {documents.map((doc) => {
                const isReady = doc.status === "ready";
                const isProcessing = doc.status === "processing" || doc.status === "queued";
                const isFailed = doc.status === "failed";

                const badgeBg = isReady
                  ? "bg-emerald-950/60 text-emerald-400 border-emerald-800/40"
                  : isProcessing
                  ? "bg-sky-950/60 text-sky-400 border-sky-800/40 animate-pulse"
                  : isFailed
                  ? "bg-rose-950/60 text-rose-400 border-rose-800/40"
                  : "bg-slate-800/60 text-slate-400 border-slate-700/40";

                return (
                  <div
                    key={doc.id}
                    className="p-5 rounded-3xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition flex flex-col justify-between space-y-4"
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="flex items-center gap-2.5 min-w-0">
                          <div className="h-9 w-9 rounded-2xl bg-slate-950 border border-slate-800 flex items-center justify-center shrink-0 text-slate-300">
                            <FileText className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <h4 className="text-sm font-semibold text-white truncate">
                              {doc.original_filename}
                            </h4>
                            <div className="flex items-center gap-2 text-[11px] text-slate-500">
                              <span>{(doc.size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
                              <span>•</span>
                              <span>{doc.page_count} pages</span>
                              <span>•</span>
                              <span>{doc.word_count.toLocaleString()} words</span>
                            </div>
                          </div>
                        </div>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0 ${badgeBg}`}
                        >
                          {doc.status}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-slate-800/60">
                      <button
                        type="button"
                        onClick={() => setDocumentToDelete(doc)}
                        className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition cursor-pointer"
                        title="Delete Document"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>

                      <div className="flex items-center gap-2">
                        <Link
                          href={`/documents/${doc.id}`}
                          className="px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white rounded-xl hover:bg-slate-800 transition"
                        >
                          Details
                        </Link>
                        {isReady && (
                          <Link
                            href={`/assessments/new?document_id=${doc.id}`}
                            className="px-3 py-1.5 text-xs font-semibold text-slate-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition shadow-sm"
                          >
                            Create Assessment
                          </Link>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* ------------------------------------------------------------------- */}
        {/* Section 2: User Assessments */}
        {/* ------------------------------------------------------------------- */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight">
                Generated Assessments & Question Sets
              </h2>
              <p className="text-xs text-slate-400">
                Cognitive blueprints, evaluated question items, and LMS export bundles
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => refetchAssessments()}
                className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
                title="Refresh assessments"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
              <Link
                href="/assessments/new"
                className="text-xs font-semibold text-emerald-400 hover:text-emerald-300 flex items-center gap-1"
              >
                <span>New Assessment</span>
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </div>
          </div>

          {assessmentsLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <CardSkeleton />
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : assessments.length === 0 ? (
            /* Empty State for Assessments */
            <div className="p-10 rounded-3xl border border-dashed border-slate-800 bg-slate-900/20 text-center space-y-4">
              <div className="h-12 w-12 rounded-2xl bg-sky-500/10 text-sky-400 border border-sky-500/20 mx-auto flex items-center justify-center">
                <Layers className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-white">No assessments generated yet</h3>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Configure an assessment blueprint with Bloom’s taxonomy distribution to generate your first test bank.
                </p>
              </div>
              <Link
                href="/assessments/new"
                className="inline-flex items-center gap-2 rounded-2xl bg-sky-500 px-5 py-2.5 text-xs font-semibold text-slate-950 hover:bg-sky-400 transition"
              >
                <Plus className="h-3.5 w-3.5" />
                Configure Assessment
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {assessments.map((assessment) => {
                const isReady = assessment.status === "ready";
                const isRunning =
                  assessment.status === "running" || assessment.status === "queued";
                const isFailed = assessment.status === "failed";
                const isCancelled = assessment.status === "cancelled";

                const badgeBg = isReady
                  ? "bg-emerald-950/60 text-emerald-400 border-emerald-800/40"
                  : isRunning
                  ? "bg-sky-950/60 text-sky-400 border-sky-800/40 animate-pulse"
                  : isFailed
                  ? "bg-rose-950/60 text-rose-400 border-rose-800/40"
                  : isCancelled
                  ? "bg-amber-950/60 text-amber-400 border-amber-800/40"
                  : "bg-slate-800/60 text-slate-400 border-slate-700/40";

                const targetCount =
                  assessment.configuration?.total_questions ||
                  assessment.metrics?.total_questions ||
                  0;
                const acceptedCount = assessment.metrics?.accepted_questions || 0;
                const avgScore = assessment.metrics?.average_quality_score;

                return (
                  <div
                    key={assessment.id}
                    className="p-5 rounded-3xl border border-slate-800 bg-slate-900/40 hover:border-slate-700 transition flex flex-col justify-between space-y-4"
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <h4 className="text-sm font-semibold text-white truncate">
                            {assessment.name}
                          </h4>
                          <div className="flex items-center gap-2 text-[11px] text-slate-500 mt-0.5">
                            <span>
                              {acceptedCount} / {targetCount} Questions
                            </span>
                            {avgScore && (
                              <>
                                <span>•</span>
                                <span className="text-emerald-400 font-medium">
                                  Score: {(avgScore * 100).toFixed(0)}%
                                </span>
                              </>
                            )}
                          </div>
                        </div>
                        <span
                          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0 ${badgeBg}`}
                        >
                          {assessment.status}
                        </span>
                      </div>

                      {isRunning && (
                        <div className="space-y-1.5">
                          <div className="flex justify-between text-[11px] text-slate-400">
                            <span>Generating items...</span>
                            <span className="font-mono">{assessment.progress.toFixed(0)}%</span>
                          </div>
                          <div className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                            <div
                              className="h-full bg-sky-500 transition-all duration-300 rounded-full"
                              style={{ width: `${Math.max(5, assessment.progress)}%` }}
                            />
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center justify-between pt-3 border-t border-slate-800/60">
                      <button
                        type="button"
                        onClick={() => setAssessmentToDelete(assessment)}
                        className="p-1.5 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-slate-800 transition cursor-pointer"
                        title="Delete Assessment"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>

                      <div className="flex items-center gap-2">
                        {isRunning && (
                          <Link
                            href={`/assessments/${assessment.id}/progress`}
                            className="px-3 py-1.5 text-xs font-semibold text-slate-950 bg-sky-500 hover:bg-sky-400 rounded-xl transition"
                          >
                            Live Progress
                          </Link>
                        )}
                        {isReady && (
                          <>
                            <Link
                              href={`/assessments/${assessment.id}/report`}
                              className="px-3 py-1.5 text-xs font-medium text-slate-300 hover:text-white rounded-xl hover:bg-slate-800 transition"
                            >
                              Report
                            </Link>
                            <Link
                              href={`/assessments/${assessment.id}/review`}
                              className="px-3 py-1.5 text-xs font-semibold text-slate-950 bg-emerald-500 hover:bg-emerald-400 rounded-xl transition shadow-sm"
                            >
                              Review Questions
                            </Link>
                          </>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>

      {/* Delete Document Confirmation Dialog */}
      <ConfirmDialog
        open={!!documentToDelete}
        onOpenChange={(open) => !open && setDocumentToDelete(null)}
        title="Delete Source Document"
        description={`Are you sure you want to delete "${documentToDelete?.original_filename}"? This will permanently remove its parsed chunks, embeddings, and topics.`}
        confirmLabel="Delete Document"
        variant="danger"
        isLoading={deleteDocMutation.isPending}
        onConfirm={async () => {
          if (documentToDelete) {
            await deleteDocMutation.mutateAsync(documentToDelete.id);
          }
        }}
      />

      {/* Delete Assessment Confirmation Dialog */}
      <ConfirmDialog
        open={!!assessmentToDelete}
        onOpenChange={(open) => !open && setAssessmentToDelete(null)}
        title="Delete Assessment"
        description={`Are you sure you want to delete "${assessmentToDelete?.name}"? All generated questions, evaluations, and export records for this assessment will be removed.`}
        confirmLabel="Delete Assessment"
        variant="danger"
        isLoading={deleteAssessmentMutation.isPending}
        onConfirm={async () => {
          if (assessmentToDelete) {
            await deleteAssessmentMutation.mutateAsync(assessmentToDelete.id);
          }
        }}
      />
    </div>
  );
}
