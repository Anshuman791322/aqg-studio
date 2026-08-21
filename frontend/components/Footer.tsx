import { Sparkles, Terminal, ShieldCheck } from "lucide-react";

export default function Footer() {
  return (
    <footer className="mt-auto border-t border-slate-800/80 bg-slate-950/60 py-12 text-slate-400">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div className="md:col-span-2 space-y-4">
            <div className="flex items-center space-x-2.5">
              <div className="flex h-7 w-7 items-center justify-center rounded bg-emerald-500 text-slate-950 font-bold">
                <Sparkles className="h-4 w-4" />
              </div>
              <span className="text-lg font-bold text-white tracking-tight">
                AQG <span className="text-emerald-400">Studio</span>
              </span>
            </div>
            <p className="text-sm text-slate-400 max-w-md leading-relaxed">
              Multi-Agent Automated Question Generation Platform. Calibrated to
              Bloom’s Revised Taxonomy with vector-chunk grounding and automated
              pedagogical quality evaluation.
            </p>
            <div className="flex items-center space-x-4 pt-2 text-xs text-slate-500">
              <span className="inline-flex items-center gap-1.5">
                <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
                Zero-Secret Isolation
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Terminal className="h-3.5 w-3.5 text-sky-400" />
                FastAPI + Next.js 15
              </span>
            </div>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-200 tracking-wider uppercase mb-3">
              Supported Inputs
            </h3>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>PDF Documents (.pdf)</li>
              <li>Microsoft Word (.docx)</li>
              <li>PowerPoint Decks (.pptx)</li>
              <li>Plain Text / Markdown (.txt)</li>
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-semibold text-slate-200 tracking-wider uppercase mb-3">
              Export Formats
            </h3>
            <ul className="space-y-2 text-sm text-slate-400">
              <li>Moodle XML & GIFT Format</li>
              <li>IMS Global QTI 2.1 Package</li>
              <li>Printable PDF Assessment</li>
              <li>Microsoft Word (.docx) & CSV</li>
            </ul>
          </div>
        </div>

        <div className="mt-8 border-t border-slate-800/60 pt-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-500">
          <p>© 2026 AQG Studio. Enterprise-Grade Multi-Agent Assessment System.</p>
          <p className="mt-2 sm:mt-0">Phase 01: Application Foundation Active</p>
        </div>
      </div>
    </footer>
  );
}
