"use client";

import { usePathname } from "next/navigation";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  LayoutDashboard,
  SearchCheck,
  MessageSquare,
  BarChart2,
  History,
  Scale,
  Gavel,
} from "lucide-react";
import { cn } from "cn";

const NAV_ITEMS = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/evidence", label: "Evidence", icon: SearchCheck },
  { href: "/debate", label: "Debate", icon: MessageSquare },
  { href: "/baseline", label: "SonarQube Baseline", icon: BarChart2 },
  { href: "/history", label: "History", icon: History },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside
      className="fixed left-0 top-0 z-40 h-full w-64 border-r border-border bg-card/50 backdrop-blur supports-[backdrop-filter]:bg-card/60 flex flex-col"
      aria-label="Main navigation"
    >
      <div className="flex h-16 items-center justify-center border-b border-border">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-foreground">
          <Scale className="size-5 text-primary" />
          <span>PatchCourt</span>
        </Link>
      </div>

      <nav className="flex-1 p-4 space-y-1 overflow-y-auto" role="navigation">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:text-foreground hover:bg-accent"
              )}
              onClick={(e: React.MouseEvent) => {
                e.preventDefault();
                router.push(item.href);
              }}
            >
              <Icon className="size-4 shrink-0" aria-hidden="true" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="p-4 border-t border-border">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Gavel className="size-3.5" />
          <span>Evidence-gated review</span>
        </div>
      </div>
    </aside>
  );
}