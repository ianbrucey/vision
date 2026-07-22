"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { listSolicitations, createSolicitation, deleteSolicitation, triggerTriage, type Solicitation } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Plus, FolderOpen, Loader2, FileSearch, AlertTriangle, Trash2, RefreshCw, Search, ArrowUpDown, ArrowUp, ArrowDown, X } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-surface-2 text-text-disabled",
  fetching: "bg-warning-bg text-warning",
  complete: "bg-success-bg text-success",
  failed: "bg-danger-bg text-danger",
};

const TRIAGE_STATUS_COLORS: Record<string, string> = {
  pending: "bg-surface-2 text-text-disabled",
  running: "bg-warning-bg text-warning",
  complete: "bg-success-bg text-success",
  failed: "bg-danger-bg text-danger",
};

const SOURCE_TYPE_COLORS: Record<string, string> = {
  federal: "bg-info-bg text-info",
  state: "bg-brand-bg text-brand",
  local: "bg-surface-2 text-text-secondary",
};

type SourceType = "federal" | "state" | "local";

type SortKey = "title" | "agency" | "response_deadline" | "ingestion_status";
type SortDir = "asc" | "desc";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "title", label: "Title" },
  { key: "agency", label: "Agency" },
  { key: "response_deadline", label: "Deadline" },
  { key: "ingestion_status", label: "Status" },
];

export default function SolicitationsPage() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [solicitations, setSolicitations] = useState<Solicitation[]>([]);
  const [sourceType, setSourceType] = useState<SourceType>("federal");
  const [manualFederal, setManualFederal] = useState(false);
  const [url, setUrl] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);
  const [showCreateMobile, setShowCreateMobile] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [deleting, setDeleting] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  const refresh = useCallback(async () => {
    const res = await listSolicitations();
    setSolicitations(res.solicitations);
  }, []);

  // Initial load
  const mountedRef = useRef(false);
  useEffect(() => {
    if (mountedRef.current) return;
    mountedRef.current = true;
    refresh();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Poll while any row is still ingesting (federal async intake) or triaging
  useEffect(() => {
    const hasPending = solicitations.some(
      (s) =>
        s.ingestion_status === "pending" ||
        s.ingestion_status === "fetching" ||
        s.triage_status === "running",
    );
    if (!hasPending) return;
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, [solicitations, refresh]);

  const resetForm = () => {
    setUrl("");
    setTitle("");
    setDescription("");
    setCreateError("");
  };

  const isManualEntry = sourceType === "federal" && manualFederal;
  const needsManualFields = sourceType !== "federal" || isManualEntry;

  const handleCreate = async () => {
    if (!needsManualFields && !url.trim()) return;
    if (needsManualFields && !title.trim()) return;
    setCreateError("");
    setCreating(true);
    try {
      const { solicitation } = await createSolicitation({
        source_type: sourceType,
        url: needsManualFields ? "" : url,
        ...(needsManualFields ? { title, description } : {}),
      });
      resetForm();
      setShowCreateMobile(false);
      setManualFederal(false);
      if (needsManualFields) {
        // No sam_fetch job — send user to Documents tab to upload files.
        router.push(`/cases/${solicitation.case_id}?tab=documents`);
      } else {
        refresh();
      }
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create solicitation");
    } finally {
      setCreating(false);
    }
  };

  const [triaging, setTriaging] = useState<number | null>(null);

  const handleTriage = async (id: number) => {
    setTriaging(id);
    try {
      await triggerTriage(id);
      // triggerTriage just enqueues a job and returns almost instantly, so
      // triage_status is still "pending" here. Poll briefly until the
      // background worker claims it (status leaves "pending"), otherwise the
      // spinner would vanish for a second or two with nothing visibly happening.
      for (let i = 0; i < 10; i++) {
        const res = await listSolicitations();
        setSolicitations(res.solicitations);
        const row = res.solicitations.find((x) => x.id === id);
        if (!row || row.triage_status !== "pending") break;
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch {
      // keep the row, let user retry
    } finally {
      setTriaging(null);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this solicitation and all its documents? This cannot be undone.")) return;
    setDeleting(id);
    try {
      await deleteSolicitation(id);
      setSolicitations((prev) => prev.filter((s) => s.id !== id));
    } catch {
      // keep the row, let user retry
    } finally {
      setDeleting(null);
    }
  };

  const urlPlaceholder =
    sourceType === "federal" ? "Paste SAM.gov opportunity URL..." : "Paste solicitation URL...";

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  };

  const q = search.trim().toLowerCase();
  const filtered = solicitations
    .filter(
      (s) =>
        (typeFilter === "all" || s.source_type === typeFilter) &&
        (!statusFilter || s.ingestion_status === statusFilter) &&
        (!q ||
          s.title.toLowerCase().includes(q) ||
          (s.agency || "").toLowerCase().includes(q)),
    )
    .sort((a, b) => {
      if (!sortKey) return 0;
      const av = a[sortKey] || "";
      const bv = b[sortKey] || "";
      const cmp = String(av).localeCompare(String(bv));
      return sortDir === "asc" ? cmp : -cmp;
    });

  const inputClasses =
    "bg-surface-2 border border-border rounded-sm px-3 py-2 text-sm " +
    "placeholder:text-text-disabled " +
    "focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden " +
    "transition-colors duration-150";

  const sourceTypeSelector = (
    <div className="flex gap-1.5 mb-3 flex-wrap">
      {(["federal", "state", "local"] as const).map((t) => (
        <button
          key={t}
          onClick={() => { setSourceType(t); setManualFederal(false); }}
          className={`text-[11px] px-3 py-1.5 rounded-md border transition-colors ${
            sourceType === t && !manualFederal
              ? "bg-brand-bg border-brand text-brand"
              : "border-border text-text-secondary hover:border-border-strong active:border-brand"
          }`}
        >
          {t === "federal" ? "Federal (SAM.gov)" : t[0].toUpperCase() + t.slice(1)}
        </button>
      ))}
      {sourceType === "federal" && (
        <button
          onClick={() => setManualFederal(true)}
          className={`text-[11px] px-3 py-1.5 rounded-md border transition-colors ${
            manualFederal
              ? "bg-brand-bg border-brand text-brand"
              : "border-border text-text-secondary hover:border-border-strong active:border-brand"
          }`}
        >
          DIBBs / Manual Entry
        </button>
      )}
    </div>
  );

  return (
    <main className="min-h-dvh bg-surface-0 text-text-primary flex flex-col">
      {/* === Header === */}
      <header className="sticky top-0 z-30 bg-surface-0/80 backdrop-blur-sm border-b border-border">
        <div className="max-w-5xl mx-auto flex items-center justify-between h-14 px-4">
          {/* Left: branding */}
          <div className="flex items-center gap-3 min-w-0">
            <h1 className="text-lg font-semibold tracking-tight shrink-0">Vision</h1>
            <span className="hidden sm:block text-xs text-text-disabled border-l border-border pl-3 truncate">
              War Room Agent
            </span>
          </div>

          {/* Right: cases link + user */}
          <div className="flex items-center gap-3 sm:gap-4 shrink-0">
            <button onClick={() => router.push("/cases")}
                    className="text-xs text-text-secondary hover:text-brand transition-colors
                               flex items-center gap-1">
              <FolderOpen size={14} />
              <span className="hidden sm:inline">Cases</span>
            </button>

            {/* User */}
            {user && (
              <div className="flex items-center gap-2">
                <span className="text-sm text-text-secondary hidden sm:inline">
                  {user.username}
                </span>
                <button
                  onClick={logout}
                  className="text-xs text-text-disabled hover:text-text-secondary transition-colors duration-150"
                >
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* === Content === */}
      <div className="flex-1 max-w-5xl mx-auto w-full px-4 py-6">
        {/* --- Create Solicitation (Desktop) --- */}
        <div className="hidden sm:block bg-surface-1 border border-border rounded-lg p-4 mb-6">
          <h2 className="text-sm font-medium text-text-secondary mb-3">New Solicitation</h2>
          {sourceTypeSelector}
          <div className="flex gap-3">
            {needsManualFields && (
              <input
                required
                className={inputClasses}
                placeholder="Solicitation title..."
                value={title}
                onChange={(e) => setTitle(e.target.value)}
              />
            )}
            {!needsManualFields && (
              <input
                required
                className={`flex-1 ${inputClasses}`}
                placeholder={urlPlaceholder}
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleCreate()}
              />
            )}
            <button
              onClick={handleCreate}
              disabled={creating}
              className="bg-brand hover:bg-brand-hover active:bg-brand-active
                         disabled:opacity-50 disabled:cursor-not-allowed
                         text-white px-4 py-2 rounded-lg text-sm font-medium
                         transition-colors duration-150 inline-flex items-center gap-2 shrink-0"
            >
              {creating && <Loader2 size={14} className="animate-spin" />}
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
          {needsManualFields && (
            <textarea
              required
              rows={2}
              className={`w-full mt-3 resize-none ${inputClasses}`}
              placeholder="Description... (what is this solicitation for? you'll upload documents next)"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          )}
          {createError && (
            <p className="text-danger text-xs mt-2">{createError}</p>
          )}
        </div>

        {/* --- Create Solicitation (Mobile FAB) --- */}
        <button
          onClick={() => setShowCreateMobile(true)}
          className="sm:hidden fixed bottom-20 right-4 z-20 size-14 rounded-full
                     bg-brand text-white shadow-md
                     hover:bg-brand-hover active:bg-brand-active
                     flex items-center justify-center transition-colors duration-150"
          aria-label="Create solicitation"
        >
          <Plus size={24} />
        </button>

        {/* --- Create Solicitation (Mobile Modal) --- */}
        {showCreateMobile && (
          <div
            className="sm:hidden fixed inset-0 z-50 bg-black/60 flex items-end justify-center"
            onClick={(e) => {
              if (e.target === e.currentTarget) setShowCreateMobile(false);
            }}
          >
            <div
              className="bg-surface-1 border border-border rounded-t-xl shadow-md
                        w-full max-h-[90dvh] overflow-y-auto p-5
                        animate-in slide-in-from-bottom-4 duration-250"
            >
              <div className="w-10 h-1 bg-surface-5 rounded-full mx-auto mb-4" />
              <h2 className="text-lg font-semibold mb-4">New Solicitation</h2>
              <div className="flex flex-col gap-3">
                {sourceTypeSelector}
                {needsManualFields && (
                  <input
                    required
                    className={`${inputClasses} text-[16px]`}
                    placeholder="Solicitation title..."
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    autoFocus
                  />
                )}
                {!needsManualFields && (
                  <input
                    required
                    className={`${inputClasses} text-[16px]`}
                    placeholder={urlPlaceholder}
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                )}
                {needsManualFields && (
                  <textarea
                    required
                    rows={2}
                    className={`resize-none ${inputClasses} text-[16px]`}
                    placeholder="Description... (what is this solicitation for? you'll upload documents next)"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                  />
                )}
                {createError && <p className="text-danger text-xs">{createError}</p>}
                <div className="flex flex-col gap-2 mt-2">
                  <button
                    onClick={handleCreate}
                    disabled={creating}
                    className="bg-brand hover:bg-brand-hover active:bg-brand-active
                               disabled:opacity-50 disabled:cursor-not-allowed
                               text-white py-3 rounded-lg text-sm font-medium
                               transition-colors duration-150 inline-flex items-center justify-center gap-2
                               min-h-[44px]"
                  >
                    {creating && <Loader2 size={16} className="animate-spin" />}
                    {creating ? "Creating..." : "Create"}
                  </button>
                  <button
                    onClick={() => setShowCreateMobile(false)}
                    className="bg-surface-2 hover:bg-surface-3 active:bg-surface-4
                               text-text-primary py-3 rounded-lg text-sm font-medium
                               transition-colors duration-150 min-h-[44px]"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* === Search === */}
        <div className="relative mb-3">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-text-disabled pointer-events-none"
          />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by title or agency..."
            className={`w-full pl-9 pr-9 ${inputClasses}`}
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              aria-label="Clear search"
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-text-disabled hover:text-text-primary transition-colors"
            >
              <X size={14} />
            </button>
          )}
        </div>

        {/* === FilterBar === */}
        <div className="flex items-center justify-between mb-2 flex-wrap gap-2">
          <div className="flex gap-1.5">
            {(["all", "federal", "state", "local"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`text-[11px] px-2.5 py-1 rounded-md border transition-colors ${
                  typeFilter === t
                    ? "bg-brand-bg border-brand text-brand"
                    : "border-border text-text-secondary hover:border-border-strong active:border-brand"
                }`}
              >
                {t === "all" ? "All" : t[0].toUpperCase() + t.slice(1)}
              </button>
            ))}
          </div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-surface-2 border border-border rounded-sm px-3 py-2 text-sm
                       focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                       transition-colors duration-150"
          >
            <option value="">All statuses</option>
            <option value="pending">Pending</option>
            <option value="fetching">Fetching</option>
            <option value="complete">Complete</option>
            <option value="failed">Failed</option>
          </select>
        </div>

        {/* === SortBar === */}
        <div className="flex items-center gap-1.5 mb-4 flex-wrap">
          <span className="text-[11px] text-text-disabled inline-flex items-center gap-1">
            <ArrowUpDown size={12} />
            Sort:
          </span>
          {SORT_OPTIONS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => handleSort(key)}
              className={`text-[11px] px-2.5 py-1 rounded-md border transition-colors inline-flex items-center gap-1 ${
                sortKey === key
                  ? "bg-brand-bg border-brand text-brand"
                  : "border-border text-text-secondary hover:border-border-strong active:border-brand"
              }`}
            >
              {label}
              {sortKey === key &&
                (sortDir === "asc" ? <ArrowUp size={11} /> : <ArrowDown size={11} />)}
            </button>
          ))}
        </div>

        {/* === Solicitations List === */}
        <div className="flex flex-col gap-3">
          {filtered.map((s) => (
            <div
              key={s.id}
              onClick={() => router.push(`/cases/${s.case_id}`)}
              className="bg-surface-1 border border-border rounded-lg
                         hover:bg-surface-2 hover:border-border-strong active:border-brand
                         transition-colors duration-150 cursor-pointer"
            >
              <div className="flex items-center gap-3 p-3">
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-text-primary truncate">{s.title}</p>
                  <p className="text-[10px] text-text-disabled truncate">{s.agency || s.url}</p>
                </div>
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-sm font-medium shrink-0 ${
                    SOURCE_TYPE_COLORS[s.source_type] || "bg-surface-2 text-text-secondary"
                  }`}
                >
                  {s.source_type}
                </span>
                <span
                  className={`text-[11px] px-2 py-0.5 rounded-sm font-medium shrink-0 ${
                    STATUS_COLORS[s.ingestion_status] || "bg-surface-2 text-text-secondary"
                  }`}
                >
                  {s.ingestion_status}
                </span>
                {s.has_missing_docs && (
                  <span title="Some attachments failed to download" className="shrink-0">
                    <AlertTriangle size={14} className="text-warning" />
                  </span>
                )}
                {s.ingestion_status === "complete" && (
                  <span
                    title={s.triage_error || undefined}
                    className={`text-[11px] px-2 py-0.5 rounded-sm font-medium shrink-0 ${
                      TRIAGE_STATUS_COLORS[s.triage_status] || "bg-surface-2 text-text-secondary"
                    }`}
                  >
                    triage: {s.triage_status}
                  </span>
                )}
                {s.ingestion_status === "complete" && s.triage_status !== "running" && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTriage(s.id);
                    }}
                    disabled={triaging === s.id}
                    title={s.triage_status === "complete" ? "Re-run triage" : "Run triage"}
                    className="p-1.5 rounded-md text-text-disabled shrink-0
                               hover:bg-brand-bg hover:text-brand
                               disabled:opacity-50 disabled:cursor-not-allowed
                               transition-colors duration-150"
                    aria-label="Run triage"
                  >
                    {triaging === s.id ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <RefreshCw size={14} />
                    )}
                  </button>
                )}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(s.id);
                  }}
                  disabled={deleting === s.id}
                  className="p-1.5 rounded-md text-text-disabled shrink-0
                             hover:bg-danger-bg hover:text-danger
                             disabled:opacity-50 disabled:cursor-not-allowed
                             transition-colors duration-150"
                  aria-label="Delete solicitation"
                >
                  {deleting === s.id ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <Trash2 size={14} />
                  )}
                </button>
              </div>
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
              <FileSearch size={32} className="text-text-disabled" />
              <p className="text-sm text-text-secondary">No solicitations yet</p>
              <p className="text-xs text-text-disabled">Paste a SAM.gov URL above to get started.</p>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
