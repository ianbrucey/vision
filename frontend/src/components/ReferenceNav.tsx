"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Home, Database, TrendingUp, Building2, Users, Settings } from "lucide-react";
import { useAuth } from "@/components/AuthProvider";

const NAV_ITEMS = [
  { href: "/sam-notices", label: "SAM Notices", icon: Database },
  { href: "/subcontracting-leads", label: "Sub Leads", icon: Users },
  { href: "/forecasts", label: "Forecasts", icon: TrendingUp },
  { href: "/vendors", label: "Vendors", icon: Building2 },
];

export default function ReferenceNav() {
  const pathname = usePathname();
  const { user } = useAuth();

  return (
    <header className="sticky top-0 shrink-0 bg-surface-1 border-b border-border z-30">
      <div className="flex items-center h-14 px-4 gap-1 max-w-7xl mx-auto">
        {/* Home */}
        <Link
          href="/"
          className="text-text-secondary hover:text-brand transition-colors shrink-0
                     min-h-[44px] min-w-[44px] flex items-center justify-center"
          aria-label="Home"
        >
          <Home size={20} />
        </Link>

        {/* Reference Desk label */}
        <span className="text-[11px] font-semibold text-text-disabled uppercase tracking-wide mr-2 border-l border-border pl-3">
          Reference Desk
        </span>

        {/* Nav items */}
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                         transition-colors
                         ${isActive
                           ? "bg-brand-bg text-brand"
                           : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
                         }`}
            >
              <item.icon size={16} />
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          );
        })}

        {/* Admin Settings — only visible to admin */}
        {user?.role === "admin" && (
          <>
            <span className="text-text-disabled/30 mx-1">|</span>
            <Link
              href="/settings"
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium
                         transition-colors
                         ${pathname === "/settings"
                           ? "bg-brand-bg text-brand"
                           : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
                         }`}
            >
              <Settings size={16} />
              <span className="hidden sm:inline">Settings</span>
            </Link>
          </>
        )}
      </div>
    </header>
  );
}
