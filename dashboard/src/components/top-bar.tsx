"use client";

import { useEffect, useState } from "react";
import { Gavel, Wifi, WifiOff, RefreshCw, Shield, Key, Circle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "cn";
import { useReview } from "@/lib/review-context";

interface LLMSettings {
  provider: string;
  model: string;
  use_mock_llm: boolean;
}

export function TopBar() {
  const { runReview, runDemo, busy } = useReview();
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [prUrl, setPrUrl] = useState("");
  const [llmSettings, setLlmSettings] = useState<LLMSettings | null>(null);

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

  useEffect(() => {
    const fetchLlmSettings = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/api/settings/llm`);
        if (res.ok) {
          const data = await res.json();
          setLlmSettings({
            provider: data.provider,
            model: data.model,
            use_mock_llm: data.use_mock_llm,
          });
        }
      } catch {
        // silent fail
      }
    };
    fetchLlmSettings();
    const interval = setInterval(fetchLlmSettings, 30000);
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

  const getProviderIcon = (provider: string) => {
    switch (provider) {
      case "gemini": return <Key className="size-3" />;
      case "openai": return <Shield className="size-3" />;
      case "ollama": return <Shield className="size-3" />;
      default: return <Circle className="size-3" />;
    }
  };

  const getProviderLabel = (provider: string) => {
    switch (provider) {
      case "gemini": return "Gemini";
      case "openai": return "OpenAI";
      case "ollama": return "Ollama";
      default: return "Mock";
    }
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
        {/* LLM Provider Status Chip */}
        {llmSettings && (
          <div className={cn(
            "flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium font-mono",
            llmSettings.use_mock_llm ? "bg-green-500/10 text-green-400" : "bg-primary/10 text-primary"
          )} title={`LLM: ${getProviderLabel(llmSettings.provider)} (${llmSettings.model})`}>
            {getProviderIcon(llmSettings.provider)}
            <span>LLM: {getProviderLabel(llmSettings.provider)}</span>
            <span className="text-muted-foreground">|</span>
            <span>{llmSettings.use_mock_llm ? "Offline" : "Live"}</span>
          </div>
        )}

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