"use client";

import { type ListView, type ViewEnvelope } from "./types";
import { useInlineEdit } from "@/hooks/useInlineEdit";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface DynamicListProps {
  view: ListView;
  viewIndex: number;
  itemId: number;
  editMode: boolean;
  envelope: ViewEnvelope;
  onContentChange: (updated: ViewEnvelope) => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DynamicList({
  view,
  viewIndex,
  itemId,
  editMode,
  envelope,
  onContentChange,
}: DynamicListProps) {
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
    onContentChange(newContent as unknown as ViewEnvelope);
  });

  const { listStyle, items } = view.data;

  /* ---- empty state ---- */
  if (!items || items.length === 0) {
    return (
      <p className="text-sm text-[--text-disabled] text-center py-8">
        No items
      </p>
    );
  }

  /* ---- handlers ---- */
  const handleTextEdit = (itemId: string) => {
    if (!editMode) return;
    const item = items.find((i) => i.id === itemId);
    if (!item) return;
    const cellKey = `${viewIndex}-${itemId}-text`;
    startEdit(cellKey, item.text);
  };

  const handleTextSave = async (itemId: string) => {
    const updated = structuredClone(envelope);
    const listData = (updated.views[viewIndex] as ListView).data;
    const item = listData.items.find((i) => i.id === itemId);
    if (item) {
      item.text = editValue;
    }
    await commitEdit(updated as unknown as Record<string, unknown>);
  };

  const handleKeyDown = (e: React.KeyboardEvent, itemId: string) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleTextSave(itemId);
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  };

  /** Toggle checkbox completion — saves immediately */
  const handleCheckboxToggle = async (itemId: string) => {
    if (!editMode) return;
    const updated = structuredClone(envelope);
    const listData = (updated.views[viewIndex] as ListView).data;
    const item = listData.items.find((i) => i.id === itemId);
    if (item) {
      item.completed = !item.completed;
    }
    await commitEdit(updated as unknown as Record<string, unknown>);
  };

  /* ---- render ---- */
  if (listStyle === "checkbox") {
    return (
      <div className="flex flex-col gap-2">
        {items.map((item) => {
          const textKey = `${viewIndex}-${item.id}-text`;
          const isEditingText = editMode && editingCell === textKey;

          return (
            <div key={item.id} className="flex items-start gap-3 group">
              {/* Checkbox */}
              <input
                type="checkbox"
                checked={item.completed ?? false}
                onChange={() => handleCheckboxToggle(item.id)}
                disabled={!editMode}
                className="mt-1 accent-[--brand] shrink-0"
              />

              {/* Text + optional notes */}
              <div className="flex-1 min-w-0">
                {isEditingText ? (
                  <div className="flex flex-col gap-1">
                    <textarea
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={() => handleTextSave(item.id)}
                      onKeyDown={(e) => handleKeyDown(e, item.id)}
                      className={`w-full bg-[--surface-1] border border-[--brand] rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[--brand-ring] resize-y ${isSaving ? "animate-pulse" : ""}`}
                      autoFocus
                      rows={2}
                      // eslint-disable-next-line jsx-a11y/no-autofocus
                    />
                    {saveError && (
                      <p className="text-xs text-[--danger]">{saveError}</p>
                    )}
                  </div>
                ) : (
                  <span
                    className={`text-sm ${
                      item.completed
                        ? "line-through text-[--text-disabled]"
                        : "text-[--text-primary]"
                    } ${editMode ? "cursor-pointer hover:bg-[--surface-3] rounded px-1 -mx-1 transition-colors" : ""}`}
                    onDoubleClick={() => handleTextEdit(item.id)}
                    title={editMode ? "Double-click to edit" : undefined}
                  >
                    {item.text}
                  </span>
                )}

                {/* Notes */}
                {item.notes && (
                  <p className="text-xs text-[--text-secondary] mt-0.5 ml-0">
                    {item.notes}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  /* ---- ordered or bullet ---- */
  if (listStyle === "ordered") {
    return (
      <ol className="list-decimal list-inside flex flex-col gap-2">
        {items.map((item) => {
          const textKey = `${viewIndex}-${item.id}-text`;
          const isEditingText = editMode && editingCell === textKey;

          return (
            <li key={item.id} className="text-sm text-[--text-primary]">
              {isEditingText ? (
                <div className="inline-flex flex-col gap-1 w-full">
                  <textarea
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    onBlur={() => handleTextSave(item.id)}
                    onKeyDown={(e) => handleKeyDown(e, item.id)}
                    className={`w-full bg-[--surface-1] border border-[--brand] rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[--brand-ring] resize-y ${isSaving ? "animate-pulse" : ""}`}
                    autoFocus
                    rows={2}
                    // eslint-disable-next-line jsx-a11y/no-autofocus
                  />
                  {saveError && (
                    <p className="text-xs text-[--danger]">{saveError}</p>
                  )}
                </div>
              ) : (
                <span
                  className={editMode ? "cursor-pointer hover:bg-[--surface-3] rounded px-1 -mx-1 transition-colors" : ""}
                  onDoubleClick={() => handleTextEdit(item.id)}
                  title={editMode ? "Double-click to edit" : undefined}
                >
                  {item.text}
                </span>
              )}
              {item.notes && (
                <p className="text-xs text-[--text-secondary] mt-0.5 ml-6">
                  {item.notes}
                </p>
              )}
            </li>
          );
        })}
      </ol>
    );
  }

  /* ---- bullet ---- */
  return (
    <ul className="list-disc list-inside flex flex-col gap-2">
      {items.map((item) => {
        const textKey = `${viewIndex}-${item.id}-text`;
        const isEditingText = editMode && editingCell === textKey;

        return (
          <li key={item.id} className="text-sm text-[--text-primary]">
            {isEditingText ? (
              <div className="inline-flex flex-col gap-1 w-full">
                <textarea
                  value={editValue}
                  onChange={(e) => setEditValue(e.target.value)}
                  onBlur={() => handleTextSave(item.id)}
                  onKeyDown={(e) => handleKeyDown(e, item.id)}
                  className={`w-full bg-[--surface-1] border border-[--brand] rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[--brand-ring] resize-y ${isSaving ? "animate-pulse" : ""}`}
                  autoFocus
                  rows={2}
                  // eslint-disable-next-line jsx-a11y/no-autofocus
                />
                {saveError && (
                  <p className="text-xs text-[--danger]">{saveError}</p>
                )}
              </div>
            ) : (
              <span
                className={editMode ? "cursor-pointer hover:bg-[--surface-3] rounded px-1 -mx-1 transition-colors" : ""}
                onDoubleClick={() => handleTextEdit(item.id)}
                title={editMode ? "Double-click to edit" : undefined}
              >
                {item.text}
              </span>
            )}
            {item.notes && (
              <p className="text-xs text-[--text-secondary] mt-0.5 ml-6">
                {item.notes}
              </p>
            )}
          </li>
        );
      })}
    </ul>
  );
}
