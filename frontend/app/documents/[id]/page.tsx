"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/components/ui/ToastContext";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { CardSkeleton, Skeleton } from "@/components/ui/Skeleton";
import {
  ArrowLeft,
  Database,
  Lightbulb,
  Plus,
  RefreshCw,
  Sparkles,
  Trash2,
} from "lucide-react";

export default function DocumentDetailPage() {
  const params = useParams();
  const router = useRouter();
  const queryClient = useQueryClient();
  const { success, error: toastError } = useToast();

  const documentId = (params?.id as string) || "";
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

  // Document Query
  const {
    data: docResponse,
    isLoading: docLoading,
    refetch: refetchDoc,
  } = useQuery({
    queryKey: ["document", documentId],
    queryFn: () => apiClient.getDocument(documentId),
    enabled: Boolean(documentId),
    refetchInterval: (query) => {
      const status = query.state.data?.data?.status;
      return status === "processing" || status === "queued" ? 3000 : false;
    },
  });

  // Chunks Query
  const { data: chunksResponse } = useQuery({
    queryKey: ["documentChunks", documentId],
    queryFn: () => apiClient.getDocumentChunks(documentId),
    enabled: Boolean(documentId),
  });

  // Analysis Query (Topics & Concepts)
  const { data: analysisResponse, isLoading: analysisLoading } = useQuery({
    queryKey: ["documentAnalysis", documentId],
    queryFn: () => apiClient.getDocumentAnalysis(documentId),
    enabled: Boolean(documentId) && docResponse?.data?.status === "ready",
    retry: false,
  });

  // Reprocess Mutation
  const reprocessMutation = useMutation({
    mutationFn: () => apiClient.processDocument(documentId),
    onSuccess: () => {
      success("Document queued for reprocessing");
      queryClient.invalidateQueries({ queryKey: ["document", documentId] });
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Reprocessing failed";
      toastError(msg);
    },
  });

  // Delete Mutation
  const deleteMutation = useMutation({
    mutationFn: () => apiClient.deleteDocument(documentId),
    onSuccess: () => {
      success("Document deleted");
      router.push("/dashboard");
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to delete document";
      toastError(msg);
    },
  });

  const doc = docResponse?.data;
  const chunks = chunksResponse?.data || [];
  const analysis = analysisResponse?.data;

  if (docLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto space-y-6">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-10 w-96" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        </div>
      </div>
    );
  }

  if (!doc) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-16 px-4 text-center space-y-4">
        <h2 className="text-xl font-bold text-white">Document Not Found</h2>
        <p className="text-xs text-slate-400">
          The requested document may have been deleted or does not belong to your account.
        </p>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition"
        >
          <ArrowLeft className="h-4 w-4" />
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const isReady = doc.status === "ready";
  const isProcessing = doc.status === "processing" || doc.status === "queued";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Navigation & Actions */}
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
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white truncate max-w-lg">
                {doc.original_filename}
              </h1>
              <span
                className={`px-3 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider border ${
                  isReady
                    ? "bg-emerald-950/60 text-emerald-400 border-emerald-800/40"
                    : isProcessing
                    ? "bg-sky-950/60 text-sky-400 border-sky-800/40 animate-pulse"
                    : "bg-rose-950/60 text-rose-400 border-rose-800/40"
                }`}
              >
                {doc.status}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => refetchDoc()}
              className="p-2.5 rounded-2xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
              title="Refresh status"
            >
              <RefreshCw className="h-4 w-4" />
            </button>

            <button
              type="button"
              disabled={reprocessMutation.isPending}
              onClick={() => reprocessMutation.mutate()}
              className="px-4 py-2 rounded-2xl text-xs font-medium border border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800 hover:text-white transition cursor-pointer disabled:opacity-50"
            >
              Reprocess
            </button>

            <button
              type="button"
              onClick={() => setShowDeleteDialog(true)}
              className="p-2.5 rounded-2xl border border-slate-800 bg-slate-900 text-slate-500 hover:text-rose-400 hover:bg-slate-800 transition cursor-pointer"
              title="Delete Document"
            >
              <Trash2 className="h-4 w-4" />
            </button>

            {isReady && (
              <Link
                href={`/assessments/new?document_id=${doc.id}`}
                className="inline-flex items-center gap-2 px-5 py-2 rounded-2xl text-xs font-semibold text-slate-950 bg-emerald-500 hover:bg-emerald-400 transition shadow-md shadow-emerald-500/20"
              >
                <Plus className="h-4 w-4" />
                Create Assessment
              </Link>
            )}
          </div>
        </div>

        {/* Processing Notification if Running */}
        {isProcessing && (
          <div className="p-6 rounded-3xl border border-sky-500/30 bg-sky-950/20 flex items-center gap-4">
            <RefreshCw className="h-6 w-6 text-sky-400 animate-spin shrink-0" />
            <div className="space-y-1">
              <h3 className="text-sm font-bold text-white">Document is Being Processed</h3>
              <p className="text-xs text-slate-400">
                The 7-node LangGraph extraction, chunking, and knowledge map analysis workflow is running in the background. This page will update automatically.
              </p>
            </div>
          </div>
        )}

        {/* Metadata & Stats Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              File Size
            </span>
            <div className="text-xl font-bold text-white">
              {(doc.size_bytes / (1024 * 1024)).toFixed(2)} MB
            </div>
            <p className="text-[11px] text-slate-500 truncate">{doc.mime_type}</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Page Count
            </span>
            <div className="text-xl font-bold text-sky-400">{doc.page_count} Pages</div>
            <p className="text-[11px] text-slate-500">{doc.word_count.toLocaleString()} Words</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Semantic Chunks
            </span>
            <div className="text-xl font-bold text-violet-400">{chunks.length} Chunks</div>
            <p className="text-[11px] text-slate-500">600–900 token segments</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Uploaded At
            </span>
            <div className="text-sm font-bold text-white">
              {new Date(doc.created_at).toLocaleDateString()}
            </div>
            <p className="text-[11px] text-slate-500">
              {new Date(doc.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </p>
          </div>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* Extracted Knowledge Map (Topics & Concepts) */}
        {/* ------------------------------------------------------------------- */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                <Lightbulb className="h-5 w-5 text-amber-400" />
                Extracted Topics & Knowledge Map
              </h2>
              <p className="text-xs text-slate-400">
                Concepts extracted via bounded map-and-reduce knowledge analysis
              </p>
            </div>
            {analysis && (
              <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2.5 py-0.5 rounded-full">
                Difficulty: {analysis.estimated_difficulty?.toUpperCase() || "MEDIUM"}
              </span>
            )}
          </div>

          {analysisLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <CardSkeleton />
              <CardSkeleton />
            </div>
          ) : !analysis || analysis.topics?.length === 0 ? (
            <div className="p-8 rounded-3xl border border-slate-800 bg-slate-900/20 text-center space-y-2">
              <Sparkles className="h-6 w-6 text-slate-500 mx-auto" />
              <p className="text-xs text-slate-400">
                {isProcessing
                  ? "Extracting knowledge map in the background..."
                  : "No topics extracted. Click Reprocess to analyze this document."}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {analysis.topics.map((topic) => (
                <div
                  key={topic.id || topic.name}
                  className="p-5 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="text-sm font-bold text-white">{topic.name}</h3>
                      {topic.description && (
                        <p className="text-xs text-slate-400 mt-0.5">{topic.description}</p>
                      )}
                    </div>
                    <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 px-2 py-0.5 rounded-full shrink-0">
                      Score: {(topic.importance_score || 1.0).toFixed(1)}
                    </span>
                  </div>

                  {topic.concepts && topic.concepts.length > 0 && (
                    <div className="space-y-2 pt-2 border-t border-slate-800/60">
                      <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                        Key Concepts
                      </div>
                      <div className="space-y-1.5">
                        {topic.concepts.map((c, i) => (
                          <div
                            key={c.id || i}
                            className="p-2.5 rounded-xl bg-slate-950/80 border border-slate-800/80 space-y-1"
                          >
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-semibold text-slate-200">{c.name}</span>
                              <span className="text-[10px] font-mono text-sky-400 bg-sky-950/60 px-1.5 py-0.5 rounded">
                                {c.difficulty || "medium"}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-400 leading-relaxed">
                              {c.definition}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>

        {/* ------------------------------------------------------------------- */}
        {/* Semantic Chunks Preview */}
        {/* ------------------------------------------------------------------- */}
        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                <Database className="h-5 w-5 text-sky-400" />
                Indexed Semantic Chunks ({chunks.length})
              </h2>
              <p className="text-xs text-slate-400">
                Segmented with 10% overlap and 384-dimensional vector embeddings
              </p>
            </div>
          </div>

          <div className="space-y-3">
            {chunks.slice(0, 5).map((chunk) => (
              <div
                key={chunk.id}
                className="p-4 rounded-2xl border border-slate-800 bg-slate-900/30 space-y-2"
              >
                <div className="flex items-center justify-between text-xs">
                  <span className="font-mono text-emerald-400">
                    Chunk #{chunk.chunk_index} {chunk.chapter ? `• ${chunk.chapter}` : ""}{" "}
                    {chunk.section ? `• ${chunk.section}` : ""}
                  </span>
                  <span className="text-slate-500 font-mono">
                    {chunk.token_count} tokens {chunk.page_start ? `• Page ${chunk.page_start}` : ""}
                  </span>
                </div>
                <p className="text-xs text-slate-300 line-clamp-3 leading-relaxed">
                  {chunk.content}
                </p>
              </div>
            ))}

            {chunks.length > 5 && (
              <p className="text-center text-xs text-slate-500 pt-2">
                Showing first 5 of {chunks.length} total semantic chunks.
              </p>
            )}
          </div>
        </section>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        open={showDeleteDialog}
        onOpenChange={setShowDeleteDialog}
        title="Delete Document"
        description={`Are you sure you want to permanently delete "${doc.original_filename}"? This action cannot be undone.`}
        confirmLabel="Delete Document"
        variant="danger"
        isLoading={deleteMutation.isPending}
        onConfirm={async () => {
          await deleteMutation.mutateAsync();
        }}
      />
    </div>
  );
}
