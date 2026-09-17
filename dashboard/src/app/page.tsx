"use client";

import { useState, useEffect, useMemo } from "react";
import { usePathname } from "next/navigation";
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
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

type Phase = "idle" | "loading" | "done" | "error";
type View = "overview" | "evidence" | "debate" | "baseline" | "history";

const VIEW_CONFIG = [
  { id: "overview", label: "Overview", icon: Gavel, path: "/" },
  { id: "evidence", label: "Evidence", icon: SearchCheck, path: "/evidence" },
  { id: "debate", label: "Debate", icon: MessageSquare, path: "/debate" },
  { id: "baseline", label: "SonarQube Baseline", icon: BarChart2, path: "/baseline" },
  { id: "history", label: "History", icon: History, path: "/history" },
] as const;

function pathToView(path: string): View {
  if (path.startsWith("/evidence")) return "evidence";
  if (path.startsWith("/debate")) return "debate";
  if (path.startsWith("/baseline")) return "baseline";
  if (path.startsWith("/history")) return "history";
  return "overview";
}

export default function Page() {
  const pathname = usePathname();
  const [phase, setPhase] = useState<Phase>("idle");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string>("");
  const [activeView, setActiveView] = useState<View>(() => pathToView(pathname));

  useEffect(() => {
    setActiveView(pathToView(pathname));
  }, [pathname]);

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
        {phase === "loading" && <LoadingState />}
        {phase === "error" && <ErrorState error={error} onRetry={() => setPhase("idle")} />}
        {phase === "done" && report && <OverviewContent report={report} onNewReview={handleNewReview} />}
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
      <KPIRow report={report} />
      <ChartsRow report={report} />
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

function ViewHeader({ title, actions }: { title: string; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
      </div>
      {actions && <div className="flex-shrink-0">{actions}</div>}
    </div>
  );
}

function KPIRow({ report }: { report: Report }) {
  const totalClaims = report.claims.length;
  const toolClaims = report.claims.filter(c => c.source === "tool").length;
  const corroborated = report.claims.filter(c => c.corroborated).length;
  const debated = report.debate_transcripts.length;
  const riskScore = report.overall_score.toFixed(1);

  const tiles = [
    { label: "Verdict", value: report.verdict, class: "font-mono text-xl font-semibold" },
    { label: "Risk Score", value: riskScore, class: "font-mono text-xl font-semibold" },
    { label: "Total Claims", value: totalClaims.toString(), class: "font-mono text-xl font-semibold" },
    { label: "Tool-backed", value: toolClaims.toString(), class: "font-mono text-xl font-semibold" },
    { label: "Corroborated", value: corroborated.toString(), class: "font-mono text-xl font-semibold" },
    { label: "Debated", value: debated.toString(), class: "font-mono text-xl font-semibold" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
      {tiles.map((t, i) => (
        <div key={i} className="rounded-md border border-border bg-card p-4">
          <p className="text-xs text-muted-foreground uppercase tracking-wide">{t.label}</p>
          <p className={cn("mt-1", t.class)}>{t.value}</p>
        </div>
      ))}
    </div>
  );
}

function ChartsRow({ report }: { report: Report }) {
  const severityData = useMemo(() => 
    [1, 2, 3, 4, 5].map(s => ({
      severity: s,
      count: report.claims.filter(c => c.severity === s).length,
      label: ["Info", "Low", "Medium", "High", "Critical"][s - 1],
      color: `var(--severity-${["info", "low", "medium", "high", "critical"][s - 1]})`,
    })).filter(d => d.count > 0),
    [report.claims]
  );

  const tierData = useMemo(() => 
    [1, 2, 3, 4, 5].map(t => ({
      tier: t,
      count: report.claims.filter(c => c.tier === t).length,
      label: `T${t}`,
      color: `var(--severity-${["critical", "high", "medium", "low", "info"][t - 1]})`,
    })).filter(d => d.count > 0),
    [report.claims]
  );

  const SEVERITY_COLORS = {
    1: "var(--severity-info)",
    2: "var(--severity-low)",
    3: "var(--severity-medium)",
    4: "var(--severity-high)",
    5: "var(--severity-critical)",
  } as const;

  const TIER_COLORS = {
    1: "var(--severity-critical)",
    2: "var(--severity-high)",
    3: "var(--severity-medium)",
    4: "var(--severity-low)",
    5: "var(--severity-info)",
  } as const;

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-base">Severity Distribution</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={severityData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <YAxis dataKey="label" type="category" tick={{ fontSize: 11, fill: "var(--foreground)", fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} width={60} />
              <Tooltip
                contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 6 }}
                formatter={(value: unknown) => [Number(value ?? 0), "claims"]}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={28}>
                {severityData.map((entry, index) => (
                  <Cell key={index} fill={SEVERITY_COLORS[entry.severity as keyof typeof SEVERITY_COLORS]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card className="w-full">
        <CardHeader>
          <CardTitle className="text-base">Tier Distribution (T1–T5)</CardTitle>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={tierData} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} axisLine={false} tickLine={false} />
              <YAxis dataKey="label" type="category" tick={{ fontSize: 11, fill: "var(--foreground)", fontFamily: "var(--font-mono)" }} axisLine={false} tickLine={false} width={60} />
              <Tooltip
                contentStyle={{ backgroundColor: "var(--card)", border: "1px solid var(--border)", borderRadius: 6 }}
                formatter={(value: unknown) => [Number(value ?? 0), "claims"]}
              />
              <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={28}>
                {tierData.map((entry, index) => (
                  <Cell key={index} fill={TIER_COLORS[entry.tier as keyof typeof TIER_COLORS]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>
    </div>
  );
}