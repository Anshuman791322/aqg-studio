"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState, useEffect, useMemo, Suspense } from "react";
import { apiClient, ApiClientError } from "@/lib/api-client";
import { DocumentData, TopicData } from "@/types/api";
import { useToast } from "@/components/ui/ToastContext";
import { Skeleton } from "@/components/ui/Skeleton";
import {
  AlertCircle,
  ArrowLeft,
  BookOpen,
  Check,
  FileText,
  Layers,
  Loader2,
  Sliders,
  Zap,
} from "lucide-react";

function AssessmentForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { success, error: toastError } = useToast();

  const preselectedDocId = searchParams.get("document_id") || "";

  // Form State
  const [selectedDocId, setSelectedDocId] = useState<string>(preselectedDocId);
  const [assessmentName, setAssessmentName] = useState<string>("");
  const [totalQuestions, setTotalQuestions] = useState<number>(10);
  const [customInstructions, setCustomInstructions] = useState<string>("");
  const [includeAnswers, setIncludeAnswers] = useState<boolean>(true);
  const [includeExplanations, setIncludeExplanations] = useState<boolean>(true);
  const [includeSources, setIncludeSources] = useState<boolean>(true);

  // Distribution State (percentages from 0 to 100)
  const [typeDist, setTypeDist] = useState({
    mcq_single: 60,
    mcq_multi: 10,
    true_false: 15,
    short_answer: 15,
    descriptive: 0,
  });

  const [diffDist, setDiffDist] = useState({
    easy: 30,
    medium: 50,
    hard: 20,
  });

  const [bloomDist, setBloomDist] = useState({
    remember: 20,
    understand: 30,
    apply: 25,
    analyze: 15,
    evaluate: 10,
    create: 0,
  });

  // Selected Topics
  const [selectedTopicIds, setSelectedTopicIds] = useState<string[]>([]);
  const [selectAllTopics, setSelectAllTopics] = useState<boolean>(true);

  // Error & Progress
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Queries
  const { data: docsResponse, isLoading: docsLoading } = useQuery({
    queryKey: ["documents"],
    queryFn: () => apiClient.listDocuments({ limit: 50 }),
  });

  const readyDocs = useMemo(
    () => (docsResponse?.data || []).filter((d: DocumentData) => d.status === "ready"),
    [docsResponse]
  );

  useEffect(() => {
    if (preselectedDocId) {
      setSelectedDocId(preselectedDocId);
    } else if (readyDocs.length > 0 && !selectedDocId) {
      setSelectedDocId(readyDocs[0].id);
    }
  }, [preselectedDocId, readyDocs, selectedDocId]);

  // Set default name when document changes
  useEffect(() => {
    if (selectedDocId && readyDocs.length > 0) {
      const doc = readyDocs.find((d) => d.id === selectedDocId);
      if (doc && !assessmentName) {
        const baseName = doc.original_filename.replace(/\.[^/.]+$/, "");
        setAssessmentName(`${baseName} - Assessment`);
      }
    }
  }, [selectedDocId, readyDocs, assessmentName]);

  // Analysis Query for Selected Document Topics
  const { data: analysisResponse } = useQuery({
    queryKey: ["documentAnalysis", selectedDocId],
    queryFn: () => apiClient.getDocumentAnalysis(selectedDocId),
    enabled: Boolean(selectedDocId),
  });

  const rawTopics = analysisResponse?.data?.topics;
  const topics: TopicData[] = useMemo(() => rawTopics || [], [rawTopics]);

  useEffect(() => {
    if (topics.length > 0 && selectAllTopics) {
      setSelectedTopicIds(topics.map((t) => t.id));
    }
  }, [topics, selectAllTopics]);

  // Live Distribution Sums
  const typeSum = Object.values(typeDist).reduce((a, b) => a + b, 0);
  const diffSum = Object.values(diffDist).reduce((a, b) => a + b, 0);
  const bloomSum = Object.values(bloomDist).reduce((a, b) => a + b, 0);

  const isValidDistribution = typeSum === 100 && diffSum === 100 && bloomSum === 100;

  // Create & Generate Mutation
  const createMutation = useMutation({
    mutationFn: async () => {
      if (!selectedDocId) throw new Error("Please select a source document.");
      if (!assessmentName.trim()) throw new Error("Please enter an assessment name.");
      if (!isValidDistribution) {
        throw new Error("All distribution categories (Type, Difficulty, Bloom) must total exactly 100%.");
      }

      // Normalize to float fractions 0.0 - 1.0
      const normTypeDist: Record<string, number> = {};
      Object.entries(typeDist).forEach(([k, v]) => {
        if (v > 0) normTypeDist[k] = v / 100;
      });

      const normDiffDist: Record<string, number> = {};
      Object.entries(diffDist).forEach(([k, v]) => {
        if (v > 0) normDiffDist[k] = v / 100;
      });

      const normBloomDist: Record<string, number> = {};
      Object.entries(bloomDist).forEach(([k, v]) => {
        if (v > 0) normBloomDist[k] = v / 100;
      });

      // 1. Create Assessment & Blueprint
      const createRes = await apiClient.createAssessment({
        document_id: selectedDocId,
        name: assessmentName.trim(),
        total_questions: totalQuestions,
        topic_ids: selectAllTopics ? undefined : selectedTopicIds,
        question_type_distribution: normTypeDist,
        difficulty_distribution: normDiffDist,
        bloom_distribution: normBloomDist,
        custom_instructions: customInstructions.trim() || undefined,
        include_answers: includeAnswers,
        include_explanations: includeExplanations,
        include_source_references: includeSources,
      });

      const assessmentId = createRes.data.assessment_id;

      // 2. Trigger asynchronous LangGraph generation job
      await apiClient.generateAssessment(assessmentId);

      return assessmentId;
    },
    onSuccess: (assessmentId) => {
      success("Assessment created and generation queued!");
      router.push(`/assessments/${assessmentId}/progress`);
    },
    onError: (err: unknown) => {
      const msg =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
          ? err.message
          : "Failed to configure assessment.";
      setErrorMessage(msg);
      toastError(msg);
    },
  });

  const toggleTopic = (topicId: string) => {
    setSelectAllTopics(false);
    setSelectedTopicIds((prev) =>
      prev.includes(topicId) ? prev.filter((id) => id !== topicId) : [...prev, topicId]
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Navigation & Header */}
        <div>
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-400 hover:text-white transition mb-3"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
          <div className="space-y-1">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white">
              Configure Assessment Blueprint
            </h1>
            <p className="text-sm text-slate-400">
              Calibrate cognitive taxonomy levels, item formats, and difficulty quotas before generation.
            </p>
          </div>
        </div>

        {/* Error Alert */}
        {errorMessage && (
          <div
            role="alert"
            className="p-4 rounded-2xl bg-rose-950/80 border border-rose-500/40 text-rose-200 text-xs flex items-start gap-3 animate-in fade-in"
          >
            <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
            <div className="flex-1">
              <div className="font-semibold">Configuration Error</div>
              <div className="mt-0.5 leading-relaxed">{errorMessage}</div>
            </div>
          </div>
        )}

        <form
          onSubmit={(e) => {
            e.preventDefault();
            createMutation.mutate();
          }}
          className="space-y-8"
        >
          {/* ----------------------------------------------------------------- */}
          {/* Card 1: Document & Core Info */}
          {/* ----------------------------------------------------------------- */}
          <div className="p-6 sm:p-8 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                <FileText className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">1. Source Document & Name</h2>
                <p className="text-xs text-slate-400">Select which ingested file to draw knowledge from</p>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300">
                  Source Document <span className="text-rose-400">*</span>
                </label>
                {docsLoading ? (
                  <div className="h-10 rounded-2xl bg-slate-800 animate-pulse" />
                ) : readyDocs.length === 0 ? (
                  <div className="p-3 rounded-2xl bg-slate-950 border border-slate-800 text-xs text-slate-400">
                    No ready documents. Please{" "}
                    <Link href="/documents/new" className="text-emerald-400 underline">
                      upload a document
                    </Link>{" "}
                    first.
                  </div>
                ) : (
                  <select
                    value={selectedDocId}
                    onChange={(e) => setSelectedDocId(e.target.value)}
                    className="w-full px-4 py-2.5 rounded-2xl border border-slate-800 bg-slate-950 text-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500 cursor-pointer"
                  >
                    {readyDocs.map((doc) => (
                      <option key={doc.id} value={doc.id}>
                        {doc.original_filename} ({doc.page_count} pages)
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="space-y-2">
                <label className="block text-xs font-semibold text-slate-300">
                  Assessment Name <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={assessmentName}
                  onChange={(e) => setAssessmentName(e.target.value)}
                  placeholder="e.g. Midterm Cell Biology Exam"
                  className="w-full px-4 py-2.5 rounded-2xl border border-slate-800 bg-slate-950 text-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
                />
              </div>
            </div>

            {/* Total Questions Slider */}
            <div className="space-y-3 pt-2 border-t border-slate-800/60">
              <div className="flex items-center justify-between">
                <label className="text-xs font-semibold text-slate-300">
                  Total Question Count:{" "}
                  <span className="text-emerald-400 font-bold">{totalQuestions}</span>
                </label>
                <span className="text-[11px] text-slate-500 font-mono">1 – 50 Items</span>
              </div>
              <input
                type="range"
                min="1"
                max="50"
                value={totalQuestions}
                onChange={(e) => setTotalQuestions(parseInt(e.target.value))}
                className="w-full accent-emerald-500 cursor-pointer"
              />
            </div>
          </div>

          {/* ----------------------------------------------------------------- */}
          {/* Card 2: Question Type Distribution */}
          {/* ----------------------------------------------------------------- */}
          <div className="p-6 sm:p-8 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="h-9 w-9 rounded-2xl bg-sky-500/10 text-sky-400 border border-sky-500/20 flex items-center justify-center">
                  <Sliders className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-base font-bold text-white">2. Question Type Allocation</h2>
                  <p className="text-xs text-slate-400">Specify proportion of item formats</p>
                </div>
              </div>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-mono font-bold ${
                  typeSum === 100
                    ? "bg-emerald-950/60 text-emerald-400 border border-emerald-800/40"
                    : "bg-rose-950/60 text-rose-400 border border-rose-800/40"
                }`}
              >
                Total: {typeSum}%
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 text-xs">
              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="flex justify-between font-semibold">
                  <span className="text-slate-200">Single-Select MCQ</span>
                  <span className="text-sky-400">{typeDist.mcq_single}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={typeDist.mcq_single}
                  onChange={(e) =>
                    setTypeDist({ ...typeDist, mcq_single: parseInt(e.target.value) })
                  }
                  className="w-full accent-sky-500"
                />
              </div>

              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="flex justify-between font-semibold">
                  <span className="text-slate-200">Multiple-Select MCQ</span>
                  <span className="text-sky-400">{typeDist.mcq_multi}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={typeDist.mcq_multi}
                  onChange={(e) =>
                    setTypeDist({ ...typeDist, mcq_multi: parseInt(e.target.value) })
                  }
                  className="w-full accent-sky-500"
                />
              </div>

              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="flex justify-between font-semibold">
                  <span className="text-slate-200">True / False</span>
                  <span className="text-sky-400">{typeDist.true_false}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={typeDist.true_false}
                  onChange={(e) =>
                    setTypeDist({ ...typeDist, true_false: parseInt(e.target.value) })
                  }
                  className="w-full accent-sky-500"
                />
              </div>

              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="flex justify-between font-semibold">
                  <span className="text-slate-200">Short Answer</span>
                  <span className="text-sky-400">{typeDist.short_answer}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={typeDist.short_answer}
                  onChange={(e) =>
                    setTypeDist({ ...typeDist, short_answer: parseInt(e.target.value) })
                  }
                  className="w-full accent-sky-500"
                />
              </div>

              <div className="p-4 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-2">
                <div className="flex justify-between font-semibold">
                  <span className="text-slate-200">Descriptive</span>
                  <span className="text-sky-400">{typeDist.descriptive}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  step="5"
                  value={typeDist.descriptive}
                  onChange={(e) =>
                    setTypeDist({ ...typeDist, descriptive: parseInt(e.target.value) })
                  }
                  className="w-full accent-sky-500"
                />
              </div>
            </div>
          </div>

          {/* ----------------------------------------------------------------- */}
          {/* Card 3: Difficulty & Bloom Taxonomy Distribution */}
          {/* ----------------------------------------------------------------- */}
          <div className="p-6 sm:p-8 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-2xl bg-violet-500/10 text-violet-400 border border-violet-500/20 flex items-center justify-center">
                <Layers className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">
                  3. Difficulty & Bloom&apos;s Taxonomy
                </h2>
                <p className="text-xs text-slate-400">Balance cognitive depth and challenge tiers</p>
              </div>
            </div>

            {/* Difficulty Tier */}
            <div className="space-y-3">
              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-slate-300">Difficulty Distribution</span>
                <span
                  className={`font-mono ${
                    diffSum === 100 ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  Total: {diffSum}%
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div className="p-3 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1">
                  <div className="flex justify-between text-slate-300 font-medium">
                    <span>Easy</span>
                    <span className="text-emerald-400">{diffDist.easy}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={diffDist.easy}
                    onChange={(e) => setDiffDist({ ...diffDist, easy: parseInt(e.target.value) })}
                    className="w-full accent-emerald-500"
                  />
                </div>
                <div className="p-3 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1">
                  <div className="flex justify-between text-slate-300 font-medium">
                    <span>Medium</span>
                    <span className="text-sky-400">{diffDist.medium}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={diffDist.medium}
                    onChange={(e) =>
                      setDiffDist({ ...diffDist, medium: parseInt(e.target.value) })
                    }
                    className="w-full accent-sky-500"
                  />
                </div>
                <div className="p-3 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1">
                  <div className="flex justify-between text-slate-300 font-medium">
                    <span>Hard</span>
                    <span className="text-violet-400">{diffDist.hard}%</span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    step="5"
                    value={diffDist.hard}
                    onChange={(e) => setDiffDist({ ...diffDist, hard: parseInt(e.target.value) })}
                    className="w-full accent-violet-500"
                  />
                </div>
              </div>
            </div>

            {/* Bloom Taxonomy */}
            <div className="space-y-3 pt-4 border-t border-slate-800/60">
              <div className="flex justify-between items-center text-xs font-semibold">
                <span className="text-slate-300">Bloom&apos;s Taxonomy Distribution</span>
                <span
                  className={`font-mono ${
                    bloomSum === 100 ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  Total: {bloomSum}%
                </span>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 text-xs">
                {(["remember", "understand", "apply", "analyze", "evaluate", "create"] as const).map(
                  (level) => (
                    <div
                      key={level}
                      className="p-3 rounded-2xl bg-slate-950/60 border border-slate-800 space-y-1"
                    >
                      <div className="flex justify-between text-slate-300 font-medium capitalize">
                        <span>{level}</span>
                        <span className="text-violet-400">{bloomDist[level]}%</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="100"
                        step="5"
                        value={bloomDist[level]}
                        onChange={(e) =>
                          setBloomDist({ ...bloomDist, [level]: parseInt(e.target.value) })
                        }
                        className="w-full accent-violet-500"
                      />
                    </div>
                  )
                )}
              </div>
            </div>
          </div>

          {/* ----------------------------------------------------------------- */}
          {/* Card 4: Topic Selection & Instructions */}
          {/* ----------------------------------------------------------------- */}
          <div className="p-6 sm:p-8 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-9 w-9 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/20 flex items-center justify-center">
                <BookOpen className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white">4. Topic Selection & Options</h2>
                <p className="text-xs text-slate-400">Target specific extracted chapters or topics</p>
              </div>
            </div>

            {topics.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-300">Covered Topics</span>
                  <button
                    type="button"
                    onClick={() => {
                      if (selectAllTopics) {
                        setSelectAllTopics(false);
                        setSelectedTopicIds([]);
                      } else {
                        setSelectAllTopics(true);
                        setSelectedTopicIds(topics.map((t) => t.id));
                      }
                    }}
                    className="text-emerald-400 hover:underline"
                  >
                    {selectAllTopics ? "Deselect All" : "Select All"}
                  </button>
                </div>
                <div className="flex flex-wrap gap-2">
                  {topics.map((t) => {
                    const isSelected = selectedTopicIds.includes(t.id);
                    return (
                      <button
                        key={t.id}
                        type="button"
                        onClick={() => toggleTopic(t.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-medium border transition flex items-center gap-1.5 cursor-pointer ${
                          isSelected
                            ? "bg-emerald-950/60 border-emerald-500/50 text-emerald-300"
                            : "bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200"
                        }`}
                      >
                        {isSelected && <Check className="h-3.5 w-3.5 text-emerald-400" />}
                        <span>{t.name}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Custom Instructions */}
            <div className="space-y-2">
              <label className="block text-xs font-semibold text-slate-300">
                Custom Pedagogical Instructions (Optional)
              </label>
              <textarea
                rows={2}
                maxLength={500}
                value={customInstructions}
                onChange={(e) => setCustomInstructions(e.target.value)}
                placeholder="e.g. Focus on mitochondrial dysfunction and clinical applications. Avoid questions about history."
                className="w-full px-4 py-2.5 rounded-2xl border border-slate-800 bg-slate-950 text-slate-200 text-xs focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>

            {/* Inclusions */}
            <div className="pt-2 border-t border-slate-800/60 flex flex-wrap gap-6 text-xs text-slate-300">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeAnswers}
                  onChange={(e) => setIncludeAnswers(e.target.checked)}
                  className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                />
                <span>Include Correct Answers</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeExplanations}
                  onChange={(e) => setIncludeExplanations(e.target.checked)}
                  className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                />
                <span>Include Explanations</span>
              </label>

              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={includeSources}
                  onChange={(e) => setIncludeSources(e.target.checked)}
                  className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                />
                <span>Include Source Chunks</span>
              </label>
            </div>
          </div>

          {/* Action Row */}
          <div className="flex items-center justify-end gap-4 pt-4">
            <Link
              href="/dashboard"
              className="px-5 py-2.5 rounded-2xl text-xs font-medium text-slate-400 hover:text-white hover:bg-slate-800 transition"
            >
              Cancel
            </Link>
            <button
              type="submit"
              disabled={createMutation.isPending || !isValidDistribution || !selectedDocId}
              className="inline-flex items-center gap-2 px-7 py-3 rounded-2xl text-xs font-semibold text-slate-950 bg-emerald-500 hover:bg-emerald-400 transition shadow-lg shadow-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              {createMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Generating Blueprints...
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Generate Assessment ({totalQuestions} Items)
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function NewAssessmentPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
          <div className="max-w-4xl mx-auto space-y-8">
            <Skeleton className="h-6 w-32" />
            <Skeleton className="h-10 w-80" />
            <div className="space-y-6">
              <Skeleton className="h-48 w-full rounded-3xl" />
              <Skeleton className="h-48 w-full rounded-3xl" />
            </div>
          </div>
        </div>
      }
    >
      <AssessmentForm />
    </Suspense>
  );
}
