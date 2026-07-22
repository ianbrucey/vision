"use client";

import { useState, useMemo } from "react";
import { type TableView, type ViewEnvelope } from "./types";
import { useInlineEdit } from "@/hooks/useInlineEdit";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface DynamicTableProps {
  view: TableView;
  viewIndex: number;
  itemId: number;
  editMode: boolean;
  envelope: ViewEnvelope;
  onContentChange: (updated: ViewEnvelope) => void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

type SortDir = "asc" | "desc" | null;

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DynamicTable({
  view,
  viewIndex,
  itemId,
  editMode,
  envelope,
  onContentChange,
}: DynamicTableProps) {
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

  const { headers, rows } = view.data;

  /* ---- sort state ---- */
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>(null);

  const sortedRows = useMemo(() => {
    if (!sortColumn || !sortDir) return rows;
    return [...rows].sort((a, b) => {
      const aVal = (a[sortColumn] ?? "").toLowerCase();
      const bVal = (b[sortColumn] ?? "").toLowerCase();
      if (aVal < bVal) return sortDir === "asc" ? -1 : 1;
      if (aVal > bVal) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
  }, [rows, sortColumn, sortDir]);

  const handleHeaderClick = (column: string) => {
    if (sortColumn === column) {
      // Cycle: asc → desc → off
      if (sortDir === "asc") {
        setSortDir("desc");
      } else if (sortDir === "desc") {
        setSortColumn(null);
        setSortDir(null);
      }
    } else {
      setSortColumn(column);
      setSortDir("asc");
    }
  };

  const sortIndicator = (column: string) => {
    if (sortColumn !== column || !sortDir) return null;
    return (
      <span className="ml-1 text-xs text-[--text-secondary]">
        {sortDir === "asc" ? "▲" : "▼"}
      </span>
    );
  };

  /* ---- editing ---- */
  const handleCellClick = (rowId: string, colIndex: number, value: string) => {
    if (!editMode) return;
    const cellKey = `${viewIndex}-${rowId}-${colIndex}`;
    startEdit(cellKey, value);
  };

  const handleSave = async (rowId: string, colIndex: number) => {
    const updated = structuredClone(envelope);
    const tableData = (updated.views[viewIndex] as TableView).data;
    const header = tableData.headers[colIndex];
    const row = tableData.rows.find((r) => r.id === rowId);
    if (row) {
      row[header] = editValue;
    }
    await commitEdit(updated as unknown as Record<string, unknown>);
  };

  const handleKeyDown = (
    e: React.KeyboardEvent,
    rowId: string,
    colIndex: number,
  ) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSave(rowId, colIndex);
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  };

  /* ---- empty state ---- */
  if (!rows || rows.length === 0) {
    return (
      <p className="text-sm text-[--text-disabled] text-center py-8">
        No data available
      </p>
    );
  }

  /* ---- render ---- */
  return (
    <div className="overflow-x-auto">
      {/* Desktop table */}
      <table className="hidden md:table w-full text-sm">
        <thead>
          <tr className="bg-[--surface-2]">
            {/* id column — not sortable, not editable */}
            <th className="px-3 py-2 text-left font-semibold text-[--text-secondary] text-xs uppercase tracking-wide">
              #
            </th>
            {headers.map((header, ci) => (
              <th
                key={header}
                className="px-3 py-2 text-left font-semibold text-[--text-primary] cursor-pointer select-none hover:bg-[--surface-3] transition-colors"
                onClick={() => handleHeaderClick(header)}
              >
                <span className="inline-flex items-center">
                  {header}
                  {sortIndicator(header)}
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {sortedRows.map((row, ri) => (
            <tr
              key={row.id}
              className={`border-t border-[--border] hover:bg-[--surface-3] transition-colors ${
                ri % 2 === 0 ? "bg-[--surface-1]" : "bg-[--surface-2]"
              }`}
            >
              {/* id column — read-only */}
              <td className="px-3 py-2 text-xs text-[--text-disabled] font-mono">
                {row.id}
              </td>
              {headers.map((header, ci) => {
                const cellKey = `${viewIndex}-${row.id}-${ci}`;
                const isEditing = editMode && editingCell === cellKey;
                const value = row[header] ?? "";

                return (
                  <td key={`${row.id}-${header}`} className="px-3 py-2">
                    {isEditing ? (
                      <div className="flex flex-col gap-1">
                        {value.length > 50 ? (
                          <textarea
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => handleSave(row.id, ci)}
                            onKeyDown={(e) => {
                              if (e.key === "Escape") cancelEdit();
                              // Enter saves only without Shift
                              if (e.key === "Enter" && !e.shiftKey) {
                                e.preventDefault();
                                handleSave(row.id, ci);
                              }
                            }}
                            className={`w-full min-w-[120px] bg-[--surface-1] border border-[--brand] rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[--brand-ring] resize-y ${isSaving ? "animate-pulse" : ""}`}
                            autoFocus
                            rows={2}
                            // eslint-disable-next-line jsx-a11y/no-autofocus
                          />
                        ) : (
                          <input
                            type="text"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            onBlur={() => handleSave(row.id, ci)}
                            onKeyDown={(e) =>
                              handleKeyDown(e, row.id, ci)
                            }
                            className={`w-full min-w-[120px] bg-[--surface-1] border border-[--brand] rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[--brand-ring] ${isSaving ? "animate-pulse" : ""}`}
                            autoFocus
                            // eslint-disable-next-line jsx-a11y/no-autofocus
                          />
                        )}
                        {saveError && (
                          <p className="text-xs text-[--danger]">
                            {saveError}
                          </p>
                        )}
                      </div>
                    ) : (
                      <span
                        className={`block min-w-[60px] ${editMode ? "cursor-pointer hover:bg-[--surface-3] rounded px-1 -mx-1 transition-colors" : ""}`}
                        onClick={() =>
                          handleCellClick(row.id, ci, value)
                        }
                        title={editMode ? "Click to edit" : undefined}
                      >
                        {value || (
                          <span className="text-[--text-disabled] italic">
                            Empty
                          </span>
                        )}
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {/* Mobile card stack */}
      <div className="md:hidden flex flex-col gap-3">
        {sortedRows.map((row) => (
          <div
            key={row.id}
            className="rounded-lg border border-[--border] bg-[--surface-1] p-3 flex flex-col gap-2"
          >
            {headers.map((header, ci) => {
              const cellKey = `${viewIndex}-${row.id}-${ci}`;
              const isEditing = editMode && editingCell === cellKey;
              const value = row[header] ?? "";

              return (
                <div
                  key={`${row.id}-${header}`}
                  className="flex items-start gap-2"
                >
                  <span className="text-xs font-medium text-[--text-secondary] w-28 shrink-0 pt-0.5">
                    {header}
                  </span>
                  {isEditing ? (
                    <input
                      type="text"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={() => handleSave(row.id, ci)}
                      onKeyDown={(e) => handleKeyDown(e, row.id, ci)}
                      className={`flex-1 min-w-0 bg-[--surface-1] border border-[--brand] rounded px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-[--brand-ring] ${isSaving ? "animate-pulse" : ""}`}
                      autoFocus
                      // eslint-disable-next-line jsx-a11y/no-autofocus
                    />
                  ) : (
                    <span
                      className={`flex-1 min-w-0 text-sm ${editMode ? "cursor-pointer hover:bg-[--surface-3] rounded px-1 -mx-1 transition-colors" : ""}`}
                      onClick={() =>
                        handleCellClick(row.id, ci, value)
                      }
                      title={editMode ? "Click to edit" : undefined}
                    >
                      {value || (
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
        ))}
      </div>
    </div>
  );
}
