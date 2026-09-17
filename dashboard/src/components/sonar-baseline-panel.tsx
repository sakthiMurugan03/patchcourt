"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ExternalLink, RefreshCw, XCircle, Search, ShieldAlert, ShieldCheck, ShieldQuestion, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getBaselineLatest, refreshBaseline } from "@/lib/api";
import type { BaselineReport, Verdict, SonarSeverity, BaselineComparison } from "@/lib/types";
import { VERDICT_META } from "@/lib/types";

const SONAR_SEV_META: Record<SonarSeverity, { color: string; label: string }> = {
  BLOCKER:  { color: "#f87171", label: "BLOCKER" },
  CRITICAL: { color: "#fb923c", label: "CRITICAL" },
  MAJOR:    { color: "#fbbf24", label: "MAJOR" },
  MINOR:    { color: "#38bdf8", label: "MINOR" },
  INFO:     { color: "#94a3b8", label: "INFO" },
};

function SeverityChip({ severity }: { severity: SonarSeverity }) {
  const meta = SONAR_SEV_META[severity] ?? SONAR_SEV_META.INFO;
  return <Badge style={{ backgroundColor: meta.color, color: "#0b1220" }}>{meta.label}</Badge>;
}

function DiffSection({
  title,
  color,
  count,
  empty,
  children,
}: {
  title: string;
  color: string;
  count: number;
  empty: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: color }} />
        <h4 className="text-sm font-medium text-foreground">{title}</h4>
        <Badge variant="outline" className="ml-auto font-mono text-[11px]">{count}</Badge>
      </div>
      {count === 0 ? (
        <p className="text-xs italic text-muted-foreground">{empty}</p>
      ) : (
        <div className="rounded-md border border-border bg-muted/30 divide-y divide-border text-xs">
          {children}
        </div>
      )}
    </div>
  );
}

function RowLabel({ file, line }: { file: string; line: number }) {
  return (
    <code className="break-all text-[11px] text-foreground">{file}:{line}</code>
  );
}

export function SonarBaselinePanel({ defaultPrUrl = "" }: { defaultPrUrl?: string }) {
  const [report, setReport] = useState<BaselineReport | null>(null);
  const [error, setError] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [prUrl, setPrUrl] = useState(defaultPrUrl);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const r = await getBaselineLatest();
        if (!cancelled) setReport(r);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load baseline");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => { if (defaultPrUrl) setPrUrl(defaultPrUrl); }, [defaultPrUrl]);

  async function handleRefresh() {
    if (!prUrl) return;
    setRefreshing(true);
    setError("");
    try {
      const r = await refreshBaseline(prUrl);
      setReport(r);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Refresh failed — is SonarQube running?");
    } finally {
      setRefreshing(false);
    }
  }

  const comp: BaselineComparison | undefined = report?.patchcourt?.comparison;
  const verdict: Verdict | undefined = report?.patchcourt?.verdict ?? comp?.verdict;
  const rawN = comp?.counts.raw ?? 0;
  const confirmedM = comp?.counts.confirmed ?? 0;
  const suppressed = comp?.counts.suppressed ?? 0;
  const sonarMissed = comp?.counts.sonar_missed ?? 0;
  const severityCounts = (report?.issues ?? []).reduce(
    (acc, issue) => { acc[issue.severity] = (acc[issue.severity] ?? 0) + 1; return acc; },
    {} as Record<SonarSeverity, number>,
  );
  const hasBaseline = !!report;

  return (
    <Card className="w-full border-l-4" style={{ borderLeftColor: "#38bdf8" }}>
      <CardHeader className="pb-0">
        <div className="flex items-center justify-between gap-3">
          <CardTitle className="text-base">SonarQube Baseline</CardTitle>
          <a
            href="http://localhost:9000"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 rounded-md bg-muted px-2.5 py-1.5 text-xs font-medium text-muted-foreground transition hover:bg-primary/10 hover:text-primary"
          >
            <ExternalLink className="size-3" />
            Open SonarQube UI
          </a>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-5 pt-4">
        {/* controls */}
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
          <Input
            placeholder="https://github.com/owner/repo/pull/123"
            value={prUrl}
            onChange={(e) => setPrUrl(e.target.value)}
            className="flex-1 text-xs"
          />
          <Button
            variant="secondary"
            className="inline-flex items-center gap-2 text-xs"
            disabled={!prUrl || refreshing}
            onClick={() => handleRefresh()}
          >
            <RefreshCw className={`size-3 ${refreshing ? "animate-spin" : ""}`} />
            Refresh baseline
          </Button>
        </div>

        {loading && (
          <div className="flex items-center gap-2 py-8 text-xs text-muted-foreground">
            <Search className="size-3 animate-pulse" />
            Loading saved baseline…
          </div>
        )}

        {error && !loading && (
          <p className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {error}
          </p>
        )}

        {!loading && !hasBaseline && (
          <div className="flex flex-col items-center gap-4 rounded-lg border border-border bg-muted/30 p-8 text-center">
            <ShieldQuestion className="size-10 text-muted-foreground/40" />
            <div>
              <p className="text-sm font-medium text-foreground">No baseline report yet</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Enter a PR URL above and click <strong>Refresh baseline</strong>, or run from the terminal:
              </p>
              <code className="mt-2 block rounded-md bg-muted px-3 py-1.5 text-[11px] text-muted-foreground">
                python -m patchcourt baseline https://github.com/owner/repo/pull/123
              </code>
            </div>
          </div>
        )}

        {!loading && hasBaseline && (
          <>
            {/* headline stat */}
            {comp ? (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-foreground">
                <span className="font-semibold">SonarQube raw: <span className="font-mono">{rawN}</span></span>
                <span className="text-muted-foreground">|</span>
                <span>PatchCourt confirmed: <span className="font-mono font-semibold" style={{ color: "#2dd4bf" }}>{confirmedM}</span></span>
                <span className="text-muted-foreground">|</span>
                <span>suppressed as unbacked: <span className="font-mono font-semibold" style={{ color: "#fbbf24" }}>{suppressed}</span></span>
              </div>
            ) : (
              <div className="rounded-md bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                Raw report loaded — click <strong>Refresh baseline</strong> to compute PatchCourt comparison.
              </div>
            )}

            {/* severity breakdown */}
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">Raw findings breakdown:</span>
              {(Object.keys(SONAR_SEV_META) as SonarSeverity[]).map((s) => (
                <Badge key={s} variant="outline" className="font-mono text-[11px]" style={{ borderColor: SONAR_SEV_META[s].color }}>
                  <span style={{ color: SONAR_SEV_META[s].color }}>{SONAR_SEV_META[s].label}</span>
                  <span className="ml-1.5 text-foreground">{severityCounts[s] ?? 0}</span>
                </Badge>
              ))}
              <span className="ml-auto font-mono text-xs text-muted-foreground">
                total open: {report.total_open_issues} | touching PR: {report.issues_touching_pr}
              </span>
            </div>

            {/* PatchCourt verdict badge */}
            {verdict && (
              <div className="flex items-center gap-3 rounded-md border border-border bg-muted/30 px-4 py-3">
                {verdict === "BLOCK" ? <XCircle className="size-5 text-destructive" /> : verdict === "NEEDS_REVIEW" ? <AlertTriangle className="size-5 text-amber-400" /> : <CheckCircle2 className="size-5 text-teal-400" />}
                <div>
                  <Badge style={{ backgroundColor: VERDICT_META[verdict].color, color: "#0b1220" }}>
                    {VERDICT_META[verdict].label}
                  </Badge>
                  <span className="ml-2 text-xs text-muted-foreground">
                    PatchCourt score {report.patchcourt?.overall_score?.toFixed(1) ?? "—"}
                  </span>
                </div>
              </div>
            )}

            {/* diff table */}
            {comp && (
              <div className="flex flex-col gap-5">
                <DiffSection title="Confirmed / kept (corroborated)" color="#2dd4bf" count={confirmedM} empty="No corroborated issues — all SonarQube findings suppressed as unbacked.">
                  {comp.confirmed.map((issue, i) => (
                    <div key={`c-${i}`} className="flex items-center gap-3 px-3 py-2">
                      <RowLabel file={issue.file} line={issue.line} />
                      <SeverityChip severity={issue.severity} />
                      <span className="text-muted-foreground">{issue.rule}</span>
                      <span className="ml-auto truncate text-[11px] text-muted-foreground">{issue.message}</span>
                    </div>
                  ))}
                </DiffSection>

                <DiffSection title="Down-tiered as unbacked (likely false positives)" color="#fbbf24" count={suppressed} empty="All SonarQube findings backed.">
                  {comp.down_tiered.map((issue, i) => (
                    <div key={`d-${i}`} className="flex items-center gap-3 px-3 py-2">
                      <RowLabel file={issue.file} line={issue.line} />
                      <SeverityChip severity={issue.severity} />
                      <span className="text-muted-foreground">{issue.rule}</span>
                      <span className="ml-auto truncate text-[11px] text-muted-foreground">{issue.message}</span>
                    </div>
                  ))}
                </DiffSection>

                <DiffSection title="Sonar-missed (PatchCourt caught, Sonar didn't)" color="#818cf8" count={sonarMissed} empty="No PatchCourt-only findings beyond SonarQube.">
                  {comp.sonar_missed.map((issue, i) => (
                    <div key={`m-${i}`} className="flex items-center gap-3 px-3 py-2">
                      <RowLabel file={issue.file} line={issue.line} />
                      <Badge variant="outline" className="border-indigo-400 text-indigo-400">T{issue.tier}</Badge>
                      <span className="text-muted-foreground">{issue.agent}</span>
                      <span className="ml-auto truncate text-[11px] text-muted-foreground">{issue.issue}</span>
                    </div>
                  ))}
                </DiffSection>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
