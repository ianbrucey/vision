"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Upload, Search, Loader2, ChevronDown, ChevronUp, ExternalLink, Layers } from "lucide-react";
import {
  querySubcontractingLeads,
  uploadSubLeadsCsv,
  processSubLeadsPools,
  type SubcontractingLead,
  type SubLeadsQuery,
} from "@/lib/api";
import ReferenceNav from "@/components/ReferenceNav";

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const PAGE_SIZE = 50;

const PRIORITY_COLORS: Record<string, string> = {
  high: "bg-red-100 text-red-800 border-red-200",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-200",
  low: "bg-gray-100 text-gray-600 border-gray-200",
};

const PLAN_LABELS: Record<string, string> = {
  F: "Individual Plan",
  G: "Commercial Plan",
};

const CATEGORY_LABELS: Record<string, string> = {
  construction: "Construction",
  facilities: "Facilities",
  it: "IT",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function SubcontractingLeadsPage() {
  /* ---- state ---- */
  const [results, setResults] = useState<SubcontractingLead[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);

  // Filters
  const [filters, setFilters] = useState<SubLeadsQuery>({ limit: PAGE_SIZE });
  const [showFilters, setShowFilters] = useState(false);
  const [categoryFilter, setCategoryFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [planFilter, setPlanFilter] = useState("");

  // Upload
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadStats, setUploadStats] = useState<Record<string, any> | null>(null);

  // Pool processing
  const [processingPools, setProcessingPools] = useState(false);

  // Expanded row
  const [expandedId, setExpandedId] = useState<number | null>(null);

  /* ---- fetch ---- */

  const search = useCallback(async (newOffset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const body: SubLeadsQuery = {
        ...filters,
        limit: PAGE_SIZE,
        offset: newOffset,
      };
      if (categoryFilter) body.pipeline_category = categoryFilter;
      if (priorityFilter) body.pipeline_priority = priorityFilter;
      if (planFilter) body.subcontracting_plan_code = planFilter;

      const res = await querySubcontractingLeads(body);
      setResults(res.results);
      setTotal(res.total);
      setOffset(newOffset);
    } catch (e: any) {
      setError(e.message || "Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, [filters, categoryFilter, priorityFilter, planFilter]);

  useEffect(() => {
    search(0);
  }, []);

  /* ---- upload ---- */

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadMsg(null);
    setUploadStats(null);
    try {
      const res = await uploadSubLeadsCsv(file);
      setUploadMsg(
        `Upload complete: ${res.inserted} inserted, ${res.updated} updated, ${res.skipped} skipped (${res.total_rows} total rows)`
      );
      setUploadStats(res);
      search(0);
    } catch (err: any) {
      setUploadMsg(`Upload failed: ${err.message || "Unknown error"}`);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  /* ---- pool processing ---- */

  const handleProcessPools = async () => {
    setProcessingPools(true);
    try {
      const res = await processSubLeadsPools();
      setUploadMsg(`Pool processing complete: ${res.pools_updated} leads updated`);
      search(offset);
    } catch (err: any) {
      setUploadMsg(`Pool processing failed: ${err.message || "Unknown error"}`);
    } finally {
      setProcessingPools(false);
    }
  };

  /* ---- pagination ---- */

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  /* ---- format helpers ---- */

  const fmtMoney = (val: number | null) => {
    if (!val || val === 0) return "—";
    if (val >= 1e9) return `$${(val / 1e9).toFixed(1)}B`;
    if (val >= 1e6) return `$${(val / 1e6).toFixed(0)}M`;
    if (val >= 1e3) return `$${(val / 1e3).toFixed(0)}K`;
    return `$${val}`;
  };

  return (
    <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
      <ReferenceNav />
      <div className="flex-1 flex flex-col min-h-0 p-4">
        {/* ---- Header ---- */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-xl font-semibold">Subcontracting Leads</h1>
            <p className="text-sm text-text-secondary">
              IDV vehicles from USASpending.gov — primes with subcontracting obligations
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* Pool processing */}
            <button
              onClick={handleProcessPools}
              disabled={processingPools}
              className="flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-md hover:bg-surface-50 disabled:opacity-50"
            >
              <Layers className="w-4 h-4" />
              {processingPools ? "Processing..." : "Compute Pools"}
            </button>

            {/* Upload */}
            <label className={`flex items-center gap-2 px-3 py-2 text-sm border border-border rounded-lg cursor-pointer
                              text-text-secondary hover:text-text-primary transition-colors
                              ${uploading ? "opacity-50 pointer-events-none" : ""}`}>
              {uploading ? (
                <><Loader2 size={14} className="animate-spin" /> Uploading...</>
              ) : (
                <><Upload size={14} /> Upload CSV</>
              )}
              <input
                type="file"
                accept=".csv"
                className="hidden"
                onChange={handleUpload}
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {/* Upload feedback */}
        {uploadMsg && (
          <div className={`mb-4 p-3 rounded-md text-sm ${
            uploadMsg.includes("failed") ? "bg-red-50 text-red-700" : "bg-green-50 text-green-700"
          }`}>
            {uploadMsg}
            {uploadStats?.skipped_breakdown && (
              <div className="mt-1 flex flex-wrap gap-2 text-xs opacity-75">
                {Object.entries(uploadStats.skipped_breakdown).map(([reason, count]) => (
                  <span key={reason} className="bg-white/50 px-2 py-0.5 rounded">
                    {reason}: {count as number}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* ---- Filters ---- */}
        <div className="flex items-center gap-3 mb-4 flex-wrap">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-1 text-sm text-text-secondary hover:text-text-primary"
          >
            {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            Filters
          </button>

          {showFilters && (
            <>
              <select
                value={categoryFilter}
                onChange={(e) => { setCategoryFilter(e.target.value); }}
                className="px-2 py-1.5 text-sm border border-border rounded-md bg-surface-0"
              >
                <option value="">All Categories</option>
                <option value="construction">Construction</option>
                <option value="facilities">Facilities</option>
                <option value="it">IT</option>
              </select>

              <select
                value={priorityFilter}
                onChange={(e) => { setPriorityFilter(e.target.value); }}
                className="px-2 py-1.5 text-sm border border-border rounded-md bg-surface-0"
              >
                <option value="">All Priorities</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>

              <select
                value={planFilter}
                onChange={(e) => { setPlanFilter(e.target.value); }}
                className="px-2 py-1.5 text-sm border border-border rounded-md bg-surface-0"
              >
                <option value="">All Plan Types</option>
                <option value="F">Individual Plan (F)</option>
                <option value="G">Commercial Plan (G)</option>
              </select>

              <button
                onClick={() => search(0)}
                className="flex items-center gap-1 px-3 py-1.5 text-sm bg-brand text-white rounded-md hover:bg-brand-hover"
              >
                <Search className="w-3 h-3" />
                Apply
              </button>
            </>
          )}

          <span className="ml-auto text-sm text-text-secondary">
            {total.toLocaleString()} leads
          </span>
        </div>

        {/* ---- Table ---- */}
        <div className="flex-1 min-h-0 overflow-auto border border-border rounded-lg">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <Loader2 className="w-6 h-6 animate-spin text-text-tertiary" />
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-32 text-red-600 text-sm">{error}</div>
          ) : results.length === 0 ? (
            <div className="flex items-center justify-center h-32 text-text-tertiary text-sm">
              No leads yet. Upload a USASpending Prime Award Summaries CSV to get started.
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-50 text-text-secondary border-b border-border">
                <tr>
                  <th className="text-left px-3 py-2 font-medium w-16">Score</th>
                  <th className="text-left px-3 py-2 font-medium">Prime</th>
                  <th className="text-left px-3 py-2 font-medium">Vehicle</th>
                  <th className="text-left px-3 py-2 font-medium">Category</th>
                  <th className="text-left px-3 py-2 font-medium">Plan</th>
                  <th className="text-right px-3 py-2 font-medium">Ceiling</th>
                  <th className="text-left px-3 py-2 font-medium">Pool</th>
                  <th className="text-left px-3 py-2 font-medium">Ordering End</th>
                </tr>
              </thead>
              <tbody>
                {results.map((lead) => (
                  <React.Fragment key={lead.id}>
                    <tr
                      className={`border-b border-border hover:bg-surface-50 cursor-pointer ${
                        expandedId === lead.id ? "bg-surface-50" : ""
                      }`}
                      onClick={() => setExpandedId(expandedId === lead.id ? null : lead.id)}
                    >
                      <td className="px-3 py-2">
                        <span className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium border ${
                          PRIORITY_COLORS[lead.pipeline_priority || "low"] || PRIORITY_COLORS.low
                        }`}>
                          {lead.pipeline_priority_score || "—"}
                        </span>
                      </td>
                      <td className="px-3 py-2">
                        <div className="font-medium truncate max-w-[220px]">{lead.recipient_name}</div>
                        {lead.recipient_parent_name && (
                          <div className="text-xs text-text-tertiary truncate max-w-[220px]">
                            {lead.recipient_parent_name}
                          </div>
                        )}
                      </td>
                      <td className="px-3 py-2 text-text-secondary font-mono text-xs">
                        <div className="truncate max-w-[140px]">{lead.award_id_piid}</div>
                        <div className="text-text-tertiary">{lead.idv_type || "—"}</div>
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-xs">{CATEGORY_LABELS[lead.pipeline_category || ""] || lead.pipeline_category || "—"}</span>
                      </td>
                      <td className="px-3 py-2">
                        <span className="text-xs font-medium">
                          {PLAN_LABELS[lead.subcontracting_plan_code || ""] || lead.subcontracting_plan_code || "—"}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-right font-mono text-xs">
                        {fmtMoney(lead.potential_value)}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {lead.pool_awardee_count ? (
                          <span className="inline-block bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                            {lead.pool_awardee_count} awardees
                          </span>
                        ) : (
                          <span className="text-text-tertiary">—</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs text-text-secondary">
                        {lead.ordering_period_end || "Open-ended"}
                      </td>
                    </tr>

                    {/* Expanded detail row */}
                    {expandedId === lead.id && (
                      <tr>
                        <td colSpan={8} className="px-4 py-3 bg-surface-25 border-b border-border">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                            <div>
                              <span className="text-text-tertiary text-xs">Agency</span>
                              <p className="text-text-primary">{lead.awarding_agency || "—"}</p>
                              {lead.awarding_sub_agency && (
                                <p className="text-text-secondary text-xs">{lead.awarding_sub_agency}</p>
                              )}
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">NAICS</span>
                              <p className="text-text-primary">{lead.naics_code || "—"}</p>
                              <p className="text-text-secondary text-xs truncate">{lead.naics_description || ""}</p>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">Location</span>
                              <p className="text-text-primary">
                                {[lead.recipient_city, lead.recipient_state].filter(Boolean).join(", ") || "—"}
                              </p>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">Socioeconomic</span>
                              <p className="text-text-primary text-xs flex flex-wrap gap-1">
                                {lead.is_sdvosb && <span className="bg-purple-50 text-purple-700 px-1 rounded">SDVOSB</span>}
                                {lead.is_8a && <span className="bg-blue-50 text-blue-700 px-1 rounded">8(a)</span>}
                                {lead.is_hubzone && <span className="bg-orange-50 text-orange-700 px-1 rounded">HUBZone</span>}
                                {lead.is_woman_owned && <span className="bg-pink-50 text-pink-700 px-1 rounded">WOSB</span>}
                                {lead.is_small_disadvantaged && <span className="bg-green-50 text-green-700 px-1 rounded">SDB</span>}
                                {!lead.is_sdvosb && !lead.is_8a && !lead.is_hubzone && !lead.is_woman_owned && !lead.is_small_disadvantaged && (
                                  <span className="text-text-tertiary">None flagged</span>
                                )}
                              </p>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">Solicitation</span>
                              <p className="text-text-primary text-xs font-mono">{lead.solicitation_identifier || "—"}</p>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">Multiple / Single Award</span>
                              <p className="text-text-primary">{lead.multiple_or_single_award || "—"}</p>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">Set-Aside</span>
                              <p className="text-text-primary text-xs">{lead.set_aside_type || "—"}</p>
                            </div>
                            <div>
                              <span className="text-text-tertiary text-xs">Permalink</span>
                              {lead.usaspending_permalink ? (
                                <a
                                  href={lead.usaspending_permalink}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-brand hover:underline flex items-center gap-1"
                                  onClick={(e) => e.stopPropagation()}
                                >
                                  USASpending <ExternalLink className="w-3 h-3" />
                                </a>
                              ) : (
                                <span className="text-text-tertiary">—</span>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* ---- Pagination ---- */}
        {total > PAGE_SIZE && (
          <div className="flex items-center justify-between mt-3 text-sm">
            <span className="text-text-secondary">
              Page {currentPage} of {totalPages} ({total.toLocaleString()} leads)
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => search(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-3 py-1 border border-border rounded-md disabled:opacity-30 hover:bg-surface-50"
              >
                Previous
              </button>
              <button
                onClick={() => search(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="px-3 py-1 border border-border rounded-md disabled:opacity-30 hover:bg-surface-50"
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
