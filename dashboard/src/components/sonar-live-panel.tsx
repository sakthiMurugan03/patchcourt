"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import {
  AlertCircle,
  CheckCircle2,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  Loader2,
  TriangleAlert,
  CircleAlert,
  Info,
  Shield,
  ShieldCheck,
  Wrench,
  Bug,
  ShieldAlert,
  Code,
  Flame,
  Percent,
  Copy,
  Activity,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "cn";
import {
  getSonarHealth,
  getSonarQualityGate,
  getSonarMeasures,
  getSonarIssues,
} from "@/lib/api";
import type { SonarHealth, SonarQualityGate, SonarMeasures, SonarIssuesResponse, SonarIssueLive } from "@/lib/types";

const SEVERITY_META = {
  BLOCKER: { color: "var(--severity-critical)", label: "BLOCKER" },
  CRITICAL: { color: "var(--severity-high)", label: "CRITICAL" },
  MAJOR: { color: "var(--severity-medium)", label: "MAJOR" },
  MINOR: { color: "var(--severity-low)", label: "MINOR" },
  INFO: { color: "var(--severity-info)", label: "INFO" },
} as const;

const RATING_LABELS: Record<string, string> = {
  "1": "A",
  "2": "B",
  "3": "C",
  "4": "D",
  "5": "E",
};

function SeverityDot({ severity }: { severity: string }) {
  const meta = SEVERITY_META[severity] ?? SEVERITY_META.INFO;
  return (
    <span
      className="inline-flex items-center justify-center w-3 h-3 rounded-full"
      style={{ backgroundColor: meta.color }}
      title={meta.label}
    />
  );
}

function RatingBadge({ rating }: { rating: string | undefined }) {
  const label = rating ? RATING_LABELS[rating] : "—";
  const num = rating ? parseInt(rating, 10) : 0;
  const colors = ["", "text-green-400", "text-lime-400", "text-amber-400", "text-orange-400", "text-red-400"];
  return (
    <Badge variant="outline" className={cn("font-mono text-base", colors[num])}>
      {label}
    </Badge>
  );
}

function StatTile({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <span className="text-muted-foreground/50">{icon}</span>
      </div>
      <p className="mt-2 font-mono text-2xl font-semibold">{value}</p>
    </div>
  );
}

function SeverityBar({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  if (total === 0) return <p className="text-xs text-muted-foreground">No issues</p>;
  const order: (keyof typeof SEVERITY_META)[] = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"];
  return (
    <div className="flex items-center gap-1 h-4">
      {order.map((s) => {
        const count = counts[s] ?? 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        return (
          <div
            key={s}
            className="flex-1 rounded transition-all"
            style={{ width: `${Math.max(2, pct)}%`, backgroundColor: SEVERITY_META[s].color }}
            title={`${SEVERITY_META[s].label}: ${count}`}
          />
        );
      })}
      <div className="ml-2 text-xs font-mono text-muted-foreground w-12 text-right">{total}</div>
    </div>
  );
}

export function SonarLivePanel() {
  const [health, setHealth] = useState<{ available: boolean; error?: string } | null>(null);
  const [qualityGate, setQualityGate] = useState<{
    available: boolean;
    status?: string;
    conditions?: any[];
    error?: string;
  } | null>(null);
  const [measures, setMeasures] = useState<{
    available: boolean;
    bugs?: string;
    vulnerabilities?: string;
    code_smells?: string;
    security_hotspots?: string;
    coverage?: string;
    duplicated_lines_density?: string;
    reliability_rating?: string;
    security_rating?: string;
    sqale_rating?: string;
    error?: string;
  } | null>(null);
  const [issues, setIssues] = useState<{
    available: boolean;
    total: number;
    page: number;
    page_size: number;
    issues: any[];
    error?: string;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);

  const fetchAll = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);

    try {
      const [healthRes, qgRes, measuresRes, issuesRes] = await Promise.all([
        fetch("/api/sonar/health").then(r => r.json()),
        fetch("/api/sonar/quality-gate").then(r => r.json()),
        fetch("/api/sonar/measures").then(r => r.json()),
        fetch(`/api/sonar/issues?page=${1}&page_size=20`).then(r => r.json()),
      ]);
      setHealth(healthRes);
      setQualityGate(qgRes);
      setMeasures(measuresRes);
      setIssues(issuesRes);
      setCurrentPage(1);
      setLastUpdated(new Date().toISOString());
    } catch (e) {
      console.error("SonarQube fetch failed:", e);
      setHealth({ available: false, error: "Failed to fetch" });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const fetchIssuesPage = useCallback(async (page: number) => {
    setRefreshing(true);
    try {
      const res = await fetch(`/api/sonar/issues?page=${page}&page_size=20`);
      const data = await res.json();
      setIssues(data);
      setCurrentPage(page);
      setLastUpdated(new Date().toISOString());
    } catch (e) {
      console.error("SonarQube issues fetch failed:", e);
    } finally {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(() => fetchAll(true), 15000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  if (loading) {
    return (
      <Card className="w-full border-l-4" style={{ borderLeftColor: "var(--primary)" }}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <span>SonarQube Live</span>
            <Loader2 className="size-4 animate-spin text-primary" />
          </CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center text-muted-foreground">
          Loading SonarQube data…
        </CardContent>
      </Card>
    );
  }

  const isOffline = !health?.available;
  const qg = qualityGate;
  const m = measures;
  const issueData = issues;

  const severityCounts = issueData?.issues?.reduce((acc: Record<string, number>, i) => {
    acc[i.severity] = (acc[i.severity] ?? 0) + 1;
    return acc;
  }, {} as Record<string, number>) ?? {};

  const qgStatus = qg?.status ?? "UNKNOWN";
  const qgPassed = qg?.status === "OK";

  return (
    <Card className="w-full border-l-4" style={{ borderLeftColor: isOffline ? "var(--destructive)" : qgPassed ? "var(--severity-low)" : "var(--severity-critical)" }}>
      <CardHeader className="pb-0">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div className="flex items-center gap-2">
            <CardTitle className="text-base">SonarQube Live</CardTitle>
            {health?.available ? (
              <Badge variant="outline" className={cn("text-[10px]", qgPassed ? "text-green-400 border-green-400" : "text-red-400 border-red-400")}>
                {qgPassed ? "PASSED" : qg?.status === "ERROR" ? "FAILED" : qg?.status === "WARN" ? "WARN" : "UNKNOWN"}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px] text-destructive border-destructive">OFFLINE</Badge>
            )}
          </div>
          <div className="flex items-center gap-2">
            {lastUpdated && (
              <span className="text-xs text-muted-foreground font-mono">
                Updated: {new Date(lastUpdated).toLocaleTimeString()}
              </span>
            )}
            <Button
              variant="secondary"
              size="sm"
              className="gap-1.5"
              onClick={() => fetchAll(true)}
              disabled={refreshing}
            >
              <Loader2 className={cn("size-3.5", refreshing && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex flex-col gap-5 pt-4">
        {isOffline && (
          <div className="flex flex-col items-center gap-4 rounded-lg border border-destructive/20 bg-destructive/5 p-8 text-center">
            <TriangleAlert className="size-12 text-destructive" />
            <div>
              <p className="text-sm font-medium text-foreground">SonarQube offline</p>
              <p className="mt-1 text-xs text-muted-foreground max-w-md">
                {health?.error ?? "Cannot reach SonarQube at the configured host."}
              </p>
              <p className="mt-2 text-xs text-muted-foreground font-mono">
                docker compose -f docker-compose.sonar.yml up -d
              </p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => fetchAll(true)}>
                Retry
              </Button>
            </div>
          </div>
        )}

        {!isOffline && (
          <>
            {/* Quality Gate Banner */}
            <div className={cn("rounded-md border px-4 py-3", qgPassed ? "border-green-500/30 bg-green-500/5" : "border-red-500/30 bg-red-500/5")}>
              <div className="flex items-center gap-3">
                {qgPassed ? (
                  <CheckCircle2 className="size-6 text-green-400" />
                ) : (
                  <CircleAlert className="size-6 text-red-400" />
                )}
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{qgPassed ? "Quality Gate Passed" : "Quality Gate Failed"}</span>
                    <Badge variant="outline" className={qgPassed ? "text-green-400 border-green-400" : "text-red-400 border-red-400"}>
                      {qg?.status ?? "UNKNOWN"}
                    </Badge>
                  </div>
                  {qg?.conditions && qg.conditions.length > 0 && (
                    <ul className="mt-2 text-xs text-muted-foreground space-y-1">
                      {qg.conditions.map((c, i) => (
                        <li key={i} className="flex items-center gap-1.5">
                          <span className={cn("size-1.5 rounded-full", c.status === "OK" ? "bg-green-400" : c.status === "WARN" ? "bg-amber-400" : "bg-red-400")} />
                          <span className="font-mono">{c.metric}</span>
                          <span>{c.value}</span>
                          {c.error_threshold && <span className="text-[10px]">(error ≤ {c.error_threshold})</span>}
                          {c.warning_threshold && <span className="text-[10px]">(warn ≤ {c.warning_threshold})</span>}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </div>

            {/* Ratings Row */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              <StatTile label="Reliability" value={m?.reliability_rating ? RATING_LABELS[m.reliability_rating] : "—"} icon={<Shield className="size-4" />} />
              <StatTile label="Security" value={m?.security_rating ? RATING_LABELS[m.security_rating] : "—"} icon={<ShieldCheck className="size-4" />} />
              <StatTile label="Maintainability" value={m?.sqale_rating ? RATING_LABELS[m.sqale_rating] : "—"} icon={<Wrench className="size-4" />} />
            </div>

            {/* Stat Tiles */}
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              <StatTile label="Bugs" value={m?.bugs ?? "—"} icon={<Bug className="size-4" />} />
              <StatTile label="Vulnerabilities" value={m?.vulnerabilities ?? "—"} icon={<ShieldAlert className="size-4" />} />
              <StatTile label="Code Smells" value={m?.code_smells ?? "—"} icon={<Code className="size-4" />} />
              <StatTile label="Hotspots" value={m?.security_hotspots ?? "—"} icon={<Flame className="size-4" />} />
              <StatTile label="Coverage" value={m?.coverage ? `${m.coverage}%` : "—"} icon={<Percent className="size-4" />} />
              <StatTile label="Duplications" value={m?.duplicated_lines_density ? `${m.duplicated_lines_density}%` : "—"} icon={<Copy className="size-4" />} />
            </div>

            {/* Severity Breakdown */}
            <div className="rounded-md border border-border bg-muted/30 p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">Issue Severity Breakdown</span>
                <span className="font-mono text-xs text-muted-foreground">{issueData?.total ?? 0} total</span>
              </div>
              <SeverityBar counts={severityCounts} />
            </div>

            {/* Issues Table */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm" role="table">
                <thead>
                  <tr className="bg-muted/50 border-b border-border">
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider w-8">Sev</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Type</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Rule</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">File:Line</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Message</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider w-20">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {issueData?.issues?.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-3 py-8 text-center text-sm text-muted-foreground">
                        No issues found
                      </td>
                    </tr>
                  ) : (
                    issueData?.issues?.map((issue, i) => (
                      <tr key={issue.key} className="border-b border-border/50 hover:bg-accent/30">
                        <td className="px-3 py-2 text-center"><SeverityDot severity={issue.severity} /></td>
                        <td className="px-3 py-2">
                          <Badge variant="outline" className="text-[10px]">{issue.type}</Badge>
                        </td>
                        <td className="px-3 py-2 font-mono text-[10px] text-muted-foreground">{issue.rule}</td>
                        <td className="px-3 py-2 font-mono text-xs break-all">{issue.file}{issue.line ? `:${issue.line}` : ""}</td>
                        <td className="px-3 py-2 text-[11px] text-foreground truncate max-w-xs">{issue.message}</td>
                        <td className="px-3 py-2 text-center text-[10px] text-muted-foreground">{issue.status}</td>
                      </tr>
                    )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {issueData && issueData.total > issueData.page_size && (
              <div className="flex items-center justify-between border-t border-border pt-3">
                <span className="text-xs text-muted-foreground">
                  Showing {((currentPage - 1) * 20) + 1}–{Math.min(currentPage * 20, issueData.total)} of {issueData.total}
                </span>
                <div className="flex items-center gap-1">
                  <Button variant="outline" size="sm" onClick={() => fetchIssuesPage(currentPage - 1)} disabled={currentPage <= 1 || refreshing}>
                    <ChevronLeft className="size-3.5" />
                  </Button>
                  <span className="px-2 text-xs font-mono text-muted-foreground">{currentPage}</span>
                  <Button variant="outline" size="sm" onClick={() => fetchIssuesPage(currentPage + 1)} disabled={currentPage * 20 >= (issueData?.total ?? 0) || refreshing}>
                    <ChevronRight className="size-3.5" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

const SEVERITY_META = {
  BLOCKER: { color: "var(--severity-critical)", label: "BLOCKER" },
  CRITICAL: { color: "var(--severity-high)", label: "CRITICAL" },
  MAJOR: { color: "var(--severity-medium)", label: "MAJOR" },
  MINOR: { color: "var(--severity-low)", label: "MINOR" },
  INFO: { color: "var(--severity-info)", label: "INFO" },
} as const;

const RATING_LABELS: Record<string, string> = {
  "1": "A",
  "2": "B",
  "3": "C",
  "4": "D",
  "5": "E",
};


const SEVERITY_META = {
  BLOCKER: { color: "var(--severity-critical)", label: "BLOCKER" },
  CRITICAL: { color: "var(--severity-high)", label: "CRITICAL" },
  MAJOR: { color: "var(--severity-medium)", label: "MAJOR" },
  MINOR: { color: "var(--severity-low)", label: "MINOR" },
  INFO: { color: "var(--severity-info)", label: "INFO" },
} as const;

const RATING_LABELS: Record<string, string> = {
  "1": "A",
  "2": "B",
  "3": "C",
  "4": "D",
  "5": "E",
};


const SEVERITY_META = {
  BLOCKER: { color: "var(--severity-critical)", label: "BLOCKER" },
  CRITICAL: { color: "var(--severity-high)", label: "CRITICAL" },
  MAJOR: { color: "var(--severity-medium)", label: "MAJOR" },
  MINOR: { color: "var(--severity-low)", label: "MINOR" },
  INFO: { color: "var(--severity-info)", label: "INFO" },
} as const;

const RATING_LABELS: Record<string, string> = {
  "1": "A",
  "2": "B",
  "3": "C",
  "4": "D",
  "5": "E",
};

function SeverityDot({ severity }: { severity: string }) {
  const meta = SEVERITY_META[severity as keyof typeof SEVERITY_META] ?? SEVERITY_META.INFO;
  return (
    <span
      className="inline-flex items-center justify-center w-3 h-3 rounded-full"
      style={{ backgroundColor: meta.color }}
      title={meta.label}
    />
  );
}

function RatingBadge({ rating }: { rating: string | undefined }) {
  const label = rating ? RATING_LABELS[rating] : "—";
  const num = rating ? parseInt(rating, 10) : 0;
  const colors = ["", "text-green-400", "text-lime-400", "text-amber-400", "text-orange-400", "text-red-400"];
  return (
    <Badge variant="outline" className={cn("font-mono text-base", colors[num])}>
      {label}
    </Badge>
  );
}

function StatTile({ label, value, icon }: { label: string; value: string; icon: React.ReactNode }) {
  return (
    <div className="rounded-md border border-border bg-card p-4">
      <div className="flex items-center justify-between">
        <p className="text-xs text-muted-foreground uppercase tracking-wide">{label}</p>
        <span className="text-muted-foreground/50">{icon}</span>
      </div>
      <p className="mt-2 font-mono text-2xl font-semibold">{value}</p>
    </div>
  );
}

function SeverityBar({ counts }: { counts: Record<string, number> }) {
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  if (total === 0) return <p className="text-xs text-muted-foreground">No issues</p>;
  const order = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"] as const;
  return (
    <div className="flex items-center gap-1 h-4">
      {order.map((s) => {
        const count = counts[s] ?? 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        return (
          <div
            key={s}
            className="flex-1 rounded transition-all"
            style={{ width: `${Math.max(2, pct)}%`, backgroundColor: SEVERITY_META[s].color }}
            title={`${SEVERITY_META[s].label}: ${count}`}
          />
        );
      })}
      <div className="ml-2 text-xs font-mono text-muted-foreground w-12 text-right">{total}</div>
    </div>
  );
}
