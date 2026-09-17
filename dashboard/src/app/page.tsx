"use client";

import { useState } from "react";
import { Gavel } from "lucide-react";
import { AuditView } from "@/components/audit-view";
import { DebateTranscript } from "@/components/debate-transcript";
import { EvidencePanel } from "@/components/evidence-panel";
import { ReportForm } from "@/components/report-form";
import { TierLegend } from "@/components/tier-legend";
import { VerdictBanner } from "@/components/verdict-banner";
import { runDemo, submitReview } from "@/lib/api";
import type { Report } from "@/lib/types";

type Phase = "idle" | "loading" | "done" | "error";

export default function Page() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [report, setReport] = useState<Report | null>(null);
  const [error, setError] = useState<string>("");

  async function load(fn: () => Promise<Report>) {
    setPhase("loading");
    setError("");
    try {
      const r = await fn();
      setReport(r);
      setPhase("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed unexpectedly");
      setPhase("error");
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 px-4 py-8">
      <header className="flex items-center gap-3">
        <div className="flex size-10 items-center justify-center rounded-xl bg-primary/15 text-primary">
          <Gavel className="size-5" />
        </div>
        <div>
          <h1 className="text-lg font-semibold tracking-wide">
            PatchCourt
            <span className="ml-2 text-xs font-normal text-muted-foreground">
              evidence-gated multi-agent review
            </span>
          </h1>
          <p className="text-xs text-muted-foreground">
            Security · Quality · Pragmatist agents debate tool-grounded findings before a judge scores.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_280px]">
        <div className="flex flex-col gap-6">
          {phase !== "done" && (
            <ReportForm
              onReview={(u) => load(() => submitReview(u))}
              onDemo={() => load(runDemo)}
              busy={phase === "loading"}
            />
          )}
          {phase === "loading" && (
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
          )}
          {phase === "error" && (
            <div className="rounded-lg border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
              {error}
              <p className="mt-1 text-xs text-muted-foreground">
                Is the PatchCourt API running? Start it with{" "}
                <code className="rounded bg-muted px-1 py-0.5 font-mono">uvicorn patchcourt.api.app:app --port 8000</code>{" "}
                — or run the demo.
              </p>
            </div>
          )}
          {phase === "done" && report && (
            <>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate font-mono text-xs text-muted-foreground">{report.pr_url}</p>
                  <p className="text-xs text-muted-foreground">
                    {report.files.length} file(s), {report.claims.length} total claim(s)
                  </p>
                </div>
                <button
                  onClick={() => {
                    setReport(null);
                    setPhase("idle");
                  }}
                  className="shrink-0 text-xs text-muted-foreground underline-offset-2 hover:text-primary hover:underline"
                >
                  New review
                </button>
              </div>
              <VerdictBanner report={report} />
              <EvidencePanel claims={report.claims} />
              <DebateTranscript debates={report.debate_transcripts} />
              <AuditView report={report} />
            </>
          )}
        </div>

        <aside className="flex flex-col gap-6">
          {(phase === "idle" || phase === "done" || phase === "error") && <TierLegend />}
        </aside>
      </div>
    </main>
  );
}