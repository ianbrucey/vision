"use client";

import { type CardPair, type CardsView } from "./types";
import { useInlineEdit } from "@/hooks/useInlineEdit";
import type { ViewEnvelope } from "./types";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface DynamicCardsProps {
  view: CardsView;
  viewIndex: number;
  itemId: number;
  editMode: boolean;
  envelope: ViewEnvelope;
  onContentChange: (updated: ViewEnvelope) => void;
}

/* ------------------------------------------------------------------ */
/* Emphasis styling                                                   */
/* ------------------------------------------------------------------ */

const EMPHASIS_CLASSES: Record<string, string> = {
  default: "border-l",
  warning: "border-l-2 border-l-[--warning]",
  danger: "border-l-2 border-l-[--danger]",
  success: "border-l-2 border-l-[--success]",
  info: "border-l-2 border-l-[--info]",
};

const EMPHASIS_TEXT: Record<string, string> = {
  default: "text-[--text-primary]",
  warning: "text-[--warning]",
  danger: "text-[--danger]",
  success: "text-[--success]",
  info: "text-[--info]",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DynamicCards({
  view,
  viewIndex,
  itemId,
  editMode,
  envelope,
  onContentChange,
}: DynamicCardsProps) {
  const {
    editingCell,
    editValue,
    startEdit,
    setEditValue,
    commitEdit,
    cancelEdit,
    isSaving,
    saveError,
  } = useInlineEdit(itemId, (newContent) => {
    onContentChange(newContent as ViewEnvelope);
  });

  const pairs = view.data.pairs;

  /* ---- empty state ---- */
  if (!pairs || pairs.length === 0) {
    return (
      <p className="text-sm text-[--text-disabled] text-center py-8">
        No data available
      </p>
    );
  }

  /* ---- handlers ---- */
  const handleValueClick = (pair: CardPair, pairIndex: number) => {
    if (!editMode) return;
    const cellKey = `${viewIndex}-pairs-${pairIndex}-value`;
    startEdit(cellKey, pair.value);
  };

  const handleSave = async (pairIndex: number) => {
    const updated = structuredClone(envelope);
    const cardsView = updated.views[viewIndex] as CardsView;
    cardsView.data.pairs[pairIndex].value = editValue;
    await commitEdit(updated);
  };

  const handleKeyDown = (e: React.KeyboardEvent, pairIndex: number) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave(pairIndex);
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  };

  /* ---- render ---- */
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {pairs.map((pair, i) => {
        const cellKey = `${viewIndex}-pairs-${i}-value`;
        const isEditing = editMode && editingCell === cellKey;
        const emphasis = pair.emphasis ?? "default";

        return (
          <div
            key={`${viewIndex}-pair-${i}`}
            className={`rounded-lg border p-4 flex flex-col gap-2 bg-[--surface-1] ${EMPHASIS_CLASSES[emphasis]}`}
          >
            {/* Key — not editable */}
            <span className="text-xs font-medium text-[--text-secondary] uppercase tracking-wide">
              {pair.key}
            </span>

            {/* Value — editable in edit mode */}
            {isEditing ? (
              <div className="flex flex-col gap-1">
                <input
                  type="text"
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onBlur={() => handleSave(i)}
                  onKeyDown={(e) => handleKeyDown(e, i)}
                  className={`text-2xl font-semibold bg-[--surface-1] border border-[--brand] rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-[--brand-ring] ${EMPHASIS_TEXT[emphasis]} ${isSaving ? "animate-pulse" : ""}`}
                  autoFocus
                  // eslint-disable-next-line jsx-a11y/no-autofocus
                />
                {saveError && (
                  <p className="text-xs text-[--danger]">{saveError}</p>
                )}
              </div>
            ) : (
              <span
                className={`text-2xl font-semibold ${EMPHASIS_TEXT[emphasis]} ${editMode ? "cursor-pointer hover:bg-[--surface-3] rounded px-1 -mx-1 transition-colors" : ""}`}
                onClick={() => handleValueClick(pair, i)}
                title={editMode ? "Click to edit" : undefined}
              >
                {pair.value || (
                  <span className="text-[--text-disabled] italic">
                    Empty
                  </span>
                )}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
