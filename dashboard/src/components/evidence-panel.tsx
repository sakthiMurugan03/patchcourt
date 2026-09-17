"use client";

import { useMemo, useState } from "react";
import { BadgeCheck, FileCode2, TestTubes, ChevronDown } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { AGENT_META, TIER_INFO, type Claim } from "@/lib/types";
import { cn } from "cn";

const SEVERITY_STYLE: Record<number, { color: string; label: string; class: string }> = {
  5: { color: "var(--severity-critical)", label: "Critical", class: "sev-critical" },
  4: { color: "var(--severity-high)", label: "High", class: "sev-high" },
  3: { color: "var(--severity-medium)", label: "Medium", class: "sev-medium" },
  2: { color: "var(--severity-low)", label: "Low", class: "sev-low" },
  1: { color: "var(--severity-info)", label: "Info", class: "sev-info" },
};

function severityScore(c: Claim) {
  return (
    c.severity * (c.corroborated ? 1.25 : 1) * TIER_INFO[c.tier]?.weight
  );
}

function ClaimCard({ claim }: { claim: Claim }) {
  const agent = AGENT_META[claim.agent] ?? { color: "var(--muted-foreground)", name: claim.agent || "Agent" };
  const sev = SEVERITY_STYLE[claim.severity] ?? SEVERITY_STYLE[3];
  const tier = TIER_INFO[claim.tier] ?? TIER_INFO[3];

  return (
    <div className="flex flex-col gap-3 rounded-md border border-border bg-card p-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: `${agent.color}1f`, color: agent.color }}>
          <span className="size-1.5 rounded-full" style={{ backgroundColor: agent.color }} />
          {agent.name}
        </span>
        <Badge variant="outline" title={tier.blurb} className="font-mono text-[10px]">
          {tier.name.split(" — ")[0]}
        </Badge>
        {claim.corroborated && (
          <Badge className="gap-1 bg-primary/15 text-primary hover:bg-primary/20 text-[10px]">
            <BadgeCheck className="size-2.5" /> corroborated
          </Badge>
        )}
        <span className="ml-auto inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: sev.color }}>
          <TestTubes className="size-3.5" />
          <span className={sev.class}>{sev.label}</span>
          {typeof claim.severity === "number" ? ` (${claim.severity}/5)` : ""}
        </span>
      </div>

      <p className="text-sm leading-relaxed text-foreground">{claim.issue}</p>

      <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-muted-foreground">
        <span className="inline-flex items-center gap-1">
          <FileCode2 className="size-3.5" />
          {claim.file}
          {claim.line > 0 ? `:${claim.line}` : ""}
        </span>
        <Separator orientation="vertical" className="h-3.5" />
        <span>confidence {(claim.confidence * 100).toFixed(0)}%</span>
        <Separator orientation="vertical" className="h-3.5" />
        <span className="text-primary">weight ×{tier.weight.toFixed(1)}</span>
      </div>

      <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full rounded-full"
          style={{
            width: `${Math.min(100, Math.max(6, claim.confidence * 100))}%`,
            backgroundColor: sev.color,
          }}
        />
      </div>

      {claim.evidence.length > 0 && (
        <ul className="flex flex-col gap-1 border-l pl-3" style={{ borderColor: `${agent.color}55` }}>
          {claim.evidence.map((ev, i) => (
            <li key={i} className="text-xs text-muted-foreground">
              T{ev.tier}: {ev.text}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

type SortKey = "severity" | "tier" | "confidence" | "file";

export function EvidencePanel({ claims }: { claims: Claim[] }) {
  const [minSeverity, setMinSeverity] = useState("1");
  const [maxTier, setMaxTier] = useState("5");
  const [source, setSource] = useState("all");
  const [sortBy, setSortBy] = useState<SortKey>("severity");

  const visible = useMemo(() => {
    const min = Number(minSeverity);
    const max = Number(maxTier);
    let list = claims.filter(
      (c) => c.severity >= min && c.tier <= max && (source === "all" || c.source === source),
    );
    list = [...list].sort((a, b) => {
      if (sortBy === "severity") return severityScore(b) - severityScore(a);
      if (sortBy === "tier") return a.tier - b.tier;
      if (sortBy === "confidence") return b.confidence - a.confidence;
      return a.file.localeCompare(b.file);
    });
    return list;
  }, [claims, minSeverity, maxTier, source, sortBy]);

  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle className="text-base">Evidence Docket</CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          <Select value={minSeverity} onValueChange={setMinSeverity}>
            <SelectTrigger className="h-8 w-[9.5rem] text-xs" aria-label="Min severity">
              <SelectValue placeholder="Severity" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Severity ≥ 1</SelectItem>
              <SelectItem value="2">Severity ≥ 2</SelectItem>
              <SelectItem value="3">Severity ≥ 3</SelectItem>
              <SelectItem value="4">Severity ≥ 4</SelectItem>
              <SelectItem value="5">Severity = 5</SelectItem>
            </SelectContent>
          </Select>
          <Select value={maxTier} onValueChange={setMaxTier}>
            <SelectTrigger className="h-8 w-[8.5rem] text-xs" aria-label="Max tier">
              <SelectValue placeholder="Tier" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1">Only T1</SelectItem>
              <SelectItem value="2">T1–T2</SelectItem>
              <SelectItem value="3">T1–T3</SelectItem>
              <SelectItem value="5">All tiers</SelectItem>
            </SelectContent>
          </Select>
          <Select value={source} onValueChange={setSource}>
            <SelectTrigger className="h-8 w-[8rem] text-xs" aria-label="Source">
              <SelectValue placeholder="Source" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All sources</SelectItem>
              <SelectItem value="tool">Tool findings</SelectItem>
              <SelectItem value="llm">LLM reasoning</SelectItem>
            </SelectContent>
          </Select>
          <Select value={sortBy} onValueChange={(v) => setSortBy(v as SortKey)}>
            <SelectTrigger className="h-8 w-[9.5rem] text-xs" aria-label="Sort">
              <SelectValue placeholder="Sort" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="severity">Sort: weighted risk</SelectItem>
              <SelectItem value="tier">Sort: tier</SelectItem>
              <SelectItem value="confidence">Sort: confidence</SelectItem>
              <SelectItem value="file">Sort: file</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardHeader>
      <CardContent>
        <p className="mb-4 text-xs text-muted-foreground">
          {visible.length} of {claims.length} claim(s) match the current filters.
        </p>
        <div className="flex flex-col gap-3">
          {visible.length === 0 && (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No evidence matches these filters.
            </p>
          )}
          {visible.map((c, i) => (
            <ClaimCard key={i} claim={c} />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}