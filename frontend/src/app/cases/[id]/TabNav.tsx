"use client";

import { useState, useRef, useEffect } from "react";
import { Eye, MessageCircle, FolderOpen, FolderTree, PenLine, Mail, CheckSquare, CalendarDays, MoreHorizontal, FileSearch, Users, Send, Building2, Database, TrendingUp } from "lucide-react";

export type TabId = "overview" | "chat" | "documents" | "drafts" | "workspace" | "correspondence" | "tasks" | "calendar" | "triage" | "vendor_matches" | "outreach";

interface TabNavProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  /** Only shown for solicitation-backed cases. */
  showTriage?: boolean;
  /** Only shown for solicitation-backed cases. */
  showVendorMatches?: boolean;
}

interface TabDef {
  id: TabId;
  label: string;
  shortLabel: string;
  icon: typeof Eye;
}

const BASE_TABS: TabDef[] = [
  { id: "overview", label: "Overview", shortLabel: "Overview", icon: Eye },
  { id: "chat", label: "Chat", shortLabel: "Chat", icon: MessageCircle },
  { id: "documents", label: "Documents", shortLabel: "Docs", icon: FolderOpen },
  { id: "triage", label: "Triage", shortLabel: "Triage", icon: FileSearch },
  { id: "vendor_matches", label: "Vendor Matches", shortLabel: "Matches", icon: Users },
  { id: "outreach", label: "Outreach", shortLabel: "Outreach", icon: Send },
  { id: "workspace", label: "Workspace", shortLabel: "Work", icon: FolderTree },
  { id: "correspondence", label: "Correspondence", shortLabel: "Corr.", icon: Mail },
  { id: "tasks", label: "Tasks", shortLabel: "Tasks", icon: CheckSquare },
  { id: "calendar", label: "Calendar", shortLabel: "Cal", icon: CalendarDays },
];

/** First 4 tabs are always visible on mobile */
const PRIMARY_COUNT = 4;

export default function TabNav({
  activeTab,
  onTabChange,
  showTriage = false,
  showVendorMatches = false,
}: TabNavProps) {
  const TABS = BASE_TABS.filter((t) => {
    if (t.id === "triage" && !showTriage) return false;
    if ((t.id === "vendor_matches" || t.id === "outreach") && !showVendorMatches) return false;
    return true;
  });
  const primaryTabs = TABS.slice(0, PRIMARY_COUNT);
  const secondaryTabs = TABS.slice(PRIMARY_COUNT);
  /* ---- mobile "More" menu ---- */
  const [moreOpen, setMoreOpen] = useState(false);
  const moreRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!moreOpen) return;
    const handler = (e: MouseEvent) => {
      if (moreRef.current && !moreRef.current.contains(e.target as Node)) {
        setMoreOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [moreOpen]);

  const activeSecondary = secondaryTabs.some((t) => t.id === activeTab);

  return (
    <>
      {/* ================================================================ */}
      {/* Desktop Sidebar                                                  */}
      {/* ================================================================ */}
      <aside className="hidden md:flex fixed left-0 top-14 bottom-0 w-[220px] bg-surface-1 border-r border-border flex-col z-20">
        <nav className="flex-1 p-2 flex flex-col gap-0.5">
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => onTabChange(tab.id)}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
                            transition-colors
                            ${isActive
                              ? "bg-brand-bg text-brand"
                              : "text-text-secondary hover:bg-surface-2 hover:text-text-primary"
                            }`}
              >
                <tab.icon size={18} />
                {tab.label}
              </button>
            );
          })}
        </nav>

        {/* Reference Desk — global data accessible from any case */}
        <div className="border-t border-border p-2">
          <p className="px-2 py-1 text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
            Reference Desk
          </p>
          <a
            href="/vendors"
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       text-text-secondary hover:bg-surface-2 hover:text-text-primary transition-colors"
          >
            <Building2 size={14} />
            Vendors
          </a>
          <a
            href="/sam-notices"
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       text-text-secondary hover:bg-surface-2 hover:text-text-primary transition-colors"
          >
            <Database size={14} />
            SAM Notices
          </a>
          <a
            href="/forecasts"
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg text-xs font-medium
                       text-text-secondary hover:bg-surface-2 hover:text-text-primary transition-colors"
          >
            <TrendingUp size={14} />
            Forecasts
          </a>
        </div>

        {/* User footer */}
        <div className="p-3 border-t border-border flex items-center gap-2">
          <div className="size-7 rounded-full bg-surface-3 flex items-center justify-center text-xs font-medium text-text-secondary">
            IB
          </div>
          <span className="text-xs text-text-secondary flex-1 truncate">
            ian@justicequest.ai
          </span>
        </div>
      </aside>

      {/* ================================================================ */}
      {/* Mobile Bottom Tab Bar                                            */}
      {/* ================================================================ */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-surface-1 border-t border-border
                      flex items-stretch justify-around
                      h-14 pb-[env(safe-area-inset-bottom,0px)] z-30">
        {/* Primary tabs */}
        {primaryTabs.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className="flex flex-col items-center justify-center gap-0.5 flex-1
                         text-[10px] font-medium transition-colors min-h-0"
              style={{ color: isActive ? "var(--color-brand)" : "var(--color-text-secondary)" }}
            >
              <tab.icon
                size={22}
                strokeWidth={isActive ? 2.5 : 2}
              />
              {tab.shortLabel}
            </button>
          );
        })}

        {/* More tab */}
        <div ref={moreRef} className="relative flex-1">
          <button
            onClick={() => setMoreOpen(!moreOpen)}
            className="flex flex-col items-center justify-center gap-0.5 w-full h-full
                       text-[10px] font-medium transition-colors min-h-0 relative"
            style={{ color: activeSecondary ? "var(--color-brand)" : "var(--color-text-secondary)" }}
          >
            <div className="relative">
              <MoreHorizontal
                size={22}
                strokeWidth={activeSecondary ? 2.5 : 2}
              />
              {activeSecondary && (
                <span className="absolute -top-0.5 -right-1 size-2 rounded-full bg-danger" />
              )}
            </div>
            More
          </button>

          {/* More menu */}
          {moreOpen && (
            <div className="absolute bottom-full right-0 mb-2 w-44 bg-surface-2 border border-border
                            rounded-lg shadow-lg z-40 py-1">
              {secondaryTabs.map((tab) => {
                const isActive = activeTab === tab.id;
                return (
                  <button
                    key={tab.id}
                    onClick={() => { onTabChange(tab.id); setMoreOpen(false); }}
                    className={`w-full text-left px-3 py-2.5 text-xs flex items-center gap-2.5
                                transition-colors
                                ${isActive
                                  ? "bg-brand-bg text-brand"
                                  : "text-text-secondary hover:bg-surface-3 hover:text-text-primary"
                                }`}
                  >
                    <tab.icon size={16} />
                    {tab.label}
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </nav>
    </>
  );
}
