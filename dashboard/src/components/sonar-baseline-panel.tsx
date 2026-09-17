"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, ExternalLink, RefreshCw, XCircle, Search, ShieldAlert, ShieldCheck, ShieldQuestion } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { getBaselineLatest, refreshBaseline } from "@/lib/api";
import type { BaselineReport, Verdict, SonarSeverity, BaselineComparison } from "@/lib/types";
import { VERDICT_META } from "@/lib/types";
import { cn } from "cn";

const SONAR_SEV_META: Record<SonarSeverity, { color: string; label: string; class: string }> = {
  BLOCKER:  { color: "var(--severity-critical)", label: "BLOCKER", class: "sev-critical" },
  CRITICAL: { color: "var(--severity-high)", label: "CRITICAL", class: "sev-high" },
  MAJOR:    { color: "var(--severity-medium)", label: "MAJOR", class: "sev-medium" },
  MINOR:    { color: "var(--severity-low)", label: "MINOR", class: "sev-low" },
  INFO:     { color: "var(--severity-info)", label: "INFO", class: "sev-info" },
};

function SeverityChip({ severity }: { severity: SonarSeverity }) {
  const meta = SONAR_SEV_META[severity] ?? SONAR_SEV_META.INFO;
  return <Badge variant="outline" className={cn("font-mono text-[10px]", meta.class)} style={{ borderColor: meta.color, color: meta.color }}>{meta.label}</Badge>;
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

  const VerdictIcon = {
    MERGE: CheckCircle2,
    NEEDS_REVIEW: AlertTriangle,
    BLOCK: XCircle,
  } as const;

  const verdictColors = {
    MERGE: "text-green-400",
    NEEDS_REVIEW: "text-amber-400",
    BLOCK: "text-red-400",
  } as const;

  return (
    <Card className="w-full border-l-4" style={{ borderLeftColor: "var(--primary)" }}>
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
            {comp ? (
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-foreground">
                <span className="font-semibold">SonarQube raw: <span className="font-mono">{rawN}</span></span>
                <span className="text-muted-foreground">|</span>
                <span>PatchCourt confirmed: <span className="font-mono font-semibold sev-low">{confirmedM}</span></span>
                <span className="text-muted-foreground">|</span>
                <span>suppressed as unbacked: <span className="font-mono font-semibold sev-medium">{suppressed}</span></span>
              </div>
            ) : (
              <div className="rounded-md bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
                Raw report loaded — click <strong>Refresh baseline</strong> to compute PatchCourt comparison.
              </div>
            )}

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-xs font-medium text-muted-foreground">Raw findings breakdown:</span>
              {(Object.keys(SONAR_SEV_META) as SonarSeverity[]).map((s) => (
                <Badge key={s} variant="outline" className={cn("font-mono text-[11px]", SONAR_SEV_META[s].class)} style={{ borderColor: SONAR_SEV_META[s].color }}>
                  <span style={{ color: SONAR_SEV_META[s].color }}>{SONAR_SEV_META[s].label}</span>
                  <span className="ml-1.5 text-foreground">{severityCounts[s] ?? 0}</span>
                </Badge>
              ))}
              <span className="ml-auto font-mono text-xs text-muted-foreground">
                total open: {report.total_open_issues} | touching PR: {report.issues_touching_pr}
              </span>
            </div>

            {verdict && (
              <div className="flex items-center gap-3 rounded-md border border-border bg-muted/30 px-4 py-3">
                {(() => {
                  switch (verdict) {
                    case "MERGE":
                      return <CheckCircle2 className={cn("size-5", verdictColors.MERGE)} />;
                    case "NEEDS_REVIEW":
                      return <AlertTriangle className={cn("size-5", verdictColors.NEEDS_REVIEW)} />;
                    case "BLOCK":
                      return <XCircle className={cn("size-5", verdictColors.BLOCK)} />;
                    default:
                      return null;
                  }
                })()}
                <div>
                  <Badge className={cn("bg-sev-critical text-black", verdict === "MERGE" && "bg-sev-low", verdict === "NEEDS_REVIEW" && "bg-sev-medium")}>
                    {VERDICT_META[verdict].label}
                  </Badge>
                  <span className="ml-2 text-xs text-muted-foreground">
                    PatchCourt score {report.patchcourt?.overall_score?.toFixed(1) ?? "—"}
                  </span>
                </div>
              </div>
            )}

            {comp && (
              <div className="flex flex-col gap-5">
                <DiffSection title="Confirmed / kept (corroborated)" color="var(--severity-low)" count={confirmedM} empty="No corroborated issues — all SonarQube findings suppressed as unbacked.">
                  {comp.confirmed.map((issue, i) => (
                    <div key={`c-${i}`} className="flex items-center gap-3 px-3 py-2">
                      <RowLabel file={issue.file} line={issue.line} />
                      <SeverityChip severity={issue.severity} />
                      <span className="text-muted-foreground font-mono text-[10px]">{issue.rule}</span>
                      <span className="ml-auto truncate text-[11px] text-muted-foreground">{issue.message}</span>
                    </div>
                  ))}
                </DiffSection>

                <DiffSection title="Down-tiered as unbacked (likely false positives)" color="var(--severity-medium)" count={suppressed} empty="All SonarQube findings backed.">
                  {comp.down_tiered.map((issue, i) => (
                    <div key={`d-${i}`} className="flex items-center gap-3 px-3 py-2">
                      <RowLabel file={issue.file} line={issue.line} />
                      <SeverityChip severity={issue.severity} />
                      <span className="text-muted-foreground font-mono text-[10px]">{issue.rule}</span>
                      <span className="ml-auto truncate text-[11px] text-muted-foreground">{issue.message}</span>
                    </div>
                  ))}
                </DiffSection>

                <DiffSection title="Sonar-missed (PatchCourt caught, Sonar didn't)" color="var(--primary)" count={sonarMissed} empty="No PatchCourt-only findings beyond SonarQube.">
                  {comp.sonar_missed.map((issue, i) => (
                    <div key={`m-${i}`} className="flex items-center gap-3 px-3 py-2">
                      <RowLabel file={issue.file} line={issue.line} />
                      <Badge variant="outline" className="border-primary text-primary text-[10px]">T{issue.tier}</Badge>
                      <span className="text-muted-foreground text-[10px]">{issue.agent}</span>
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