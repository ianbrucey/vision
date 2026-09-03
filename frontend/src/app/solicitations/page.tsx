"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { listSolicitations, createSolicitation, deleteSolicitation, rerunSolicitation, triggerTriage, lookupSolicitationUrl, listNaicsCodes, previewSamMetadata, ingestSolicitationPackage, type Solicitation, type SamMetadataPreview } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Plus, ChevronDown, FolderOpen, ClipboardList, Loader2, FileSearch, AlertTriangle, Trash2, RefreshCw, RotateCcw, Search, ArrowUpDown, ArrowUp, ArrowDown, X, Sparkles, Send, Bot, ExternalLink, Settings, UploadCloud, FileArchive, FileText } from "lucide-react";
import { useSystemAgent, type SystemMessage } from "@/hooks/useSystemAgent";

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

const US_STATES: { code: string; name: string }[] = [
  { code: "AL", name: "Alabama" }, { code: "AK", name: "Alaska" },
  { code: "AZ", name: "Arizona" }, { code: "AR", name: "Arkansas" },
  { code: "CA", name: "California" }, { code: "CO", name: "Colorado" },
  { code: "CT", name: "Connecticut" }, { code: "DE", name: "Delaware" },
  { code: "DC", name: "District of Columbia" }, { code: "FL", name: "Florida" },
  { code: "GA", name: "Georgia" }, { code: "HI", name: "Hawaii" },
  { code: "ID", name: "Idaho" }, { code: "IL", name: "Illinois" },
  { code: "IN", name: "Indiana" }, { code: "IA", name: "Iowa" },
  { code: "KS", name: "Kansas" }, { code: "KY", name: "Kentucky" },
  { code: "LA", name: "Louisiana" }, { code: "ME", name: "Maine" },
  { code: "MD", name: "Maryland" }, { code: "MA", name: "Massachusetts" },
  { code: "MI", name: "Michigan" }, { code: "MN", name: "Minnesota" },
  { code: "MS", name: "Mississippi" }, { code: "MO", name: "Missouri" },
  { code: "MT", name: "Montana" }, { code: "NE", name: "Nebraska" },
  { code: "NV", name: "Nevada" }, { code: "NH", name: "New Hampshire" },
  { code: "NJ", name: "New Jersey" }, { code: "NM", name: "New Mexico" },
  { code: "NY", name: "New York" }, { code: "NC", name: "North Carolina" },
  { code: "ND", name: "North Dakota" }, { code: "OH", name: "Ohio" },
  { code: "OK", name: "Oklahoma" }, { code: "OR", name: "Oregon" },
  { code: "PA", name: "Pennsylvania" }, { code: "RI", name: "Rhode Island" },
  { code: "SC", name: "South Carolina" }, { code: "SD", name: "South Dakota" },
  { code: "TN", name: "Tennessee" }, { code: "TX", name: "Texas" },
  { code: "UT", name: "Utah" }, { code: "VT", name: "Vermont" },
  { code: "VA", name: "Virginia" }, { code: "WA", name: "Washington" },
  { code: "WV", name: "West Virginia" }, { code: "WI", name: "Wisconsin" },
  { code: "WY", name: "Wyoming" },
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
  const [files, setFiles] = useState<File[]>([]);
  const [formOpen, setFormOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mobileFileInputRef = useRef<HTMLInputElement>(null);
  const [showCreateMobile, setShowCreateMobile] = useState(false);
  const [showAgent, setShowAgent] = useState(false);
  const [agentInput, setAgentInput] = useState("");
  const agent = useSystemAgent();
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loaded, setLoaded] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [search, setSearch] = useState("");
  const [naicsFilter, setNaicsFilter] = useState<string>("");
  const [stateFilter, setStateFilter] = useState<string>("");
  const [naicsCodes, setNaicsCodes] = useState<{ code: string; title: string }[]>([]);
  const [naicsDropdownOpen, setNaicsDropdownOpen] = useState(false);
  const [naicsSearch, setNaicsSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortDir, setSortDir] = useState<SortDir>("asc");

  // Pagination
  const PAGE_SIZE = 50;
  const [offset, setOffset] = useState(0);
  const [total, setTotal] = useState(0);

  const refresh = useCallback(async (newOffset = 0) => {
    const res = await listSolicitations({ limit: PAGE_SIZE, offset: newOffset });
    setSolicitations(res.solicitations);
    setTotal(res.total ?? res.count ?? 0);
    setOffset(newOffset);
    setLoaded(true);
  }, []);

  // Initial load
  const mountedRef = useRef(false);
  useEffect(() => {
    if (mountedRef.current) return;
    mountedRef.current = true;
    refresh();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Load NAICS codes for filter dropdown
  useEffect(() => {
    listNaicsCodes().then(setNaicsCodes).catch(() => {});
  }, []);

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
    setFiles([]);
    setCreateError("");
  };

  const isManualEntry = sourceType === "federal" && manualFederal;
  const needsManualFields = sourceType !== "federal" || isManualEntry;

  const handleCreate = async () => {
    // If files are attached, use the direct Smart Ingest workflow (no SAM download bottleneck)
    if (files.length > 0) {
      setCreateError("");
      setCreating(true);
      try {
        const formData = new FormData();
        formData.append("source_type", sourceType);
        if (url.trim()) formData.append("url", url.trim());
        if (title.trim()) formData.append("title", title.trim());
        if (description.trim()) formData.append("description", description.trim());
        files.forEach((f) => formData.append("files", f));

        await ingestSolicitationPackage(formData);
        resetForm();
        setFormOpen(false);
        setShowCreateMobile(false);
        await refresh();
      } catch (err: unknown) {
        setCreateError(err instanceof Error ? err.message : "Failed to ingest package");
      } finally {
        setCreating(false);
      }
      return;
    }

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
      setFormOpen(false);
      setShowCreateMobile(false);
      setManualFederal(false);
      if (needsManualFields) {
        // No sam_fetch job — send user to Documents tab to upload files.
        router.push(`/cases/${solicitation.case_id}?tab=documents`);
      } else {
        await refresh();
      }
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create solicitation");
    } finally {
      setCreating(false);
    }
  };

  const [triaging, setTriaging] = useState<number | null>(null);
  const [rerunning, setRerunning] = useState<number | null>(null);

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

  const handleRerun = async (id: number) => {
    if (!confirm("Restart this solicitation from scratch? This re-fetches SAM.gov, re-runs triage, and re-matches vendors. Old data will be replaced.")) return;
    setRerunning(id);
    try {
      await rerunSolicitation(id);
      refresh();
    } catch {
      // keep row, let user retry
    } finally {
      setRerunning(null);
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
        (!naicsFilter || s.naics_code === naicsFilter) &&
        (!stateFilter || ((s.place_of_performance as Record<string, unknown> | null)?.state as Record<string, unknown> | undefined)?.code === stateFilter) &&
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
            <button onClick={() => router.push("/my-work")}
                    className="text-xs text-text-secondary hover:text-brand transition-colors
                               flex items-center gap-1">
              <ClipboardList size={14} />
              <span className="hidden sm:inline">My Work</span>
            </button>

            <button onClick={() => router.push("/cases")}
                    className="text-xs text-text-secondary hover:text-brand transition-colors
                               flex items-center gap-1">
              <FolderOpen size={14} />
              <span className="hidden sm:inline">Cases</span>
            </button>

            {user?.role === "admin" && (
              <button onClick={() => router.push("/settings")}
                      className="text-xs text-text-secondary hover:text-brand transition-colors
                                 flex items-center gap-1"
                      title="Settings">
                <Settings size={14} />
              </button>
            )}

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
        {/* --- Create Solicitation (Desktop Collapsible Card) --- */}
        <div className="hidden sm:block bg-surface-1 border border-border rounded-lg mb-6 shadow-sm overflow-hidden transition-all">
          <div
            onClick={() => setFormOpen((prev) => !prev)}
            className="flex items-center justify-between p-4 cursor-pointer hover:bg-surface-2/40 select-none transition-colors"
          >
            <div className="flex items-center gap-3">
              <div className="size-8 rounded-lg bg-brand/10 text-brand flex items-center justify-center font-bold shrink-0">
                <Plus size={18} className={`transition-transform duration-200 ${formOpen ? "rotate-45 text-text-secondary" : "text-brand"}`} />
              </div>
              <div>
                <h2 className="text-sm font-semibold text-text-primary">New Solicitation</h2>
                <p className="text-xs text-text-disabled">Upload attachments directly — bypasses SAM.gov download rate limits</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-secondary font-medium px-2.5 py-1 rounded-md border border-border bg-surface-2 hover:bg-surface-3 flex items-center gap-1.5 transition-colors">
                {formOpen ? "Collapse Form" : "Create Solicitation"}
                <ChevronDown size={14} className={`transition-transform duration-200 ${formOpen ? "rotate-180" : ""}`} />
              </span>
            </div>
          </div>

          {formOpen && (
            <div className="px-5 pb-5 pt-3 border-t border-border">
              {sourceTypeSelector}

              {/* SAM Opportunity URL */}
              {!needsManualFields && (
                <div className="mb-3">
                  <div className="flex items-center gap-1.5 mb-1.5">
                    <label className="text-xs font-medium text-text-secondary">SAM.gov Opportunity URL or Notice ID</label>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-disabled font-medium uppercase tracking-wide">Optional</span>
                    <span className="text-[10px] text-text-disabled">— if provided without title/description, metadata will be fetched in the background</span>
                  </div>
                  <input
                    className={`w-full ${inputClasses}`}
                    placeholder={urlPlaceholder}
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                  />
                </div>
              )}

              {/* Title */}
              <div className="mb-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <label className="text-xs font-medium text-text-secondary">Title</label>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-disabled font-medium uppercase tracking-wide">Optional</span>
                  <span className="text-[10px] text-text-disabled">— auto-derived from SAM.gov if URL provided</span>
                </div>
                <input
                  className={`w-full ${inputClasses}`}
                  placeholder="Solicitation title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
              </div>

              {/* Description */}
              <div className="mb-4">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <label className="text-xs font-medium text-text-secondary">Description</label>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-surface-3 text-text-disabled font-medium uppercase tracking-wide">Optional</span>
                  <span className="text-[10px] text-text-disabled">— auto-populated from SAM.gov in background when available</span>
                </div>
                <textarea
                  rows={2}
                  className={`w-full resize-none ${inputClasses}`}
                  placeholder="What is this solicitation for? (Leave blank to auto-populate from SAM.gov)"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
              </div>

              {/* Document Dropzone — REQUIRED */}
              <div className="mb-3">
                <div className="flex items-center gap-1.5 mb-1.5">
                  <label className="text-xs font-medium text-text-secondary">Solicitation Documents</label>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-brand/10 text-brand font-semibold uppercase tracking-wide">Required</span>
                  <span className="text-[10px] text-text-disabled">— upload the .ZIP &ldquo;Download All&rdquo; package or individual files from SAM.gov</span>
                </div>
                <div
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => {
                    e.preventDefault();
                    if (e.dataTransfer.files) {
                      const newFiles = Array.from(e.dataTransfer.files);
                      setFiles((prev) => [...prev, ...newFiles]);
                    }
                  }}
                  className={`border-2 border-dashed rounded-lg p-4 text-center transition-colors cursor-pointer
                    ${files.length > 0
                      ? "border-brand/40 bg-brand/5"
                      : "border-border hover:border-brand/50 bg-surface-2/30"
                    }`}
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files) {
                        const newFiles = Array.from(e.target.files);
                        setFiles((prev) => [...prev, ...newFiles]);
                      }
                    }}
                  />
                  <div className="flex flex-col items-center justify-center gap-1 pointer-events-none">
                    <UploadCloud size={22} className={files.length > 0 ? "text-brand mb-0.5" : "text-text-disabled mb-0.5"} />
                    <div className="text-xs font-medium text-text-primary">
                      {files.length > 0
                        ? <><span className="text-brand font-semibold">{files.length} file{files.length > 1 ? "s" : ""} selected</span> — click or drop to add more</>
                        : <>Drop <span className="font-semibold text-brand">.ZIP</span> package or files here, or <span className="underline text-brand">click to browse</span></>
                      }
                    </div>
                    <div className="text-[11px] text-text-disabled">
                      Accepts: .zip, .pdf, .docx, .doc, .xlsx, .txt, .csv, .md — ZIP files are auto-extracted
                    </div>
                  </div>
                </div>

                {/* Attached Files List */}
                {files.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2 max-h-36 overflow-y-auto p-1.5 bg-surface-2/60 rounded-md border border-border">
                    {files.map((f, idx) => (
                      <div
                        key={`${f.name}-${idx}`}
                        className="flex items-center gap-1.5 px-2.5 py-1 bg-surface-1 border border-border rounded text-xs text-text-primary shadow-xs"
                      >
                        {f.name.toLowerCase().endsWith(".zip") ? (
                          <FileArchive size={14} className="text-warning shrink-0" />
                        ) : (
                          <FileText size={14} className="text-text-secondary shrink-0" />
                        )}
                        <span className="truncate max-w-[220px]" title={f.name}>{f.name}</span>
                        <span className="text-[10px] text-text-disabled shrink-0">
                          ({f.size > 1024 * 1024 ? `${(f.size / (1024 * 1024)).toFixed(1)} MB` : `${Math.round(f.size / 1024)} KB`})
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setFiles((prev) => prev.filter((_, i) => i !== idx));
                          }}
                          className="hover:text-danger ml-1"
                          title="Remove file"
                        >
                          <X size={12} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {createError && (
                <p className="text-danger text-xs mb-3">{createError}</p>
              )}

              <div className="flex items-center justify-between pt-2 border-t border-border mt-2">
                <span className="text-xs text-text-disabled">
                  {files.length > 0
                    ? `${files.length} file(s) ready — background ingestion &amp; triage will start immediately`
                    : <span className="text-warning text-xs">⚠ No files attached yet — documents are required to run triage</span>
                  }
                </span>
                <button
                  onClick={handleCreate}
                  disabled={creating || files.length === 0}
                  className="bg-brand hover:bg-brand-hover active:bg-brand-active
                             disabled:opacity-40 disabled:cursor-not-allowed
                             text-white px-5 py-2 rounded-lg text-sm font-medium
                             transition-colors duration-150 inline-flex items-center gap-2 shrink-0 shadow-xs"
                >
                  {creating && <Loader2 size={14} className="animate-spin" />}
                  {creating ? "Creating..." : "Create & Start Triage"}
                </button>
              </div>
            </div>
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
              <h2 className="text-lg font-semibold mb-3">New Solicitation</h2>
              <div className="flex flex-col gap-3">
                {sourceTypeSelector}

                {!needsManualFields && (
                  <div>
                    <label className="text-xs font-medium text-text-secondary block mb-1">
                      SAM.gov Opportunity URL or Notice ID <span className="text-[10px] text-text-disabled">(Optional)</span>
                    </label>
                    <input
                      className={`w-full ${inputClasses} text-[16px]`}
                      placeholder={urlPlaceholder}
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                    />
                  </div>
                )}

                <input
                  className={`${inputClasses} text-[16px]`}
                  placeholder="Solicitation title..."
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />

                <textarea
                  rows={2}
                  className={`resize-none ${inputClasses} text-[16px]`}
                  placeholder="Description (optional)..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />

                {/* Mobile Dropzone */}
                <div
                  className="border-2 border-dashed border-border rounded-lg p-3 text-center bg-surface-2/30"
                  onClick={() => mobileFileInputRef.current?.click()}
                >
                  <input
                    ref={mobileFileInputRef}
                    type="file"
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files) {
                        setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
                      }
                    }}
                  />
                  <UploadCloud size={20} className="text-brand mx-auto mb-1" />
                  <div className="text-xs font-medium">Attach .ZIP or document files</div>
                  <div className="text-[10px] text-text-disabled">Tap to select files</div>
                </div>

                {files.length > 0 && (
                  <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
                    {files.map((f, idx) => (
                      <span key={idx} className="inline-flex items-center gap-1 text-[11px] bg-surface-2 px-2 py-0.5 rounded">
                        {f.name}
                        <button type="button" onClick={() => setFiles((p) => p.filter((_, i) => i !== idx))}><X size={10} /></button>
                      </span>
                    ))}
                  </div>
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
                    {creating ? "Ingesting & Triaging..." : (files.length > 0 ? "Create & Start Triage" : "Create Solicitation")}
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

        {/* === NAICS + State filters === */}
        <div className="flex items-center gap-2 mb-2 flex-wrap">
          {/* NAICS searchable combobox */}
          <div className="relative">
            <input
              type="text"
              placeholder={naicsFilter ? `${naicsFilter} — ${naicsCodes.find(n => n.code === naicsFilter)?.title?.slice(0, 40) || ""}` : "Filter by NAICS…"}
              value={naicsFilter ? `${naicsFilter} — ${naicsCodes.find(n => n.code === naicsFilter)?.title || ""}` : naicsSearch}
              onChange={(e) => {
                const val = e.target.value;
                if (naicsFilter) {
                  // Clear the filter if user starts typing
                  setNaicsFilter("");
                  setNaicsSearch(val);
                } else {
                  setNaicsSearch(val);
                }
                setNaicsDropdownOpen(true);
              }}
              onFocus={() => setNaicsDropdownOpen(true)}
              onBlur={() => setTimeout(() => setNaicsDropdownOpen(false), 200)}
              className={`bg-surface-2 border rounded-sm px-3 py-2 text-sm
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         transition-colors duration-150 min-w-[200px] ${
                           naicsFilter ? "border-brand text-brand" : "border-border"
                         }`}
            />
            {naicsFilter && (
              <button
                onClick={() => { setNaicsFilter(""); setNaicsSearch(""); }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-text-disabled hover:text-text-secondary"
              >
                <X size={14} />
              </button>
            )}
            {naicsDropdownOpen && !naicsFilter && (
              <div className="absolute top-full mt-1 left-0 z-40 max-h-48 overflow-y-auto
                              bg-surface-1 border border-border rounded-md shadow-lg min-w-[320px]">
                {naicsCodes
                  .filter(n => !naicsSearch ||
                    n.code.includes(naicsSearch) ||
                    n.title.toLowerCase().includes(naicsSearch.toLowerCase()))
                  .slice(0, 50)
                  .map(n => (
                    <button
                      key={n.code}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        setNaicsFilter(n.code);
                        setNaicsSearch("");
                        setNaicsDropdownOpen(false);
                      }}
                      className="w-full text-left px-3 py-1.5 text-sm hover:bg-surface-2
                                 transition-colors flex items-center gap-2"
                    >
                      <span className="text-text-disabled text-[11px] font-mono shrink-0">{n.code}</span>
                      <span className="text-text-secondary truncate">{n.title}</span>
                    </button>
                  ))}
                {naicsCodes.filter(n => !naicsSearch ||
                    n.code.includes(naicsSearch) ||
                    n.title.toLowerCase().includes(naicsSearch.toLowerCase())).length === 0 && (
                  <div className="px-3 py-2 text-sm text-text-disabled">No matching NAICS codes</div>
                )}
              </div>
            )}
          </div>

          {/* State dropdown */}
          <select
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
            className="bg-surface-2 border border-border rounded-sm px-3 py-2 text-sm
                       focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                       transition-colors duration-150"
          >
            <option value="">All states</option>
            {US_STATES.map((st) => (
              <option key={st.code} value={st.code}>{st.name}</option>
            ))}
          </select>

          {/* Clear filters */}
          {(naicsFilter || stateFilter) && (
            <button
              onClick={() => { setNaicsFilter(""); setNaicsSearch(""); setStateFilter(""); }}
              className="text-[11px] px-2.5 py-1 rounded-md border border-border
                         text-text-secondary hover:border-border-strong hover:text-text-primary
                         transition-colors inline-flex items-center gap-1"
            >
              <X size={12} />
              Clear filters
            </button>
          )}
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
              <div className="p-3">
                <div className="flex items-start gap-2">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-text-primary truncate">{s.title}</p>
                    <p className="text-[10px] text-text-disabled truncate mt-0.5">
                      {s.agency || s.url}
                      {s.notice_id && (
                        <>
                          {" · "}
                          <a
                            href={`https://sam.gov/search?index=opp&keywords=${encodeURIComponent(s.notice_id)}&sort=-modifiedDate`}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={async (e) => {
                              e.stopPropagation();
                              e.preventDefault();
                              try {
                                const result = await lookupSolicitationUrl(s.notice_id!);
                                window.open(result.ui_link, "_blank", "noopener,noreferrer");
                              } catch {
                                window.open(e.currentTarget.getAttribute("href")!, "_blank", "noopener,noreferrer");
                              }
                            }}
                            className="text-brand hover:underline inline-flex items-center gap-0.5"
                          >
                            {s.notice_id}
                            <ExternalLink size={10} />
                          </a>
                        </>
                      )}
                    </p>
                  </div>
                  {(s.quotes_submitted ?? 0) > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded font-medium shrink-0 bg-success-bg text-success">
                      {s.quotes_submitted} quote{s.quotes_submitted !== 1 ? "s" : ""}
                    </span>
                  )}
                  {(s.quotes_draft ?? 0) > 0 && (
                    <span className="text-[10px] px-2 py-0.5 rounded font-medium shrink-0 bg-warning-bg text-warning">
                      {s.quotes_draft} draft
                    </span>
                  )}
                  {s.unread_replies ? (
                    <span className="text-[11px] px-2 py-0.5 rounded-full font-bold shrink-0 bg-danger text-white">
                      {s.unread_replies}
                    </span>
                  ) : null}
                </div>
                {/* NAICS + Place of Performance metadata */}
                {(s.naics_code || s.place_of_performance) && (
                  <div className="flex items-center gap-2 mt-1.5 text-[11px] text-text-secondary">
                    {s.naics_code && (
                      <span className="inline-flex items-center gap-1">
                        <span className="text-text-disabled">NAICS:</span>
                        <span className="font-mono text-text-secondary">{s.naics_code}</span>
                        {s.naics_label && (
                          <span className="text-text-disabled truncate max-w-[200px]">
                            — {s.naics_label}
                          </span>
                        )}
                      </span>
                    )}
                    {s.naics_code && s.place_of_performance && (
                      <span className="text-text-disabled">·</span>
                    )}
                    {s.place_of_performance && (
                      <span className="inline-flex items-center gap-1 truncate">
                        <span className="text-text-disabled shrink-0">📍</span>
                        {(() => {
                          const pop = s.place_of_performance as Record<string, unknown>;
                          const city = (pop?.city as Record<string, unknown>)?.name;
                          const state = (pop?.state as Record<string, unknown>)?.code;
                          return city && state ? `${city}, ${state}` : null;
                        })()}
                      </span>
                    )}
                  </div>
                )}
                <div className="flex items-center gap-1.5 mt-2 flex-wrap">
                  <span
                    className={`text-[10px] px-2 py-0.5 rounded-sm font-medium ${
                      SOURCE_TYPE_COLORS[s.source_type] || "bg-surface-2 text-text-secondary"
                    }`}
                  >
                    {s.source_type}
                  </span>
                  <span
                    className={`inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-sm font-medium ${
                      STATUS_COLORS[s.ingestion_status] || "bg-surface-2 text-text-secondary"
                    }`}
                  >
                    {(s.ingestion_status === "pending" || s.ingestion_status === "fetching") && (
                      <Loader2 size={10} className="animate-spin" />
                    )}
                    {s.ingestion_status}
                  </span>
                  {s.has_outreach && (
                    <span className="text-[10px] px-2 py-0.5 rounded-sm font-medium bg-success-bg text-success">
                      outreach sent
                    </span>
                  )}
                  {s.has_missing_docs && (
                    <span title="Some attachments failed to download" className="shrink-0">
                      <AlertTriangle size={14} className="text-warning" />
                    </span>
                  )}
                {s.ingestion_status === "complete" && (
                  <span
                    title={s.triage_error || undefined}
                    className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-sm font-medium shrink-0 ${
                      TRIAGE_STATUS_COLORS[s.triage_status] || "bg-surface-2 text-text-secondary"
                    }`}
                  >
                    {s.triage_status === "running" && (
                      <Loader2 size={10} className="animate-spin" />
                    )}
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
                {/* Assignee (read-only — manage inside case Overview tab) */}
                {s.assignee_username && (
                  <span className="text-[11px] text-text-secondary shrink-0 ml-1">
                    <span className="text-text-disabled">·</span>{" "}
                    <span className="font-medium">{s.assignee_username}</span>
                  </span>
                )}
                {s.source_type === "federal" && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRerun(s.id);
                    }}
                    disabled={rerunning === s.id}
                    title="Restart from SAM.gov fetch"
                    className="p-1.5 rounded-md text-text-disabled shrink-0
                               hover:bg-info-bg hover:text-info
                               disabled:opacity-50 disabled:cursor-not-allowed
                               transition-colors duration-150"
                    aria-label="Rerun solicitation"
                  >
                    {rerunning === s.id ? (
                      <Loader2 size={14} className="animate-spin" />
                    ) : (
                      <RotateCcw size={14} />
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
            </div>
          ))}

          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-center">
              <FileSearch size={32} className="text-text-disabled" />
              <p className="text-sm text-text-secondary">No solicitations yet</p>
              <p className="text-xs text-text-disabled">Paste a SAM.gov URL above to get started.</p>
            </div>
          )}

          {/* Pagination — only render after first data load to avoid hydration mismatch */}
          {loaded && (
          <div className="flex items-center justify-between px-4 py-3 border-t border-border text-sm">
            <span className="text-text-secondary">
              {total.toLocaleString()} total · showing {offset + 1}–{Math.min(offset + PAGE_SIZE, total)}
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => refresh(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-3 py-1 border border-border rounded-md disabled:opacity-30 hover:bg-surface-50"
              >
                Previous
              </button>
              <button
                onClick={() => refresh(offset + PAGE_SIZE)}
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
      {/* System Agent FAB */}
      <button
        onClick={() => setShowAgent(!showAgent)}
        className={`fixed bottom-6 right-6 z-40 size-14 rounded-full shadow-lg
                     flex items-center justify-center transition-all duration-200
                     ${showAgent ? "bg-danger text-white rotate-45" : "bg-brand text-white hover:bg-brand-hover"}`}
        aria-label="System Agent"
      >
        {showAgent ? <X size={22} /> : <Sparkles size={22} />}
      </button>

      {/* System Agent Panel */}
      {showAgent && (
        <div className="fixed bottom-24 right-6 z-40 w-[380px] max-w-[calc(100vw-2rem)]
                        h-[550px] max-h-[70vh] bg-surface-1 border border-border rounded-xl
                        shadow-2xl flex flex-col overflow-hidden">
          {/* Header */}
          <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b border-border">
            <div className="flex items-center gap-2">
              <Bot size={18} className="text-brand" />
              <span className="text-sm font-semibold">System Agent</span>
            </div>
            <button onClick={agent.clear} className="text-xs text-text-disabled hover:text-text-secondary">
              Clear
            </button>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {agent.messages.length === 0 && (
              <p className="text-xs text-text-disabled text-center py-8">
                Ask me anything — case status, job queue, SAM notices, vendor replies…
              </p>
            )}
            {agent.messages.map((msg, i) => (
              <div key={i} className={`text-xs leading-relaxed ${msg.role === "user" ? "text-right" : ""}`}>
                <span className={`inline-block max-w-[85%] rounded-lg px-3 py-2 ${
                  msg.role === "user"
                    ? "bg-brand text-white"
                    : "bg-surface-2 text-text-primary"
                }`}>
                  <span className="whitespace-pre-wrap">{msg.content}</span>
                </span>
              </div>
            ))}
            {agent.loading && (
              <div className="text-xs text-text-disabled flex items-center gap-1">
                <Loader2 size={12} className="animate-spin" />
                Thinking…
              </div>
            )}
          </div>

          {/* Input */}
          <form
            onSubmit={(e) => { e.preventDefault(); agent.send(agentInput); setAgentInput(""); }}
            className="shrink-0 border-t border-border p-3 flex gap-2"
          >
            <input
              value={agentInput}
              onChange={(e) => setAgentInput(e.target.value)}
              placeholder="Ask about cases, jobs, notices..."
              className="flex-1 text-xs bg-surface-2 border border-border rounded-lg px-3 py-2
                         text-text-primary placeholder:text-text-disabled outline-none focus:border-brand"
            />
            <button
              type="submit"
              disabled={agent.loading || !agentInput.trim()}
              className="bg-brand text-white px-3 py-2 rounded-lg disabled:opacity-50"
            >
              <Send size={14} />
            </button>
          </form>
        </div>
      )}
    </main>
  );
}
