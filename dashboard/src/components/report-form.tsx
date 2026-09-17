"use client";

import { useState } from "react";
import { Gavel, LoaderCircle, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Gavel className="size-4 text-primary" />
          New Review
        </CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <form onSubmit={(e) => { e.preventDefault(); if (prUrl) onReview(prUrl); }} className="flex flex-col gap-4">
          <div>
            <Label htmlFor="pr-url" className="text-sm font-medium mb-1.5">
              GitHub Pull Request URL
            </Label>
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
          <div className="flex flex-wrap gap-3 pt-2">
            <Button type="submit" disabled={busy || !prUrl} className="gap-2">
              {busy ? <LoaderCircle className="size-4 animate-spin" /> : <Gavel className="size-4" />}
              {busy ? "Agents deliberating…" : "Run Review"}
            </Button>
            <Button type="button" variant="outline" onClick={onDemo} disabled={busy} className="gap-2">
              <Sparkles className="size-4 text-primary" />
              Offline Demo
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}