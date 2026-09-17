"use client";

import { ReactNode } from "react";
import { AppLayout } from "@/components/app-layout";

interface LayoutWrapperProps {
  children: ReactNode;
}

export function LayoutWrapper({ children }: LayoutWrapperProps) {
  return <AppLayout>{children}</AppLayout>;
}