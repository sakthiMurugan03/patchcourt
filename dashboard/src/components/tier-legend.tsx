"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TIER_INFO } from "@/lib/types";
import { cn } from "cn";

const ORDER = [1, 2, 3, 4, 5];

const TIER_COLORS = {
  1: "var(--severity-critical)",
  2: "var(--severity-high)",
  3: "var(--severity-medium)",
  4: "var(--severity-low)",
  5: "var(--severity-info)",
} as const;

export function TierLegend() {
  return (
    <Card className="w-full sticky top-20 h-fit">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <span className="text-primary">Evidence Tiers</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {ORDER.map((t) => {
          const info = TIER_INFO[t];
          const color = TIER_COLORS[t as keyof typeof TIER_COLORS];
          return (
            <div key={t} className="flex items-center gap-3">
              <span className="w-9 shrink-0 rounded border border-border bg-muted px-1 py-0.5 text-center font-mono text-xs font-semibold" style={{ color }}>
                T{t}
              </span>
              <div className="flex-1">
                <p className="text-xs font-medium">{info.name.split(" — ")[1] ?? info.name}</p>
                <p className="text-[11px] text-muted-foreground">{info.blurb}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <div className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full" style={{ width: `${info.weight * 100}%`, backgroundColor: color }} />
                </div>
                <span className="w-8 text-right font-mono text-xs text-muted-foreground">
                  ×{info.weight.toFixed(1)}
                </span>
              </div>
            </div>
          );
        })}
        <p className="mt-1 border-t border-border pt-2.5 text-[11px] leading-relaxed text-muted-foreground">
          Hard rule: a BLOCK verdict can never rest on T5 (LLM reasoning) alone — tier weights sit on top
          of the raw score only when static-analysis evidence exists.
        </p>
      </CardContent>
    </Card>
  );
}