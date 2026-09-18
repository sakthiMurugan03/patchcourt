"use client";

import React, { useState, useRef, useEffect } from "react";
import { cn } from "cn";

interface TooltipProps {
  content: React.ReactNode;
  children: React.ReactElement;
  side?: "top" | "bottom" | "left" | "right";
  delayMs?: number;
}

export function Tooltip({ content, children, side = "top", delayMs = 150 }: TooltipProps) {
  const [open, setOpen] = useState(false);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const childRef = useRef<HTMLElement>(null);

  const setOpenWithDelay = (value: boolean) => {
    if (timeoutRef.current) clearTimeout(timeoutRef.current);
    if (value) {
      timeoutRef.current = setTimeout(() => setOpen(true), delayMs);
    } else {
      timeoutRef.current = setTimeout(() => setOpen(false), delayMs);
    }
  };

  useEffect(() => {
    return () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };
  }, []);

  // Clone the child to add event handlers
  const childWithProps = React.cloneElement(children as React.ReactElement<any>, {
    ref: childRef,
    onMouseEnter: () => setOpenWithDelay(true),
    onMouseLeave: () => setOpenWithDelay(false),
    onFocus: () => setOpenWithDelay(true),
    onBlur: () => setOpenWithDelay(false),
  } as any);

  if (!open) return childWithProps;

  return (
    <div className="relative inline-block">
      {childWithProps}
      <div
        className={cn(
          "absolute z-50 px-3 py-2 text-xs text-white bg-slate-900 rounded-md shadow-lg",
          "whitespace-pre-wrap max-w-xs",
          side === "top" && "bottom-full left-1/2 -translate-x-1/2 mb-2",
          side === "bottom" && "top-full left-1/2 -translate-x-1/2 mt-2",
          side === "left" && "right-full top-1/2 -translate-y-1/2 mr-2",
          side === "right" && "left-full top-1/2 -translate-y-1/2 ml-2",
        )}
        role="tooltip"
      >
        {content}
        <div
          className={cn(
            "absolute size-0 border-4 border-transparent",
            side === "top" && "top-full left-1/2 -translate-x-1/2 border-t-slate-900",
            side === "bottom" && "bottom-full left-1/2 -translate-x-1/2 border-b-slate-900",
            side === "left" && "left-full top-1/2 -translate-y-1/2 border-l-slate-900",
            side === "right" && "right-full top-1/2 -translate-y-1/2 border-r-slate-900",
          )}
        />
      </div>
    </div>
  );
}