"use client";

import { useState } from "react";
import { Gavel, LoaderCircle, Play, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

type Props = {
  onReview: (prUrl: string) => void;
  onDemo: () => void;
  busy: boolean;
};

export function ReportForm({ onReview, onDemo, busy }: Props) {
  const [prUrl, setPrUrl] = useState("");

  return (
    <Card className="w-full">
      <CardContent className="pt-6">
        <div className="flex flex-col gap-5">
          <div className="grid w-full items-center gap-1.5">
            <Label htmlFor="pr-url">GitHub Pull Request</Label>
            <Input
              id="pr-url"
              placeholder="https://github.com/owner/repo/pull/123"
              value={prUrl}
              onChange={(e) => setPrUrl(e.target.value)}
              disabled={busy}
              className="font-mono"
              onKeyDown={(e) => {
                if (e.key === "Enter" && prUrl) onReview(prUrl);
              }}
            />
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              onClick={() => prUrl && onReview(prUrl)}
              disabled={busy || !prUrl}
              className="gap-2"
            >
              {busy ? <LoaderCircle className="size-4 animate-spin" /> : <Gavel className="size-4" />}
              {busy ? "Agents deliberating…" : "Run Review"}
            </Button>
            <Button variant="outline" onClick={onDemo} disabled={busy} className="gap-2">
              <Sparkles className="size-4 text-primary" />
              Offline Demo
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}