"use client";

import { Gavel } from "lucide-react";

interface EmptyStateProps {
  message: string;
  description?: string;
  icon?: React.ComponentType<{ className?: string }>;
}

export function EmptyState({ message, description, icon: Icon = Gavel }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Icon className="size-16 text-muted-foreground/30" />
      <p className="mt-4 text-lg font-medium text-foreground">{message}</p>
      {description && <p className="mt-2 text-sm text-muted-foreground max-w-md">{description}</p>}
    </div>
  );
}