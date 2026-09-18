"use client";

import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { LayoutWrapper } from "@/components/layout-wrapper";
import { OverviewTab } from "@/components/tabs/overview-tab";
import { EvidenceTab } from "@/components/tabs/evidence-tab";
import { DebateTab } from "@/components/tabs/debate-tab";
import { BaselineTab } from "@/components/tabs/baseline-tab";
import { SonarLiveTab } from "@/components/tabs/sonar-live-tab";
import { HistoryTab } from "@/components/tabs/history-tab";
import { SettingsTab } from "@/components/tabs/settings-tab";

type TabKey = "overview" | "evidence" | "debate" | "baseline" | "sonar-live" | "history" | "settings";

const VALID_TABS: TabKey[] = ["overview", "evidence", "debate", "baseline", "sonar-live", "history", "settings"];

interface DashboardContextType {
  activeTab: TabKey;
  switchTab: (tab: TabKey) => void;
}

const DashboardContext = createContext<DashboardContextType | null>(null);

export function useDashboard() {
  const context = useContext(DashboardContext);
  if (!context) {
    throw new Error("useDashboard must be used within a DashboardProvider");
  }
  return context;
}

interface DashboardProviderProps {
  children: ReactNode;
  value: DashboardContextType;
}

export function DashboardProvider({ children }: DashboardProviderProps) {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [mounted, setMounted] = useState(false);

  // Initialize activeTab from ?tab= query param on mount
  useEffect(() => {
    const tab = searchParams?.get("tab");
    if (tab && VALID_TABS.includes(tab as TabKey)) {
      setActiveTab(tab as TabKey);
    }
    setMounted(true);
  }, [searchParams]);

  // Sync URL when tab changes (shallow, no navigation)
  const switchTab = useCallback((tab: TabKey) => {
    if (tab === activeTab) return;
    setActiveTab(tab);
    const params = new URLSearchParams(searchParams?.toString());
    if (tab === "overview") {
      params.delete("tab");
    } else {
      params.set("tab", tab);
    }
    // Use replace to avoid history entry and navigation
    router.replace(`/?${params.toString()}`, { scroll: false });
  }, [router, searchParams, activeTab]);

  return (
    <DashboardContext.Provider value={{ activeTab, switchTab }}>
      <LayoutWrapper>
        <div className="flex flex-col gap-6 min-h-0 flex-1">
          {children}
        </div>
      </LayoutWrapper>
    </DashboardContext.Provider>
  );
}

export function DashboardShell() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeTab, setActiveTab] = useState<TabKey>("overview");
  const [mounted, setMounted] = useState(false);

  // Initialize activeTab from ?tab= query param on mount
  useEffect(() => {
    const tab = searchParams?.get("tab");
    if (tab && VALID_TABS.includes(tab as TabKey)) {
      setActiveTab(tab as TabKey);
    }
    setMounted(true);
  }, [searchParams]);

  // Sync URL when tab changes (shallow, no navigation)
  const switchTab = useCallback((tab: TabKey) => {
    if (tab === activeTab) return;
    setActiveTab(tab);
    const params = new URLSearchParams(searchParams?.toString());
    if (tab === "overview") {
      params.delete("tab");
    } else {
      params.set("tab", tab);
    }
    // Use replace to avoid history entry and navigation
    router.replace(`/?${params.toString()}`, { scroll: false });
  }, [router, searchParams, activeTab]);

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
    <DashboardProvider value={{ activeTab, switchTab }}>
      <LayoutWrapper>
        <div className="flex flex-col gap-6 min-h-0 flex-1">
          {renderTab()}
        </div>
      </LayoutWrapper>
    </DashboardProvider>
  );
}