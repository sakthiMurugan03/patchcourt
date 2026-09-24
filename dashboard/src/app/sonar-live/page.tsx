"use client";

import { SonarLivePanel } from "@/components/sonar-live-panel";
import { LayoutWrapper } from "@/components/layout-wrapper";
import { ViewHeader } from "@/components/view-header";
import { useReview } from "@/lib/review-context";
import { projectKeyForPr } from "@/lib/api";

export default function SonarLivePage() {
  const { report, phase } = useReview();
  const component = report?.pr_url ? projectKeyForPr(report.pr_url) ?? undefined : undefined;

  if (phase === "loading") {
    return (
      <LayoutWrapper>
        <div className="flex flex-col items-center gap-4 rounded-lg border border-border bg-card p-10">
          <div className="flex items-center gap-2">
            <svg className="animate-spin size-5 text-primary" viewBox="0 0 24 24"><circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" /><path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" /></svg>
            <span className="text-sm text-muted-foreground">Loading review…</span>
          </div>
        </div>
      </LayoutWrapper>
    );
  }

  return (
    <LayoutWrapper>
      <div className="flex flex-col gap-6">
        <ViewHeader
          title="SonarQube Live"
          subtitle={report?.pr_url}
        />
        <SonarLivePanel component={component} />
      </div>
    </LayoutWrapper>
  );
}