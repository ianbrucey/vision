"use client";

import {
  useState, useEffect, useRef, useCallback, useMemo, type KeyboardEvent,
} from "react";
import {
  Plus, Search, X, Trash2, Pencil, MessageCircle, Loader2, PanelLeftClose,
} from "lucide-react";
import type { ChatSession } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

interface SessionSidebarProps {
  sessions: ChatSession[];
  activeSessionId: number | null;
  loading: boolean;
  /** Desktop sidebar collapsed state — ChatTab manages this */
  collapsed: boolean;
  /** Mobile drawer open state — ChatTab manages this via useSessionSidebarMobile */
  mobileOpen: boolean;
  onSelect: (id: number) => void;
  onNew: () => void;
  onArchive: (id: number) => void;
  onRename: (id: number, title: string) => void;
  onToggleCollapse: () => void;
  onCloseMobile: () => void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

function relativeDate(iso: string): string {
  const then = new Date(iso).getTime();
  const now = Date.now();
  const diffSec = Math.floor((now - then) / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHr = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHr / 24);

  if (diffSec < 60) return "Just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHr < 24) return `${diffHr}h ago`;
  if (diffDay === 1) return "Yesterday";
  if (diffDay < 7) return `${diffDay}d ago`;
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

function msgLabel(count: number): string {
  if (count === 0) return "No messages";
  if (count === 1) return "1 message";
  return `${count} messages`;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function SessionSidebar({
  sessions,
  activeSessionId,
  loading,
  collapsed,
  mobileOpen,
  onSelect,
  onNew,
  onArchive,
  onRename,
  onToggleCollapse,
  onCloseMobile,
}: SessionSidebarProps) {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [focusedIdx, setFocusedIdx] = useState(0);
  const renameInputRef = useRef<HTMLInputElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  /* Debounce search */
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 150);
    return () => clearTimeout(timer);
  }, [search]);

  /* Focus rename input when it appears */
  useEffect(() => {
    if (renamingId !== null) {
      renameInputRef.current?.focus();
      renameInputRef.current?.select();
    }
  }, [renamingId]);

  /* Filter sessions */
  const filtered = useMemo(() => {
    if (!debouncedSearch.trim()) return sessions;
    const q = debouncedSearch.toLowerCase();
    return sessions.filter(
      (s) => (s.title || `Chat ${s.id}`).toLowerCase().includes(q),
    );
  }, [sessions, debouncedSearch]);

  /* Keep focusedIdx in bounds when filtered list changes */
  useEffect(() => {
    if (focusedIdx >= filtered.length) {
      setFocusedIdx(Math.max(0, filtered.length - 1));
    }
  }, [filtered.length, focusedIdx]);

  /* Lock body scroll when mobile drawer is open */
  useEffect(() => {
    if (mobileOpen) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [mobileOpen]);

  /* ---- rename handlers ---- */

  const commitRename = useCallback(() => {
    if (renamingId !== null && renameValue.trim()) {
      onRename(renamingId, renameValue.trim());
    }
    setRenamingId(null);
    setRenameValue("");
  }, [renamingId, renameValue, onRename]);

  const cancelRename = useCallback(() => {
    setRenamingId(null);
    setRenameValue("");
  }, []);

  const startRename = (id: number, currentTitle: string | null) => {
    setRenamingId(id);
    setRenameValue(currentTitle || "");
  };

  /* ---- delete handler (two-click confirm) ---- */

  const handleDelete = (id: number) => {
    if (deletingId === id) {
      onArchive(id);
      setDeletingId(null);
    } else {
      setDeletingId(id);
      setTimeout(() => setDeletingId((prev) => (prev === id ? null : prev)), 3000);
    }
  };

  /* ---- keyboard navigation ---- */

  const handleKeyDown = (e: KeyboardEvent) => {
    if (renamingId !== null) return;
    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setFocusedIdx((prev) => Math.min(prev + 1, filtered.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setFocusedIdx((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (filtered[focusedIdx]) {
          onSelect(filtered[focusedIdx].id);
        }
        break;
    }
  };

  const handleMobileSelect = (id: number) => {
    onSelect(id);
    onCloseMobile();
  };

  /* ---- render helpers ---- */

  const sessionRow = (s: ChatSession, idx: number) => {
    const isActive = s.id === activeSessionId;
    const isRenaming = s.id === renamingId;
    const isDeleting = s.id === deletingId;
    const isFocused = idx === focusedIdx;
    const displayTitle = s.title || `Chat ${s.id}`;

    return (
      <div
        key={s.id}
        role="option"
        aria-selected={isActive}
        tabIndex={isFocused ? 0 : -1}
        onClick={() => {
          if (renamingId !== null) return;
          handleMobileSelect(s.id);
        }}
        onKeyDown={handleKeyDown}
        onFocus={() => setFocusedIdx(idx)}
        className={`group flex items-center gap-2 px-3 py-2.5 cursor-pointer
                    transition-colors border-l-[3px] outline-none
                    ${isActive
                      ? "border-l-brand bg-brand-bg"
                      : "border-l-transparent hover:bg-surface-2"
                    }
                    ${isFocused && !isActive ? "bg-surface-2" : ""}`}
      >
        <MessageCircle
          size={16}
          className={`shrink-0 ${isActive ? "text-brand" : "text-text-disabled"}`}
          strokeWidth={isActive ? 2 : 1.5}
        />

        <div className="flex-1 min-w-0">
          {isRenaming ? (
            <input
              ref={renameInputRef}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onBlur={commitRename}
              onKeyDown={(e) => {
                if (e.key === "Enter") commitRename();
                if (e.key === "Escape") cancelRename();
                e.stopPropagation();
              }}
              onClick={(e) => e.stopPropagation()}
              className="w-full bg-surface-1 border border-brand rounded px-1.5 py-0.5
                         text-xs text-text-primary outline-none
                         focus:ring-2 focus:ring-brand-ring"
              maxLength={120}
            />
          ) : (
            <>
              <p
                className={`text-xs font-medium truncate ${
                  isActive ? "text-text-primary" : "text-text-secondary"
                }`}
                title={displayTitle}
              >
                {displayTitle}
              </p>
              <p className="text-[10px] text-text-disabled mt-0.5">
                {relativeDate(s.updated_at)}
                {" · "}
                {msgLabel(s.message_count)}
              </p>
            </>
          )}
        </div>

        {/* Hover actions */}
        {!isRenaming && (
          <div
            className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100
                       transition-opacity shrink-0"
          >
            <button
              onClick={(e) => {
                e.stopPropagation();
                startRename(s.id, s.title);
              }}
              className="p-1 rounded text-text-disabled hover:text-text-secondary
                         hover:bg-surface-3 transition-colors"
              title="Rename"
              aria-label="Rename session"
            >
              <Pencil size={12} />
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                handleDelete(s.id);
              }}
              className={`p-1 rounded transition-colors ${
                isDeleting
                  ? "bg-danger-bg text-danger"
                  : "text-text-disabled hover:text-danger hover:bg-danger-bg"
              }`}
              title={isDeleting ? "Click again to confirm" : "Delete"}
              aria-label={isDeleting ? "Confirm delete" : "Delete session"}
            >
              {isDeleting ? (
                <span className="text-[9px] font-bold px-0.5">?</span>
              ) : (
                <Trash2 size={12} />
              )}
            </button>
          </div>
        )}
      </div>
    );
  };

  /* ---- sidebar content (shared by desktop + mobile drawer) ---- */

  const sidebarContent = (
    <>
      {/* Header */}
      <div className="shrink-0 px-3 py-2.5 flex items-center justify-between border-b border-border">
        <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          Chats
        </h2>
        <div className="flex items-center gap-1">
          <button
            onClick={onNew}
            className="p-1 rounded text-text-disabled hover:text-brand hover:bg-brand-bg
                       transition-colors"
            title="New session"
            aria-label="New session"
          >
            <Plus size={16} strokeWidth={2} />
          </button>
          {/* Desktop collapse toggle */}
          <button
            onClick={onToggleCollapse}
            className="hidden md:flex p-1 rounded text-text-disabled hover:text-text-secondary
                       hover:bg-surface-2 transition-colors"
            title="Collapse sidebar"
            aria-label="Collapse sidebar"
          >
            <PanelLeftClose size={14} />
          </button>
        </div>
      </div>

      {/* Search */}
      <div className="shrink-0 px-2 py-2">
        <div className="relative">
          <Search
            size={13}
            className="absolute left-2 top-1/2 -translate-y-1/2 text-text-disabled pointer-events-none"
          />
          <input
            ref={searchInputRef}
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search sessions..."
            className="w-full bg-surface-2 border border-border rounded-md
                       pl-7 pr-7 py-1.5 text-xs text-text-primary
                       placeholder:text-text-disabled
                       focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-none"
          />
          {search && (
            <button
              onClick={() => {
                setSearch("");
                searchInputRef.current?.focus();
              }}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5
                         text-text-disabled hover:text-text-secondary transition-colors"
              aria-label="Clear search"
            >
              <X size={12} />
            </button>
          )}
        </div>
      </div>

      {/* Session list */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto"
        role="listbox"
        aria-label="Chat sessions"
      >
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 size={16} className="animate-spin text-text-disabled" />
          </div>
        ) : filtered.length === 0 ? (
          <div className="px-3 py-8 text-center">
            <div className="size-10 rounded-full bg-surface-3 flex items-center justify-center mx-auto mb-2">
              <MessageCircle size={18} className="text-text-disabled" strokeWidth={1.5} />
            </div>
            <p className="text-xs text-text-secondary font-medium">
              {search ? "No matching sessions" : "No conversations yet"}
            </p>
            <p className="text-[10px] text-text-disabled mt-1">
              {search
                ? "Try a different search term."
                : "Start one to begin analyzing your case."}
            </p>
            {!search && (
              <button
                onClick={onNew}
                className="mt-3 inline-flex items-center gap-1.5 text-xs px-3 py-1.5
                           rounded-full bg-brand text-white hover:bg-brand-hover
                           transition-colors"
              >
                <Plus size={12} />
                New session
              </button>
            )}
          </div>
        ) : (
          filtered.map((s, i) => sessionRow(s, i))
        )}
      </div>
    </>
  );

  /* ---- render ---- */

  return (
    <>
      {/* Desktop: inline sidebar — hidden when collapsed */}
      {!collapsed && (
        <aside
          className="hidden md:flex flex-col w-65 shrink-0
                     border-r border-border bg-surface-1 h-full"
        >
          {sidebarContent}
        </aside>
      )}

      {/* Mobile: overlay drawer */}
      {mobileOpen && (
        <div className="md:hidden fixed inset-0 z-40">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/30"
            onClick={onCloseMobile}
            aria-hidden
          />
          {/* Drawer */}
          <aside
            className="absolute left-0 top-0 bottom-0 w-70 max-w-[85vw]
                       bg-surface-1 border-r border-border flex flex-col z-50
                       shadow-lg"
            style={{
              animation: "slideInLeft 200ms ease-out",
              paddingTop: "env(safe-area-inset-top, 0px)",
              paddingBottom: "env(safe-area-inset-bottom, 0px)",
            }}
          >
            {/* Mobile close button */}
            <div className="shrink-0 px-3 py-2.5 flex items-center justify-between border-b border-border">
              <h2 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
                Chats
              </h2>
              <div className="flex items-center gap-1">
                <button
                  onClick={onNew}
                  className="p-1 rounded text-text-disabled hover:text-brand hover:bg-brand-bg
                             transition-colors"
                  aria-label="New session"
                >
                  <Plus size={16} />
                </button>
                <button
                  onClick={onCloseMobile}
                  className="p-1 rounded text-text-disabled hover:text-text-secondary
                             hover:bg-surface-2 transition-colors"
                  aria-label="Close sessions"
                >
                  <X size={16} />
                </button>
              </div>
            </div>
            {/* Search */}
            <div className="shrink-0 px-2 py-2">
              <div className="relative">
                <Search
                  size={13}
                  className="absolute left-2 top-1/2 -translate-y-1/2 text-text-disabled pointer-events-none"
                />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search sessions..."
                  className="w-full bg-surface-2 border border-border rounded-md
                             pl-7 pr-7 py-1.5 text-xs text-text-primary
                             placeholder:text-text-disabled
                             focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-none"
                />
                {search && (
                  <button
                    onClick={() => {
                      setSearch("");
                      searchInputRef.current?.focus();
                    }}
                    className="absolute right-1.5 top-1/2 -translate-y-1/2 p-0.5
                               text-text-disabled hover:text-text-secondary transition-colors"
                    aria-label="Clear search"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
            </div>
            {/* Session list */}
            <div className="flex-1 overflow-y-auto" role="listbox" aria-label="Chat sessions">
              {loading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 size={16} className="animate-spin text-text-disabled" />
                </div>
              ) : filtered.length === 0 ? (
                <div className="px-3 py-8 text-center">
                  <p className="text-xs text-text-secondary">
                    {search ? "No matching sessions" : "No conversations yet"}
                  </p>
                </div>
              ) : (
                filtered.map((s, i) => sessionRow(s, i))
              )}
            </div>
          </aside>
        </div>
      )}
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Hook for mobile state — ChatTab uses this                           */
/* ------------------------------------------------------------------ */

export function useSessionSidebarMobile() {
  const [open, setOpen] = useState(false);
  return {
    mobileOpen: open,
    openMobile: () => setOpen(true),
    closeMobile: () => setOpen(false),
  };
}
