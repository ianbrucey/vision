"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Upload, Search, Loader2, X, FileText, ChevronDown, ChevronUp, Trash2, ExternalLink, PanelLeft } from "lucide-react";
import {
  querySamNotices,
  uploadSamNoticesCsv,
  listSamNoticeBatches,
  deleteSamNoticeBatch,
  lookupSolicitationUrl,
  deleteSamNotice,
  deleteAllSamNotices,
  processBatch,
  type SamNotice,
  type SamNoticesQuery,
  type SamNoticeBatch,
  type ProcessBatchResult,
  type SavedReport,
} from "@/lib/api";
import ReportsSidebar from "@/components/ReportsSidebar";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface SamNoticesTabProps {
  caseId: number | null;
}

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const OPPORTUNITY_TYPES = [
  "Combined Synopsis/Solicitation",
  "Sources Sought",
  "Award Notice",
  "Presolicitation",
  "Special Notice",
  "Justification",
];

const SET_ASIDE_CODES = ["SBA", "SDVOSBC", "WOSB", "HZC", "8A", "NONE"];

const PAGE_SIZE = 50;

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function SamNoticesTab({ caseId }: SamNoticesTabProps) {
  /* ---- state ---- */
  const [results, setResults] = useState<SamNotice[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  // Search filters
  const [q, setQ] = useState("");
  const [filters, setFilters] = useState<SamNoticesQuery>({ limit: PAGE_SIZE });
  const [showFilters, setShowFilters] = useState(false);

  // Upload
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [batches, setBatches] = useState<SamNoticeBatch[]>([]);
  const [showBatches, setShowBatches] = useState(false);
  const [lastBatchId, setLastBatchId] = useState<string | null>(null);

  // Pipeline processing
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<ProcessBatchResult | null>(null);

  // Expanded row
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showReports, setShowReports] = useState(false);
  const [activeReport, setActiveReport] = useState<SavedReport | null>(null);

  /* ---- fetch ---- */

  const search = useCallback(async (newOffset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const body: SamNoticesQuery = {
        ...filters,
        q: q.trim() || undefined,
        limit: PAGE_SIZE,
        offset: newOffset,
      };
      const data = await querySamNotices(body);
      setResults(data.results);
      setTotal(data.total);
      setOffset(newOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  }, [q, filters]);

  useEffect(() => {
    search(0);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const refreshBatches = useCallback(async () => {
    try {
      const data = await listSamNoticeBatches();
      setBatches(data.batches);
      // Auto-select most recent batch so the Filter button survives refresh
      if (data.batches.length > 0 && !lastBatchId) {
        setLastBatchId(data.batches[0].batch_id);
      }
    } catch { /* silent */ }
  }, [lastBatchId]);

  useEffect(() => {
    refreshBatches();
  }, [refreshBatches]);

  /* ---- handlers ---- */

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    try {
      const result = await uploadSamNoticesCsv(file);
      const dupMsg = result.duplicates_skipped > 0
        ? ` (${result.duplicates_skipped.toLocaleString()} duplicates skipped)`
        : "";
      setUploadMsg(`✅ ${result.rows_inserted.toLocaleString()} new rows from ${result.source}${dupMsg}`);
      setLastBatchId(result.batch_id);
      setProcessResult(null);
      refreshBatches();
      search(0);
    } catch (err) {
      setUploadMsg(`❌ ${err instanceof Error ? err.message : "Upload failed"}`);
    } finally {
      setUploading(false);
      if (e.target) e.target.value = "";
    }
  };

  const handleDeleteBatch = async (batchId: string) => {
    try {
      await deleteSamNoticeBatch(batchId);
      refreshBatches();
      search(0);
    } catch { /* silent */ }
  };

  const handleProcess = async (batchId: string) => {
    setProcessing(true);
    setProcessResult(null);
    try {
      const result = await processBatch(batchId, false);
      setProcessResult(result);
      setUploadMsg(
        `Pipeline: ${result.queued} solicitations created, ${result.skipped} skipped, ${result.duplicate} duplicates`
      );
    } catch (err) {
      setUploadMsg(`❌ Pipeline failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setProcessing(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    search(0);
  };

  const handleFilterChange = (key: string, value: string | undefined) => {
    setFilters((prev) => ({ ...prev, [key]: value || undefined }));
  };

  const clearFilters = () => {
    setQ("");
    setFilters({ limit: PAGE_SIZE });
  };

  const handleSelectReport = (report: SavedReport) => {
    setActiveReport(report);
    const f = report.query_filters;
    setQ((f.q as string) || "");
    setFilters({
      q: f.q as string | undefined,
      naics_code: f.naics_code as string | undefined,
      current_set_aside_code: f.current_set_aside_code as string | undefined,
      current_set_aside: f.current_set_aside as string | undefined,
      contract_opportunity_type: f.contract_opportunity_type as string | undefined,
      sub_tier_name: f.sub_tier_name as string | undefined,
      pop_state: f.pop_state as string | undefined,
      pop_city: f.pop_city as string | undefined,
      status: f.status as string | undefined,
      has_attachments: f.has_attachments as boolean | undefined,
      response_date_from: f.response_date_from as string | undefined,
      response_date_to: f.response_date_to as string | undefined,
      limit: PAGE_SIZE,
      order_by: (report.sort_by as string) || undefined,
      order_dir: (report.sort_dir as "ASC" | "DESC") || undefined,
    });
    search(0);
  };

  /* ---- render ---- */

  return (
    <div className="flex-1 flex min-h-0">
      {showReports && (
        <ReportsSidebar
          caseId={caseId}
          dataSource="sam_notices"
          onSelectReport={handleSelectReport}
          activeReportId={activeReport?.id || null}
          currentFilters={{ ...filters, q: q.trim() || undefined }}
        />
      )}
      <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-border flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowReports(prev => !prev)}
            className={`p-1.5 rounded transition-colors ${showReports ? "text-brand bg-brand-bg" : "text-text-disabled hover:text-text-primary"}`}
            title="Toggle reports sidebar"
          >
            <PanelLeft size={16} />
          </button>
          <div>
            <p className="text-sm font-medium text-text-primary">SAM.gov Databank</p>
            <p className="text-xs text-text-disabled">
              Search federal contract opportunities from imported SAM.gov CSV exports.
            </p>
          </div>
        </div>
        {total > 0 && (
          <button
            onClick={async () => {
              if (!confirm(`Delete all ${total.toLocaleString()} notices? This cannot be undone.`)) return;
              try {
                const result = await deleteAllSamNotices();
                setUploadMsg(`✅ Deleted ${result.deleted.toLocaleString()} notices`);
                search(0);
                refreshBatches();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Delete failed");
              }
            }}
            className="shrink-0 px-3 py-1.5 text-xs text-danger border border-danger/30 rounded
                       hover:bg-danger-bg transition-colors"
          >
            <Trash2 size={12} className="inline mr-1" />
            Delete All
          </button>
        )}
      </div>

      {/* Search bar */}
      <div className="shrink-0 px-4 py-3 border-b border-border bg-surface-1">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-disabled" />
            <input
              type="text"
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Full-text search — title, description, NAICS, agency..."
              className="w-full pl-9 pr-3 py-2 text-sm bg-surface-2 border border-border rounded-lg
                         text-text-primary placeholder:text-text-disabled outline-none
                         focus:border-brand"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 text-sm bg-brand text-white rounded-lg hover:opacity-90 transition-opacity"
          >
            Search
          </button>
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className={`px-3 py-2 text-sm border rounded-lg transition-colors ${
              showFilters ? "border-brand text-brand bg-brand-bg" : "border-border text-text-secondary hover:text-text-primary"
            }`}
          >
            Filters
          </button>
          <label className={`px-3 py-2 text-sm border border-border rounded-lg cursor-pointer
                            text-text-secondary hover:text-text-primary transition-colors
                            ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
            {uploading ? (
              <><Loader2 size={14} className="inline mr-1 animate-spin" /> Uploading...</>
            ) : (
              <><Upload size={14} className="inline mr-1" /> Upload CSV</>
            )}
            <input type="file" accept=".csv" onChange={handleUpload} className="hidden" disabled={uploading} />
          </label>

          {lastBatchId && (
            <button
              onClick={() => handleProcess(lastBatchId)}
              disabled={processing}
              className="px-3 py-2 text-sm border border-border rounded-lg
                         text-text-secondary hover:text-text-primary transition-colors
                         disabled:opacity-50"
            >
              {processing ? (
                <><Loader2 size={14} className="inline mr-1 animate-spin" /> Processing...</>
              ) : (
                "Filter → Solicitations"
              )}
            </button>
          )}
        </form>

        {uploadMsg && (
          <div className={`mt-2 text-xs ${uploadMsg.startsWith("✅") || uploadMsg.startsWith("Pipeline") ? "text-success" : "text-danger"}`}>
            {uploadMsg}
          </div>
        )}

        {processResult && (
          <div className="mt-2 p-2 bg-surface-50 border border-border rounded-md text-xs">
            <div className="flex gap-3">
              <span className="text-success font-medium">{processResult.queued} queued</span>
              <span className="text-text-secondary">{processResult.skipped} skipped</span>
              <span className="text-text-tertiary">{processResult.duplicate} duplicates</span>
            </div>
            <div className="mt-1 flex flex-wrap gap-1 text-text-tertiary">
              {Object.entries(processResult.skipped_breakdown).map(([reason, count]) => (
                <span key={reason} className="bg-white px-1.5 py-0.5 rounded border border-border">
                  {reason}: {count}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Filters panel */}
      {showFilters && (
        <div className="shrink-0 px-4 py-3 border-b border-border bg-surface-2">
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
            <FilterSelect
              label="Opportunity Type"
              value={filters.contract_opportunity_type || ""}
              onChange={(v) => handleFilterChange("contract_opportunity_type", v)}
              options={OPPORTUNITY_TYPES}
            />
            <FilterSelect
              label="Set-Aside Code"
              value={filters.current_set_aside_code || ""}
              onChange={(v) => handleFilterChange("current_set_aside_code", v)}
              options={SET_ASIDE_CODES}
            />
            <FilterInput
              label="NAICS Code"
              value={filters.naics_code || ""}
              onChange={(v) => handleFilterChange("naics_code", v)}
              placeholder="e.g. 541511"
            />
            <FilterInput
              label="PSC Code"
              value={filters.psc_code || ""}
              onChange={(v) => handleFilterChange("psc_code", v)}
              placeholder="e.g. 2330"
            />
            <FilterInput
              label="State"
              value={filters.pop_state || ""}
              onChange={(v) => handleFilterChange("pop_state", v)}
              placeholder="e.g. VA"
            />
            <FilterInput
              label="Agency"
              value={filters.sub_tier_name || ""}
              onChange={(v) => handleFilterChange("sub_tier_name", v)}
              placeholder="e.g. DEPT OF THE ARMY"
            />
            <FilterInput
              label="Status"
              value={filters.status || ""}
              onChange={(v) => handleFilterChange("status", v)}
              placeholder="active"
            />
            <FilterInput
              label="Response Date From"
              value={filters.response_date_from || ""}
              onChange={(v) => handleFilterChange("response_date_from", v)}
              placeholder="2026-07-01"
            />
            <FilterInput
              label="Response Date To"
              value={filters.response_date_to || ""}
              onChange={(v) => handleFilterChange("response_date_to", v)}
              placeholder="2026-08-31"
            />
            <label className="flex items-center gap-2 text-xs text-text-secondary pt-5">
              <input
                type="checkbox"
                checked={!!filters.has_attachments}
                onChange={(e) => handleFilterChange("has_attachments", e.target.checked ? "true" : undefined)}
                className="rounded"
              />
              Has attachments
            </label>
          </div>
          <div className="flex gap-2 mt-3">
            <button
              onClick={() => search(0)}
              className="px-3 py-1.5 text-xs bg-brand text-white rounded hover:opacity-90"
            >
              Apply Filters
            </button>
            <button
              onClick={clearFilters}
              className="px-3 py-1.5 text-xs border border-border text-text-secondary rounded hover:text-text-primary"
            >
              Clear All
            </button>
          </div>
        </div>
      )}

      {/* Batches bar */}
      {batches.length > 0 && (
        <div className="shrink-0 px-4 py-1.5 border-b border-border bg-surface-2 flex items-center gap-2 text-xs">
          <button
            onClick={() => setShowBatches(!showBatches)}
            className="text-text-secondary hover:text-text-primary flex items-center gap-1"
          >
            <FileText size={12} />
            {batches.length} upload batch{batches.length > 1 ? "es" : ""}
            {" "}({batches.reduce((sum, b) => sum + b.rows, 0).toLocaleString()} total rows)
            {showBatches ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          </button>
          {showBatches && (
            <div className="flex gap-2 ml-2">
              {batches.map((b) => (
                <span key={b.batch_id} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-surface-1 border border-border">
                  {b.source} ({b.rows.toLocaleString()} rows)
                  <button onClick={() => handleDeleteBatch(b.batch_id)} className="text-text-disabled hover:text-danger">
                    <X size={10} />
                  </button>
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="shrink-0 px-4 py-2 text-xs text-danger bg-danger-bg">{error}</div>
      )}

      {/* Results table */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="animate-spin text-text-disabled" size={24} />
          </div>
        ) : results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-text-disabled">
            <Search size={32} strokeWidth={1.5} />
            <p className="text-sm">
              {batches.length === 0
                ? "Upload a SAM.gov databank CSV to get started."
                : "No results match your search."}
            </p>
            {batches.length === 0 && (
              <label className="px-4 py-2 text-sm bg-brand text-white rounded-lg cursor-pointer hover:opacity-90">
                Upload CSV
                <input type="file" accept=".csv" onChange={handleUpload} className="hidden" />
              </label>
            )}
          </div>
        ) : (
          <div>
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-1 border-b border-border z-10">
                <tr className="text-left text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
                  <th className="px-3 py-2 w-8"></th>
                  <th className="px-3 py-2">Title</th>
                  <th className="px-3 py-2 hidden md:table-cell">Type</th>
                  <th className="px-3 py-2 hidden lg:table-cell">NAICS</th>
                  <th className="px-3 py-2 hidden lg:table-cell">Set-Aside</th>
                  <th className="px-3 py-2 hidden md:table-cell">Agency</th>
                  <th className="px-3 py-2 hidden xl:table-cell">Response Date</th>
                  <th className="px-3 py-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {results.map((notice) => (
                  <React.Fragment key={notice.id}>
                    <tr
                      className="hover:bg-surface-2 transition-colors cursor-pointer"
                      onClick={() => setExpandedId(expandedId === notice.id ? null : notice.id)}
                    >
                      <td className="px-3 py-2">
                        {expandedId === notice.id ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
                      </td>
                      <td className="px-3 py-2 max-w-[300px]">
                        <p className="font-medium text-text-primary truncate" title={notice.opportunity_title}>
                          {notice.opportunity_title}
                        </p>
                        {notice.notice_id && (
                          <a
                            href={`https://sam.gov/search?index=opp&keywords=${encodeURIComponent(notice.notice_id)}&sort=-modifiedDate`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={async (e) => {
                              e.preventDefault();
                              try {
                                const result = await lookupSolicitationUrl(notice.notice_id!);
                                window.open(result.ui_link, "_blank", "noopener,noreferrer");
                              } catch {
                                // Fallback: open the search link directly
                                window.open(e.currentTarget.getAttribute("href")!, "_blank", "noopener,noreferrer");
                              }
                            }}
                            className="text-[11px] text-brand hover:underline inline-flex items-center gap-1"
                          >
                            {notice.notice_id}
                            <ExternalLink size={10} />
                          </a>
                        )}
                      </td>
                      <td className="px-3 py-2 hidden md:table-cell text-text-secondary text-xs">
                        {notice.contract_opportunity_type || "—"}
                      </td>
                      <td className="px-3 py-2 hidden lg:table-cell text-text-secondary text-xs">
                        {notice.naics_code ? `${notice.naics_code}` : "—"}
                      </td>
                      <td className="px-3 py-2 hidden lg:table-cell text-text-secondary text-xs">
                        {notice.current_set_aside_code || "—"}
                      </td>
                      <td className="px-3 py-2 hidden md:table-cell text-text-secondary text-xs max-w-[150px] truncate">
                        {notice.sub_tier_name || notice.contracting_office || "—"}
                      </td>
                      <td className="px-3 py-2 hidden xl:table-cell text-text-secondary text-xs">
                        {notice.current_response_date
                          ? new Date(notice.current_response_date).toLocaleDateString()
                          : "—"}
                      </td>
                      <td className="px-3 py-2">
                        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${
                          notice.status === "active"
                            ? "bg-success-bg text-success"
                            : "bg-surface-2 text-text-disabled"
                        }`}>
                          {notice.status || "—"}
                        </span>
                      </td>
                    </tr>
                    {expandedId === notice.id && (
                      <tr key={`${notice.id}-expanded`}>
                        <td colSpan={8} className="px-6 py-3 bg-surface-2">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                            {notice.description && (
                              <div className="col-span-full">
                                <span className="font-medium text-text-primary">Description:</span>
                                <p className="text-text-secondary mt-0.5 whitespace-pre-wrap">
                                  {notice.description.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim().slice(0, 800)}
                                </p>
                              </div>
                            )}
                            {notice.naics_description && (
                              <div>
                                <span className="font-medium text-text-primary">NAICS Desc:</span>
                                <p className="text-text-secondary">{notice.naics_description}</p>
                              </div>
                            )}
                            {notice.psc_code && (
                              <div>
                                <span className="font-medium text-text-primary">PSC:</span>
                                <p className="text-text-secondary">{notice.psc_code}</p>
                              </div>
                            )}
                            {notice.pop_city && (
                              <div>
                                <span className="font-medium text-text-primary">Location:</span>
                                <p className="text-text-secondary">
                                  {[notice.pop_city, notice.pop_state, notice.pop_country].filter(Boolean).join(", ")}
                                </p>
                              </div>
                            )}
                            {notice.poc_name && (
                              <div>
                                <span className="font-medium text-text-primary">POC:</span>
                                <p className="text-text-secondary">{notice.poc_name}</p>
                                {notice.poc_email && <p className="text-text-disabled">{notice.poc_email}</p>}
                              </div>
                            )}
                            {notice.awardee_name && (
                              <div>
                                <span className="font-medium text-text-primary">Awardee:</span>
                                <p className="text-text-secondary">{notice.awardee_name}</p>
                              </div>
                            )}
                            {notice.attachment_count != null && (
                              <div>
                                <span className="font-medium text-text-primary">Attachments:</span>
                                <p className="text-text-secondary">{notice.attachment_count}</p>
                              </div>
                            )}
                            {notice.contracting_office && (
                              <div>
                                <span className="font-medium text-text-primary">Office:</span>
                                <p className="text-text-secondary">{notice.contracting_office}</p>
                              </div>
                            )}
                            {notice.last_published_date && (
                              <div>
                                <span className="font-medium text-text-primary">Published:</span>
                                <p className="text-text-secondary">
                                  {new Date(notice.last_published_date).toLocaleDateString()}
                                </p>
                              </div>
                            )}
                          </div>
                          <div className="mt-3 pt-3 border-t border-border flex justify-end">
                            <button
                              onClick={async (e) => {
                                e.stopPropagation();
                                if (!confirm("Delete this notice?")) return;
                                try {
                                  await deleteSamNotice(notice.id);
                                  search(offset);
                                } catch (err) {
                                  setError(err instanceof Error ? err.message : "Delete failed");
                                }
                              }}
                              className="px-2 py-1 text-[11px] text-danger border border-danger/30 rounded
                                         hover:bg-danger-bg transition-colors"
                            >
                              <Trash2 size={10} className="inline mr-1" />
                              Delete
                            </button>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="shrink-0 px-4 py-2 border-t border-border flex items-center justify-between text-xs text-text-secondary">
          <span>
            Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total.toLocaleString()}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => search(Math.max(0, offset - PAGE_SIZE))}
              disabled={offset === 0}
              className="px-3 py-1 border border-border rounded hover:bg-surface-2 disabled:opacity-50"
            >
              Previous
            </button>
            <button
              onClick={() => search(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= total}
              className="px-3 py-1 border border-border rounded hover:bg-surface-2 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Mini filter components                                             */
/* ------------------------------------------------------------------ */

function FilterSelect({
  label, value, onChange, options,
}: {
  label: string; value: string; onChange: (v: string) => void; options: string[];
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold text-text-disabled uppercase">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs bg-surface-1 border border-border rounded px-2 py-1.5 text-text-primary"
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>{o}</option>
        ))}
      </select>
    </label>
  );
}

function FilterInput({
  label, value, onChange, placeholder,
}: {
  label: string; value: string; onChange: (v: string) => void; placeholder: string;
}) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold text-text-disabled uppercase">{label}</span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="text-xs bg-surface-1 border border-border rounded px-2 py-1.5 text-text-primary
                   placeholder:text-text-disabled outline-none focus:border-brand"
      />
    </label>
  );
}
