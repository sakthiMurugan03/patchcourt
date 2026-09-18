"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { Shield, Key, CheckCircle2, AlertCircle, Loader2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { cn } from "cn";

interface LLMSettings {
  provider: string;
  model: string;
  base_url: string;
  use_mock_llm: boolean;
  has_api_key: boolean;
  available_providers: string[];
}

interface TestResponse {
  ok: boolean;
  detail: string;
}

const PROVIDER_OPTIONS = [
  { value: "mock", label: "Mock (Offline)", description: "Deterministic offline review, no API key needed", icon: Shield },
  { value: "gemini", label: "Gemini", description: "Google Gemini (free tier: 4 req/min)", icon: Key },
  { value: "openai", label: "OpenAI", description: "OpenAI GPT models", icon: Key },
  { value: "ollama", label: "Ollama (Local)", description: "Local LLM via Ollama server", icon: Key },
] as const;

export default function SettingsPage() {
  const router = useRouter();
  const [settings, setSettings] = useState<LLMSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResponse | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [saveStatus, setSaveStatus] = useState<{ ok: boolean; msg: string } | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    
    fetch(`${process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"}/api/settings/llm`, {
      signal: controller.signal,
    })
      .then((res) => res.json())
      .then((data) => setSettings(data))
      .catch((e) => {
        if (e.name !== "AbortError") console.error("Failed to fetch LLM settings:", e);
      })
      .finally(() => {
        clearTimeout(timeout);
        setLoading(false);
      });

    return () => {
      controller.abort();
      clearTimeout(timeout);
    };
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    setSaveStatus(null);
    try {
      const res = await fetch(`${apiBase}/api/settings/llm`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          provider: settings.provider,
          model: settings.model,
          api_key: apiKey || undefined,
          base_url: settings.base_url,
          use_mock_llm: settings.use_mock_llm,
        }),
      });
      const data = await res.json();
      if (res.ok) {
        setSettings(data);
        setApiKey("");
        setSaveStatus({ ok: true, msg: "Settings saved successfully" });
      } else {
        setSaveStatus({ ok: false, msg: data.detail || "Failed to save" });
      }
    } catch (e) {
      setSaveStatus({ ok: false, msg: "Network error" });
    } finally {
      setSaving(false);
    }
  };

  const apiBase = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

  const handleTest = async () => {
    if (!settings) return;
    setTesting(true);
    setTestResult(null);
    try {
      const res = await fetch(`${apiBase}/api/settings/llm/test`, { method: "POST" });
      const data = await res.json();
      setTestResult(data);
    } catch (e) {
      setTestResult({ ok: false, detail: "Network error" });
    } finally {
      setTesting(false);
    }
  };

  const handleProviderChange = (provider: string) => {
    const opt = PROVIDER_OPTIONS.find((o) => o.value === provider);
    setSettings((prev) => prev ? { ...prev, provider, use_mock_llm: provider === "mock", model: opt?.label === "Mock (Offline)" ? "mock" : prev.model } : null);
    setApiKey("");
    setTestResult(null);
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSettings((prev) => prev ? { ...prev, model: e.target.value } : null);
  };

  const handleBaseUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSettings((prev) => prev ? { ...prev, base_url: e.target.value } : null);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="size-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!settings) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        Failed to load settings
      </div>
    );
  }

  const currentProvider = PROVIDER_OPTIONS.find((o) => o.value === settings.provider);
  const showApiKey = settings.provider !== "mock";

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Settings</h1>
          <p className="text-muted-foreground text-sm">Configure LLM provider and API keys</p>
        </div>
      </div>

      {/* Provider Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="size-5" />
            LLM Provider
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {PROVIDER_OPTIONS.map((opt) => {
              const isActive = settings.provider === opt.value;
              const Icon = opt.icon;
              return (
                <button
                  key={opt.value}
                  type="button"
                  onClick={() => handleProviderChange(opt.value)}
                  className={cn(
                    "relative p-4 rounded-md border-2 text-left transition-all",
                    isActive
                      ? "border-primary bg-primary/5"
                      : "border-border hover:border-primary/50"
                  )}
                >
                  <div className="flex items-center gap-3">
                    <Icon className={cn("size-5", isActive ? "text-primary" : "text-muted-foreground")} />
                    <div>
                      <p className="font-medium">{opt.label}</p>
                      <p className="text-xs text-muted-foreground">{opt.description}</p>
                    </div>
                  </div>
                  {isActive && (
                    <CheckCircle2 className="absolute top-2 right-2 size-4 text-primary" />
                  )}
                </button>
              );
            })}
          </div>

          <Separator />

          {/* Model field */}
          <div className="space-y-2">
            <Label htmlFor="model">Model</Label>
            <Input
              id="model"
              value={settings.model}
              onChange={handleModelChange}
              placeholder="e.g. gemini-2.5-flash"
            />
            <p className="text-xs text-muted-foreground">
              Model name for the selected provider
            </p>
          </div>

          {/* Base URL field (for Ollama) */}
          {settings.provider === "ollama" && (
            <div className="space-y-2">
              <Label htmlFor="base_url">Base URL</Label>
              <Input
                id="base_url"
                value={settings.base_url}
                onChange={handleBaseUrlChange}
                placeholder="http://localhost:11434/v1"
              />
            </div>
          )}

          {/* API Key field */}
          {showApiKey && (
            <div className="space-y-2">
              <Label htmlFor="api_key">API Key</Label>
              <div className="relative">
                <Input
                  id="api_key"
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder={settings.has_api_key ? "•••••••• (leave blank to keep current)" : "Enter API key"}
                  autoComplete="off"
                />
                {settings.has_api_key && (
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">
                    Key is set
                  </span>
                )}
              </div>
              <p className="text-xs text-muted-foreground">
                Never stored in logs or echoed back. Resets on container restart.
              </p>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="size-4 animate-spin mr-2" /> : null} Save Settings
            </Button>
            <Button variant="outline" onClick={handleTest} disabled={testing}>
              {testing ? <Loader2 className="size-4 animate-spin mr-2" /> : null} Test Connection
            </Button>
          </div>

          {saveStatus && (
            <div className={cn("text-sm", saveStatus.ok ? "text-green-400" : "text-red-400")}>
              {saveStatus.msg}
            </div>
          )}

          {testResult && (
            <div className={cn("p-3 rounded-md text-sm", testResult.ok ? "bg-green-500/10 border border-green-500/30 text-green-400" : "bg-red-500/10 border border-red-500/30 text-red-400")}>
              <div className="flex items-center gap-2">
                {testResult.ok ? <CheckCircle2 className="size-4" /> : <AlertCircle className="size-4" />}
                <span>{testResult.detail}</span>
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground">
            Settings are stored in memory and reset on container restart. For persistence, set environment variables.
          </p>
        </CardContent>
      </Card>

      {/* Active Provider Status */}
      <Card className="border-primary/30">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={cn("size-10 rounded-full flex items-center justify-center", settings.use_mock_llm ? "bg-green-500/10" : "bg-primary/10")}>
                {currentProvider?.icon && <currentProvider.icon className={cn("size-5", settings.use_mock_llm ? "text-green-400" : "text-primary")} />}
              </div>
              <div>
                <p className="font-medium">{currentProvider?.label || settings.provider}</p>
                <p className="text-sm text-muted-foreground">
                  Model: {settings.model} | Base URL: {settings.base_url || "default"}
                </p>
              </div>
            </div>
            <span className={cn("px-3 py-1 rounded-full text-xs font-mono", settings.use_mock_llm ? "bg-green-500/10 text-green-400" : "bg-primary/10 text-primary")}>
              {settings.use_mock_llm ? "OFFLINE" : "LIVE"}
            </span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}