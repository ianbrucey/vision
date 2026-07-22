"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, X, Loader2, FileText, Trash2 } from "lucide-react";
import { listReports, createReport, deleteReport, type SavedReport } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface ReportsSidebarProps {
  /** Case ID for scoped reports, or null for global (Reference Desk) reports. */
  caseId: number | null;
  dataSource: "forecasts" | "sam_notices";
  /** Called when user clicks a report — passes the stored filters to apply */
  onSelectReport: (report: SavedReport) => void;
  /** Currently active report ID */
  activeReportId: number | null;
  /** Current filter state — captured when creating a new report */
  currentFilters: Record<string, unknown>;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function ReportsSidebar({
  caseId,
  dataSource,
  onSelectReport,
  activeReportId,
  currentFilters,
}: ReportsSidebarProps) {
  const [reports, setReports] = useState<SavedReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [newName, setNewName] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const data = await listReports(caseId, dataSource);
      setReports(data.reports);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reports");
    } finally {
      setLoading(false);
    }
  }, [caseId, dataSource]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleCreate = async () => {
    const name = newName.trim();
    if (!name) return;
    setSaving(true);
    try {
      await createReport({
        case_id: caseId ?? null,
        name,
        data_source: dataSource,
        query_filters: currentFilters,
      });
      setNewName("");
      setShowNew(false);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create report");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this report?")) return;
    try {
      await deleteReport(id);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  return (
    <div className="w-52 shrink-0 border-r border-border bg-surface-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-3 py-2.5 border-b border-border flex items-center justify-between">
        <span className="text-[11px] font-semibold text-text-disabled uppercase tracking-wide">
          Reports
        </span>
        <button
          onClick={() => setShowNew(!showNew)}
          className="text-text-disabled hover:text-brand transition-colors"
          title="Save current filters as report"
        >
          <Plus size={14} />
        </button>
      </div>

      {/* New report form */}
      {showNew && (
        <div className="shrink-0 px-3 py-2 border-b border-border bg-surface-2">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") handleCreate(); }}
            placeholder="Report name..."
            autoFocus
            className="w-full text-xs bg-surface-1 border border-border rounded px-2 py-1.5
                       text-text-primary placeholder:text-text-disabled outline-none focus:border-brand"
          />
          <div className="flex gap-1 mt-1.5">
            <button
              onClick={handleCreate}
              disabled={!newName.trim() || saving}
              className="flex-1 text-[11px] px-2 py-1 bg-brand text-white rounded
                         hover:opacity-90 disabled:opacity-50 transition-opacity"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={() => { setShowNew(false); setNewName(""); }}
              className="text-[11px] px-2 py-1 border border-border rounded text-text-secondary
                         hover:text-text-primary transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && (
        <div className="shrink-0 px-3 py-1.5 text-[10px] text-danger bg-danger-bg">{error}</div>
      )}

      {/* Report list */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="animate-spin text-text-disabled" size={16} />
          </div>
        ) : reports.length === 0 ? (
          <div className="px-3 py-6 text-center text-[11px] text-text-disabled">
            <FileText size={18} className="mx-auto mb-2 text-text-disabled" strokeWidth={1.5} />
            No saved reports.<br />
            Set filters and click <Plus size={10} className="inline text-text-disabled" /> to save.
          </div>
        ) : (
          reports.map((r) => (
            <div
              key={r.id}
              onClick={() => onSelectReport(r)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => { if (e.key === "Enter") onSelectReport(r); }}
              className={`w-full text-left px-3 py-2 text-xs flex items-center gap-2
                         transition-colors group cursor-pointer
                         ${r.id === activeReportId
                           ? "bg-brand-bg text-brand border-r-2 border-brand"
                           : "text-text-secondary hover:text-text-primary hover:bg-surface-2"}`}
            >
              <FileText size={12} className="shrink-0 text-text-disabled" />
              <span className="truncate flex-1">{r.name}</span>
              <span
                onClick={(e) => handleDelete(r.id, e)}
                className="opacity-0 group-hover:opacity-100 text-text-disabled hover:text-danger
                           transition-all shrink-0 cursor-pointer"
                title="Delete report"
                role="button"
                tabIndex={0}
              >
                <X size={11} />
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
