"use client";

import { useMemo, useState } from "react";
import { BadgeCheck, FileCode2, TestTubes, ChevronDown, ChevronRight, ChevronUp, ArrowUpDown } from "lucide-react";
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

function generateClaimId(claim: Claim): string {
  const str = `${claim.file}:${claim.line}:${claim.issue}:${claim.agent}:${claim.tier}`;
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash).toString(36);
}

type ClaimWithExp = Claim & { _expanded?: boolean; _id: string };

const SEVERITY_STYLE: Record<number, { color: string; label: string; class: string }> = {
  5: { color: "var(--severity-critical)", label: "Critical", class: "sev-critical" },
  4: { color: "var(--severity-high)", label: "High", class: "sev-high" },
  3: { color: "var(--severity-medium)", label: "Medium", class: "sev-medium" },
  2: { color: "var(--severity-low)", label: "Low", class: "sev-low" },
  1: { color: "var(--severity-info)", label: "Info", class: "sev-info" },
};

type SortKey = "severity" | "tier" | "confidence" | "file" | "source";
type SortDirection = "asc" | "desc";

function severityScore(c: Claim) {
  return c.severity * (c.corroborated ? 1.25 : 1) * TIER_INFO[c.tier]?.weight;
}

function EvidenceRow({ claim, onToggle }: { claim: ClaimWithExp; onToggle: () => void }) {
  const agent = AGENT_META[claim.agent] ?? { color: "var(--muted-foreground)", name: claim.agent || "Agent" };
  const sev = SEVERITY_STYLE[claim.severity] ?? SEVERITY_STYLE[3];
  const tier = TIER_INFO[claim.tier] ?? TIER_INFO[3];
  const expanded = claim._expanded;

  return (
    <>
      <tr className="border-b border-border/50 hover:bg-accent/30 transition-colors">
        <td className="px-3 py-2.5 text-center">
          <button onClick={onToggle} className="p-1 hover:bg-accent rounded" aria-label={expanded ? "Collapse" : "Expand"}>
            {expanded ? <ChevronDown className="size-4 text-muted-foreground" /> : <ChevronRight className="size-4 text-muted-foreground" />}
          </button>
        </td>
        <td className="px-3 py-2.5 text-center">
          <span className={cn("inline-flex items-center justify-center w-5 h-5 rounded-full font-mono text-[10px] font-semibold", sev.class)}>
            {claim.severity}
          </span>
        </td>
        <td className="px-3 py-2.5 text-center">
          <Badge variant="outline" title={tier.blurb} className="font-mono text-[10px]">
            {tier.name.split(" — ")[0]}
          </Badge>
        </td>
        <td className="px-3 py-2.5 text-center">
          <span className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium" style={{ backgroundColor: `${agent.color}1f`, color: agent.color }}>
            <span className="size-1.5 rounded-full" style={{ backgroundColor: agent.color }} />
            {agent.name}
          </span>
        </td>
        <td className="px-3 py-2.5 w-40">
          <code className="font-mono text-xs break-words whitespace-normal" title={`${claim.file}${claim.line > 0 ? `:${claim.line}` : ""}`}>
            {claim.file}{claim.line > 0 ? `:${claim.line}` : ""}
          </code>
        </td>
        <td className="px-3 py-2.5">
          <p className="line-clamp-2 text-xs leading-snug" title={claim.issue}>
            {claim.issue}
          </p>
        </td>
        <td className="px-3 py-2.5 text-center">
          {claim.corroborated && (
            <Badge className="gap-1 bg-primary/15 text-primary hover:bg-primary/20 text-[10px]">
              <BadgeCheck className="size-2.5" /> Yes
            </Badge>
          )}
        </td>
        <td className="px-3 py-2.5 text-center font-mono text-xs text-muted-foreground">
          ×{tier.weight.toFixed(1)}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-muted/30">
          <td colSpan={8} className="p-0">
            <div className="border-l-2 pl-4 ml-8" style={{ borderColor: `${agent.color}55` }}>
              <p className="py-2 text-xs text-foreground" title={claim.issue}>
                <span className="font-medium">Finding:</span> {claim.issue}
              </p>
              {claim.evidence.map((ev, i) => (
                <div key={i} className="py-2 border-b border-border/50 last:border-0">
                  <div className="flex items-start gap-2 text-xs">
                    <Badge variant="outline" className="font-mono text-[10px] border-border">
                      T{ev.tier}
                    </Badge>
                    <span className="text-muted-foreground whitespace-normal break-words" title={ev.text}>{ev.text}</span>
                  </div>
                </div>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export function EvidencePanel({ claims }: { claims: Claim[] }) {
  const [minSeverity, setMinSeverity] = useState("1");
  const [maxTier, setMaxTier] = useState("5");
  const [source, setSource] = useState("all");
  const [sortBy, setSortBy] = useState<SortKey>("severity");
  const [sortDir, setSortDir] = useState<SortDirection>("desc");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  const claimsWithIds = useMemo(() => 
    claims.map(c => ({ ...c, _id: generateClaimId(c) })), 
    [claims]
  );

  const toggleRow = (id: string) => {
    setExpandedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const claimsWithExpanded = useMemo(() => 
    claimsWithIds.map(c => ({ ...c, _expanded: expandedIds.has(c._id) })), 
    [claimsWithIds, expandedIds]
  );

  const visible = useMemo(() => {
    const min = Number(minSeverity);
    const max = Number(maxTier);
    let list = claimsWithExpanded.filter(
      (c) => c.severity >= min && c.tier <= max && (source === "all" || c.source === source),
    );
    list = [...list].sort((a, b) => {
      let cmp = 0;
      if (sortBy === "severity") cmp = severityScore(b) - severityScore(a);
      else if (sortBy === "tier") cmp = a.tier - b.tier;
      else if (sortBy === "confidence") cmp = b.confidence - a.confidence;
      else if (sortBy === "source") cmp = a.source.localeCompare(b.source);
      else cmp = a.file.localeCompare(b.file);
      return sortDir === "asc" ? -cmp : cmp;
    });
    return list;
  }, [claimsWithExpanded, minSeverity, maxTier, source, sortBy, sortDir]);

  function SortableHeader({ label, key, currentSort, onSort }: { label: string; key: SortKey; currentSort: SortKey; onSort: (k: SortKey) => void }) {
    const isActive = currentSort === key;
    return (
      <th
        onClick={() => onSort(key)}
        className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider cursor-pointer hover:text-foreground select-none"
        style={{ userSelect: "none" }}
      >
        <div className="flex items-center gap-1">
          {label}
          {isActive && (sortDir === "asc" ? <ChevronUp className="size-3.5" /> : <ChevronDown className="size-3.5" />)}
          {!isActive && <ArrowUpDown className="size-3.5 text-muted-foreground/30" />}
        </div>
      </th>
    );
  }

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
        </div>
      </CardHeader>
      <CardContent className="p-0">
        <div className="overflow-x-auto">
          <table className="w-full text-sm" role="table">
            <thead>
              <tr className="bg-muted/50 border-b border-border">
                <th className="px-3 py-2 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider w-8" />
                <SortableHeader label="Sev" key="severity" currentSort={sortBy} onSort={k => { setSortBy(k); setSortDir(sortBy === k && sortDir === "desc" ? "asc" : "desc"); }} />
                <SortableHeader label="Tier" key="tier" currentSort={sortBy} onSort={k => { setSortBy(k); setSortDir(sortBy === k && sortDir === "desc" ? "asc" : "desc"); }} />
                <SortableHeader label="Source" key="source" currentSort={sortBy} onSort={k => { setSortBy(k); setSortDir(sortBy === k && sortDir === "desc" ? "asc" : "desc"); }} />
                <SortableHeader label="File:Line" key="file" currentSort={sortBy} onSort={k => { setSortBy(k); setSortDir(sortBy === k && sortDir === "desc" ? "asc" : "desc"); }} />
                <th className="px-3 py-2 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">Finding</th>
                <th className="px-3 py-2 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">Corroborated</th>
                <th className="px-3 py-2 text-center text-xs font-medium text-muted-foreground uppercase tracking-wider">Weight</th>
              </tr>
            </thead>
            <tbody>
              {visible.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-sm text-muted-foreground">
                    {claims.length === 0 ? (
                      <span className="flex items-center justify-center gap-2">
                        <BadgeCheck className="size-4 text-green-400" />
                        No findings — this PR is clean.
                      </span>
                    ) : (
                      "No evidence matches these filters."
                    )}
                  </td>
                </tr>
              ) : (
                visible.map((c) => (
                  <EvidenceRow key={c._id} claim={c} onToggle={() => toggleRow(c._id)} />
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="mt-3 px-3 pb-3 text-xs text-muted-foreground">
          {visible.length} of {claims.length} claim(s) match the current filters.
        </div>
      </CardContent>
    </Card>
  );
}