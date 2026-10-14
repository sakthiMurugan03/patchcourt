"use client";

import { useState } from "react";
import { LayoutWrapper } from "@/components/layout-wrapper";
import { ViewHeader } from "@/components/view-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useReview } from "@/lib/review-context";
import { submitReview, runComparisonDemo } from "@/lib/api";
import type { BaselineComparison, FindingComparison } from "@/lib/types";

const VERDICT_COLOR: Record<string, string> = {
  BLOCK: "text-red-400",
  REMEDIATE: "text-orange-400",
  MONITOR: "text-yellow-400",
  PASS: "text-green-400",
  MERGE: "text-green-400",
  NEEDS_REVIEW: "text-yellow-400",
};

const GROUP_COLOR: Record<string, string> = {
  confirmed: "border-l-green-500",
  contradicted: "border-l-red-500",
  out_of_scope: "border-l-gray-500",
  uncertain: "border-l-yellow-500",
  unmatched: "border-l-zinc-600",
};

const GROUP_LABEL: Record<string, string> = {
  confirmed: "SUPPORTED",
  contradicted: "CONTRADICTED",
  out_of_scope: "OUT OF SCOPE",
  uncertain: "UNCERTAIN",
  unmatched: "UNMATCHED",
};

const SEV_COLOR: Record<string, string> = {
  CRITICAL: "text-red-400",
  BLOCKER: "text-red-400",
  MAJOR: "text-orange-400",
  MINOR: "text-yellow-400",
  INFO: "text-blue-400",
};

const FAULT_CORR_COLOR: Record<string, string> = {
  high: "text-red-400 border-red-400",
  medium: "text-yellow-400 border-yellow-400",
  low: "text-zinc-400 border-zinc-500",
};

const QA_COLOR: Record<string, string> = {
  VALID: "text-green-400",
  INCONSISTENT: "text-red-400",
  NEEDS_REWORK: "text-yellow-400",
};

const EMPTY_COMPARISON: FindingComparison = {
  verdict: "",
  overall_score: 0,
  counts: { confirmed: 0, contradicted: 0, out_of_scope: 0, uncertain: 0, unmatched: 0 },
  total_in_pr: 0,
  adjudicated: 0,
  coverage: 0,
  findings: [],
};

function CodeSnippet({ snippet }: { snippet: string }) {
  const lines = snippet.split("\n");
  return (
    <pre className="mt-2 overflow-x-auto rounded bg-zinc-950 border border-zinc-800 px-0 py-1 text-xs font-mono leading-5 whitespace-pre">
      {lines.map((line, i) => {
        const isTarget = line.startsWith("\u2192");
        return (
          <div
            key={i}
            className={isTarget ? "bg-yellow-500/10 text-yellow-200 px-3" : "text-zinc-400 px-3"}
          >
            {line}
          </div>
        );
      })}
    </pre>
  );
}

export default function ComparisonPage() {
  const { report, phase, setReport, setPhase, setError } = useReview();
  const [inputUrl, setInputUrl] = useState("");
  const [fetching, setFetching] = useState(false);
  const [fetchError, setFetchError] = useState("");
  const [demoLoading, setDemoLoading] = useState(false);

  async function handleRun() {
    const url = inputUrl.trim();
    if (!url) return;
    setFetching(true);
    setFetchError("");
    try {
      const r = await submitReview(url);
      setReport(r);
      setPhase("done");
      setError("");
    } catch (e) {
      setFetchError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setFetching(false);
    }
  }

  async function handleLoadDemo() {
    setDemoLoading(true);
    setFetchError("");
    try {
      const raw = await runComparisonDemo();
      // Wrap the comparison demo payload into a Report-shaped object
      const demoReport = {
        pr_url: (raw as any)?.baseline?.pr_url ?? "https://github.com/patchcourt/demo/pull/1337",
        overall_score: (raw as any)?.baseline?.patchcourt?.overall_score ?? 0,
        verdict: (raw as any)?.baseline?.patchcourt?.verdict ?? "MERGE",
        files: (raw as any)?.report?.files ?? [],
        claims: (raw as any)?.report?.claims ?? [],
        debate_transcripts: (raw as any)?.report?.debate_transcripts ?? [],
        finding_assessments: (raw as any)?.report?.finding_assessments ?? [],
        baseline_report: (raw as any)?.baseline ?? null,
      };
      setReport(demoReport as any);
      setPhase("done");
      setError("");
    } catch (e) {
      setFetchError(e instanceof Error ? e.message : "Demo load failed");
    } finally {
      setDemoLoading(false);
    }
  }

  const prInputBlock = (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <input
          type="url"
          placeholder="https://github.com/owner/repo/pull/123"
          value={inputUrl}
          onChange={(e) => setInputUrl(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleRun()}
          className="flex-1 rounded-md border border-border bg-background px-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary"
        />
        <button
          onClick={handleRun}
          disabled={fetching || !inputUrl.trim()}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground disabled:opacity-50"
        >
          {fetching ? "Running…" : "Run"}
        </button>
        <button
          onClick={handleLoadDemo}
          disabled={demoLoading || fetching}
          className="rounded-md border border-border bg-zinc-800 px-4 py-2 text-sm font-medium text-zinc-200 hover:bg-zinc-700 disabled:opacity-50"
        >
          {demoLoading ? "Loading…" : "Load Demo"}
        </button>
      </div>
      {fetchError && <p className="text-xs text-destructive">{fetchError}</p>}
    </div>
  );

  if (phase === "loading" || fetching) {
    return (
      <LayoutWrapper>
        <div className="flex flex-col items-center gap-4 rounded-lg border border-border bg-card p-10">
          <div className="flex items-center gap-2">
            <svg className="animate-spin size-5 text-primary" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <span className="text-sm text-muted-foreground">Running comparison…</span>
          </div>
        </div>
      </LayoutWrapper>
    );
  }

  if (!report) {
    return (
      <LayoutWrapper>
        <div className="flex flex-col gap-6">
          <ViewHeader title="SonarQube vs PatchCourt" />
          <Card>
            <CardContent className="pt-4 pb-4 space-y-3">
              <p className="text-sm text-muted-foreground">
                Enter a GitHub PR URL to run a fresh comparison, or run a review from the Overview tab first.
              </p>
              {prInputBlock}
            </CardContent>
          </Card>
        </div>
      </LayoutWrapper>
    );
  }

  const data = report?.baseline_report ?? null;

  if (!data) {
    return (
      <LayoutWrapper>
        <div className="flex flex-col gap-6">
          <ViewHeader title="SonarQube vs PatchCourt" subtitle={report.pr_url} />
          <Card>
            <CardContent className="pt-4 pb-4 space-y-3">
              <p className="text-sm text-muted-foreground">No comparison data for this review. Run a different PR:</p>
              {prInputBlock}
            </CardContent>
          </Card>
        </div>
      </LayoutWrapper>
    );
  }

  const pc = data.patchcourt;
  const fc: FindingComparison = pc?.finding_comparison ?? EMPTY_COMPARISON;
  const legacy: BaselineComparison | undefined = pc?.comparison;
  const findings = fc.findings;
  const verdict: string = fc.verdict || pc?.verdict || "";
  const score: number = Number(pc?.overall_score ?? 0);
  const counts = fc.counts;
  const summary = data.summary;
  const contextual_summary = pc?.contextual_summary ?? null;
  const isDemo = report.pr_url.includes("patchcourt/demo");

  return (
    <LayoutWrapper>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-bold">SonarQube vs PatchCourt</h1>
            <p className="mt-1 truncate font-mono text-xs text-muted-foreground max-w-[420px]">
              {report.pr_url}
            </p>
            <p className="text-sm text-muted-foreground mt-1">
              Evidence-based adjudication · {isDemo ? "Demo workspace" : "derived from active review"}
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <span className="text-sm text-muted-foreground">Score: {score.toFixed(1)}</span>
            <span className={`px-3 py-1 rounded-full text-sm font-bold border border-current ${VERDICT_COLOR[verdict] ?? "text-zinc-300"}`}>
              {verdict || "—"}
            </span>
          </div>
        </div>

        {/* Run a different PR inline */}
        <Card>
          <CardContent className="pt-3 pb-3">
            <p className="text-xs text-muted-foreground mb-2">Run comparison for a different PR:</p>
            {prInputBlock}
          </CardContent>
        </Card>

        {/* Summary */}
        {contextual_summary ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">PatchCourt Assessment Summary</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-4 text-sm">
              <span>Total findings: <strong>{contextual_summary.total ?? 0}</strong></span>
              <span>Blocking: <strong className="text-red-400">{contextual_summary.blocking ?? 0}</strong></span>
              {Object.entries(contextual_summary.by_status ?? {}).map(([k, v]) => (
                <span key={k}>{k}: <strong>{String(v)}</strong></span>
              ))}
            </CardContent>
          </Card>
        ) : null}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card><CardContent className="pt-4 pb-3">
            <div className="text-2xl font-bold">{data.total_open_issues ?? 0}</div>
            <div className="text-xs mt-0.5">Static-analysis Findings</div>
            <div className="text-xs text-muted-foreground">{data.issues_touching_pr ?? 0} in PR</div>
          </CardContent></Card>
          <Card><CardContent className="pt-4 pb-3">
            <div className="text-2xl font-bold">{fc.adjudicated ?? 0}</div>
            <div className="text-xs mt-0.5">Adjudicated</div>
            <div className="text-xs text-muted-foreground">{((Number(fc.coverage ?? 0)) * 100).toFixed(0)}% coverage</div>
          </CardContent></Card>
          <Card><CardContent className="pt-4 pb-3">
            <div className="text-2xl font-bold text-green-400">{counts.confirmed ?? 0}</div>
            <div className="text-xs mt-0.5">Supported</div>
          </CardContent></Card>
          <Card><CardContent className="pt-4 pb-3">
            <div className="text-2xl font-bold text-red-400">{counts.contradicted ?? 0}</div>
            <div className="text-xs mt-0.5">Contradicted</div>
          </CardContent></Card>
        </div>

        {/* Scanner breakdown */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">Scanner Breakdown</CardTitle>
          </CardHeader>
          <CardContent className="flex gap-6 text-sm">
            <span>Vulnerabilities: <strong>{summary.vulnerabilities ?? 0}</strong></span>
            <span>Bugs: <strong>{summary.bugs ?? 0}</strong></span>
            <span>Code Smells: <strong>{summary.code_smells ?? 0}</strong></span>
          </CardContent>
        </Card>

        {/* Finding-by-finding */}
        <div>
          <h2 className="text-base font-semibold mb-3">Finding-by-Finding Adjudication</h2>
          <div className="space-y-3">
            {findings.map((row, i) => {
              const sonar = row.sonar;
              const pcr = row.patchcourt;
              const group: string = row.group ?? "unmatched";
              return (
                <div key={i} className={`border-l-4 rounded-r-lg p-4 bg-card ${GROUP_COLOR[group] ?? ""}`}>
                  {/* Finding header */}
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className={`text-xs font-bold ${SEV_COLOR[sonar.severity] ?? "text-zinc-400"}`}>{sonar.severity}</span>
                    <span className="text-xs bg-zinc-800 px-2 py-0.5 rounded font-mono">{sonar.rule}</span>
                    <span className="text-xs text-muted-foreground">{sonar.type}</span>
                    {/* PR-introduction badge — the most important signal */}
                    {(pcr as any)?.introduced_by_pr ? (
                      <span className="text-xs font-bold bg-red-500/20 text-red-300 border border-red-500/40 px-1.5 py-0.5 rounded">NEW IN PR</span>
                    ) : (pcr as any)?.pre_existing ? (
                      <span className="text-xs font-bold bg-zinc-700/60 text-zinc-400 border border-zinc-600 px-1.5 py-0.5 rounded">PRE-EXISTING</span>
                    ) : null}
                    <span className="ml-auto text-xs font-bold uppercase">{GROUP_LABEL[group] ?? group}</span>
                  </div>

                  {/* Location + message */}
                  <div className="mb-1">
                    <span className="text-xs text-muted-foreground font-mono">{sonar.file}:{sonar.line}</span>
                    <p className="text-sm mt-0.5">{sonar.message}</p>
                  </div>

                  {/* Code snippet — highlighted context window around the flagged line */}
                  {(pcr as any)?.code_snippet ? (
                    <CodeSnippet snippet={(pcr as any).code_snippet} />
                  ) : null}

                  {/* PatchCourt adjudication details */}
                  {pcr ? (
                    <div className="mt-3 pt-2 border-t border-white/10 space-y-1.5">
                      <div className="flex flex-wrap gap-3 text-xs">
                        <span><span className="text-muted-foreground">Priority: </span><strong>{pcr.contextual_priority || "—"}</strong></span>
                        <span><span className="text-muted-foreground">Action: </span><strong>{pcr.contextual_action || "—"}</strong></span>
                        {pcr.corroborated ? <span className="text-green-400 font-medium">✓ Corroborated</span> : null}
                        {pcr.corroborating_tools?.length > 0 ? (
                          <span className="text-muted-foreground">Tools: {pcr.corroborating_tools.join(", ")}</span>
                        ) : null}
                        {pcr.fault_correlation ? (
                          <span className={`border rounded px-1.5 py-0.5 text-xs font-medium ${FAULT_CORR_COLOR[pcr.fault_correlation] ?? "text-zinc-400"}`}>
                            Fault-risk: {pcr.fault_correlation}
                          </span>
                        ) : null}
                        {pcr.qa_verdict && pcr.qa_verdict !== "VALID" ? (
                          <span className={`text-xs font-medium ${QA_COLOR[pcr.qa_verdict] ?? "text-zinc-400"}`}>
                            QA: {pcr.qa_verdict}
                          </span>
                        ) : null}
                      </div>
                      {pcr.rationale ? (
                        <p className="text-xs text-muted-foreground leading-relaxed">{pcr.rationale}</p>
                      ) : null}
                      {(pcr as any).pre_existing ? (
                        <p className="text-xs text-zinc-500 italic">⚠ This issue existed before this PR. It is not introduced by the current change — consider tracking separately.</p>
                      ) : null}
                      {pcr.fp_fn_root_cause ? (
                        <div className="text-xs bg-zinc-900/60 rounded px-2 py-1 border-l-2 border-l-orange-500">
                          <span className="font-medium text-orange-400">FP/FN Root Cause: {pcr.fp_fn_root_cause}</span>
                          {pcr.fp_fn_explanation ? (
                            <p className="text-muted-foreground mt-0.5">{pcr.fp_fn_explanation}</p>
                          ) : null}
                        </div>
                      ) : null}
                      {pcr.qa_note ? (
                        <p className="text-xs text-yellow-400/80 italic">{pcr.qa_note}</p>
                      ) : null}
                      {pcr.policies?.length > 0 ? (
                        <div className="mt-1 space-y-1">
                          {pcr.policies.map((pol: any, j: number) => (
                            <div key={j} className="text-xs bg-zinc-900/60 rounded px-2 py-1">
                              <span className="font-medium text-primary">[{pol.id}] {pol.title}</span>
                              {pol.excerpt ? <p className="text-muted-foreground mt-0.5">{pol.excerpt}</p> : null}
                            </div>
                          ))}
                        </div>
                      ) : null}
                      {row.scenario ? <p className="text-xs text-zinc-500 mt-1">Scenario: {row.scenario}</p> : null}
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-500 mt-2 italic">No PatchCourt assessment matched.</p>
                  )}
                </div>
              );
            })}
            {findings.length === 0 && (
              <p className="text-sm text-muted-foreground italic">No findings in this PR — nothing to adjudicate.</p>
            )}
          </div>
        </div>

        {/* PatchCourt found, scanner missed */}
        {legacy?.sonar_missed && legacy.sonar_missed.length > 0 ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">
                PatchCourt Found — Scanner Missed ({legacy.sonar_missed.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {legacy.sonar_missed.map((m: any, i: number) => (
                <div key={i} className="text-sm border-l-2 border-l-primary pl-3 py-1">
                  <span className="font-mono text-xs text-muted-foreground">{m.file}:{m.line}</span>
                  <span className="ml-2 text-xs text-muted-foreground">Agent: {m.agent} · Tier T{m.tier}</span>
                  <p className="mt-0.5">{m.issue}</p>
                </div>
              ))}
            </CardContent>
          </Card>
        ) : null}

        {/* Taint-inference findings (IRIS-inspired) */}
        {(() => {
          const taintAssessments = (report?.finding_assessments ?? []).filter(
            (a: any) => a?.tool === "taint-inference"
          );
          if (!taintAssessments.length) return null;
          return (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">
                  LLM-Inferred Taint Flows — Scanner Missed ({taintAssessments.length})
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-xs text-muted-foreground">
                  Not flagged by the static analyzer. Inferred from source/sink patterns (IRIS-inspired). Requires human verification.
                </p>
                {taintAssessments.map((a: any, i: number) => (
                  <div key={i} className="border-l-2 border-l-purple-500 pl-3 py-1">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="font-mono text-xs text-muted-foreground">{a.file}:{a.line}</span>
                      <span className="text-xs bg-purple-900/40 text-purple-300 px-1.5 rounded">{a.rule}</span>
                      <span className="text-xs text-muted-foreground">Severity {a.severity}/5</span>
                    </div>
                    <p className="text-sm">{a.message}</p>
                    {a.code_snippet ? <CodeSnippet snippet={a.code_snippet} /> : null}
                    {a.rationale ? <p className="text-xs text-muted-foreground mt-0.5 italic">{a.rationale}</p> : null}
                  </div>
                ))}
              </CardContent>
            </Card>
          );
        })()}

      </div>
    </LayoutWrapper>
  );
}
