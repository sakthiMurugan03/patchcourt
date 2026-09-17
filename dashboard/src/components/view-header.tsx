"use client";

import { cn } from "cn";

interface ViewHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
}

export function ViewHeader({ title, subtitle, actions }: ViewHeaderProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
        {subtitle && <p className="mt-1 truncate font-mono text-xs text-muted-foreground max-w-[400px]">{subtitle}</p>}
      </div>
      {actions && <div className="flex-shrink-0">{actions}</div>}
    </div>
  );
}