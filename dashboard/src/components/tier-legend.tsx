"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TIER_INFO } from "@/lib/types";

const ORDER = [1, 2, 3, 4, 5];

export function TierLegend() {
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="text-base">Evidence Tiers</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2.5">
        {ORDER.map((t) => {
          const info = TIER_INFO[t];
          return (
            <div key={t} className="flex items-center gap-3">
              <span className="w-9 shrink-0 rounded border border-border bg-muted px-1 py-0.5 text-center font-mono text-xs font-semibold text-primary">
                T{t}
              </span>
              <div className="flex-1">
                <p className="text-xs font-medium">{info.name.split(" — ")[1] ?? info.name}</p>
                <p className="text-[11px] text-muted-foreground">{info.blurb}</p>
              </div>
              <div className="flex shrink-0 items-center gap-1.5">
                <div className="h-1.5 w-12 overflow-hidden rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${info.weight * 100}%` }} />
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