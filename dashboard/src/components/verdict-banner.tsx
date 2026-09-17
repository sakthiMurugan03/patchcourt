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

  return (
    <Card className="w-full border-l-4" style={{ borderLeftColor: meta.color }}>
      <CardContent className="flex flex-col gap-5 pt-6 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-4">
          <div
            className="flex size-14 items-center justify-center rounded-full"
            style={{ backgroundColor: `${meta.color}1f`, color: meta.color }}
          >
            <Icon className="size-7" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <Badge style={{ backgroundColor: meta.color, color: "#0b1220" }}>
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