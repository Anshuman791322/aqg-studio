"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/components/ui/ToastContext";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  Cpu,
  Loader2,
  RefreshCw,
  StopCircle,
  XCircle,
} from "lucide-react";

const PIPELINE_STAGES = [
  {
    key: "blueprint",
    label: "1. Question Planning & Blueprint",
    description: "Allocating Bloom taxonomy levels and difficulty quotas",
  },
  {
    key: "generation",
    label: "2. Batched Generation & RAG Retrieval",
    description: "Retrieving semantic chunks and drafting grounded stems",
  },
  {
    key: "evaluation",
    label: "3. 10-Metric Quality Evaluation",
    description: "Scoring grounding, clarity, and distractor plausibility",
  },
  {
    key: "refinement",
    label: "4. Adversarial Refinement & Repair",
    description: "Repairing borderline items and regenerating failures",
  },
  {
    key: "deduplication",
    label: "5. Duplicate Control & Quota Verification",
    description: "Eliminating peer duplicates and balancing target count",
  },
  {
    key: "finalize",
    label: "6. Assessment Ready",
    description: "Finalizing metrics and compiling scorecards",
  },
];

export default function AssessmentProgressPage() {
  const params = useParams();
  const router = useRouter();
  const { success, error: toastError } = useToast();

  const assessmentId = (params?.id as string) || "";
  const [showCancelDialog, setShowCancelDialog] = useState(false);

  // Poll Job Status
  const {
    data: statusResponse,
    refetch: refetchStatus,
  } = useQuery({
    queryKey: ["assessmentStatus", assessmentId],
    queryFn: () => apiClient.getAssessmentStatus(assessmentId),
    enabled: Boolean(assessmentId),
    refetchInterval: (query) => {
      const status = query.state.data?.data?.status;
      // Continue polling while queued or running
      return status === "queued" || status === "running" ? 2500 : false;
    },
  });

  // Assessment Info Query
  const { data: assessmentResponse } = useQuery({
    queryKey: ["assessment", assessmentId],
    queryFn: () => apiClient.getAssessment(assessmentId),
    enabled: Boolean(assessmentId),
  });

  const job = statusResponse?.data;
  const assessment = assessmentResponse?.data;

  // Auto-navigate to review when ready
  useEffect(() => {
    if (job?.status === "completed" || assessment?.status === "ready") {
      const timer = setTimeout(() => {
        router.push(`/assessments/${assessmentId}/review`);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [job?.status, assessment?.status, assessmentId, router]);

  // Cancel Mutation
  const cancelMutation = useMutation({
    mutationFn: () => apiClient.cancelAssessment(assessmentId),
    onSuccess: () => {
      success("Generation job cancelled");
      setShowCancelDialog(false);
      refetchStatus();
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to cancel job";
      toastError(msg);
    },
  });

  const isCompleted = job?.status === "completed" || assessment?.status === "ready";
  const isFailed = job?.status === "failed" || assessment?.status === "failed";
  const isRunning = job?.status === "running" || job?.status === "queued";

  const progress = job?.progress || assessment?.progress || 0;
  const currentStep = job?.current_step || "Queued";
  const targetCount = job?.target_questions || assessment?.configuration?.total_questions || 0;
  const acceptedCount = job?.accepted_questions || assessment?.metrics?.accepted_questions || 0;

  // Calculate Active Stage Index
  let activeStageIndex = 0;
  if (currentStep.includes("blueprint") || currentStep.includes("load")) activeStageIndex = 0;
  else if (currentStep.includes("generate") || currentStep.includes("batch")) activeStageIndex = 1;
  else if (currentStep.includes("eval")) activeStageIndex = 2;
  else if (currentStep.includes("refine") || currentStep.includes("regen")) activeStageIndex = 3;
  else if (currentStep.includes("dedup") || currentStep.includes("count")) activeStageIndex = 4;
  else if (isCompleted) activeStageIndex = 5;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <div className="inline-flex items-center gap-1.5 px-3 py-0.5 rounded-full text-xs font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/30">
              <Cpu className="h-3.5 w-3.5" />
              LangGraph State Orchestrator
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              {assessment?.name || "Generating Assessment"}
            </h1>
            <p className="text-xs text-slate-400">
              Session ID: <span className="font-mono text-slate-300">{assessmentId}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => refetchStatus()}
              className="p-2.5 rounded-2xl border border-slate-800 bg-slate-900 text-slate-400 hover:text-white hover:bg-slate-800 transition cursor-pointer"
              title="Refresh status"
            >
              <RefreshCw className={`h-4 w-4 ${isRunning ? "animate-spin" : ""}`} />
            </button>
            {isRunning && (
              <button
                type="button"
                onClick={() => setShowCancelDialog(true)}
                className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-2xl text-xs font-medium text-rose-400 hover:text-rose-300 bg-rose-950/40 border border-rose-800/40 transition cursor-pointer"
              >
                <StopCircle className="h-3.5 w-3.5" />
                Cancel
              </button>
            )}
          </div>
        </div>

        {/* Cold-Start Notice for Free Instances */}
        {isRunning && progress < 15 && (
          <div className="p-4 rounded-2xl bg-amber-950/40 border border-amber-500/30 text-amber-200 text-xs flex items-start gap-3">
            <Clock className="h-5 w-5 shrink-0 text-amber-400 mt-0.5" />
            <div className="leading-relaxed">
              <span className="font-semibold">Render Free Instance Wakeup:</span> If the backend was sleeping, the initial cold start takes ~20–30 seconds. Your job is tracked in PostgreSQL and will not be lost.
            </div>
          </div>
        )}

        {/* Failure / Cancelled Alert */}
        {isFailed && (
          <div className="p-6 rounded-3xl bg-rose-950/40 border border-rose-500/40 space-y-3">
            <div className="flex items-center gap-3 text-rose-300 font-bold">
              <XCircle className="h-6 w-6 text-rose-400" />
              <span>Generation Workflow Failed</span>
            </div>
            <p className="text-xs text-rose-200 leading-relaxed">
              {job?.error_message || "An unexpected error occurred during item generation. Please check your document and retry."}
            </p>
            <div className="pt-2">
              <Link
                href="/assessments/new"
                className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-rose-500 text-white hover:bg-rose-400 transition"
              >
                Configure New Assessment
              </Link>
            </div>
          </div>
        )}

        {/* Completed Alert */}
        {isCompleted && (
          <div className="p-6 rounded-3xl bg-emerald-950/40 border border-emerald-500/40 space-y-3 animate-in fade-in">
            <div className="flex items-center gap-3 text-emerald-300 font-bold">
              <CheckCircle2 className="h-6 w-6 text-emerald-400" />
              <span>All Questions Generated & Evaluated!</span>
            </div>
            <p className="text-xs text-emerald-200 leading-relaxed">
              {acceptedCount} of {targetCount} calibrated questions accepted and ready for review. Redirecting to Question Review Studio...
            </p>
            <div className="pt-2">
              <Link
                href={`/assessments/${assessmentId}/review`}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-2xl text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition shadow-md"
              >
                Open Question Review Studio
                <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
          </div>
        )}

        {/* Progress Bar Card */}
        <div className="p-6 sm:p-8 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Current Pipeline Step
              </span>
              <div className="text-lg font-bold text-white mt-0.5">{currentStep}</div>
            </div>
            <div className="text-right">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Questions Accepted
              </span>
              <div className="text-lg font-bold text-emerald-400 mt-0.5 font-mono">
                {acceptedCount} / {targetCount}
              </div>
            </div>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between text-xs text-slate-400 font-mono">
              <span>Progress</span>
              <span>{progress.toFixed(0)}%</span>
            </div>
            <div className="h-3 w-full rounded-full bg-slate-800 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  isCompleted
                    ? "bg-emerald-500"
                    : isFailed
                    ? "bg-rose-500"
                    : "bg-gradient-to-r from-sky-500 to-emerald-500"
                }`}
                style={{ width: `${Math.max(5, progress)}%` }}
              />
            </div>
          </div>
        </div>

        {/* 6-Stage Timeline */}
        <div className="space-y-3">
          <h2 className="text-sm font-bold text-slate-300 uppercase tracking-wider">
            Pipeline Execution Stages
          </h2>

          <div className="space-y-3">
            {PIPELINE_STAGES.map((stage, idx) => {
              const isPast = activeStageIndex > idx || isCompleted;
              const isCurrent = activeStageIndex === idx && isRunning;

              return (
                <div
                  key={stage.key}
                  className={`p-4 rounded-2xl border transition-all flex items-start gap-4 ${
                    isPast
                      ? "border-emerald-500/30 bg-emerald-950/10 text-slate-300"
                      : isCurrent
                      ? "border-sky-500/50 bg-sky-950/20 text-white shadow-lg shadow-sky-950/50"
                      : "border-slate-800/80 bg-slate-900/20 text-slate-500 opacity-60"
                  }`}
                >
                  <div className="mt-0.5 shrink-0">
                    {isPast ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-400" />
                    ) : isCurrent ? (
                      <Loader2 className="h-5 w-5 text-sky-400 animate-spin" />
                    ) : (
                      <div className="h-5 w-5 rounded-full border border-slate-700 flex items-center justify-center text-[10px] font-mono text-slate-500">
                        {idx + 1}
                      </div>
                    )}
                  </div>

                  <div className="flex-1">
                    <div className="text-xs font-bold">{stage.label}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">{stage.description}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Cancel Confirmation Modal */}
      <ConfirmDialog
        open={showCancelDialog}
        onOpenChange={setShowCancelDialog}
        title="Cancel Assessment Generation"
        description="Are you sure you want to stop question generation? Any questions generated so far will remain in draft state."
        confirmLabel="Cancel Job"
        variant="warning"
        isLoading={cancelMutation.isPending}
        onConfirm={async () => {
          await cancelMutation.mutateAsync();
        }}
      />
    </div>
  );
}
