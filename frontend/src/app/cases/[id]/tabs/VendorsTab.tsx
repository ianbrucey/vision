"use client";

import { useState, useEffect, useCallback } from "react";
import { Search, ChevronLeft, ChevronRight, Loader2, MapPin, Mail, Phone, Globe, Building2, Plus } from "lucide-react";
import AddVendorModal from "@/components/AddVendorModal";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8400";

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("vision_token");
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

interface Vendor {
  vendor_name: string;
  trade_name: string | null;
  source: string;
  uei: string;
  cage_code: string | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  website: string | null;
  city: string | null;
  state: string | null;
  county: string | null;
  naics_codes_all: string | null;
  naics_code_primary: string | null;
  sba_certifications: string | null;
  capabilities: string | null;
  is_small_business: boolean;
  is_woman_owned: boolean;
  is_veteran_owned: boolean;
  is_sdvosb: boolean;
  is_hubzone: boolean;
  is_8a: boolean;
  gsa_contract_number: string | null;
  gsa_large_category: string | null;
}

interface SearchResponse {
  total: number;
  limit: number;
  offset: number;
  vendors: Vendor[];
}

/* ------------------------------------------------------------------ */
/* Set-aside badge                                                     */
/* ------------------------------------------------------------------ */

const FLAG_DEFS: { key: keyof Vendor; label: string; color: string }[] = [
  { key: "is_8a", label: "8(a)", color: "bg-purple-bg text-purple-700" },
  { key: "is_sdvosb", label: "SDVOSB", color: "bg-emerald-bg text-emerald-700" },
  { key: "is_woman_owned", label: "WOSB", color: "bg-pink-bg text-pink-700" },
  { key: "is_hubzone", label: "HUBZone", color: "bg-amber-bg text-amber-700" },
  { key: "is_veteran_owned", label: "VOSB", color: "bg-blue-bg text-blue-700" },
  { key: "is_small_business", label: "SB", color: "bg-info-bg text-info" },
];

function Flags({ vendor }: { vendor: Vendor }) {
  const active = FLAG_DEFS.filter((f) => vendor[f.key]);
  if (!active.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {active.map((f) => (
        <span key={f.label} className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${f.color}`}>
          {f.label}
        </span>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

interface Props {
  caseId: number;
}

const PAGE_SIZE = 25;

export default function VendorsTab({ caseId: _caseId }: Props) {
  const [q, setQ] = useState("");
  const [naics, setNaics] = useState("");
  const [state, setState] = useState("");
  const [setAside, setSetAside] = useState("");
  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showAddVendor, setShowAddVendor] = useState(false);

  const search = useCallback(async (newOffset = 0) => {
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams();
      if (q.trim()) params.set("q", q.trim());
      if (naics.trim()) params.set("naics", naics.trim());
      if (state.trim()) params.set("state", state.trim());
      if (setAside) params.set("set_aside", setAside);
      params.set("limit", String(PAGE_SIZE));
      params.set("offset", String(newOffset));

      const res = await fetch(`${API_BASE}/api/vendors?${params}`, {
        headers: getAuthHeaders(),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json: SearchResponse = await res.json();
      setData(json);
      setOffset(newOffset);
    } catch (e: any) {
      setError(e.message || "Search failed");
    } finally {
      setLoading(false);
    }
  }, [q, naics, state, setAside]);

  // Search on first mount
  useEffect(() => { search(0); }, []);

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    search(0);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ---- filters ---- */}
      <form
        onSubmit={handleSubmit}
        className="shrink-0 p-3 md:p-4 border-b border-border bg-surface-1"
      >
        <div className="flex flex-wrap gap-2 items-end">
          {/* Keyword search */}
          <div className="flex-1 min-w-[180px]">
            <label className="block text-[10px] font-semibold text-text-disabled uppercase tracking-wide mb-0.5">
              Search
            </label>
            <div className="relative">
              <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-text-disabled" />
              <input
                type="text"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Name or capability..."
                className="w-full h-8 pl-8 pr-2.5 rounded border border-border bg-surface-0
                           text-sm text-text-primary placeholder:text-text-disabled
                           focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
              />
            </div>
          </div>

          {/* NAICS */}
          <div className="w-[110px]">
            <label className="block text-[10px] font-semibold text-text-disabled uppercase tracking-wide mb-0.5">
              NAICS
            </label>
            <input
              type="text"
              value={naics}
              onChange={(e) => setNaics(e.target.value)}
              placeholder="e.g. 541511"
              className="w-full h-8 px-2.5 rounded border border-border bg-surface-0
                         text-sm text-text-primary placeholder:text-text-disabled
                         focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
            />
          </div>

          {/* State */}
          <div className="w-[80px]">
            <label className="block text-[10px] font-semibold text-text-disabled uppercase tracking-wide mb-0.5">
              State
            </label>
            <input
              type="text"
              value={state}
              onChange={(e) => setState(e.target.value.toUpperCase())}
              placeholder="VA"
              maxLength={2}
              className="w-full h-8 px-2.5 rounded border border-border bg-surface-0
                         text-sm text-text-primary placeholder:text-text-disabled
                         focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
            />
          </div>

          {/* Set-aside */}
          <div className="w-[130px]">
            <label className="block text-[10px] font-semibold text-text-disabled uppercase tracking-wide mb-0.5">
              Set-aside
            </label>
            <select
              value={setAside}
              onChange={(e) => setSetAside(e.target.value)}
              className="w-full h-8 px-2 rounded border border-border bg-surface-0
                         text-sm text-text-primary
                         focus:outline-none focus:border-brand focus:ring-1 focus:ring-brand/20"
            >
              <option value="">All</option>
              <option value="small_business">Small Business</option>
              <option value="sdvosb">SDVOSB</option>
              <option value="woman_owned">Woman-Owned</option>
              <option value="veteran_owned">Veteran-Owned</option>
              <option value="hubzone">HUBZone</option>
              <option value="8a">8(a)</option>
            </select>
          </div>

          <button
            type="submit"
            className="h-8 px-4 rounded bg-brand text-white text-sm font-medium
                       hover:bg-brand-emphasis transition-colors shrink-0"
          >
            Search
          </button>

          <button
            type="button"
            onClick={() => setShowAddVendor(true)}
            className="h-8 px-3 rounded border border-border bg-surface-1 text-text-primary
                       text-sm font-medium hover:bg-surface-3 transition-colors shrink-0
                       inline-flex items-center gap-1.5"
          >
            <Plus size={14} />
            Add Vendor
          </button>
        </div>
      </form>

      {/* ---- results ---- */}
      <div className="flex-1 overflow-auto">
        {error && (
          <div className="p-4 text-sm text-danger bg-danger-bg border-b border-danger/20">
            {error}
          </div>
        )}

        {loading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={24} className="animate-spin text-text-disabled" />
          </div>
        )}

        {!loading && data && data.vendors.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-text-disabled gap-2">
            <Building2 size={36} strokeWidth={1} />
            <p className="text-sm">No vendors found</p>
            <p className="text-xs">Try adjusting your search filters</p>
          </div>
        )}

        {!loading && data && data.vendors.length > 0 && (
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface-1 border-b border-border">
              <tr className="text-left text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
                <th className="px-3 py-2">Vendor</th>
                <th className="px-3 py-2 hidden md:table-cell">NAICS</th>
                <th className="px-3 py-2 hidden lg:table-cell">Set-aside</th>
                <th className="px-3 py-2 hidden sm:table-cell">Location</th>
                <th className="px-3 py-2 hidden xl:table-cell">Contact</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.vendors.map((v, i) => (
                <tr
                  key={`${v.uei}-${i}`}
                  className="hover:bg-surface-2 transition-colors cursor-pointer"
                  onClick={() => {
                    // Expand row? For now, copy email
                  }}
                >
                  <td className="px-3 py-2.5">
                    <div className="font-medium text-text-primary truncate max-w-[200px]">
                      {v.vendor_name}
                    </div>
                    {v.trade_name && v.trade_name !== v.vendor_name && (
                      <div className="text-xs text-text-disabled truncate max-w-[200px]">
                        dba {v.trade_name}
                      </div>
                    )}
                    <div className="flex gap-1 mt-0.5 md:hidden">
                      <Flags vendor={v} />
                    </div>
                  </td>
                  <td className="px-3 py-2.5 hidden md:table-cell">
                    <div className="text-xs text-text-secondary font-mono">
                      {v.naics_code_primary || "-"}
                    </div>
                    {v.naics_codes_all && v.naics_codes_all !== v.naics_code_primary && (
                      <div className="text-[10px] text-text-disabled truncate max-w-[180px]">
                        {v.naics_codes_all.split(", ").slice(0, 3).join(", ")}
                        {v.naics_codes_all.split(", ").length > 3 && " ..."}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2.5 hidden lg:table-cell">
                    <Flags vendor={v} />
                  </td>
                  <td className="px-3 py-2.5 hidden sm:table-cell">
                    {v.city && v.state ? (
                      <div className="flex items-center gap-1 text-xs text-text-secondary">
                        <MapPin size={10} className="shrink-0 text-text-disabled" />
                        {v.city}, {v.state}
                      </div>
                    ) : (
                      <span className="text-text-disabled">-</span>
                    )}
                    {v.county && (
                      <div className="text-[10px] text-text-disabled ml-4">{v.county}</div>
                    )}
                  </td>
                  <td className="px-3 py-2.5 hidden xl:table-cell">
                    <div className="space-y-0.5 text-xs">
                      {v.contact_email && (
                        <a
                          href={`mailto:${v.contact_email}`}
                          onClick={(e) => e.stopPropagation()}
                          className="flex items-center gap-1 text-info hover:text-brand transition-colors"
                        >
                          <Mail size={10} />
                          {v.contact_email}
                        </a>
                      )}
                      {v.contact_phone && (
                        <div className="flex items-center gap-1 text-text-secondary">
                          <Phone size={10} />
                          {v.contact_phone}
                        </div>
                      )}
                      {v.website && (
                        <a
                          href={v.website.startsWith("http") ? v.website : `https://${v.website}`}
                          target="_blank"
                          rel="noreferrer"
                          onClick={(e) => e.stopPropagation()}
                          className="flex items-center gap-1 text-info hover:text-brand transition-colors"
                        >
                          <Globe size={10} />
                          Website
                        </a>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* ---- pagination ---- */}
      {data && data.total > PAGE_SIZE && (
        <div className="shrink-0 flex items-center justify-between px-3 py-2 border-t border-border bg-surface-1 text-xs text-text-secondary">
          <span>
            {data.total.toLocaleString()} vendors
            {currentPage > 1 && ` · Page ${currentPage} of ${totalPages}`}
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => search(offset - PAGE_SIZE)}
              disabled={offset === 0}
              className="h-7 w-7 rounded flex items-center justify-center
                         hover:bg-surface-3 disabled:opacity-30 disabled:cursor-not-allowed
                         transition-colors"
            >
              <ChevronLeft size={14} />
            </button>
            <button
              onClick={() => search(offset + PAGE_SIZE)}
              disabled={offset + PAGE_SIZE >= data.total}
              className="h-7 w-7 rounded flex items-center justify-center
                         hover:bg-surface-3 disabled:opacity-30 disabled:cursor-not-allowed
                         transition-colors"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      <AddVendorModal
        open={showAddVendor}
        onClose={() => setShowAddVendor(false)}
        onCreated={() => search(offset)}
      />
    </div>
  );
}
