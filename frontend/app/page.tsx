import Link from "next/link";
import {
  UploadCloud,
  Cpu,
  CheckCircle2,
  Download,
  Sparkles,
  ShieldCheck,
  ArrowRight,
  BookCheck,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col space-y-24 pb-20">
      {/* --------------------------------------------------------------------- */}
      {/* 1. HERO SECTION */}
      {/* --------------------------------------------------------------------- */}
      <section className="relative overflow-hidden pt-12 pb-8 md:pt-20 md:pb-16">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-950/40 via-slate-950 to-slate-950 pointer-events-none"></div>

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-6 max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold text-emerald-400">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Multi-Agent Cognitive Assessment Engine</span>
            </div>

            <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-6xl md:text-7xl">
              Turn Learning Materials into{" "}
              <span className="gradient-text">Grounded Assessments</span>
            </h1>

            <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
              AQG Studio uses a 6-agent LangGraph pipeline to transform raw PDFs, Word docs, PowerPoint decks, and notes into pedagogically rigorous questions with automated quality scoring.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link
                href="#workflow"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-7 py-3.5 text-base font-semibold text-slate-950 transition hover:bg-emerald-400 shadow-lg shadow-emerald-500/25"
              >
                Explore Assessment Pipeline
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="#architecture"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/90 px-7 py-3.5 text-base font-medium text-slate-300 transition hover:bg-slate-800"
              >
                View System Architecture
              </Link>
            </div>
          </div>

          {/* Interactive Pipeline Teaser Mockup */}
          <div className="mt-16 rounded-2xl border border-slate-800 bg-slate-900/60 p-4 sm:p-6 shadow-2xl backdrop-blur-xl max-w-5xl mx-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
              <div className="flex items-center space-x-2">
                <div className="h-3 w-3 rounded-full bg-rose-500/80"></div>
                <div className="h-3 w-3 rounded-full bg-amber-500/80"></div>
                <div className="h-3 w-3 rounded-full bg-emerald-500/80"></div>
                <span className="text-xs text-slate-500 font-mono ml-2">
                  aqg-studio-core // generation-stream
                </span>
              </div>
              <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 rounded px-2 py-0.5">
                LangGraph State: EVALUATED
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
              <div className="rounded-lg bg-slate-950/80 border border-slate-800 p-4 space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Source Provenance
                </div>
                <div className="text-sm font-medium text-slate-200">
                  Chapter 4: Cell Bio.pdf
                </div>
                <div className="text-xs text-emerald-400 font-mono">
                  Chunk #18 (Page 24, ¶3)
                </div>
                <p className="text-xs text-slate-400 italic bg-slate-900 p-2 rounded border border-slate-800">
                  &ldquo;Mitochondria synthesize ATP through oxidative phosphorylation using the proton gradient across the inner membrane.&rdquo;
                </p>
              </div>

              <div className="rounded-lg bg-slate-950/80 border border-slate-800 p-4 space-y-2 md:col-span-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                    Generated MCQ (Bloom: Analyze | Hard)
                  </span>
                  <span className="text-xs font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded">
                    Scorecard: 4.9/5.0
                  </span>
                </div>
                <div className="text-sm font-semibold text-white">
                  If the inner mitochondrial membrane becomes permeable to protons, which metabolic outcome will occur first?
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1">
                  <div className="p-2 rounded bg-emerald-950/40 border border-emerald-500/50 text-emerald-300 font-medium">
                    ✓ A. ATP synthesis decreases while heat production increases
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    ✕ B. Glycolysis immediately terminates
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    ✕ C. Oxygen consumption immediately drops to zero
                  </div>
                  <div className="p-2 rounded bg-slate-900 border border-slate-800 text-slate-400">
                    ✕ D. The citric acid cycle halts
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------- */}
      {/* 2. THE 4-STEP CORE WORKFLOW */}
      {/* --------------------------------------------------------------------- */}
      <section id="workflow" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center space-y-4 mb-16">
          <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
            End-to-End Execution
          </span>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Four Steps to Pedagogically Rigorous Assessments
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            From raw unstructured files to verified question banks formatted for your Learning Management System.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Step 1 */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4 hover:border-emerald-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <UploadCloud className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-emerald-400 font-bold">
              STEP 01
            </div>
            <h3 className="text-lg font-bold text-white">
              Upload Learning Material
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Upload PDF, Word (.docx), PowerPoint (.pptx), or plain text documents. The ingestion engine parses layout hierarchies, page offsets, and slides deterministically.
            </p>
          </div>

          {/* Step 2 */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4 hover:border-emerald-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-sky-500/10 text-sky-400 border border-sky-500/30">
              <Cpu className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-sky-400 font-bold">
              STEP 02
            </div>
            <h3 className="text-lg font-bold text-white">
              Automatically Generate Questions
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Configure your assessment blueprint: Bloom’s Taxonomy levels, difficulty tiers (Easy/Med/Hard), and item types. LangGraph orchestrates chunk-level RAG generation with multi-provider fallback.
            </p>
          </div>

          {/* Step 3 */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4 hover:border-emerald-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-violet-500/10 text-violet-400 border border-violet-500/30">
              <BookCheck className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-violet-400 font-bold">
              STEP 03
            </div>
            <h3 className="text-lg font-bold text-white">
              Review Answers & Citations
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Inspect automated quality scorecards across 5 dimensions (groundedness, clarity, distractors, Bloom, bias). Edit stems, refine distractors, and verify side-by-side source citations.
            </p>
          </div>

          {/* Step 4 */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4 hover:border-emerald-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
              <Download className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-amber-400 font-bold">
              STEP 04
            </div>
            <h3 className="text-lg font-bold text-white">
              Export the Final Assessment
            </h3>
            <p className="text-sm text-slate-400 leading-relaxed">
              Export ready-to-use assessments into Moodle XML, GIFT, IMS Global QTI 2.1 zip packages, printable PDF exam sheets with separate answer keys, Word docs, and CSVs.
            </p>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------- */}
      {/* 3. MULTI-AGENT ARCHITECTURE & QUALITY SCORECARDS */}
      {/* --------------------------------------------------------------------- */}
      <section id="architecture" className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="rounded-3xl border border-slate-800 bg-slate-900/30 p-8 sm:p-12 relative overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
                Cognitive Pipeline Design
              </span>
              <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
                6-Agent LangGraph Orchestration
              </h2>
              <p className="text-slate-400 leading-relaxed">
                Rather than relying on single-shot LLM prompts that produce hallucinated answers and shallow recall questions, AQG Studio isolates responsibility across specialized agents:
              </p>

              <div className="space-y-3">
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">1. Document Processing:</span> Deterministic chunking with page and slide coordinates.
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">2. Knowledge Analysis:</span> Concept map extraction and topic hierarchy discovery.
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">3. Question Planning:</span> Assessment blueprint balancing Bloom’s distribution and difficulty.
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">4. Question Generation:</span> Grounded item generation with distractor rationales.
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">5. Evaluation & Refinement:</span> 5-metric adversarial grader with auto-refine feedback loop.
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-slate-200">6. Output & Reporting:</span> Assessment bundling and LMS format translation.
                  </div>
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-slate-800 bg-slate-950 p-6 space-y-6">
              <div className="text-sm font-semibold text-slate-300 border-b border-slate-800 pb-3 flex items-center justify-between">
                <span>Automated 5-Metric Evaluation Standard</span>
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
              </div>

              <div className="space-y-4 text-sm">
                <div>
                  <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                    <span>Factual Groundedness (Hallucination Defense)</span>
                    <span className="text-emerald-400">100% Chunk-Bound</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-emerald-500 rounded-full w-[96%]"></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                    <span>Stem Clarity & Unambiguity</span>
                    <span className="text-sky-400">Strict Grammar</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-sky-500 rounded-full w-[92%]"></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                    <span>Distractor Plausibility (No Lazy Options)</span>
                    <span className="text-violet-400">Targeted Misconceptions</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-violet-500 rounded-full w-[90%]"></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                    <span>Bloom Taxonomy Alignment</span>
                    <span className="text-amber-400">Cognitive Depth Match</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-amber-500 rounded-full w-[94%]"></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between text-xs font-medium text-slate-400 mb-1">
                    <span>Fairness & Bias Neutrality</span>
                    <span className="text-teal-400">Audited Neutrality</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                    <div className="h-full bg-teal-500 rounded-full w-[98%]"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------- */}
      {/* 4. CALL TO ACTION */}
      {/* --------------------------------------------------------------------- */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
        <div className="rounded-3xl border border-emerald-500/30 bg-gradient-to-b from-emerald-950/40 to-slate-950 p-10 sm:p-14 space-y-6">
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Built for Academic Integrity and Enterprise Precision
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto text-base">
            AQG Studio is ready for Phase 01 application foundations. Connect your learning materials and generate calibrated assessment items in seconds.
          </p>
          <div className="pt-2">
            <Link
              href="#workflow"
              className="inline-flex items-center gap-2 rounded-xl bg-emerald-500 px-8 py-3.5 text-base font-semibold text-slate-950 transition hover:bg-emerald-400 shadow-xl shadow-emerald-500/20"
            >
              Get Started with AQG Studio
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
