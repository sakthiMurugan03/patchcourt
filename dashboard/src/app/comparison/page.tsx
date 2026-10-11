"use client";

import { useEffect, useState } from "react";
import { LayoutWrapper } from "@/components/layout-wrapper";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

const VERDICT_COLOR: Record<string, string> = {
  BLOCK: "text-red-400",
  REMEDIATE: "text-orange-400",
  MONITOR: "text-yellow-400",
  PASS: "text-green-400",
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

export default function ComparisonPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/api/comparison/demo`)
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <LayoutWrapper><div className="p-8 text-muted-foreground">Loading…</div></LayoutWrapper>;
  if (error) return <LayoutWrapper><div className="p-8 text-red-400">Error: {error}</div></LayoutWrapper>;
  if (!data) return <LayoutWrapper><div className="p-8">No data</div></LayoutWrapper>;

  const fc = data?.baseline?.patchcourt?.finding_comparison ?? {};
  const legacy = data?.baseline?.patchcourt?.comparison ?? {};
  const findings: any[] = fc?.findings ?? [];
  const verdict: string = fc?.verdict ?? "";
  const score: number = Number(fc?.overall_score ?? 0);
  const counts = fc?.counts ?? {};
  const summary = data?.baseline?.summary ?? {};
  const contextual_summary: any = data?.baseline?.patchcourt?.contextual_summary ?? null;

  return (
    <LayoutWrapper>
      <div className="space-y-6">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">SonarQube vs PatchCourt</h1>
            <p className="text-sm text-muted-foreground mt-1">Evidence-based adjudication · Demo workspace</p>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-sm text-muted-foreground">Score: {(score * 100).toFixed(0)}%</span>
            <span className={`px-3 py-1 rounded-full text-sm font-bold border border-current ${VERDICT_COLOR[verdict] ?? "text-zinc-300"}`}>
              {verdict || "—"}
            </span>
          </div>
        </div>

        {/* Summary */}
        {contextual_summary ? (
          <Card>
            <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">PatchCourt Assessment Summary</CardTitle></CardHeader>
            <CardContent className="flex flex-wrap gap-4 text-sm">
              <span>Total findings: <strong>{contextual_summary.total ?? 0}</strong></span>
              <span>Blocking: <strong className="text-red-400">{contextual_summary.blocking ?? 0}</strong></span>
              {Object.entries(contextual_summary.by_status ?? {}).map(([k, v]: any) => (
                <span key={k}>{k}: <strong>{v}</strong></span>
              ))}
            </CardContent>
          </Card>
        ) : null}

        {/* Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Card><CardContent className="pt-4 pb-3">
            <div className="text-2xl font-bold">{data?.baseline?.total_open_issues ?? 0}</div>
            <div className="text-xs mt-0.5">SonarQube Issues</div>
            <div className="text-xs text-muted-foreground">{data?.baseline?.issues_touching_pr ?? 0} in PR</div>
          </CardContent></Card>
          <Card><CardContent className="pt-4 pb-3">
            <div className="text-2xl font-bold">{fc?.adjudicated ?? 0}</div>
            <div className="text-xs mt-0.5">Adjudicated</div>
            <div className="text-xs text-muted-foreground">{((Number(fc?.coverage ?? 0)) * 100).toFixed(0)}% coverage</div>
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

        {/* SonarQube breakdown */}
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">SonarQube Breakdown</CardTitle></CardHeader>
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
            {findings.map((row: any, i: number) => {
              const sonar = row.sonar ?? {};
              const pc = row.patchcourt;
              const group: string = row.group ?? "unmatched";
              return (
                <div key={i} className={`border-l-4 rounded-r-lg p-4 bg-card ${GROUP_COLOR[group] ?? ""}`}>
                  <div className="flex flex-wrap items-center gap-2 mb-2">
                    <span className={`text-xs font-bold ${SEV_COLOR[sonar.severity] ?? "text-zinc-400"}`}>{sonar.severity}</span>
                    <span className="text-xs bg-zinc-800 px-2 py-0.5 rounded font-mono">{sonar.rule}</span>
                    <span className="text-xs text-muted-foreground">{sonar.type}</span>
                    <span className="ml-auto text-xs font-bold uppercase">{GROUP_LABEL[group] ?? group}</span>
                  </div>
                  <div className="mb-2">
                    <span className="text-xs text-muted-foreground font-mono">{sonar.file}:{sonar.line}</span>
                    <p className="text-sm mt-0.5">{sonar.message}</p>
                  </div>
                  {pc ? (
                    <div className="mt-2 pt-2 border-t border-white/10 space-y-1">
                      <div className="flex flex-wrap gap-3 text-xs">
                        <span><span className="text-muted-foreground">Priority: </span><strong>{pc.contextual_priority || "—"}</strong></span>
                        <span><span className="text-muted-foreground">Action: </span><strong>{pc.contextual_action || "—"}</strong></span>
                        {pc.corroborated ? <span className="text-green-400 font-medium">✓ Corroborated</span> : null}
                        {pc.corroborating_tools?.length > 0 ? <span className="text-muted-foreground">Tools: {pc.corroborating_tools.join(", ")}</span> : null}
                      </div>
                      {pc.rationale ? <p className="text-xs text-muted-foreground leading-relaxed">{pc.rationale}</p> : null}
                      {pc.policies?.length > 0 ? (
                        <div className="mt-1 space-y-1">
                          {pc.policies.map((pol: any, j: number) => (
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
          </div>
        </div>

        {/* Sonar missed */}
        {legacy?.sonar_missed?.length > 0 ? (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-muted-foreground uppercase tracking-wide">
                PatchCourt Found — SonarQube Missed ({legacy.sonar_missed.length})
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

      </div>
    </LayoutWrapper>
  );
}
