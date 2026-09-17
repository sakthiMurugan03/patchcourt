"use client";

import { Scale } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { Debate } from "@/lib/types";

export function DebateTranscript({ debates }: { debates: Debate[] }) {
  if (debates.length === 0) {
    return null;
  }
  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Scale className="size-4 text-primary" /> Courtroom Debate
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {debates.map((d, i) => (
          <div key={i} className="flex flex-col gap-3">
            <div className="flex items-center gap-2">
              <p className="font-mono text-xs text-muted-foreground">{d.file}</p>
              <Badge variant="outline" className="ml-auto">
                {d.rounds} round{d.rounds === 1 ? "" : "s"}
              </Badge>
            </div>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <div className="rounded-lg border border-red-500/25 bg-red-500/5 p-3">
                <p className="mb-1.5 text-[11px] font-semibold tracking-wide text-red-400 uppercase">
                  Prosecution — flags {d.issue}
                </p>
                <p className="text-sm text-foreground">{d.opposing}</p>
              </div>
              <div className="rounded-lg border border-teal-500/25 bg-teal-500/5 p-3">
                <p className="mb-1.5 text-[11px] font-semibold tracking-wide text-teal-400 uppercase">
                  Defense — rebuttal
                </p>
                <p className="text-sm text-foreground">{d.supporting}</p>
              </div>
            </div>
            <Separator />
          </div>
        ))}
      </CardContent>
    </Card>
  );
}