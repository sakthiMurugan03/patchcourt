import type { BaselineReport, Report } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

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
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {
      /* keep default */
    }
    throw new Error(detail);
  }
  return (await res.json()) as T;
}

export function submitReview(prUrl: string): Promise<Report> {
  return request<Report>("POST", "/api/review", { pr_url: prUrl });
}

export function runDemo(): Promise<Report> {
  return request<Report>("POST", "/api/review/demo");
}

export async function getBaselineLatest(): Promise<BaselineReport> {
  const res = await fetch(`${API_BASE}/api/baseline/latest`);
  if (res.status === 404) return null as unknown as BaselineReport;
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const data = await res.json();
      if (typeof data.detail === "string") detail = data.detail;
    } catch {}
    throw new Error(detail);
  }
  return (await res.json()) as BaselineReport;
}

export function refreshBaseline(prUrl: string): Promise<BaselineReport> {
  return request<BaselineReport>("POST", "/api/baseline", { pr_url: prUrl });
}