"use client";

import { ReactNode, useState } from "react";
import { Sidebar } from "@/components/sidebar";
import { TopBar } from "@/components/top-bar";
import { cn } from "cn";

interface AppLayoutProps {
  children: ReactNode;
  onRunReview: (url: string) => void;
  onRunDemo: () => void;
  busy: boolean;
}

export function AppLayout({ children, onRunReview, onRunDemo, busy }: AppLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background flex">
      <Sidebar />
      <div className="flex-1 flex flex-col lg:ml-64 min-w-0">
        <TopBar onRunReview={onRunReview} onRunDemo={onRunDemo} busy={busy} />
        <main className="flex-1 overflow-y-auto p-4 lg:p-6" role="main">
          <div className="mx-auto max-w-7xl">{children}</div>
        </main>
      </div>
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 lg:hidden bg-black/50"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
}