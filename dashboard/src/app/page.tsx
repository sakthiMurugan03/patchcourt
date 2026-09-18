"use client";

import { Suspense } from "react";
import { DashboardShell } from "@/components/dashboard-shell";

export default function Page() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center"><div className="animate-spin size-8 border-4 border-primary border-t-transparent rounded-full" /></div>}>
      <DashboardShell />
    </Suspense>
  );
}