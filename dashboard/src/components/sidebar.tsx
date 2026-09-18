"use client";

import { useRouter } from "next/navigation";
import {
  LayoutDashboard,
  SearchCheck,
  MessageSquare,
  BarChart2,
  History,
  Scale,
  Gavel,
  Activity,
  Settings,
} from "lucide-react";
import { cn } from "cn";
import { useDashboard } from "@/components/dashboard-shell";

const NAV_ITEMS = [
  { tab: "overview", label: "Overview", icon: LayoutDashboard },
  { tab: "evidence", label: "Evidence", icon: SearchCheck },
  { tab: "debate", label: "Debate", icon: MessageSquare },
  { tab: "baseline", label: "SonarQube Baseline", icon: BarChart2 },
  { tab: "sonar-live", label: "SonarQube Live", icon: Activity },
  { tab: "history", label: "History", icon: History },
  { tab: "settings", label: "Settings", icon: Settings },
] as const;

export function Sidebar() {
  const { activeTab, switchTab } = useDashboard();

  return (
    <aside
      className="fixed left-0 top-0 z-40 h-full w-64 border-r border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/60 flex flex-col"
      aria-label="Main navigation"
    >
      <div className="flex h-16 items-center justify-center border-b border-border">
        <span className="flex items-center gap-2 text-lg font-semibold text-foreground" onClick={() => switchTab("overview")} style={{ cursor: "pointer" }}>
          <Scale className="size-5 text-primary" />
          <span>PatchCourt</span>
        </span>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto" role="navigation">
        {NAV_ITEMS.map((item) => {
          const isActive = activeTab === item.tab;
          const Icon = item.icon;
          return (
            <button
              key={item.tab}
              type="button"
              onClick={() => switchTab(item.tab)}
              className={cn(
                "flex items-center gap-3 w-full px-3 py-2.5 rounded-md text-sm font-medium transition-colors text-left",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Gavel className="size-3.5" />
          <span>Evidence-gated review</span>
        </div>
      </div>
    </aside>
  );
}