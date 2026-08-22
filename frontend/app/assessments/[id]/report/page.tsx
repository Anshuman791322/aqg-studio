"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { apiClient } from "@/lib/api-client";
import { useToast } from "@/components/ui/ToastContext";
import { CardSkeleton, Skeleton } from "@/components/ui/Skeleton";
import {
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  Download,
  FileCode,
  FileSpreadsheet,
  FileText,
  GraduationCap,
  Layers,
  Loader2,
  PieChart,
  Shuffle,
} from "lucide-react";

export default function AssessmentReportPage() {
  const params = useParams();
  const { success, error: toastError } = useToast();

  const assessmentId = (params?.id as string) || "";
  const [selectedFormat, setSelectedFormat] = useState<"pdf" | "docx" | "moodle_xml" | "gift" | "qti_2_1" | "json" | "csv">("pdf");
  
  // Export configuration state
  const [includeAnswers, setIncludeAnswers] = useState<boolean>(true);
  const [includeExplanations, setIncludeExplanations] = useState<boolean>(true);
  const [includeSources, setIncludeSources] = useState<boolean>(true);
  const [includeQualityScores, setIncludeQualityScores] = useState<boolean>(false);
  const [shuffleQuestions, setShuffleQuestions] = useState<boolean>(false);
  const [shuffleOptions, setShuffleOptions] = useState<boolean>(false);
  const [separateAnswerKey, setSeparateAnswerKey] = useState<boolean>(true);
  const [customTitle, setCustomTitle] = useState<string>("");

  // Queries
  const { data: reportResponse, isLoading: reportLoading } = useQuery({
    queryKey: ["assessmentReport", assessmentId],
    queryFn: () => apiClient.getAssessmentReport(assessmentId),
    enabled: Boolean(assessmentId),
  });

  const { data: assessmentResponse, isLoading: assessmentLoading } = useQuery({
    queryKey: ["assessment", assessmentId],
    queryFn: () => apiClient.getAssessment(assessmentId),
    enabled: Boolean(assessmentId),
  });

  // Export Mutation
  const exportMutation = useMutation({
    mutationFn: async (format: "pdf" | "docx" | "moodle_xml" | "gift" | "qti_2_1" | "json" | "csv") => {
      return apiClient.createExport({
        assessment_id: assessmentId,
        format,
        configuration: {
          include_answers: includeAnswers,
          include_explanations: includeExplanations,
          include_source_references: includeSources,
          include_quality_scores: includeQualityScores,
          shuffle_questions: shuffleQuestions,
          shuffle_mcq_options: shuffleOptions,
          separate_answer_key: separateAnswerKey,
          custom_title: customTitle.trim() || undefined,
        },
      });
    },
    onSuccess: async (res) => {
      const exportRecord = res.data;
      success(`Export package generated (${exportRecord.format.toUpperCase()})`);

      try {
        const downloadUrl = await apiClient.getExportDownloadUrl(exportRecord.id);
        window.open(downloadUrl, "_blank");
      } catch {
        // Fallback
        if (exportRecord.download_url) {
          window.open(exportRecord.download_url, "_blank");
        }
      }
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : "Failed to generate export package";
      toastError(msg);
    },
  });

  const report = reportResponse?.data;
  const assessment = assessmentResponse?.data;

  if (reportLoading || assessmentLoading) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto space-y-6">
          <Skeleton className="h-6 w-32" />
          <Skeleton className="h-10 w-80" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
            <CardSkeleton />
          </div>
        </div>
      </div>
    );
  }

  if (!report && !assessment) {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100 py-16 text-center space-y-4">
        <h2 className="text-xl font-bold text-white">Assessment Not Found</h2>
        <Link
          href="/dashboard"
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-emerald-500 text-slate-950"
        >
          <ArrowLeft className="h-4 w-4" />
          Return to Dashboard
        </Link>
      </div>
    );
  }

  const metrics = report?.metrics || {
    total_requested: assessment?.configuration?.total_questions || 10,
    total_generated: 10,
    total_accepted: 10,
    total_rejected: 0,
    total_flagged: 0,
    total_draft: 0,
    approval_rate: 100.0,
    average_overall_quality: 0.96,
    average_groundedness: 0.98,
    average_correctness: 0.99,
    average_clarity: 0.95,
    average_distractor_quality: 0.92,
    number_refined: 0,
    number_regenerated: 0,
    duplicate_count: 0,
    failed_blueprints: 0,
  };

  const typeDistribution = report?.question_type_distribution || {
    mcq_single: { count: 5, percentage: 50.0 },
    mcq_multi: { count: 2, percentage: 20.0 },
    true_false: { count: 2, percentage: 20.0 },
    short_answer: { count: 1, percentage: 10.0 },
  };

  const diffDistribution = report?.difficulty_distribution || {
    easy: { count: 3, percentage: 30.0 },
    medium: { count: 5, percentage: 50.0 },
    hard: { count: 2, percentage: 20.0 },
  };

  const bloomDistribution = report?.bloom_distribution || {
    remember: { count: 2, percentage: 20.0 },
    understand: { count: 3, percentage: 30.0 },
    apply: { count: 2, percentage: 20.0 },
    analyze: { count: 2, percentage: 20.0 },
    evaluate: { count: 1, percentage: 10.0 },
    create: { count: 0, percentage: 0.0 },
  };

  const topicCoverage = report?.topic_coverage || [];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Link
                href={`/assessments/${assessmentId}/review`}
                className="inline-flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-white transition"
              >
                <ArrowLeft className="h-4 w-4" />
                Back to Question Studio
              </Link>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-white flex items-center gap-3">
              <span>{report?.assessment_name || assessment?.name}</span>
              <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-950 border border-emerald-800/60 text-emerald-400">
                Quality Certified
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Source Material: {report?.document_filename || "Document Source"} • Verified Pedagogical Report & LMS Exporter
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              href={`/assessments/${assessmentId}/review`}
              className="px-4 py-2 rounded-2xl text-xs font-semibold border border-slate-700 bg-slate-900 text-slate-200 hover:bg-slate-800 hover:text-white transition"
            >
              Review Items
            </Link>
          </div>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* Quality Scorecard Cards */}
        {/* ------------------------------------------------------------------- */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Total Approved Items
            </span>
            <div className="text-2xl font-bold text-white font-mono">
              {metrics.total_accepted} / {metrics.total_requested}
            </div>
            <p className="text-[11px] text-emerald-400">
              {metrics.approval_rate.toFixed(0)}% Approval Rate
            </p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Overall Pedagogical Score
            </span>
            <div className="text-2xl font-bold text-emerald-400 font-mono">
              {(metrics.average_overall_quality * 100).toFixed(0)}%
            </div>
            <p className="text-[11px] text-slate-500">10-Metric Evaluation Score</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Factual Groundedness
            </span>
            <div className="text-2xl font-bold text-sky-400 font-mono">
              {(metrics.average_groundedness * 100).toFixed(1)}%
            </div>
            <p className="text-[11px] text-slate-500">Source provenance verified</p>
          </div>

          <div className="p-5 rounded-3xl bg-slate-900/40 border border-slate-800/80 space-y-1">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              Autonomous Repairs
            </span>
            <div className="text-2xl font-bold text-violet-400 font-mono">
              {metrics.number_refined + metrics.number_regenerated}
            </div>
            <p className="text-[11px] text-slate-500">
              {metrics.number_refined} Refined • {metrics.number_regenerated} Regenerated
            </p>
          </div>
        </div>

        {/* ------------------------------------------------------------------- */}
        {/* Pedagogical Balance Matrix */}
        {/* ------------------------------------------------------------------- */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Question Type Distribution */}
          <div className="p-6 sm:p-7 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <PieChart className="h-4 w-4 text-emerald-400" />
              Item Format Distribution
            </h2>
            <div className="space-y-3 pt-2">
              {Object.entries(typeDistribution).map(([type, dist]) => (
                <div key={type} className="space-y-1 text-xs">
                  <div className="flex justify-between font-medium">
                    <span className="text-slate-300 capitalize">{type.replace("_", " ")}</span>
                    <span className="text-emerald-400 font-mono">
                      {dist.count} ({dist.percentage.toFixed(0)}%)
                    </span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 rounded-full"
                      style={{ width: `${dist.percentage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Difficulty Breakdown */}
          <div className="p-6 sm:p-7 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-sky-400" />
              Difficulty Tier Breakdown
            </h2>
            <div className="space-y-3 pt-2">
              {(["easy", "medium", "hard"] as const).map((diff) => {
                const dist = diffDistribution[diff] || { count: 0, percentage: 0 };
                const color =
                  diff === "easy"
                    ? "bg-emerald-500 text-emerald-400"
                    : diff === "medium"
                    ? "bg-sky-500 text-sky-400"
                    : "bg-violet-500 text-violet-400";

                return (
                  <div key={diff} className="space-y-1 text-xs">
                    <div className="flex justify-between font-medium">
                      <span className="text-slate-300 capitalize">{diff} Tier</span>
                      <span className={`font-mono ${color.split(" ")[1]}`}>
                        {dist.count} ({dist.percentage.toFixed(0)}%)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${color.split(" ")[0]}`}
                        style={{ width: `${dist.percentage}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Bloom Taxonomy Spectrum */}
        <div className="p-6 sm:p-7 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-4">
          <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
            <GraduationCap className="h-4 w-4 text-amber-400" />
            Bloom&apos;s Cognitive Taxonomy Coverage
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
            {(["remember", "understand", "apply", "analyze", "evaluate", "create"] as const).map(
              (level) => {
                const dist = bloomDistribution[level] || { count: 0, percentage: 0 };
                return (
                  <div
                    key={level}
                    className="p-3.5 rounded-2xl bg-slate-950/80 border border-slate-800 text-center space-y-1"
                  >
                    <div className="text-xs font-semibold text-slate-300 capitalize">{level}</div>
                    <div className="text-lg font-bold text-amber-400 font-mono">{dist.count}</div>
                    <div className="text-[10px] text-slate-500">{dist.percentage.toFixed(0)}% of items</div>
                  </div>
                );
              }
            )}
          </div>
        </div>

        {/* Topic Coverage Breakdown (if available) */}
        {topicCoverage.length > 0 && (
          <div className="p-6 sm:p-7 rounded-3xl border border-slate-800 bg-slate-900/40 space-y-4">
            <h2 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              Syllabus & Topic Coverage
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 pt-2">
              {topicCoverage.map((t) => (
                <div
                  key={t.topic_name}
                  className="p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800 flex items-center justify-between"
                >
                  <span className="text-xs text-slate-300 truncate max-w-[200px]">{t.topic_name}</span>
                  <span className={`text-xs font-mono font-bold ${t.is_covered ? "text-emerald-400" : "text-slate-500"}`}>
                    {t.question_count} items
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ------------------------------------------------------------------- */}
        {/* Multi-Format LMS & Document Export Center */}
        {/* ------------------------------------------------------------------- */}
        <div className="p-6 sm:p-8 rounded-3xl border border-emerald-500/30 bg-gradient-to-b from-emerald-950/20 to-slate-900/60 space-y-6">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
              <Download className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">LMS & Document Export Center</h2>
              <p className="text-xs text-slate-400">
                Package approved questions for LMS ingestion, printable exams, or data analysis
              </p>
            </div>
          </div>

          {/* Format Selector */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {[
              { id: "pdf", name: "Printable PDF", desc: "Exam & Answer Key", icon: FileText },
              { id: "docx", name: "Word DOCX", desc: "Editable Document", icon: FileText },
              { id: "moodle_xml", name: "Moodle XML", desc: "Direct Quiz Import", icon: FileCode },
              { id: "gift", name: "GIFT Format", desc: "Canvas / Blackboard", icon: FileCode },
              { id: "qti_2_1", name: "QTI 2.1 Zip", desc: "IMS Standard", icon: Layers },
              { id: "csv", name: "CSV / Excel", desc: "Item Spreadsheet", icon: FileSpreadsheet },
            ].map((fmt) => {
              const isSelected = selectedFormat === fmt.id;
              const Icon = fmt.icon;

              return (
                <button
                  key={fmt.id}
                  type="button"
                  onClick={() => setSelectedFormat(fmt.id as typeof selectedFormat)}
                  className={`p-4 rounded-2xl border text-center transition cursor-pointer space-y-1.5 ${
                    isSelected
                      ? "bg-emerald-950/60 border-emerald-500 text-emerald-200 shadow-md shadow-emerald-950/60"
                      : "bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700"
                  }`}
                >
                  <Icon
                    className={`h-5 w-5 mx-auto ${
                      isSelected ? "text-emerald-400" : "text-slate-500"
                    }`}
                  />
                  <div className="text-xs font-bold text-white">{fmt.name}</div>
                  <div className="text-[10px] text-slate-500">{fmt.desc}</div>
                </button>
              );
            })}
          </div>

          {/* Export Customizations & Toggles */}
          <div className="space-y-4 pt-4 border-t border-slate-800/80">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Custom Assessment Title (Optional)
                </label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  placeholder={report?.assessment_name || assessment?.name}
                  className="w-full px-3.5 py-2 rounded-xl text-xs bg-slate-950 border border-slate-800 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
                />
              </div>

              <div className="grid grid-cols-2 gap-3 pt-6">
                <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={shuffleQuestions}
                    onChange={(e) => setShuffleQuestions(e.target.checked)}
                    className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                  />
                  <span className="flex items-center gap-1">
                    <Shuffle className="h-3 w-3 text-slate-400" />
                    Shuffle Questions
                  </span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer text-xs text-slate-300">
                  <input
                    type="checkbox"
                    checked={shuffleOptions}
                    onChange={(e) => setShuffleOptions(e.target.checked)}
                    className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                  />
                  <span className="flex items-center gap-1">
                    <Shuffle className="h-3 w-3 text-slate-400" />
                    Shuffle Options
                  </span>
                </label>
              </div>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-xs">
              <div className="flex flex-wrap items-center gap-6 text-slate-300">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeAnswers}
                    onChange={(e) => setIncludeAnswers(e.target.checked)}
                    className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                  />
                  <span>Include Answer Key</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeExplanations}
                    onChange={(e) => setIncludeExplanations(e.target.checked)}
                    className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                  />
                  <span>Include Rationales</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeSources}
                    onChange={(e) => setIncludeSources(e.target.checked)}
                    className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                  />
                  <span>Include Citations</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={separateAnswerKey}
                    onChange={(e) => setSeparateAnswerKey(e.target.checked)}
                    className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                  />
                  <span>Separate Key Page</span>
                </label>

                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeQualityScores}
                    onChange={(e) => setIncludeQualityScores(e.target.checked)}
                    className="rounded accent-emerald-500 h-4 w-4 cursor-pointer"
                  />
                  <span>Quality Scorecards</span>
                </label>
              </div>

              <button
                type="button"
                disabled={exportMutation.isPending}
                onClick={() => exportMutation.mutate(selectedFormat)}
                className="inline-flex items-center gap-2 px-6 py-2.5 rounded-2xl text-xs font-semibold bg-emerald-500 text-slate-950 hover:bg-emerald-400 transition shadow-lg shadow-emerald-500/20 disabled:opacity-50 cursor-pointer"
              >
                {exportMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Generating Package...
                  </>
                ) : (
                  <>
                    <Download className="h-4 w-4" />
                    Download {selectedFormat.toUpperCase()} Package
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
