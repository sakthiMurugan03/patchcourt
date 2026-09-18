"use client";

import { SonarBaselinePanel } from "@/components/sonar-baseline-panel";
import { EmptyState } from "@/components/empty-state";
import { ViewHeader } from "@/components/view-header";
import { useReview } from "@/lib/review-context";

export function BaselineTab() {
  const { report, phase } = useReview();

  if (phase === "loading") {
    return <LoadingState />;
  }

  return (
    <div className="flex flex-col gap-6">
      <ViewHeader
        title="SonarQube Baseline"
        subtitle={report?.pr_url}
      />
      <SonarBaselinePanel defaultPrUrl={report?.pr_url} />
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center gap-4 rounded-lg border border-border bg-card p-10">
      <div className="flex items-center gap-2">
        <svg className="animate-spin size-5 text-primary" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        <span className="text-sm text-muted-foreground">Loading review…</span>
      </div>
    </div>
  );
}