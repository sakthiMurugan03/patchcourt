"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { LayoutWrapper } from "@/components/layout-wrapper";
import { ViewHeader } from "@/components/view-header";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useReview } from "@/lib/review-context";
import { submitReview, runComparisonDemo } from "@/lib/api";
import type { BaselineComparison, FindingComparison, Report } from "@/lib/types";

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

// ── Capability comparison table ─────────────────────────────────────────────
function EvidencePill({ label, color }: { label: string; color: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium border ${color}`}>
      {label}
    </span>
  );
}

function CapabilityTable({ report, fc, legacy }: {
  report: Report;
  fc: FindingComparison;
  legacy: BaselineComparison | undefined;
}) {
  const [open, setOpen] = useState(false);

  // derive live evidence from report
  const assessments = (report.finding_assessments ?? []) as any[];
  const taintCount = assessments.filter((a) => a?.tool === "taint-inference").length;
  const hasTaint = taintCount > 0;
  const hasDebate = (report.debate_transcripts ?? []).length > 0;
  const hasCorroborated = assessments.some((a) => a?.corroborated);
  const hasFpFn = assessments.some((a) => a?.fp_fn_root_cause);
  const hasFaultCorr = assessments.some((a) => a?.fault_correlation);
  const hasQa = assessments.some((a) => a?.qa_verdict);
  const hasNewInPr = assessments.some((a) => a?.introduced_by_pr);
  const sonarRaw = legacy?.counts?.raw ?? fc.total_in_pr ?? 0;
  const sonarMissed = legacy?.counts?.sonar_missed ?? 0;
  const contradicted = fc.counts?.contradicted ?? 0;
  const adjCoverage = fc.total_in_pr > 0
    ? Math.round((fc.adjudicated / fc.total_in_pr) * 100)
    : 0;

  const rows: Array<{
    capability: string;
    sonar: string;
    patchcourt: string;
    evidence: React.ReactNode;
  }> = [
    {
      capability: "Source-code analysis",
      sonar: "Configured analysis engines and rules",
      patchcourt: "Static-analysis tools + AI agent analysis on the same findings",
      evidence: (
        <div className="flex flex-wrap gap-1">
          <EvidencePill label={`${sonarRaw} SonarQube findings`} color="text-blue-400 border-blue-400/40" />
          <EvidencePill label={`${assessments.length} PatchCourt assessments`} color="text-teal-400 border-teal-400/40" />
        </div>
      ),
    },
    {
      capability: "Security review",
      sonar: "Depends on configured analyzers",
      patchcourt: "Specialist SecurityAgent + taint-inference patterns (IRIS-inspired)",
      evidence: (
        <div className="flex flex-wrap gap-1">
          {hasTaint
            ? <EvidencePill label={`${taintCount} taint flows inferred`} color="text-purple-400 border-purple-400/40" />
            : <EvidencePill label="No taint flows (this PR)" color="text-zinc-500 border-zinc-600" />}
          <EvidencePill label="SecurityAgent active" color="text-red-400 border-red-400/40" />
        </div>
      ),
    },
    {
      capability: "Code-quality review",
      sonar: "Analyzer rules and metrics",
      patchcourt: "Specialist QualityAgent adds correctness and maintainability claims",
      evidence: (
        <EvidencePill
          label={`${assessments.filter((a) => a?.category === "maintainability" || a?.category === "correctness").length} quality assessments`}
          color="text-cyan-400 border-cyan-400/40"
        />
      ),
    },
    {
      capability: "Practical risk evaluation",
      sonar: "Severity labels only; no deployment-context reasoning",
      patchcourt: "PragmatistAgent weighs real-world exploitability and deployment impact",
      evidence: <EvidencePill label="PragmatistAgent active" color="text-yellow-400 border-yellow-400/40" />,
    },
    {
      capability: "Repository policies",
      sonar: "Depends on configuration",
      patchcourt: "Relevant policies retrieved via RAG and attached to each assessment",
      evidence: (
        <EvidencePill
          label={`${assessments.reduce((n, a) => n + (a?.policies?.length ?? 0), 0)} policy refs matched`}
          color="text-indigo-400 border-indigo-400/40"
        />
      ),
    },
    {
      capability: "Finding validation",
      sonar: "Tool's own analysis only",
      patchcourt: "Dedicated adjudication stage: SUPPORTED / CONTRADICTED / UNCERTAIN / OUT_OF_SCOPE",
      evidence: (
        <div className="flex flex-wrap gap-1">
          <EvidencePill label={`${adjCoverage}% adjudicated`} color="text-green-400 border-green-400/40" />
          {contradicted > 0 && <EvidencePill label={`${contradicted} contradicted`} color="text-red-400 border-red-400/40" />}
        </div>
      ),
    },
    {
      capability: "Multiple perspectives",
      sonar: "Single analyzer view",
      patchcourt: "Three independent agents (Security, Quality, Pragmatist) review in parallel",
      evidence: (
        <div className="flex flex-wrap gap-1">
          {hasCorroborated && <EvidencePill label="Corroborated findings present" color="text-green-400 border-green-400/40" />}
          <EvidencePill label="3 agents" color="text-teal-400 border-teal-400/40" />
        </div>
      ),
    },
    {
      capability: "Conflict resolution",
      sonar: "Manual investigation required",
      patchcourt: "Conflict detector + bounded debate (≤2 rounds, retrieval-gated)",
      evidence: hasDebate
        ? <EvidencePill label={`${report.debate_transcripts.length} debate(s) resolved`} color="text-orange-400 border-orange-400/40" />
        : <EvidencePill label="No conflicts this PR" color="text-zinc-500 border-zinc-600" />,
    },
    {
      capability: "Evidence strength",
      sonar: "Tool-specific severity; no common model",
      patchcourt: "Common T1–T5 tier model: T1=tool flag, T2=corroborated, T3=policy, T4=precedent, T5=LLM",
      evidence: (
        <div className="flex flex-wrap gap-1">
          {[1,2,3,4,5].map((t) => {
            const n = assessments.filter((a) =>
              (a?.evidence ?? []).some((e: any) => e?.tier === t)
            ).length;
            return n > 0
              ? <EvidencePill key={t} label={`T${t}: ${n}`} color={t<=2 ? "text-red-400 border-red-400/40" : t===3 ? "text-yellow-400 border-yellow-400/40" : "text-zinc-400 border-zinc-600"} />
              : null;
          })}
        </div>
      ),
    },
    {
      capability: "Final decision",
      sonar: "Quality gate pass/fail",
      patchcourt: "Deterministic scoring judge with explicit MERGE / NEEDS_REVIEW / BLOCK verdict",
      evidence: (
        <EvidencePill
          label={`Score ${Number(report.overall_score ?? 0).toFixed(1)} → ${report.verdict}`}
          color={report.verdict === "BLOCK" ? "text-red-400 border-red-400/40" : report.verdict === "NEEDS_REVIEW" ? "text-yellow-400 border-yellow-400/40" : "text-green-400 border-green-400/40"}
        />
      ),
    },
    {
      capability: "Unsupported AI claims",
      sonar: "Not applicable",
      patchcourt: "Hard rule: BLOCK never rests on T5 (LLM-only) evidence alone",
      evidence: <EvidencePill label="T5-alone BLOCK rule enforced" color="text-purple-400 border-purple-400/40" />,
    },
    {
      capability: "FP/FN root cause",
      sonar: "No root cause tagging",
      patchcourt: "7-category taxonomy tagged on every CONTRADICTED/UNCERTAIN assessment",
      evidence: hasFpFn
        ? <EvidencePill label={`${assessments.filter((a) => a?.fp_fn_root_cause).length} tagged`} color="text-orange-400 border-orange-400/40" />
        : <EvidencePill label="None this PR" color="text-zinc-500 border-zinc-600" />,
    },
    {
      capability: "Fault-risk weighting",
      sonar: "Uniform severity labels",
      patchcourt: "Empirical fault-correlation nudge (±15%) on T1/T2 tool claims",
      evidence: hasFaultCorr
        ? <EvidencePill label={`${assessments.filter((a) => a?.fault_correlation === "high").length} high-fault rules`} color="text-red-400 border-red-400/40" />
        : <EvidencePill label="No tool claims this PR" color="text-zinc-500 border-zinc-600" />,
    },
    {
      capability: "Review audit",
      sonar: "Platform-dependent",
      patchcourt: "Full claim + evidence + verdict persisted to PostgreSQL audit trail",
      evidence: <EvidencePill label="Audit trail active" color="text-teal-400 border-teal-400/40" />,
    },
    {
      capability: "Baseline comparison",
      sonar: "Not the primary purpose",
      patchcourt: "Finding reconciliation: confirmed / contradicted / sonar-missed groups",
      evidence: (
        <div className="flex flex-wrap gap-1">
          <EvidencePill label={`${fc.counts.confirmed ?? 0} confirmed`} color="text-green-400 border-green-400/40" />
          {sonarMissed > 0 && <EvidencePill label={`${sonarMissed} sonar-missed`} color="text-blue-400 border-blue-400/40" />}
        </div>
      ),
    },
  ];

  return (
    <Card className="border-l-4 border-l-primary">
      <CardHeader className="pb-2 cursor-pointer select-none" onClick={() => setOpen((o) => !o)}>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold">
            PatchCourt vs SonarQube — Capability Comparison
          </CardTitle>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Live evidence from this review</span>
            {open ? <ChevronUp className="size-4 text-muted-foreground" /> : <ChevronDown className="size-4 text-muted-foreground" />}
          </div>
        </div>
      </CardHeader>
      {open && (
        <CardContent className="pt-0 pb-3">
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-zinc-900">
                  <th className="text-left px-3 py-2 text-muted-foreground font-semibold w-[18%] border border-zinc-800">Capability</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-semibold w-[26%] border border-zinc-800">SonarQube alone</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-semibold w-[30%] border border-zinc-800">PatchCourt approach</th>
                  <th className="text-left px-3 py-2 text-muted-foreground font-semibold w-[26%] border border-zinc-800">Live evidence</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row, i) => (
                  <tr key={i} className={i % 2 === 0 ? "bg-zinc-950" : "bg-zinc-900/40"}>
                    <td className="px-3 py-2 font-medium text-foreground border border-zinc-800 align-top">{row.capability}</td>
                    <td className="px-3 py-2 text-zinc-400 border border-zinc-800 align-top">{row.sonar}</td>
                    <td className="px-3 py-2 text-zinc-200 border border-zinc-800 align-top">{row.patchcourt}</td>
                    <td className="px-3 py-2 border border-zinc-800 align-top">{row.evidence}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      )}
    </Card>
  );
}

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
      const demo = raw as {
        baseline?: {
          pr_url?: string;
          patchcourt?: { overall_score?: number; verdict?: string };
        };
        report?: {
          files?: Report["files"];
          claims?: Report["claims"];
          debate_transcripts?: Report["debate_transcripts"];
          finding_assessments?: Report["finding_assessments"];
        };
      };
      const demoReport: Report = {
        pr_url: demo.baseline?.pr_url ?? "https://github.com/patchcourt/demo/pull/1337",
        overall_score: demo.baseline?.patchcourt?.overall_score ?? 0,
        verdict: (demo.baseline?.patchcourt?.verdict ?? "MERGE") as Report["verdict"],
        files: demo.report?.files ?? [],
        claims: demo.report?.claims ?? [],
        debate_transcripts: demo.report?.debate_transcripts ?? [],
        finding_assessments: demo.report?.finding_assessments ?? [],
        baseline_report: (demo.baseline as Report["baseline_report"]) ?? null,
      };
      setReport(demoReport);
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

        {/* Capability comparison — collapsible, wired to live data */}
        <CapabilityTable report={report} fc={fc} legacy={legacy} />

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
                    {(pcr)?.introduced_by_pr ? (
                      <span className="text-xs font-bold bg-red-500/20 text-red-300 border border-red-500/40 px-1.5 py-0.5 rounded">NEW IN PR</span>
                    ) : (pcr)?.pre_existing ? (
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
                  {(pcr)?.code_snippet ? (
                    <CodeSnippet snippet={(pcr).code_snippet} />
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
                      {(pcr).pre_existing ? (
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
                          {pcr.policies.map((pol, j: number) => (
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
              {legacy.sonar_missed.map((m, i: number) => (
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
            (a) => a?.tool === "taint-inference"
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
                {taintAssessments.map((a, i: number) => (
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
