"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Search, Loader2, ChevronDown, ChevronUp, ExternalLink } from "lucide-react";
import { queryDlaBatch, getDlaBatchStats, type DlaBatchRow, type DlaBatchStats } from "@/lib/api";

interface Props { caseId: number | null; }

const PAGE_SIZE = 50;
const DOLLAR = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

function fmtPrice(n: number | null): string {
  if (n == null) return "—";
  return DOLLAR.format(n);
}

export default function DlaBatchSearchTab({ caseId: _caseId }: Props) {
  const [results, setResults] = useState<DlaBatchRow[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [offset, setOffset] = useState(0);
  const [stats, setStats] = useState<DlaBatchStats | null>(null);

  const [q, setQ] = useState("");
  const [nsns, setNsns] = useState("");
  const [competable, setCompetable] = useState("");
  const [fsc, setFsc] = useState("");
  const [amc, setAmc] = useState("");
  const [hasVendor, setHasVendor] = useState("");
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const search = useCallback(async (newOffset = 0) => {
    setLoading(true); setError(null);
    try {
      const params: Record<string, string | number | undefined> = {
        q: q.trim() || undefined,
        nsns: nsns.trim() || undefined,
        fsc: fsc || undefined,
        amc: amc || undefined,
        competable: competable || undefined,
        vendor_name: hasVendor === "yes" ? "NOTNULL_PLACEHOLDER" : hasVendor === "no" ? "" : undefined,
        limit: PAGE_SIZE,
        offset: newOffset,
        order_by: "unit_price",
        order_dir: "DESC",
      };
      // Handle hasVendor as a separate filter — backend does ILIKE for vendor_name
      if (hasVendor === "yes") params.vendor_name = undefined; // will be filtered client-side
      const data = await queryDlaBatch(params);
      // Client-side vendor filter if needed
      let filtered = data.results;
      if (hasVendor === "yes") {
        filtered = filtered.filter(r => r.vendor_name && r.vendor_name !== "");
      } else if (hasVendor === "no") {
        filtered = filtered.filter(r => !r.vendor_name || r.vendor_name === "");
      }
      setResults(filtered);
      setTotal(data.total);
      setOffset(newOffset);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally { setLoading(false); }
  }, [q, nsns, competable, fsc, amc, hasVendor]);

  useEffect(() => { search(0); }, []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    getDlaBatchStats().then(setStats).catch(() => {});
  }, []);

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); search(0); };
  const clearFilters = () => { setQ(""); setNsns(""); setCompetable(""); setFsc(""); setAmc(""); setHasVendor(""); };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-border">
        <div>
          <p className="text-sm font-medium text-text-primary">DLA Batch Search</p>
          <p className="text-xs text-text-disabled">
            {stats ? `${stats.total.toLocaleString()} enriched RFQ rows · ${stats.competable.toLocaleString()} competable · ${stats.with_email.toLocaleString()} with vendor email` : "Enriched DIBBS solicitations from the dibbs-enrich skill."}
          </p>
        </div>
        {/* Stat chips */}
        {stats && (
          <div className="flex gap-3 mt-2 flex-wrap">
            <StatChip label="Competable" value={stats.competable} total={stats.total} />
            <StatChip label="With Vendor" value={stats.with_vendor} total={stats.total} />
            <StatChip label="With Email" value={stats.with_email} total={stats.total} />
            <StatChip label="Priced" value={stats.priced} total={stats.total} />
            <StatChip label="Unique NSNs" value={stats.unique_nsns} total={stats.total} raw />
            <StatChip label="Solicitations" value={stats.unique_sols} total={0} raw />
          </div>
        )}
      </div>

      {/* Bulk NSN lookup */}
      <div className="shrink-0 px-4 py-3 border-b border-border bg-surface-2">
        <div className="flex gap-2 items-start">
          <textarea value={nsns} onChange={e => setNsns(e.target.value)}
            placeholder="Paste NSNs — comma-separated, up to 200&#10;e.g. 4110-01-453-2373, 6515-01-314-6694, 6240-01-353-9709"
            rows={2}
            className="flex-1 text-xs bg-surface-1 border border-border rounded-lg px-3 py-2 text-text-primary placeholder:text-text-disabled outline-none focus:border-brand resize-none font-mono" />
          <button type="button" onClick={() => search(0)}
            className="px-4 py-2 text-sm bg-brand text-white rounded-lg hover:opacity-90 whitespace-nowrap">Lookup NSNs</button>
        </div>
      </div>

      {/* Search bar */}
      <div className="shrink-0 px-4 py-3 border-b border-border bg-surface-1">
        <form onSubmit={handleSearch} className="flex gap-2 flex-wrap">
          <div className="flex-1 min-w-[200px] relative">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-text-disabled" />
            <input type="text" value={q} onChange={e => setQ(e.target.value)}
              placeholder='Search — "compressor", "6515", "SPE2DS"...'
              className="w-full pl-9 pr-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary placeholder:text-text-disabled outline-none focus:border-brand" />
          </div>
          <select value={competable} onChange={e => setCompetable(e.target.value)}
            className="text-sm bg-surface-2 border border-border rounded-lg px-3 py-2 text-text-primary outline-none focus:border-brand">
            <option value="">All — Competable</option>
            <option value="true">Competable ✓</option>
            <option value="false">Restricted</option>
            <option value="unknown">Unknown</option>
          </select>
          <select value={hasVendor} onChange={e => setHasVendor(e.target.value)}
            className="text-sm bg-surface-2 border border-border rounded-lg px-3 py-2 text-text-primary outline-none focus:border-brand">
            <option value="">All — Vendor</option>
            <option value="yes">Has Vendor Match</option>
            <option value="no">No Vendor Match</option>
          </select>
          <input type="text" value={fsc} onChange={e => setFsc(e.target.value)} placeholder="FSC"
            className="text-sm bg-surface-2 border border-border rounded-lg px-3 py-2 w-20 text-text-primary placeholder:text-text-disabled outline-none focus:border-brand" />
          <input type="text" value={amc} onChange={e => setAmc(e.target.value)} placeholder="AMC"
            className="text-sm bg-surface-2 border border-border rounded-lg px-3 py-2 w-20 text-text-primary placeholder:text-text-disabled outline-none focus:border-brand" />
          <button type="submit" className="px-4 py-2 text-sm bg-brand text-white rounded-lg hover:opacity-90">Search</button>
          <button type="button" onClick={clearFilters}
            className="px-3 py-2 text-sm border border-border text-text-secondary rounded-lg hover:text-text-primary">Clear</button>
        </form>
      </div>

      {error && <div className="shrink-0 px-4 py-2 text-xs text-danger bg-danger-bg">{error}</div>}

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12"><Loader2 className="animate-spin text-text-disabled" size={24} /></div>
        ) : results.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3 text-text-disabled">
            <Search size={32} strokeWidth={1.5} />
            <p className="text-sm">No results. Try adjusting your filters.</p>
          </div>
        ) : (
          <div>
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-surface-1 border-b border-border z-10">
                <tr className="text-left text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
                  <th className="px-3 py-2 w-8"></th>
                  <th className="px-3 py-2">NSN</th>
                  <th className="px-3 py-2">Nomenclature</th>
                  <th className="px-3 py-2 w-14">AMC</th>
                  <th className="px-3 py-2 w-20">Competable</th>
                  <th className="px-3 py-2 w-24 text-right">Unit Price</th>
                  <th className="px-3 py-2 hidden md:table-cell">Vendor</th>
                  <th className="px-3 py-2 hidden lg:table-cell">Contact</th>
                  <th className="px-3 py-2">Solicitation</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {results.map((r) => {
                  const isExpanded = expandedId === r.id;
                  const compColor = r.competable === "true" ? "text-success" : r.competable === "false" ? "text-danger" : "text-text-disabled";
                  return (
                    <React.Fragment key={r.id}>
                      <tr className="hover:bg-surface-2 transition-colors cursor-pointer" onClick={() => setExpandedId(isExpanded ? null : r.id)}>
                        <td className="px-3 py-2">{isExpanded ? <ChevronDown size={14} /> : <ChevronUp size={14} />}</td>
                        <td className="px-3 py-2 font-mono text-xs whitespace-nowrap">{r.nsn}</td>
                        <td className="px-3 py-2 max-w-[240px] truncate" title={r.nomenclature || ""}>{r.nomenclature || "—"}</td>
                        <td className="px-3 py-2 text-xs">{r.amc || "—"}</td>
                        <td className={`px-3 py-2 text-xs font-medium ${compColor}`}>
                          {r.competable === "true" ? "Yes" : r.competable === "false" ? "No" : r.competable || "—"}
                        </td>
                        <td className="px-3 py-2 text-right text-xs font-medium text-text-primary whitespace-nowrap">
                          {fmtPrice(r.unit_price)}
                        </td>
                        <td className="px-3 py-2 hidden md:table-cell text-xs max-w-[160px] truncate" title={r.vendor_name || r.cage_company || ""}>
                          {r.vendor_name || r.cage_company || "—"}
                        </td>
                        <td className="px-3 py-2 hidden lg:table-cell text-xs max-w-[140px] truncate">
                          {r.contact_email ? (
                            <a href={`mailto:${r.contact_email}`} onClick={e => e.stopPropagation()}
                              className="text-brand hover:underline">{r.contact_email}</a>
                          ) : r.contact_name ? r.contact_name : "—"}
                        </td>
                        <td className="px-3 py-2 text-xs">
                          {r.solicitation ? (
                            <a href={`https://www.dibbs.bsm.dla.mil/RFQ/RFQRec.aspx?sn=${r.solicitation.replace(/-/g, '')}`}
                              target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}
                              className="text-brand hover:underline inline-flex items-center gap-1 font-mono text-[11px]">
                              {r.solicitation} <ExternalLink size={10} />
                            </a>
                          ) : "—"}
                        </td>
                      </tr>
                      {isExpanded && (
                        <tr>
                          <td colSpan={9} className="px-6 py-3 bg-surface-2">
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                              {r.nomenclature && <div><span className="font-medium text-text-primary">Item:</span><p className="text-text-secondary">{r.nomenclature}</p></div>}
                              {r.competability_notes && <div className="col-span-2"><span className="font-medium text-text-primary">Competability:</span><p className="text-text-secondary">{r.competability_notes}</p></div>}
                              {r.aac && <div><span className="font-medium text-text-primary">AAC:</span><p className="text-text-secondary">{r.aac}</p></div>}
                              {r.amsc && <div><span className="font-medium text-text-primary">AMSC:</span><p className="text-text-secondary">{r.amsc}</p></div>}
                              {r.dmil && <div><span className="font-medium text-text-primary">DMIL:</span><p className="text-text-secondary">{r.dmil}</p></div>}
                              {r.hmic && <div><span className="font-medium text-text-primary">HMIC:</span><p className="text-text-secondary">{r.hmic}</p></div>}
                              {r.crit_cd && <div><span className="font-medium text-text-primary">Criticality:</span><p className="text-text-secondary">{r.crit_cd}</p></div>}
                              {r.ui && <div><span className="font-medium text-text-primary">Unit of Issue:</span><p className="text-text-secondary">{r.ui}</p></div>}
                              {r.slc && <div><span className="font-medium text-text-primary">Shelf Life:</span><p className="text-text-secondary">{r.slc}</p></div>}
                              {r.qty && <div><span className="font-medium text-text-primary">Qty:</span><p className="text-text-secondary">{r.qty}</p></div>}
                              {r.approved_cage && <div><span className="font-medium text-text-primary">Approved CAGE:</span><p className="text-text-secondary">{r.approved_cage}{r.approved_part ? ` — ${r.approved_part}` : ""}</p></div>}
                              {r.cage_company && <div><span className="font-medium text-text-primary">CAGE Company:</span><p className="text-text-secondary">{r.cage_company} — {r.cage_city}, {r.cage_state}</p></div>}
                              {r.vendor_name && <div><span className="font-medium text-text-primary">Vendor:</span><p className="text-text-secondary">{r.vendor_name}{r.contact_name ? ` — ${r.contact_name}` : ""}{r.contact_phone ? ` — ${r.contact_phone}` : ""}</p></div>}
                              {r.website && <div><span className="font-medium text-text-primary">Website:</span><a href={r.website.startsWith("http") ? r.website : `https://${r.website}`} target="_blank" rel="noopener noreferrer" className="text-brand hover:underline">{r.website}</a></div>}
                              {r.is_small_business === "t" && <div><span className="text-xs text-success font-medium">✓ Small Business</span></div>}
                              {r.purchase_request && <div><span className="font-medium text-text-primary">PR:</span><p className="text-text-secondary">{r.purchase_request}</p></div>}
                              {r.source_file && <div className="col-span-full"><span className="font-medium text-text-primary">Source:</span><p className="text-text-disabled text-[11px]">{r.source_file}</p></div>}
                            </div>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="shrink-0 px-4 py-2 border-t border-border flex items-center justify-between text-xs text-text-secondary">
          <span>Showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} of {total.toLocaleString()}</span>
          <div className="flex gap-1">
            <button onClick={() => search(Math.max(0, offset - PAGE_SIZE))} disabled={offset === 0}
              className="px-3 py-1 border border-border rounded hover:bg-surface-2 disabled:opacity-50">Previous</button>
            <button onClick={() => search(offset + PAGE_SIZE)} disabled={offset + PAGE_SIZE >= total}
              className="px-3 py-1 border border-border rounded hover:bg-surface-2 disabled:opacity-50">Next</button>
          </div>
        </div>
      )}
    </div>
  );
}

function StatChip({ label, value, total: _total, raw }: { label: string; value: number; total: number; raw?: boolean }) {
  return (
    <div className="flex items-center gap-1.5 px-2 py-1 bg-surface-2 border border-border rounded-lg">
      <span className="text-[10px] text-text-disabled uppercase">{label}</span>
      <span className="text-xs font-semibold text-text-primary">{raw ? value.toLocaleString() : `${value.toLocaleString()}`}</span>
    </div>
  );
}
