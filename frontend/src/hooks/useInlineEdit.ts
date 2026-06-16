"use client";

import { useState, useCallback, useRef } from "react";
import { updateWorkspaceItem } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

export interface InlineEditState {
  /** The key of the cell currently being edited, or null. */
  editingCell: string | null;
  /** The current value in the edit input. */
  editValue: string;
  /** True while a save is in-flight. */
  isSaving: boolean;
  /** Error message from the most recent failed save, or null. */
  saveError: string | null;
}

export interface InlineEditActions {
  /** Begin editing a cell. If another cell is already being edited, it is
   *  cancelled first (no auto-save — the caller must handle save before switching). */
  startEdit: (cellKey: string, currentValue: string) => void;

  /** Update the edit value as the user types. Does NOT trigger a save. */
  setEditValue: (value: string) => void;

  /** Persist the edit. The caller provides the fully-transformed envelope.
   *  Returns true on success, false on failure. */
  commitEdit: (updatedContent: Record<string, unknown>) => Promise<boolean>;

  /** Cancel the current edit without saving. Restores original state. */
  cancelEdit: () => void;

  /** Clear the save error (e.g., when the user dismisses an error toast). */
  clearError: () => void;
}

/* ------------------------------------------------------------------ */
/* Hook                                                               */
/* ------------------------------------------------------------------ */

/**
 * Shared inline editing logic for Dynamic View components.
 *
 * Manages editing state and API persistence. The caller is responsible for
 * transforming the view envelope to apply the edit — the hook handles the
 * PATCH call, loading/error states, and edit lifecycle (start → edit → commit/cancel).
 *
 * Usage in a view component:
 * ```ts
 * const { editingCell, editValue, startEdit, setEditValue, commitEdit, cancelEdit, isSaving, saveError } =
 *   useInlineEdit(itemId, (newContent) => setLocalContent(newContent));
 *
 * // On cell click:
 * startEdit("r1-Balance", "$4,230");
 *
 * // On save (blur/Enter):
 * const updated = structuredClone(content);
 * // ... apply the edit to updated ...
 * await commitEdit(updated);
 * ```
 */
export function useInlineEdit(
  itemId: number,
  onSaved: (newContent: Record<string, unknown>) => void,
): InlineEditState & InlineEditActions {
  const [editingCell, setEditingCell] = useState<string | null>(null);
  const [editValue, setEditValueState] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Track save in-flight to prevent overlapping commits
  const savingRef = useRef(false);

  // Original value before editing started — used for revert on cancel
  const originalValueRef = useRef("");

  const startEdit = useCallback((cellKey: string, currentValue: string) => {
    // Cancel any in-progress edit before starting a new one.
    // We don't auto-save on cell switch — the component should handle
    // blur-triggered saves before starting a new edit.
    if (savingRef.current) return; // don't interrupt an in-flight save

    setEditingCell(cellKey);
    setEditValueState(currentValue);
    originalValueRef.current = currentValue;
    setSaveError(null);
  }, []);

  const setEditValue = useCallback((value: string) => {
    setEditValueState(value);
  }, []);

  const commitEdit = useCallback(
    async (updatedContent: Record<string, unknown>): Promise<boolean> => {
      if (savingRef.current) return false;

      savingRef.current = true;
      setIsSaving(true);
      setSaveError(null);

      try {
        await updateWorkspaceItem(itemId, { content: updatedContent });
        onSaved(updatedContent);
        setEditingCell(null);
        setEditValueState("");
        return true;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to save changes";
        setSaveError(message);
        return false;
      } finally {
        savingRef.current = false;
        setIsSaving(false);
      }
    },
    [itemId, onSaved],
  );

  const cancelEdit = useCallback(() => {
    if (savingRef.current) return;
    setEditingCell(null);
    setEditValueState("");
    setSaveError(null);
  }, []);

  const clearError = useCallback(() => {
    setSaveError(null);
  }, []);

  return {
    editingCell,
    editValue,
    isSaving,
    saveError,
    startEdit,
    setEditValue,
    commitEdit,
    cancelEdit,
    clearError,
  };
}
