"use client";

import { AlertTriangle, CheckCircle2, Scale, XCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { VERDICT_META, type Report } from "@/lib/types";

export function VerdictBanner({ report }: { report: Report }) {
  const meta = VERDICT_META[report.verdict];
  const Icon =
    report.verdict === "MERGE"
      ? CheckCircle2
      : report.verdict === "BLOCK"
        ? XCircle
        : AlertTriangle;
  const counts = report.claims.reduce(
    (acc, c) => {
      acc = { ...acc, [c.tier]: (acc[c.tier] ?? 0) + 1 };
      return acc;
    },
    {} as Record<number, number>,
  );
  const toolClaims = report.claims.filter((c) => c.source === "tool").length;

  const verdictColors = {
    MERGE: { bg: "bg-green-500/15", border: "border-green-500", text: "text-green-400", badge: "bg-green-500 text-black" },
    NEEDS_REVIEW: { bg: "bg-amber-500/15", border: "border-amber-500", text: "text-amber-400", badge: "bg-amber-500 text-black" },
    BLOCK: { bg: "bg-red-500/15", border: "border-red-500", text: "text-red-400", badge: "bg-red-500 text-black" },
  } as const;

  const colors = verdictColors[report.verdict];

  return (
    <Card className={cn("w-full border-l-4", colors.border)}>
      <CardContent className="flex flex-col gap-5 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div className={cn("flex size-12 items-center justify-center rounded-full", colors.bg, colors.text)}>
            <Icon className="size-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Badge className={cn("text-xs", colors.badge)}>
                {meta.label}
              </Badge>
              <span className="text-xs text-muted-foreground">{meta.blurb}</span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {toolClaims} static-analysis finding(s), {counts[3] ?? 0} policy,{" "}
              {counts[5] ?? 0} LLM-only reasoning — final score weighted by tier
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2.5">
          <Scale className="size-5 text-muted-foreground" />
          <div className="text-right">
            <p className="font-mono text-4xl font-semibold tabular-nums" style={{ color: meta.color }}>
              {report.overall_score.toFixed(1)}
            </p>
            <p className="text-xs text-muted-foreground">risk score</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

import { cn } from "cn";