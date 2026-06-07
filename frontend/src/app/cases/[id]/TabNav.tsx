"use client";

import { Eye, MessageCircle, FolderOpen, PenLine } from "lucide-react";

export type TabId = "overview" | "chat" | "documents" | "drafts";

interface TabNavProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
}

const TABS: { id: TabId; label: string; shortLabel: string; icon: typeof Eye }[] = [
  { id: "overview", label: "Overview", shortLabel: "Overview", icon: Eye },
  { id: "chat", label: "Chat", shortLabel: "Chat", icon: MessageCircle },
  { id: "documents", label: "Documents", shortLabel: "Docs", icon: FolderOpen },
  { id: "drafts", label: "Drafts", shortLabel: "Drafts", icon: PenLine },
];

export default function TabNav({ activeTab, onTabChange }: TabNavProps) {
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
      <nav className="md:hidden shrink-0 bg-surface-1 border-t border-border flex items-stretch justify-around
                      h-14 pb-[env(safe-area-inset-bottom,0px)]">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => onTabChange(tab.id)}
              className="flex flex-col items-center justify-center gap-0.5 flex-1
                         text-[10px] font-medium transition-colors
                         min-h-0"
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
      </nav>
    </>
  );
}
