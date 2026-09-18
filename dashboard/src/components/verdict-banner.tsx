"use client";

import { AlertTriangle, CheckCircle2, Scale, XCircle, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { VERDICT_META, type Report } from "@/lib/types";
import { cn } from "cn";

export function VerdictBanner({ report }: { report: Report }) {
  const meta = VERDICT_META[report.verdict];
  const Icon =
    report.verdict === "MERGE"
      ? CheckCircle2
      : report.verdict === "BLOCK"
        ? XCircle
        : AlertTriangle;

  // Thresholds from config
  const BLOCK_THRESHOLD = 10.0;
  const NEEDS_REVIEW_THRESHOLD = 4.0;
  const score = report.overall_score;

  // Determine band
  const band =
    score >= BLOCK_THRESHOLD
      ? { label: "BLOCK", color: "red", threshold: BLOCK_THRESHOLD }
      : score >= NEEDS_REVIEW_THRESHOLD
        ? { label: "NEEDS_REVIEW", color: "amber", threshold: NEEDS_REVIEW_THRESHOLD }
        : { label: "MERGE", color: "green", threshold: NEEDS_REVIEW_THRESHOLD };

  // Build scale segments
  const scaleSegments = [
    { label: "MERGE", range: `[0, ${NEEDS_REVIEW_THRESHOLD})`, color: "green" },
    { label: "NEEDS_REVIEW", range: `[${NEEDS_REVIEW_THRESHOLD}, ${BLOCK_THRESHOLD})`, color: "amber" },
    { label: "BLOCK", range: `[${BLOCK_THRESHOLD}, ∞)`, color: "red" },
  ];

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
        <div className="flex flex-col sm:flex-row sm:items-center gap-4 w-full sm:w-auto">
          <div className="text-right">
            <p className="font-mono text-4xl font-semibold tabular-nums" style={{ color: meta.color }}>
              {report.overall_score.toFixed(1)}
            </p>
            <p className="text-xs text-muted-foreground">risk score (higher = riskier)</p>
          </div>
          {/* Threshold scale */}
          <div className="flex items-center gap-2 flex-wrap">
            {scaleSegments.map((seg) => (
              <Badge
                key={seg.label}
                variant="outline"
                className={cn(
                  "text-xs font-mono px-2 py-1",
                  seg.label === band.label && "font-semibold border-2"
                )}
                style={{
                  borderColor: seg.color === "green" ? "green" : seg.color === "amber" ? "amber" : "red",
                  color: seg.color === "green" ? "green" : seg.color === "amber" ? "amber" : "red",
                }}
              >
                {seg.label}: {seg.range}
              </Badge>
            ))}
          </div>
          {/* Current position indicator */}
          <div className="text-xs text-muted-foreground">
            <Info className="size-3 inline mr-1" />
            <span>
              Score = Σ(severity × tier_weight × corroboration × confidence) | 
              {band.label} threshold: {band.threshold}
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}