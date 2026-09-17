"use client";

import { useState, useEffect, useMemo } from "react";
import { Gavel, RefreshCw } from "lucide-react";
import { AuditView } from "@/components/audit-view";
import { DebateTranscript } from "@/components/debate-transcript";
import { EvidencePanel } from "@/components/evidence-panel";
import { ReportForm } from "@/components/report-form";
import { TierLegend } from "@/components/tier-legend";
import { VerdictBanner } from "@/components/verdict-banner";
import { runDemo, submitReview } from "@/lib/api";
import type { Report } from "@/lib/types";
import { cn } from "cn";
import { useReview } from "@/lib/review-context";
import { LayoutWrapper } from "@/components/layout-wrapper";
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
import { ViewHeader } from "@/components/view-header";

type Phase = "idle" | "loading" | "done" | "error";

export default function Page() {
  const { report, phase, error, setReport, setPhase, setError, clearReview } = useReview();
  const [localReport, setLocalReport] = useState<Report | null>(report);
  const [localPhase, setLocalPhase] = useState<Phase>(phase);
  const [localError, setLocalError] = useState<string>(error);

  useEffect(() => {
    setLocalReport(report);
    setLocalPhase(phase);
    setLocalError(error);
  }, [report, phase, error]);

  async function load(fn: () => Promise<Report>) {
    setLocalPhase("loading");
    setLocalError("");
    setPhase("loading");
    setError("");
    try {
      const r = await fn();
      setLocalReport(r);
      setLocalPhase("done");
      setReport(r);
      setPhase("done");
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Review failed unexpectedly";
      setLocalError(msg);
      setLocalPhase("error");
      setError(msg);
      setPhase("error");
    }
  }

  function handleNewReview() {
    setLocalReport(null);
    setLocalPhase("idle");
    clearReview();
  }

  return (
    <LayoutWrapper>
      <div className="flex flex-col gap-6">
        <ViewHeader
          title="Overview"
          actions={
            localPhase === "done" && localReport && (
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
        <div className="flex flex-col gap-6">
          {localPhase !== "done" && (
            <ReportForm
              onReview={(u) => load(() => submitReview(u))}
              onDemo={() => load(runDemo)}
              busy={localPhase === "loading"}
            />
          )}
          {localPhase === "loading" && <LoadingState />}
          {localPhase === "error" && <ErrorState error={localError} onRetry={() => setLocalPhase("idle")} />}
          {localPhase === "done" && localReport && <OverviewContent report={localReport} onNewReview={handleNewReview} />}
        </div>
      </div>
    </LayoutWrapper>
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

  const TOOLTIP_STYLE = {
    backgroundColor: "var(--card)",
    border: "1px solid var(--border)",
    borderRadius: 6,
    color: "var(--foreground)",
  };

  const TOOLTIP_LABEL_STYLE = {
    color: "var(--foreground)",
    fontWeight: 600,
    fontSize: 12,
  };

  const TOOLTIP_ITEM_STYLE = {
    color: "var(--foreground)",
    fontSize: 12,
  };

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
                contentStyle={TOOLTIP_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
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
                contentStyle={TOOLTIP_STYLE}
                labelStyle={TOOLTIP_LABEL_STYLE}
                itemStyle={TOOLTIP_ITEM_STYLE}
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