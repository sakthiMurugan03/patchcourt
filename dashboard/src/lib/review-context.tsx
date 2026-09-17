"use client";

import { createContext, useContext, useState, ReactNode, useEffect } from "react";
import type { Report } from "@/lib/types";

interface ReviewContextType {
  report: Report | null;
  phase: "idle" | "loading" | "done" | "error";
  error: string;
  setReport: (report: Report | null) => void;
  setPhase: (phase: "idle" | "loading" | "done" | "error") => void;
  setError: (error: string) => void;
  clearReview: () => void;
}

const ReviewContext = createContext<ReviewContextType | null>(null);

export function ReviewProvider({ children }: { children: ReactNode }) {
  const [report, setReport] = useState<Report | null>(null);
  const [phase, setPhase] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [error, setError] = useState<string>("");

  const clearReview = () => {
    setReport(null);
    setPhase("idle");
    setError("");
  };

  return (
    <ReviewContext.Provider value={{ report, phase, error, setReport, setPhase, setError, clearReview }}>
      {children}
    </ReviewContext.Provider>
  );
}

export function useReview() {
  const context = useContext(ReviewContext);
  if (!context) {
    throw new Error("useReview must be used within a ReviewProvider");
  }
  return context;
}