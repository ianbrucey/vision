"use client";

import { useState, useRef, useEffect } from "react";
import { COMPATIBLE_VIEWS } from "./types";
import type { ViewDefinition, ViewEnvelope } from "./types";
import { updateWorkspaceItem } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface ViewSwitcherProps {
  view: ViewDefinition;
  viewIndex: number;
  itemId: number;
  envelope: ViewEnvelope;
  onSwitch: (updated: ViewEnvelope) => void;
}

/* ------------------------------------------------------------------ */
/* Icons                                                              */
/* ------------------------------------------------------------------ */

const ICONS: Record<string, string> = {
  table: "📊",
  cards: "🃏",
  chart: "📈",
};

const LABELS: Record<string, string> = {
  table: "Table",
  cards: "Cards",
  chart: "Chart",
};

/* ------------------------------------------------------------------ */
/* Non-lossy switch helpers                                           */
/* ------------------------------------------------------------------ */

/** View types that share the {headers, rows} data model. Switching between
 *  them only changes viewType — no data transform needed. */
const SHARED_DATA_TYPES = new Set(["table", "chart"]);

/** True if switching from → to is non-lossy (only viewType changes). */
function isNonLossy(from: string, to: string): boolean {
  return SHARED_DATA_TYPES.has(from) && SHARED_DATA_TYPES.has(to);
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function ViewSwitcher({
  view,
  viewIndex,
  itemId,
  envelope,
  onSwitch,
}: ViewSwitcherProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const compatible = COMPATIBLE_VIEWS[view.viewType] ?? [];

  // Close on outside click
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  if (compatible.length === 0) return null;

  const handleSwitch = async (toType: string) => {
    const updated = structuredClone(envelope);
    const currentView = updated.views[viewIndex];

    if (isNonLossy(view.viewType, toType)) {
      // Same data model ({headers, rows}) — just change viewType.
      const v = currentView as { viewType: string; data: Record<string, unknown> };
      v.viewType = toType;
      // Add/remove chartType field as needed
      if (toType === "chart") {
        v.data.chartType = "bar"; // default to bar for categorical data
      } else if (toType === "table" && "chartType" in v.data) {
        delete v.data.chartType;
      }
    } else {
      // Lossy transform — not expected in v1 but kept as safety valve.
      // Future transforms would go here.
      return;
    }

    // Persist to API
    try {
      const result = await updateWorkspaceItem(itemId, { content: updated });
      onSwitch(result.item.content as ViewEnvelope);
    } catch {
      onSwitch(updated);
    }
    setOpen(false);
  };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="text-xs px-2 py-1 rounded border border-[--border] bg-[--surface-1] hover:bg-[--surface-3] flex items-center gap-1 transition-colors"
      >
        <span className="text-base leading-none">
          {ICONS[view.viewType] ?? "📋"}
        </span>
        <span className="hidden sm:inline text-[--text-secondary]">
          View as
        </span>
        <span className="text-[--text-secondary]">▼</span>
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 rounded-lg border border-[--border] bg-[--surface-4] shadow-lg z-10 min-w-40">
          {compatible.map((toType) => (
            <button
              key={toType}
              type="button"
              onClick={() => handleSwitch(toType)}
              className="w-full text-left px-3 py-2 text-sm text-[--text-primary] hover:bg-[--surface-2] flex items-center gap-2 first:rounded-t-lg last:rounded-b-lg transition-colors"
            >
              <span className="text-base">{ICONS[toType] ?? "📋"}</span>
              <span>{LABELS[toType] ?? toType}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
