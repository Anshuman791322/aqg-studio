import Link from "next/link";
import {
  ArrowRight,
  BookCheck,
  CheckCircle2,
  Download,
  FileType,
  FileUp,
  GraduationCap,
  Layers,
  Sparkles,
  Zap,
} from "lucide-react";

export default function LandingPage() {
  return (
    <div className="flex flex-col space-y-24 pb-20">
      {/* --------------------------------------------------------------------- */}
      {/* 1. HERO SECTION */}
      {/* --------------------------------------------------------------------- */}
      <section className="relative overflow-hidden pt-12 pb-8 md:pt-20 md:pb-16">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-emerald-950/40 via-slate-950 to-slate-950 pointer-events-none" />

        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="text-center space-y-6 max-w-4xl mx-auto">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3.5 py-1 text-xs font-semibold text-emerald-400">
              <Sparkles className="h-3.5 w-3.5" />
              <span>Multi-Agent Cognitive Assessment Engine</span>
            </div>

            <h1 className="text-4xl font-extrabold tracking-tight text-white sm:text-6xl md:text-7xl">
              Turn Learning Materials into{" "}
              <span className="bg-gradient-to-r from-emerald-400 via-teal-300 to-sky-400 bg-clip-text text-transparent">
                Calibrated Assessments
              </span>
            </h1>

            <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto leading-relaxed">
              AQG Studio orchestrates a 6-agent LangGraph workflow to transform raw textbooks, lecture slides, and notes into pedagogically rigorous questions with automated quality scoring and LMS exports.
            </p>

            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <Link
                href="/auth/sign-up"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-7 py-3.5 text-base font-semibold text-slate-950 transition hover:bg-emerald-400 shadow-lg shadow-emerald-500/25"
              >
                Get Started Free
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/auth/sign-in"
                className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/90 px-7 py-3.5 text-base font-medium text-slate-300 transition hover:bg-slate-800"
              >
                Sign In to Studio
              </Link>
            </div>
          </div>

          {/* Interactive Pipeline Teaser */}
          <div className="mt-16 rounded-3xl border border-slate-800 bg-slate-900/60 p-4 sm:p-8 shadow-2xl backdrop-blur-xl max-w-5xl mx-auto">
            <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-6">
              <div className="flex items-center space-x-2">
                <div className="h-3 w-3 rounded-full bg-rose-500/80" />
                <div className="h-3 w-3 rounded-full bg-amber-500/80" />
                <div className="h-3 w-3 rounded-full bg-emerald-500/80" />
                <span className="text-xs text-slate-500 font-mono ml-2">
                  aqg-studio-core // assessment-graph
                </span>
              </div>
              <span className="text-xs font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/40 rounded-full px-3 py-0.5">
                LangGraph State: READY
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-left">
              <div className="rounded-2xl bg-slate-950/80 border border-slate-800 p-4 space-y-2">
                <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Source Provenance
                </div>
                <div className="text-sm font-medium text-slate-200">
                  Chapter 4: Cell Biology.pdf
                </div>
                <div className="text-xs text-emerald-400 font-mono">
                  Chunk #18 (Page 24, ¶3)
                </div>
                <p className="text-xs text-slate-400 italic bg-slate-900 p-2.5 rounded-xl border border-slate-800/80">
                  &ldquo;Mitochondria synthesize ATP through oxidative phosphorylation using the proton gradient across the inner membrane.&rdquo;
                </p>
              </div>

              <div className="rounded-2xl bg-slate-950/80 border border-slate-800 p-4 space-y-3 md:col-span-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">
                    Generated MCQ (Bloom: Analyze | Hard)
                  </span>
                  <span className="text-xs font-mono bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 px-2.5 py-0.5 rounded-full">
                    Quality Score: 0.94 / 1.00
                  </span>
                </div>
                <div className="text-sm font-semibold text-white">
                  If the inner mitochondrial membrane becomes permeable to protons, which metabolic outcome will occur first?
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs pt-1">
                  <div className="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-500/50 text-emerald-300 font-medium">
                    ✓ A. ATP synthesis decreases while heat production increases
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400">
                    ✕ B. Glycolysis immediately terminates
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400">
                    ✕ C. Oxygen consumption immediately drops to zero
                  </div>
                  <div className="p-2.5 rounded-xl bg-slate-900 border border-slate-800 text-slate-400">
                    ✕ D. The citric acid cycle halts
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------- */}
      {/* 2. SUPPORTED FORMATS & LIMITS */}
      {/* --------------------------------------------------------------------- */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Formats Matrix */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
                <FileType className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Supported Input Formats</h2>
                <p className="text-xs text-slate-400">Deterministic multi-format document parser</p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-center space-y-1">
                <div className="text-base font-bold text-white">PDF</div>
                <div className="text-[11px] text-slate-400">Text & Layout</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-center space-y-1">
                <div className="text-base font-bold text-white">DOCX</div>
                <div className="text-[11px] text-slate-400">Word Documents</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-center space-y-1">
                <div className="text-base font-bold text-white">PPTX</div>
                <div className="text-[11px] text-slate-400">Slide Decks</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-center space-y-1">
                <div className="text-base font-bold text-white">TXT / MD</div>
                <div className="text-[11px] text-slate-400">Plain Notes</div>
              </div>
            </div>

            <div className="space-y-2 text-xs text-slate-400 leading-relaxed border-t border-slate-800/60 pt-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>Deterministic header/footer stripping and slide segmentation</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>600–900 token semantic chunking with 10% context overlap</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>Scanned PDF text-density detection with graceful OCR flagging</span>
              </div>
            </div>
          </div>

          {/* Free Tier Limits */}
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-8 space-y-6">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-sky-500/10 text-sky-400 border border-sky-500/20 flex items-center justify-center">
                <Zap className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">Community & Free Demo Quota</h2>
                <p className="text-xs text-slate-400">Zero cloud costs, no credit card required</p>
              </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-center space-y-1">
                <div className="text-base font-bold text-emerald-400">50 MB</div>
                <div className="text-[11px] text-slate-400">Max File Size</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-center space-y-1">
                <div className="text-base font-bold text-sky-400">50 Items</div>
                <div className="text-[11px] text-slate-400">Per Assessment</div>
              </div>
              <div className="p-3.5 rounded-2xl bg-slate-950 border border-slate-800/80 text-center space-y-1">
                <div className="text-base font-bold text-violet-400">500 / day</div>
                <div className="text-[11px] text-slate-400">Daily Requests</div>
              </div>
            </div>

            <div className="space-y-2 text-xs text-slate-400 leading-relaxed border-t border-slate-800/60 pt-4">
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>Multi-provider fallback gateway (OpenRouter + NVIDIA NIM)</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>PostgreSQL-backed job runner with crash recovery & resumability</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                <span>Multi-tenant Row Level Security enforcing private document isolation</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------- */}
      {/* 3. CORE WORKFLOW */}
      {/* --------------------------------------------------------------------- */}
      <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="text-center space-y-4 mb-16">
          <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">
            End-to-End Pipeline
          </span>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Four Steps to Validated Question Banks
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto">
            From raw unstructured educational files to evaluated questions ready for your LMS.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 space-y-4 hover:border-emerald-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <FileUp className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-emerald-400 font-bold">STEP 01</div>
            <h3 className="text-lg font-bold text-white">Upload Material</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upload PDF, Word, PowerPoint, or text files directly to user-scoped private storage with hash verification.
            </p>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 space-y-4 hover:border-sky-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-500/10 text-sky-400 border border-sky-500/30">
              <Layers className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-sky-400 font-bold">STEP 02</div>
            <h3 className="text-lg font-bold text-white">Design Blueprint</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Allocate exact quotas across Bloom Taxonomy, difficulty tiers, question types, and extracted topics.
            </p>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 space-y-4 hover:border-violet-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-violet-500/10 text-violet-400 border border-violet-500/30">
              <BookCheck className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-violet-400 font-bold">STEP 03</div>
            <h3 className="text-lg font-bold text-white">Review & Refine</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Inspect automated 10-metric scorecards, edit stems, review distractor rationales, and verify chunk citations.
            </p>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/40 p-6 space-y-4 hover:border-amber-500/40 transition">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/30">
              <Download className="h-6 w-6" />
            </div>
            <div className="text-xs font-mono text-amber-400 font-bold">STEP 04</div>
            <h3 className="text-lg font-bold text-white">Export Package</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Export ready assessments to Moodle XML, GIFT, QTI 2.1 zip bundles, printable PDF exam papers, DOCX, and CSV.
            </p>
          </div>
        </div>
      </section>

      {/* --------------------------------------------------------------------- */}
      {/* 4. CALL TO ACTION */}
      {/* --------------------------------------------------------------------- */}
      <section className="mx-auto max-w-5xl px-4 sm:px-6 lg:px-8 text-center">
        <div className="rounded-3xl border border-emerald-500/30 bg-gradient-to-b from-emerald-950/40 to-slate-950 p-10 sm:p-14 space-y-6">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-500/20 text-emerald-400 mb-2">
            <GraduationCap className="h-6 w-6" />
          </div>
          <h2 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
            Experience Cognitive Question Generation
          </h2>
          <p className="text-slate-400 max-w-xl mx-auto text-sm leading-relaxed">
            Create an account or sign in to start transforming your course materials into pedagogically grounded assessments.
          </p>
          <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/auth/sign-up"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-500 px-8 py-3.5 text-base font-semibold text-slate-950 transition hover:bg-emerald-400 shadow-xl shadow-emerald-500/20"
            >
              Start Free Assessment
              <ArrowRight className="h-4 w-4" />
            </Link>
            <Link
              href="/auth/sign-in"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900/90 px-8 py-3.5 text-base font-medium text-slate-300 transition hover:bg-slate-800"
            >
              Sign In
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
