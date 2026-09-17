"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, FileJson } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Report } from "@/lib/types";
import { cn } from "cn";

export function AuditView({ report }: { report: Report }) {
  const [open, setOpen] = useState(false);
  return (
    <Card className="w-full">
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <CardTitle className="text-base flex items-center gap-2">
          <FileJson className="size-4 text-primary" />
          Raw Audit Payload
        </CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setOpen((o) => !o)}
          className="gap-1.5 text-xs text-muted-foreground"
        >
          {open ? <ChevronDown className="size-4" /> : <ChevronRight className="size-4" />}
          {open ? "Hide" : "Show"}
        </Button>
      </CardHeader>
      {open && (
        <CardContent className="pt-0">
          <pre className="max-h-96 overflow-auto rounded-md border border-border bg-muted p-4 font-mono text-xs leading-relaxed text-muted-foreground">
            {JSON.stringify(report, null, 2)}
          </pre>
        </CardContent>
      )}
    </Card>
  );
}