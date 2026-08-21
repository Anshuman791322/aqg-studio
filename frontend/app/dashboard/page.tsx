import Link from "next/link";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import {
  Activity,
  ArrowRight,
  BookOpen,
  CheckCircle,
  FileText,
  Layers,
  LogOut,
  PlusCircle,
  Shield,
  Sparkles,
  User,
} from "lucide-react";

export default async function DashboardPage() {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/auth/sign-in?returnUrl=/dashboard");
  }

  const displayName =
    user.user_metadata?.display_name ||
    user.user_metadata?.full_name ||
    user.email?.split("@")[0] ||
    "Educator";

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      {/* Top App Header */}
      <header className="border-b border-border bg-card/60 backdrop-blur-md sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2 group">
              <div className="h-9 w-9 rounded-xl bg-primary/10 border border-primary/20 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-all">
                <BookOpen className="h-5 w-5" />
              </div>
              <span className="font-bold text-lg tracking-tight">AQG Studio</span>
            </Link>
            <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-primary/10 text-primary border border-primary/20">
              Workspace
            </span>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-2 text-xs text-muted-foreground bg-secondary/50 px-3 py-1.5 rounded-xl border border-border">
              <User className="h-3.5 w-3.5 text-primary" />
              <span className="font-medium text-foreground">{user.email}</span>
            </div>
            <form action="/auth/sign-out" method="post">
              <button
                type="submit"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-secondary/60 border border-border transition-all cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span>Sign Out</span>
              </button>
            </form>
          </div>
        </div>
      </header>

      {/* Main Dashboard Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Banner */}
        <div className="mb-8 p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-primary/15 via-primary/5 to-transparent border border-primary/20 relative overflow-hidden">
          <div className="max-w-2xl">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-primary/20 text-primary mb-3">
              <Shield className="h-3.5 w-3.5" />
              Authenticated Session
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground">
              Welcome back, {displayName}
            </h1>
            <p className="text-sm sm:text-base text-muted-foreground mt-2">
              Your multi-agent assessment workspace is active. Ingest educational materials to generate vector-grounded questions with automatic pedagogical evaluation.
            </p>
          </div>
        </div>

        {/* Status Metrics Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="p-5 rounded-2xl bg-card border border-border shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Daily Requests
              </span>
              <Activity className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-bold text-foreground">0 / 500</div>
            <p className="text-xs text-muted-foreground mt-1">Free Tier Daily Quota</p>
          </div>

          <div className="p-5 rounded-2xl bg-card border border-border shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Tokens Processed
              </span>
              <Sparkles className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-bold text-foreground">0</div>
            <p className="text-xs text-muted-foreground mt-1">Input & Output Tokens Today</p>
          </div>

          <div className="p-5 rounded-2xl bg-card border border-border shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Assessments Created
              </span>
              <Layers className="h-4 w-4 text-primary" />
            </div>
            <div className="text-2xl font-bold text-foreground">0</div>
            <p className="text-xs text-muted-foreground mt-1">Active Question Sets</p>
          </div>

          <div className="p-5 rounded-2xl bg-card border border-border shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Auth Status
              </span>
              <CheckCircle className="h-4 w-4 text-green-500" />
            </div>
            <div className="text-2xl font-bold text-green-500">Verified</div>
            <p className="text-xs text-muted-foreground mt-1">JWT Verified Session</p>
          </div>
        </div>

        {/* Next Generation Actions */}
        <h2 className="text-lg font-semibold text-foreground mb-4">Assessment Pipeline Modules</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <div className="p-6 rounded-2xl bg-card border border-border hover:border-primary/50 transition-all group shadow-sm flex flex-col justify-between">
            <div>
              <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <PlusCircle className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base text-foreground mb-2">Upload Learning Material</h3>
              <p className="text-xs text-muted-foreground">
                Ingest PDF, DOCX, PPTX, or TXT documents. Content is partitioned and indexed in pgvector.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-1 text-xs font-semibold text-primary group-hover:underline">
              <span>Ready in Phase 4</span>
              <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-card border border-border hover:border-primary/50 transition-all group shadow-sm flex flex-col justify-between">
            <div>
              <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Layers className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base text-foreground mb-2">Configure Blueprint</h3>
              <p className="text-xs text-muted-foreground">
                Set target question distribution across Bloom Taxonomy levels, difficulty tiers, and topic quotas.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-1 text-xs font-semibold text-primary group-hover:underline">
              <span>Ready in Phase 6</span>
              <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>

          <div className="p-6 rounded-2xl bg-card border border-border hover:border-primary/50 transition-all group shadow-sm flex flex-col justify-between">
            <div>
              <div className="h-10 w-10 rounded-xl bg-primary/10 text-primary border border-primary/20 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <FileText className="h-5 w-5" />
              </div>
              <h3 className="font-semibold text-base text-foreground mb-2">Multi-Format Export</h3>
              <p className="text-xs text-muted-foreground">
                Export validated question sets to Moodle XML, GIFT, QTI 2.1, PDF test papers, and DOCX.
              </p>
            </div>
            <div className="mt-6 flex items-center gap-1 text-xs font-semibold text-primary group-hover:underline">
              <span>Ready in Phase 11</span>
              <ArrowRight className="h-3.5 w-3.5 group-hover:translate-x-1 transition-transform" />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
