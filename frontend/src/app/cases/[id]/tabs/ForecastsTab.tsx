"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Upload, Search, Loader2, X, ChevronDown, ChevronUp, Trash2, ExternalLink, PanelLeft } from "lucide-react";
import {
  queryForecasts,
  uploadForecastHtml,
  deleteAllForecasts,
  deleteForecast,
  type ForecastOpportunity,
  type ForecastQuery,
  type SavedReport,
} from "@/lib/api";
import ReportsSidebar from "@/components/ReportsSidebar";

interface ForecastsTabProps { caseId: number; }

const PAGE_SIZE = 50;

export default function ForecastsTab({ caseId }: ForecastsTabProps) {
  const [results, setResults] = useState<ForecastOpportunity[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  const [q, setQ] = useState("");
  const [filters, setFilters] = useState<ForecastQuery>({ limit: PAGE_SIZE });
  const [showFilters, setShowFilters] = useState(false);

  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [showReports, setShowReports] = useState(false);
  const [activeReport, setActiveReport] = useState<SavedReport | null>(null);

  const search = useCallback(async (newOffset = 0) => {
    setLoading(true); setError(null);
    try {
      const body: ForecastQuery = { ...filters, q: q.trim() || undefined, limit: PAGE_SIZE, offset: newOffset };
      const data = await queryForecasts(body);
      setResults(data.results); setTotal(data.total); setOffset(newOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally { setLoading(false); }
  }, [q, filters]);

  useEffect(() => { search(0); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]; if (!file) return;
    setUploading(true); setUploadMsg(null);
    try {
      const result = await uploadForecastHtml(file);
      setUploadMsg(`✅ Imported ${result.rows_inserted.toLocaleString()} forecasts from ${result.source}`);
      search(0);
    } catch (err) {
      setUploadMsg(`❌ ${err instanceof Error ? err.message : "Upload failed"}`);
    } finally { setUploading(false); if (e.target) e.target.value = ""; }
  };

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); search(0); };
  const handleFilterChange = (key: string, value: string | undefined) => {
    if ((key === "value_under" || key === "value_over") && value) {
      const num = parseFloat(value);
      setFilters(prev => ({ ...prev, [key]: isNaN(num) ? undefined : num }));
    } else {
      setFilters(prev => ({ ...prev, [key]: value || undefined }));
    }
  };
  const clearFilters = () => { setQ(""); setFilters({ limit: PAGE_SIZE }); };

  const handleSelectReport = (report: SavedReport) => {
    setActiveReport(report);
    const f = report.query_filters as ForecastQuery;
    setQ((f.q as string) || "");
    setFilters({
      agency: f.agency as string | undefined,
      naics_code: f.naics_code as string | undefined,
      set_aside: f.set_aside as string | undefined,
      fiscal_year: f.fiscal_year as string | undefined,
      estimated_value_text: f.estimated_value_text as string | undefined,
      value_under: f.value_under as number | undefined,
      value_over: f.value_over as number | undefined,
      office: f.office as string | undefined,
      place_of_performance: f.place_of_performance as string | undefined,
      limit: PAGE_SIZE,
      order_by: (report.sort_by as string) || undefined,
      order_dir: (report.sort_dir as "ASC" | "DESC") || undefined,
    });
    search(0);
  };

  return (
    <div className="flex-1 flex min-h-0">
      {showReports && (
        <ReportsSidebar
          caseId={caseId}
          dataSource="forecasts"
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
            <p className="text-sm font-medium text-text-primary">Acquisition Forecasts</p>
            <p className="text-xs text-text-disabled">Future procurement projections from the Acquisition Gateway forecast tool.</p>
          </div>
        </div>
        {total > 0 && (
          <button onClick={async () => {
            if (!confirm(`Delete all ${total.toLocaleString()} forecasts?`)) return;
            try { await deleteAllForecasts(); search(0); } catch (err) { setError(err instanceof Error ? err.message : "Delete failed"); }
          }} className="shrink-0 px-3 py-1.5 text-xs text-danger border border-danger/30 rounded hover:bg-danger-bg transition-colors">
            <Trash2 size={12} className="inline mr-1" />Delete All
          </button>
        )}
      </div>

      {/* Search bar */}
      <div className="shrink-0 px-4 py-3 border-b border-border bg-surface-1">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="flex-1 relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-disabled" />
            <input type="text" value={q} onChange={e => setQ(e.target.value)}
              placeholder="Full-text search — title, description, agency..."
              className="w-full pl-9 pr-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary placeholder:text-text-disabled outline-none focus:border-brand" />
          </div>
          <button type="submit" className="px-4 py-2 text-sm bg-brand text-white rounded-lg hover:opacity-90">Search</button>
          <button type="button" onClick={() => setShowFilters(!showFilters)}
            className={`px-3 py-2 text-sm border rounded-lg transition-colors ${showFilters ? "border-brand text-brand bg-brand-bg" : "border-border text-text-secondary hover:text-text-primary"}`}>Filters</button>
          <label className={`px-3 py-2 text-sm border border-border rounded-lg cursor-pointer text-text-secondary hover:text-text-primary ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
            <Upload size={14} className="inline mr-1" />Upload HTML
            <input type="file" accept=".html,.htm" onChange={handleUpload} className="hidden" />
          </label>
        </form>
        {uploadMsg && <div className={`mt-2 text-xs ${uploadMsg.startsWith("✅") ? "text-success" : "text-danger"}`}>{uploadMsg}</div>}
      </div>

      {/* Filters */}
      {showFilters && (
        <div className="shrink-0 px-4 py-3 border-b border-border bg-surface-2">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <FilterInput label="Agency" value={filters.agency || ""} onChange={v => handleFilterChange("agency", v)} placeholder="e.g. Department of Labor" />
            <FilterInput label="NAICS Code" value={filters.naics_code || ""} onChange={v => handleFilterChange("naics_code", v)} placeholder="e.g. 541511" />
            <FilterInput label="Set-Aside" value={filters.set_aside || ""} onChange={v => handleFilterChange("set_aside", v)} placeholder="e.g. Small Business" />
            <FilterInput label="Fiscal Year" value={filters.fiscal_year || ""} onChange={v => handleFilterChange("fiscal_year", v)} placeholder="e.g. 2026" />
            <FilterInput label="Value Text" value={filters.estimated_value_text || ""} onChange={v => handleFilterChange("estimated_value_text", v)} placeholder="e.g. Below $150K" />
            <FilterInput label="Value ≤" value={filters.value_under?.toString() || ""} onChange={v => handleFilterChange("value_under", v)} placeholder="e.g. 350000" />
            <FilterInput label="Value ≥" value={filters.value_over?.toString() || ""} onChange={v => handleFilterChange("value_over", v)} placeholder="e.g. 1000000" />
            <FilterInput label="Office" value={filters.office || ""} onChange={v => handleFilterChange("office", v)} placeholder="e.g. OSHA" />
          </div>
          <div className="flex gap-2 mt-3">
            <button onClick={() => search(0)} className="px-3 py-1.5 text-xs bg-brand text-white rounded hover:opacity-90">Apply Filters</button>
            <button onClick={clearFilters} className="px-3 py-1.5 text-xs border border-border text-text-secondary rounded hover:text-text-primary">Clear All</button>
          </div>
        </div>
      )}

      {error && <div className="shrink-0 px-4 py-2 text-xs text-danger bg-danger-bg">{error}</div>}

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin text-text-disabled" size={24} /></div>
        ) : results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-text-disabled">
            <Search size={32} strokeWidth={1.5} />
            <p className="text-sm">{total === 0 ? "Upload a rendered forecast HTML page to get started." : "No results match."}</p>
            {total === 0 && (
              <label className="px-4 py-2 text-sm bg-brand text-white rounded-lg cursor-pointer hover:opacity-90">
                Upload HTML <input type="file" accept=".html,.htm" onChange={handleUpload} className="hidden" />
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
                  <th className="px-3 py-2 hidden md:table-cell">Agency</th>
                  <th className="px-3 py-2 hidden lg:table-cell">NAICS</th>
                  <th className="px-3 py-2 hidden lg:table-cell">Set-Aside</th>
                  <th className="px-3 py-2 hidden md:table-cell">Value</th>
                  <th className="px-3 py-2 hidden xl:table-cell">FY</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {results.map((f) => (
                  <React.Fragment key={f.id}>
                    <tr className="hover:bg-surface-2 transition-colors cursor-pointer" onClick={() => setExpandedId(expandedId === f.id ? null : f.id)}>
                      <td className="px-3 py-2">{expandedId === f.id ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</td>
                      <td className="px-3 py-2 max-w-[300px]">
                        <p className="font-medium text-text-primary truncate" title={f.title}>{f.title}</p>
                        {f.source_url && (
                          <a href={`https://acquisitiongateway.gov${f.source_url}`} target="_blank" rel="noopener noreferrer"
                            onClick={e => e.stopPropagation()}
                            className="text-[11px] text-brand hover:underline inline-flex items-center gap-1">
                            View <ExternalLink size={10} />
                          </a>
                        )}
                      </td>
                      <td className="px-3 py-2 hidden md:table-cell text-text-secondary text-xs max-w-[150px] truncate">{f.agency || "—"}</td>
                      <td className="px-3 py-2 hidden lg:table-cell text-text-secondary text-xs">{f.naics_code ? `${f.naics_code}` : "—"}</td>
                      <td className="px-3 py-2 hidden lg:table-cell text-text-secondary text-xs">{f.set_aside || "—"}</td>
                      <td className="px-3 py-2 hidden md:table-cell text-text-secondary text-xs">
                        {f.estimated_value_low != null || f.estimated_value_high != null
                          ? formatValue(f.estimated_value_low, f.estimated_value_high)
                          : f.estimated_value_text || "—"}
                      </td>
                      <td className="px-3 py-2 hidden xl:table-cell text-text-secondary text-xs">{f.fiscal_year || "—"}</td>
                    </tr>
                    {expandedId === f.id && (
                      <tr key={`${f.id}-expanded`}>
                        <td colSpan={7} className="px-6 py-3 bg-surface-2">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                            {f.description && (
                              <div className="col-span-full"><span className="font-medium text-text-primary">Description:</span><p className="text-text-secondary mt-0.5 whitespace-pre-wrap">{f.description.slice(0, 800)}</p></div>
                            )}
                            {f.naics_description && <div><span className="font-medium text-text-primary">NAICS Desc:</span><p className="text-text-secondary">{f.naics_description}</p></div>}
                            {f.office && <div><span className="font-medium text-text-primary">Office:</span><p className="text-text-secondary">{f.office}</p></div>}
                            {f.place_of_performance && <div><span className="font-medium text-text-primary">Location:</span><p className="text-text-secondary">{f.place_of_performance}</p></div>}
                            {f.period_of_performance && <div><span className="font-medium text-text-primary">Period:</span><p className="text-text-secondary">{f.period_of_performance}</p></div>}
                            {f.created_date && <div><span className="font-medium text-text-primary">Created:</span><p className="text-text-secondary">{f.created_date}</p></div>}
                            {f.last_updated_date && <div><span className="font-medium text-text-primary">Updated:</span><p className="text-text-secondary">{f.last_updated_date}</p></div>}
                          </div>
                          <div className="mt-3 pt-3 border-t border-border flex justify-end">
                            <button onClick={async (e) => { e.stopPropagation(); if (!confirm("Delete?")) return; try { await deleteForecast(f.id); search(offset); } catch (err) { setError(err instanceof Error ? err.message : "Delete failed"); } }}
                              className="px-2 py-1 text-[11px] text-danger border border-danger/30 rounded hover:bg-danger-bg"><Trash2 size={10} className="inline mr-1" />Delete</button>
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

      {total > PAGE_SIZE && (
        <div className="shrink-0 px-4 py-2 border-t border-border flex items-center justify-between text-xs text-text-secondary">
          <span>Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total.toLocaleString()}</span>
          <div className="flex gap-1">
            <button onClick={() => search(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0} className="px-3 py-1 border border-border rounded hover:bg-surface-2 disabled:opacity-50">Previous</button>
            <button onClick={() => search(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total} className="px-3 py-1 border border-border rounded hover:bg-surface-2 disabled:opacity-50">Next</button>
          </div>
        </div>
      )}
    </div>
    </div>
  );
}

function formatValue(low: number | null, high: number | null): string {
  const fmt = (n: number) => {
    if (n >= 1_000_000_000) return `$${(n / 1_000_000_000).toFixed(1)}B`;
    if (n >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
    if (n >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
    return `$${n}`;
  };
  if (low == null && high == null) return "—";
  if (low === 0) return `≤ ${fmt(high!)}`;
  if (high == null) return `≥ ${fmt(low!)}`;
  return `${fmt(low!)} – ${fmt(high!)}`;
}

function FilterInput({ label, value, onChange, placeholder }: { label: string; value: string; onChange: (v: string) => void; placeholder: string }) {
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold text-text-disabled uppercase">{label}</span>
      <input type="text" value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
        className="text-xs bg-surface-1 border border-border rounded px-2 py-1.5 text-text-primary placeholder:text-text-disabled outline-none focus:border-brand" />
    </label>
  );
}
