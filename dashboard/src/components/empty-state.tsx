"use client";

import { Gavel, MessageSquare, SearchCheck, BarChart2, History } from "lucide-react";
import { cn } from "cn";

interface EmptyStateProps {
  message: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

const ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  evidence: SearchCheck,
  debate: MessageSquare,
  baseline: BarChart2,
  history: History,
  default: Gavel,
};

export function EmptyState({ message, description, icon: Icon = Gavel }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Icon className="size-16 text-muted-foreground/30" />
      <p className="mt-4 text-lg font-medium text-foreground">{message}</p>
      {description && <p className="mt-2 text-sm text-muted-foreground max-w-md">{description}</p>}
    </div>
  );
}