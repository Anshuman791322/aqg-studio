import Link from "next/link";
import { FileQuestion, ArrowLeft } from "lucide-react";

export default function NotFound() {
  return (
    <div className="flex min-h-[70vh] items-center justify-center px-4 py-16">
      <div className="mx-auto max-w-md text-center">
        <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-800 text-slate-400 ring-1 ring-slate-700">
          <FileQuestion className="h-8 w-8" />
        </div>
        <span className="text-xs font-semibold uppercase tracking-wider text-emerald-400">
          404 Error
        </span>
        <h1 className="mt-2 text-2xl font-bold tracking-tight text-white sm:text-3xl">
          Page not found
        </h1>
        <p className="mt-3 text-sm text-slate-400">
          The assessment resource, blueprint, or page you requested could not be located.
        </p>

        <div className="mt-8 flex items-center justify-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-lg bg-emerald-500 px-5 py-2.5 text-sm font-semibold text-slate-950 transition hover:bg-emerald-400 shadow-sm shadow-emerald-500/25"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}
