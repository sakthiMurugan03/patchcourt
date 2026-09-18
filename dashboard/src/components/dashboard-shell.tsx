"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, usePathname, useSearchParams } from "next/navigation";
import { LayoutWrapper } from "@/components/layout-wrapper";
import { OverviewTab } from "@/components/tabs/overview-tab";
import { EvidenceTab } from "@/components/tabs/evidence-tab";
import { DebateTab } from "@/components/tabs/debate-tab";
import { BaselineTab } from "@/components/tabs/baseline-tab";
import { SonarLiveTab } from "@/components/tabs/sonar-live-tab";
import { HistoryTab } from "@/components/tabs/history-tab";
import { SettingsTab } from "@/components/tabs/settings-tab";

type TabKey = "overview" | "evidence" | "debate" | "baseline" | "sonar-live" | "history" | "settings";

const TAB_ORDER: TabKey[] = ["overview", "evidence", "debate", "baseline", "sonar-live", "history", "settings"];

const TAB_ROUTE_MAP: Record<TabKey, string> = {
  overview: "/",
  evidence: "/evidence",
  debate: "/debate",
  baseline: "/baseline",
  "sonar-live": "/sonar-live",
  history: "/history",
  settings: "/settings",
};

export function DashboardShell() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [mounted, setMounted] = useState(false);

  // Initialize activeTab from URL on mount (SSR-safe)
  useEffect(() => {
    const path = pathname || "/";
    let tab: TabKey = "overview";
    for (const [key, route] of Object.entries(TAB_ROUTE_MAP)) {
      if (route === path || (route !== "/" && path.startsWith(route))) {
        tab = key as TabKey;
        break;
      }
    }
    setActiveTab(tab);
    setMounted(true);
  }, [pathname]);

  // Sync URL when tab changes (shallow, no navigation)
  const switchTab = useCallback((tab: TabKey) => {
    if (tab === activeTab) return;
    setActiveTab(tab);
    const route = TAB_ROUTE_MAP[tab];
    // Use replaceState to avoid history entry and navigation
    router.replace(route, { scroll: false });
  }, [router, activeTab]);

  // Don't render until mounted to avoid hydration mismatch
  if (!mounted) {
    return (
      <LayoutWrapper>
        <div className="flex flex-col gap-6 min-h-[50vh]">
          <div className="flex items-center justify-center py-20">
            <svg className="animate-spin size-8 text-primary" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
        </div>
      </LayoutWrapper>
    );
  }

  const renderTab = () => {
    switch (activeTab) {
      case "overview":
        return <OverviewTab />;
      case "evidence":
        return <EvidenceTab />;
      case "debate":
        return <DebateTab />;
      case "baseline":
        return <BaselineTab />;
      case "sonar-live":
        return <SonarLiveTab />;
      case "history":
        return <HistoryTab />;
      case "settings":
        return <SettingsTab />;
      default:
        return <OverviewTab />;
    }
  };

  return (
    <LayoutWrapper>
      <div className="flex flex-col gap-6 min-h-0 flex-1">
        {renderTab()}
      </div>
    </LayoutWrapper>
  );
}