"use client";

import { createContext, useContext, useState, ReactNode } from "react";
import { useRouter } from "next/navigation";
import { runDemo as runDemoApi, submitReview } from "@/lib/api";
import type { Report } from "@/lib/types";

interface ReviewContextType {
  report: Report | null;
  phase: "idle" | "loading" | "done" | "error";
  error: string;
  errorCategory: string;
  setReport: (report: Report | null) => void;
  setPhase: (phase: "idle" | "loading" | "done" | "error") => void;
  setError: (error: string) => void;
  setErrorCategory: (category: string) => void;
  clearReview: () => void;
  runReview: (prUrl: string) => Promise<void>;
  runDemo: () => Promise<void>;
  busy: boolean;
}

const ReviewContext = createContext<ReviewContextType | null>(null);

export function ReviewProvider({ children }: { children: ReactNode }) {
  const [report, setReport] = useState<Report | null>(null);
  const [phase, setPhase] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [error, setError] = useState<string>("");
  const [errorCategory, setErrorCategory] = useState<string>("unknown");
  const router = useRouter();

  const clearReview = () => {
    setReport(null);
    setPhase("idle");
    setError("");
    setErrorCategory("unknown");
  };

  const runReview = async (prUrl: string) => {
    setPhase("loading");
    setError("");
    setErrorCategory("unknown");
    try {
      const r = await submitReview(prUrl);
      setReport(r);
      setPhase("done");
      router.push("/");
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      const msg = err.message;
      const cat = (err as any).category || "unknown";
      setError(msg);
      setErrorCategory(cat);
      setPhase("error");
    }
  };

  const runDemo = async () => {
    setPhase("loading");
    setError("");
    setErrorCategory("unknown");
    try {
      const r = await runDemoApi();
      setReport(r);
      setPhase("done");
      router.push("/");
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e));
      const msg = err.message;
      const cat = (err as any).category || "unknown";
      setError(msg);
      setErrorCategory(cat);
      setPhase("error");
    }
  };

  return (
    <ReviewContext.Provider
      value={{
        report,
        phase,
        error,
        errorCategory,
        setReport,
        setPhase,
        setError,
        setErrorCategory,
        clearReview,
        runReview,
        runDemo,
        busy: phase === "loading",
      }}
    >
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