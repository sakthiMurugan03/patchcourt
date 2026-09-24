import type { BaselineReport, Report, SonarHealth, SonarQualityGate, SonarMeasures, SonarIssuesResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

/** Mirrors patchcourt.baseline.sonarqube_baseline.project_key_for_pr exactly —
 * the per-PR SonarQube project the on-demand scan (triggered from the
 * Baseline tab) creates, so other views can point at the same project
 * instead of always falling back to the fixed default. */
export function projectKeyForPr(prUrl: string): string | null {
  const m = prUrl.match(/github\.com\/([^/]+)\/([^/]+)\/pull\/(\d+)/);
  if (!m) return null;
  const raw = `pr-${m[1]}-${m[2]}-${m[3]}`.toLowerCase();
  return raw.replace(/[^a-z0-9_.:-]/g, "-");
}

interface FriendlyError {
  category: string;
  message: string;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = {
    method,
    headers: { "Content-Type": "application/json" },
  };
  if (body !== undefined) {
    init.body = JSON.stringify(body);
  } else if (method !== "GET") {
    init.body = JSON.stringify({});
  }
  const res = await fetch(`${API_BASE}${path}`, init);
  if (!res.ok) {
    let category = "unknown";
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && typeof data === "object") {
        if (typeof data.detail === "string") {
          message = data.detail;
        } else if (data.detail && typeof data.detail === "object") {
          category = data.detail.category || "unknown";
          message = data.detail.message || `HTTP ${res.status}`;
        }
      }
    } catch {
      /* keep defaults */
    }
    const err = new Error(message) as Error & { category?: string };
    err.category = category;
    throw err;
  }
  return (await res.json()) as T;
}

export function submitReview(prUrl: string): Promise<Report> {
  return request<Report>("POST", "/api/review", { pr_url: prUrl });
}

export function runDemo(): Promise<Report> {
  return request<Report>("POST", "/api/review/demo");
}

export async function getBaselineLatest(): Promise<BaselineReport | null> {
  const res = await fetch(`${API_BASE}/api/baseline/latest`);
  if (res.status === 404) return null;
  if (!res.ok) {
    let category = "unknown";
    let message = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (data && typeof data === "object") {
        if (typeof data.detail === "string") {
          message = data.detail;
        } else if (data.detail && typeof data.detail === "object") {
          category = data.detail.category || "unknown";
          message = data.detail.message || `HTTP ${res.status}`;
        }
      }
    } catch {}
    const err = new Error(message) as Error & { category?: string };
    err.category = category;
    throw err;
  }
  return (await res.json()) as BaselineReport;
}

export function refreshBaseline(prUrl: string): Promise<BaselineReport> {
  return request<BaselineReport>("POST", "/api/baseline", { pr_url: prUrl });
}

export async function getSonarHealth(): Promise<SonarHealth> {
  const res = await fetch(`${API_BASE}/api/sonar/health`);
  return (await res.json()) as SonarHealth;
}

export async function getSonarQualityGate(): Promise<SonarQualityGate> {
  const res = await fetch(`${API_BASE}/api/sonar/quality-gate`);
  return (await res.json()) as SonarQualityGate;
}

export async function getSonarMeasures(): Promise<SonarMeasures> {
  const res = await fetch(`${API_BASE}/api/sonar/measures`);
  return (await res.json()) as SonarMeasures;
}

export async function getSonarIssues(page: number = 1, pageSize: number = 20, severities?: string, types?: string): Promise<SonarIssuesResponse> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (severities) params.set("severities", severities);
  if (types) params.set("types", types);
  const res = await fetch(`${API_BASE}/api/sonar/issues?${params.toString()}`);
  return (await res.json()) as SonarIssuesResponse;
}