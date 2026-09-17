"use client";

import { useEffect, useState } from "react";
import { Gavel, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "cn";
import { useReview } from "@/lib/review-context";
import { useRouter } from "next/navigation";

export function TopBar() {
  const { runReview, runDemo, busy, phase } = useReview();
  const router = useRouter();
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [prUrl, setPrUrl] = useState("");

  useEffect(() => {
    const checkApi = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/health`, {
          method: "GET",
          signal: AbortSignal.timeout(2000),
        });
        setApiStatus(res.ok ? "online" : "offline");
      } catch {
        setApiStatus("offline");
      }
    };
    checkApi();
    const interval = setInterval(checkApi, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (prUrl.trim()) {
      await runReview(prUrl.trim());
      setPrUrl("");
    }
  };

  const handleDemo = async () => {
    await runDemo();
    setPrUrl("");
  };

  return (
    <header className="sticky top-0 z-30 h-16 border-b border-border bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/90 flex items-center gap-4 px-4">
      <form onSubmit={handleSubmit} className="flex-1 flex items-center gap-2 max-w-2xl mx-auto">
        <label htmlFor="pr-url" className="sr-only">
          Pull Request URL
        </label>
        <Input
          id="pr-url"
          type="url"
          placeholder="https://github.com/owner/repo/pull/123"
          value={prUrl}
          onChange={(e) => setPrUrl(e.target.value)}
          className="w-full max-w-md"
          disabled={busy}
        />
        <Button type="submit" disabled={busy || !prUrl.trim()} className="gap-2">
          <RefreshCw className={cn("size-4", busy && "animate-spin")} />
          <span>Run Review</span>
        </Button>
        <Button type="button" variant="secondary" onClick={handleDemo} disabled={busy} className="gap-2">
          <Gavel className="size-4" />
          <span>Offline Demo</span>
        </Button>
      </form>

      <div className="flex items-center gap-3 ml-auto">
        <div className="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium" role="status" aria-live="polite">
          {apiStatus === "checking" && (
            <>
              <RefreshCw className="size-3 animate-spin text-muted-foreground" />
              <span className="text-muted-foreground">Checking…</span>
            </>
          )}
          {apiStatus === "online" && (
            <>
              <Wifi className="size-3 text-green-400" />
              <span className="text-green-400">API Online</span>
            </>
          )}
          {apiStatus === "offline" && (
            <>
              <WifiOff className="size-3 text-destructive" />
              <span className="text-destructive">API Offline</span>
            </>
          )}
        </div>
      </div>
    </header>
  );
}