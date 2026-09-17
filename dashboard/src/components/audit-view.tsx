"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileJson } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Report } from "@/lib/types";

export function AuditView({ report }: { report: Report }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="w-full">
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((o) => !o)}
        className="gap-1.5 text-xs text-muted-foreground"
      >
        {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
        <FileJson className="size-4" />
        {open ? "Hide raw audit payload" : "Show raw audit payload"}
      </Button>
      {open && (
        <pre className="mt-2 max-h-96 overflow-auto rounded-lg border border-border bg-black/30 p-4 font-mono text-xs leading-relaxed text-muted-foreground">
          {JSON.stringify(report, null, 2)}
        </pre>
      )}
    </div>
  );
}