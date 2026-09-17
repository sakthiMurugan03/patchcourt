"use client";

import { useState, useEffect } from "react";
import { Gavel, SearchCheck, MessageSquare, BarChart2, History, X, RefreshCw } from "lucide-react";
import { AppLayout } from "@/components/app-layout";
import { AuditView } from "@/components/audit-view";
import { DebateTranscript } from "@/components/debate-transcript";
import { EvidencePanel } from "@/components/evidence-panel";
import { ReportForm } from "@/components/report-form";
import { SonarBaselinePanel } from "@/components/sonar-baseline-panel";
import { TierLegend } from "@/components/tier-legend";
import { VerdictBanner } from "@/components/verdict-banner";
import { runDemo, submitReview } from "@/lib/api";
import type { Report } from "@/lib/types";
import { cn } from "cn";

type Phase = "idle" | "loading" | "done" | "error";
type View = "overview" | "evidence" | "debate" | "baseline" | "history";

const VIEW_CONFIG = [
  { id: "overview", label: "Overview", icon: Gavel },
  { id: "evidence", label: "Evidence", icon: SearchCheck },
  { id: "debate", label: "Debate", icon: MessageSquare },
  { id: "baseline", label: "SonarQube Baseline", icon: BarChart2 },
  { id: "history", label: "History", icon: History },
] as const;

export default function Page() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string>("");
  const [activeView, setActiveView] = useState<View>("overview");

  async function load(fn: () => Promise<Report>) {
    setPhase("loading");
    setError("");
    setActiveView("overview");
    try {
      const r = await fn();
      setReport(r);
      setPhase("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed unexpectedly");
      setPhase("error");
    }
  }

  function handleNewReview() {
    setReport(null);
    setPhase("idle");
    setActiveView("overview");
  }

  function renderOverview() {
    return (
      <div className="flex flex-col gap-6">
        {phase !== "done" && (
          <ReportForm
            onReview={(u) => load(() => submitReview(u))}
            onDemo={() => load(runDemo)}
            busy={phase === "loading"}
          />
        )}
        {phase === "loading" && (
          <LoadingState />
        )}
        {phase === "error" && (
          <ErrorState error={error} onRetry={() => setPhase("idle")} />
        )}
        {phase === "done" && report && (
          <OverviewContent report={report} onNewReview={handleNewReview} />
        )}
      </div>
    );
  }

  function renderEvidence() {
    if (!report) return <EmptyState message="Run a review to see evidence" />;
    return <EvidencePanel claims={report.claims} />;
  }

  function renderDebate() {
    if (!report) return <EmptyState message="Run a review to see debate transcript" />;
    return <DebateTranscript debates={report.debate_transcripts} />;
  }

  function renderBaseline() {
    return <SonarBaselinePanel defaultPrUrl={report?.pr_url} />;
  }

  function renderHistory() {
    return <HistoryView />;
  }

  const renderView = {
    overview: renderOverview,
    evidence: renderEvidence,
    debate: renderDebate,
    baseline: renderBaseline,
    history: renderHistory,
  }[activeView];

  return (
    <AppLayout
      onRunReview={(u) => load(() => submitReview(u))}
      onRunDemo={() => load(runDemo)}
      busy={phase === "loading"}
    >
      <div className="flex flex-col gap-6">
        <ViewHeader
          title={VIEW_CONFIG.find(v => v.id === activeView)?.label ?? ""}
          subtitle={activeView === "overview" && phase === "done" && report ? report.pr_url : ""}
          actions={
            phase === "done" && report && activeView === "overview" && (
              <button
                onClick={handleNewReview}
                className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                <RefreshCw className="size-3.5" />
                New review
              </button>
            )
          }
        />
        <ViewTabs activeView={activeView} onChange={setActiveView} disabled={phase === "loading"} />
        <div className="flex-1 min-h-0">{renderView()}</div>
      </div>
    </AppLayout>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-lg border border-border bg-card p-10">
      <div className="flex items-center gap-2">
        <Gavel className="size-5 animate-pulse text-primary" />
        <span className="text-sm text-muted-foreground">Agents deliberating…</span>
      </div>
      <div className="flex w-full max-w-sm gap-2">
        {["Security", "Quality", "Pragmatist", "Judge"].map((n, i) => (
          <div
            key={n}
            className="flex-1 rounded bg-muted py-1.5 text-center text-[11px] text-muted-foreground"
            style={{ animation: `pulse 1.2s ${i * 0.15}s infinite` }}
          >
            {n}
          </div>
        ))}
      </div>
    </div>
  );
}

function ErrorState({ error, onRetry }: { error: string; onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
      {error}
      <p className="mt-1 text-xs text-muted-foreground">
        Is the PatchCourt API running? Start it with{" "}
        <code className="rounded bg-muted px-1 py-0.5 font-mono">uvicorn patchcourt.api.app:app --port 8000</code>{" "}
        — or run the demo.
      </p>
      <button onClick={onRetry} className="mt-3 text-xs font-medium underline-offset-2 hover:text-destructive">
        Try again
      </button>
    </div>
  );
}

function OverviewContent({ report, onNewReview }: { report: Report; onNewReview: () => void }) {
  return (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-mono text-xs text-muted-foreground">{report.pr_url}</p>
          <p className="text-xs text-muted-foreground">
            {report.files.length} file(s), {report.claims.length} total claim(s)
          </p>
        </div>
      </div>
      <VerdictBanner report={report} />
      <EvidencePanel claims={report.claims} />
      <DebateTranscript debates={report.debate_transcripts} />
      <AuditView report={report} />
    </>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Gavel className="size-12 text-muted-foreground/30" />
      <p className="mt-4 text-muted-foreground">{message}</p>
    </div>
  );
}

function HistoryView() {
  return (
    <div className="rounded-lg border border-border bg-card p-6">
      <h3 className="text-lg font-medium mb-4">Review History</h3>
      <p className="text-muted-foreground text-sm">History view coming soon — connects to audit trail.</p>
    </div>
  );
}

function ViewHeader({ title, subtitle, actions }: { title: string; subtitle?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 truncate font-mono text-xs text-muted-foreground max-w-[400px]">{subtitle}</p>}
      </div>
      {actions && <div className="flex-shrink-0">{actions}</div>}
    </div>
  );
}

function ViewTabs({ activeView, onChange, disabled }: { activeView: View; onChange: (v: View) => void; disabled: boolean }) {
  return (
    <div className="flex gap-1 border-b border-border pb-1" role="tablist" aria-label="Views">
      {VIEW_CONFIG.map((view) => (
        <button
          key={view.id}
          role="tab"
          aria-selected={activeView === view.id}
          onClick={() => !disabled && onChange(view.id)}
          disabled={disabled}
          className={cn(
            "flex items-center gap-1.5 px-3 py-2 text-sm font-medium rounded-t-md transition-colors",
            activeView === view.id
              ? "text-primary border-b-2 border-primary"
              : "text-muted-foreground hover:text-foreground hover:bg-accent",
            disabled && "opacity-50 pointer-events-none"
          )}
        >
          <view.icon className="size-3.5" aria-hidden="true" />
          <span>{view.label}</span>
        </button>
      ))}
    </div>
  );
}