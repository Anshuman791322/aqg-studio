"use client";

import Link from "next/link";
import { BookOpen, LayoutDashboard, LogIn } from "lucide-react";

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 w-full border-b border-slate-800/80 bg-slate-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        <div className="flex items-center space-x-3">
          <Link href="/" className="flex items-center space-x-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 shadow-md shadow-emerald-500/20">
              <BookOpen className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">
              AQG <span className="text-emerald-400">Studio</span>
            </span>
          </Link>
          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
            Multi-Agent
          </span>
        </div>

        <nav className="hidden md:flex items-center space-x-8 text-xs font-medium text-slate-300">
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 transition-colors hover:text-emerald-400 text-slate-200"
          >
            <LayoutDashboard className="h-4 w-4 text-emerald-400" />
            <span>Studio Workspace</span>
          </Link>
          <Link
            href="/#workflow"
            className="transition-colors hover:text-emerald-400 text-slate-400"
          >
            Workflow
          </Link>
          <Link
            href="/#architecture"
            className="transition-colors hover:text-emerald-400 text-slate-400"
          >
            Architecture
          </Link>
        </nav>

        <div className="flex items-center space-x-3">
          <Link
            href="/auth/sign-in"
            className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white border border-slate-800 rounded-xl hover:bg-slate-900 transition-colors"
          >
            <LogIn className="h-3.5 w-3.5" />
            <span>Sign In</span>
          </Link>
          <Link
            href="/dashboard"
            className="inline-flex items-center justify-center rounded-xl bg-emerald-500 px-4 py-2 text-xs font-semibold text-slate-950 transition hover:bg-emerald-400 shadow-sm shadow-emerald-500/25"
          >
            Open Studio
          </Link>
        </div>
      </div>
    </header>
  );
}
