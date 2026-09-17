"use client";

import { ReactNode } from "react";
import { AppLayout } from "@/components/app-layout";
import { useReview } from "@/lib/review-context";

interface LayoutWrapperProps {
  children: ReactNode;
}

export function LayoutWrapper({ children }: LayoutWrapperProps) {
  const { setReport, setPhase, setError, clearReview } = useReview();

  return (
    <AppLayout
      onRunReview={() => {}}
      onRunDemo={() => {}}
      busy={false}
    >
      {children}
    </AppLayout>
  );
}