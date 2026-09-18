"use client";

import { useState } from "react";
import { AlertTriangle, CheckCircle2, Scale, XCircle, HelpCircle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tooltip } from "@/components/ui/tooltip";
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

  // Thresholds
  const BLOCK_THRESHOLD = 10.0;
  const NEEDS_REVIEW_THRESHOLD = 4.0;
  const score = report.overall_score;

  // Risk level words (capped at 30 for visual scale)
  const VISUAL_MAX = 30;
  const visualScore = Math.min(score, VISUAL_MAX);

  // Human-readable risk level derived from score
  const riskLevel =
    score >= BLOCK_THRESHOLD
      ? { label: "Critical", color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500/30" }
      : score >= NEEDS_REVIEW_THRESHOLD
        ? { label: "Moderate", color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500/30" }
        : { label: "Low", color: "text-green-400", bg: "bg-green-500/10", border: "border-green-500/30" };

  // Verdict colors
  const verdictColors = {
    MERGE: { color: "text-green-400", bg: "bg-green-500/10", border: "border-green-500", badge: "bg-green-500 text-black" },
    NEEDS_REVIEW: { color: "text-amber-400", bg: "bg-amber-500/10", border: "border-amber-500", badge: "bg-amber-500 text-black" },
    BLOCK: { color: "text-red-400", bg: "bg-red-500/10", border: "border-red-500", badge: "bg-red-500 text-black" },
  } as const;

  const vColors = verdictColors[report.verdict];

  // Counts for the plain sentence
  const toolClaims = report.claims.filter((c) => c.source === "tool").length;
  const totalClaims = report.claims.length;

  // Plain sentence
  const verdictSentence =
    report.verdict === "BLOCK"
      ? `${toolClaims} tool-backed issue${toolClaims !== 1 ? "s" : ""} found — these must be fixed before this PR can merge.`
      : report.verdict === "NEEDS_REVIEW"
        ? `${toolClaims} tool-backed issue${toolClaims !== 1 ? "s" : ""} need review — consider addressing before merging.`
        : `${toolClaims} tool-backed issue${toolClaims !== 1 ? "s" : ""} found — no blocking issues.`;

  // Gauge marker position (percentage)
  const markerPos = Math.min((visualScore / VISUAL_MAX) * 100, 100);

  // Tooltip content
  const [tooltipOpen, setTooltipOpen] = useState(false);

  return (
    <Card className={cn("w-full border-l-4", vColors.border)}>
      <CardContent className="p-6 space-y-5">
        {/* Top row: Verdict + Risk Level + Gauge */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          {/* Verdict + Risk Level */}
          <div className="flex flex-col sm:flex-row sm:items-center gap-3">
            <Tooltip content="Click for score details">
              <div
                className={cn(
                  "flex size-12 items-center justify-center rounded-full cursor-help",
                  vColors.bg,
                  vColors.color,
                  "border",
                  vColors.border,
                )}
                onClick={() => setTooltipOpen((p) => !p)}
                onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") setTooltipOpen((p) => !p); }}
                tabIndex={0}
                role="button"
                aria-label="Score details"
              >
                <Icon className="size-6" />
              </div>
            </Tooltip>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <Badge className={cn("text-sm font-medium", vColors.badge)}>
                  {meta.label}
                </Badge>
                <span className={cn("text-sm font-medium", riskLevel.color)}>
                  {riskLevel.label} risk
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">{meta.blurb}</p>
            </div>
          </div>

          {/* Horizontal Risk Gauge */}
          <div className="flex-1 min-w-0 max-w-md">
            <div className="relative h-8">
              {/* Track */}
              <div className="absolute inset-0 rounded-full bg-gradient-to-r from-green-500/30 via-amber-500/30 to-red-500/30" />
              {/* Zone labels */}
              <div className="absolute top-10 left-0 right-0 flex justify-between text-[10px] text-muted-foreground font-mono px-1">
                <span>Low</span>
                <span>Moderate</span>
                <span>High</span>
                <span>Critical</span>
              </div>
              {/* Marker */}
              <div
                className={cn(
                  "absolute top-1/2 -translate-y-1/2 transition-all duration-300",
                  "w-1 h-6 bg-white border-2 rounded-full shadow-lg z-10",
                  "border-slate-300 dark:border-slate-600",
                )}
                style={{ left: `${markerPos}%` }}
                role="img"
                aria-label={`Risk score: ${score.toFixed(1)} out of ${VISUAL_MAX}+`}
              />
              {/* Max label */}
              <div className="absolute bottom-full right-0 text-[10px] text-muted-foreground font-mono">
                {VISUAL_MAX}+ = maximum risk
              </div>
            </div>
          </div>
        </div>

        {/* Plain sentence */}
        <div className={cn("p-4 rounded-lg border", vColors.border, vColors.bg)}>
          <p className="text-sm text-foreground leading-relaxed">{verdictSentence}</p>
        </div>

        {/* Detail tooltip/popover */}
        <Tooltip
          content={(
            <div className="space-y-2 text-left">
              <div className="font-mono text-lg font-semibold text-foreground">{score.toFixed(1)}</div>
              <div className="text-xs text-muted-foreground">Thresholds:</div>
              <div className="text-xs font-mono grid grid-cols-3 gap-2 text-muted-foreground">
                <div>MERGE <span className="text-foreground">[0, {NEEDS_REVIEW_THRESHOLD})</span></div>
                <div>NEEDS_REVIEW <span className="text-foreground">[{NEEDS_REVIEW_THRESHOLD}, {BLOCK_THRESHOLD})</span></div>
                <div>BLOCK <span className="text-foreground">[{BLOCK_THRESHOLD}, ∞)</span></div>
              </div>
              <div className="text-xs text-muted-foreground pt-1">
                Formula: Σ(severity × tier_weight × corroboration × confidence)
              </div>
            </div>
          )}>
            <HelpCircle className="size-4 text-muted-foreground hover:text-foreground cursor-help transition-colors" />
          </Tooltip>
      </CardContent>
    </Card>
  );
}