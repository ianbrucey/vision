"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { listCases, listJobs, createCase, deleteCase, healthCheck, listCompanyProfiles, type CompanyProfile } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import { Plus, FolderOpen, Trash2, Loader2, Building2 } from "lucide-react";

interface Case {
  id: number;
  name: string;
  case_type: string;
  status: string;
  created_at: string;
}

interface Job {
  id: number;
  case_id: number;
  job_type: string;
  status: string;
  progress_pct: number;
  storage_ref: { original_name?: string } | null;
  created_at: string;
}

export default function Dashboard() {
  const { user, logout } = useAuth();
  const router = useRouter();
  const [cases, setCases] = useState<Case[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [newName, setNewName] = useState("");
  const [newType, setNewType] = useState("other");
  const [createError, setCreateError] = useState("");
  const [creating, setCreating] = useState(false);
  const [deleting, setDeleting] = useState<number | null>(null);
  const [showCreateMobile, setShowCreateMobile] = useState(false);
  const [typeFilter, setTypeFilter] = useState<string>("all");
  const [profiles, setProfiles] = useState<CompanyProfile[]>([]);

  const refresh = useCallback(async () => {
    try { await healthCheck(); setApiOk(true); } catch { setApiOk(false); return; }
    const [c, j] = await Promise.all([listCases(), listJobs()]);
    setCases(c); setJobs(j);
    // Fetch profiles
    try { const p = await listCompanyProfiles(); setProfiles(p.profiles); } catch {}
  }, []);

  // Initial load + polling
  const mountedRef = useRef(false);
  useEffect(() => {
    if (mountedRef.current) return;
    mountedRef.current = true;
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreateError("");
    setCreating(true);
    try {
      await createCase({ name: newName, case_type: newType });
      setNewName("");
      setShowCreateMobile(false);
      refresh();
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : "Failed to create case");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: number) => {
    setDeleting(id);
    try {
      await deleteCase(id);
      refresh();
    } catch {
      // keep the row, let user retry
    } finally {
      setDeleting(null);
    }
  };

  const caseTypeLabel = (t: string) => t.replace(/_/g, " ");

  const statusPill = (status: string) => {
    const map: Record<string, string> = {
      complete: "bg-success-bg text-success",
      intake: "bg-info-bg text-info",
      indexing: "bg-warning-bg text-warning",
      analysis: "bg-info-bg text-info",
      drafting: "bg-brand-bg text-brand",
      archived: "bg-surface-3 text-text-disabled",
    };
    return map[status] || "bg-surface-2 text-text-secondary";
  };

  const jobStatusPill = (status: string) => {
    const map: Record<string, string> = {
      complete: "bg-success-bg text-success",
      processing: "bg-warning-bg text-warning",
      queued: "bg-info-bg text-info",
      failed: "bg-danger-bg text-danger",
    };
    return map[status] || "bg-surface-2 text-text-secondary";
  };

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

          {/* Right: profile link + status + user */}
          <div className="flex items-center gap-3 sm:gap-4 shrink-0">
            <button onClick={() => router.push("/profile")}
                    className="text-xs text-text-secondary hover:text-brand transition-colors
                               flex items-center gap-1">
              <Building2 size={14} />
              <span className="hidden sm:inline">Profile</span>
            </button>
            {/* API status pill */}
            <span className="inline-flex items-center gap-1.5 text-xs text-text-secondary">
              <span
                className={`size-2 rounded-full shrink-0 ${
                  apiOk === true
                    ? "bg-success"
                    : apiOk === false
                      ? "bg-danger"
                      : "bg-warning animate-pulse"
                }`}
              />
              <span className="hidden sm:inline">
                {apiOk === true ? "Online" : apiOk === false ? "Offline" : "..."}
              </span>
            </span>

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
        {/* --- Create Case (Desktop) --- */}
        <div className="hidden sm:block bg-surface-1 border border-border rounded-lg p-4 mb-6">
          <h2 className="text-sm font-medium text-text-secondary mb-3">New Case</h2>
          <div className="flex gap-3">
            <input
              className="flex-1 bg-surface-2 border border-border rounded-sm px-3 py-2 text-sm
                         placeholder:text-text-disabled
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         transition-colors duration-150"
              placeholder="Case name..."
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
            <select
              className="bg-surface-2 border border-border rounded-sm px-3 py-2 text-sm
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         transition-colors duration-150"
              value={newType}
              onChange={(e) => setNewType(e.target.value)}
            >
              <option value="other">Other</option>
              <option value="medical_board_complaint">Medical Board Complaint</option>
              <option value="civil_litigation">Civil Litigation</option>
              <option value="contract_review">Contract Review</option>
              <option value="e_discovery">E-Discovery</option>
              <option value="rfp_response">RFP Response</option>
            </select>
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
          {createError && (
            <p className="text-danger text-xs mt-2">{createError}</p>
          )}
        </div>

        {/* --- Create Case (Mobile FAB) --- */}
        <button
          onClick={() => setShowCreateMobile(true)}
          className="sm:hidden fixed bottom-20 right-4 z-20 size-14 rounded-full
                     bg-brand text-white shadow-md
                     hover:bg-brand-hover active:bg-brand-active
                     flex items-center justify-center transition-colors duration-150"
          aria-label="Create case"
        >
          <Plus size={24} />
        </button>

        {/* --- Create Case (Mobile Modal) --- */}
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
              <h2 className="text-lg font-semibold mb-4">New Case</h2>
              <div className="flex flex-col gap-3">
                <input
                  className="bg-surface-2 border border-border rounded-sm px-3 py-2 text-sm
                             placeholder:text-text-disabled text-[16px]
                             focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                             transition-colors duration-150"
                  placeholder="Case name..."
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  autoFocus
                />
                <select
                  className="bg-surface-2 border border-border rounded-sm px-3 py-2 text-sm
                             focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                             transition-colors duration-150"
                  value={newType}
                  onChange={(e) => setNewType(e.target.value)}
                >
                  <option value="other">Other</option>
                  <option value="medical_board_complaint">Medical Board Complaint</option>
                  <option value="civil_litigation">Civil Litigation</option>
                  <option value="contract_review">Contract Review</option>
                  <option value="e_discovery">E-Discovery</option>
                  <option value="rfp_response">RFP Response</option>
                </select>
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
                    {creating ? "Creating..." : "Create Case"}
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

        {/* === Company Profile === */}
        {profiles.length > 0 ? (
          <div
            onClick={() => router.push("/profile")}
            className="bg-surface-1 border border-border rounded-xl p-5 mb-6
                       cursor-pointer hover:border-brand transition-colors"
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Building2 size={16} className="text-brand" />
                <h2 className="text-sm font-semibold">{profiles[0].name}</h2>
              </div>
              <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${
                profiles[0].status === "complete" ? "bg-success-bg text-success" : "bg-warning-bg text-warning"
              }`}>
                {profiles[0].status === "complete" ? "Complete" : "Draft"}
              </span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              {["cage_code", "uei", "naics_codes", "certifications"].map((key) => {
                const val = profiles[0].content?.[key];
                const display = Array.isArray(val) ? (val as string[]).join(", ") : String(val || "");
                return (
                  <div key={key} className="text-xs">
                    <span className="text-text-disabled">{key === "uei" ? "UEI" : key === "naics_codes" ? "NAICS" : key === "cage_code" ? "CAGE" : "Certs"}: </span>
                    <span className={display ? "font-medium" : "text-danger italic"}>
                      {display || "Not set"}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div
            onClick={() => router.push("/profile")}
            className="bg-surface-1 border border-dashed border-border rounded-xl p-5 mb-6
                       cursor-pointer hover:border-brand transition-colors text-center"
          >
            <Building2 size={24} className="text-text-disabled mx-auto mb-2" />
            <p className="text-sm text-text-secondary">No company profile yet</p>
            <p className="text-xs text-text-disabled mt-1">
              Create a profile for GovCon solicitations — CAGE codes, NAICS, certs, past performance.
            </p>
          </div>
        )}

        {/* === Type Filter + New Case === */}
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex gap-1.5">
            {["all", "rfp_response", "medical_board_complaint", "civil_litigation"].map((t) => (
              <button
                key={t}
                onClick={() => setTypeFilter(t)}
                className={`text-[11px] px-2.5 py-1 rounded-md border transition-colors ${
                  typeFilter === t
                    ? "bg-brand-bg border-brand text-brand"
                    : "border-border text-text-secondary hover:border-border-strong"
                }`}
              >
                {t === "all" ? "All" : t === "rfp_response" ? "RFP" : t === "medical_board_complaint" ? "Medical" : "Legal"}
              </button>
            ))}
          </div>
        </div>

        {/* === Cases List === */}
        <div className="flex flex-col gap-3">
          {cases.filter((c) => typeFilter === "all" || c.case_type === typeFilter).map((c) => {
            const caseJobs = jobs.filter((j) => j.case_id === c.id);
            const pending = caseJobs.filter(
              (j) => j.status === "queued" || j.status === "processing",
            );

            return (
              <div
                key={c.id}
                className="bg-surface-1 border border-border rounded-lg
                           hover:border-border-strong active:border-brand
                           transition-colors duration-150"
              >
                <div className="p-4 flex flex-col sm:flex-row sm:items-center gap-3">
                  {/* Case info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-semibold text-sm truncate">{c.name}</h3>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0 ${
                        c.case_type === "rfp_response" ? "bg-info-bg text-info" : "bg-surface-2 text-text-secondary"
                      }`}>
                        {c.case_type === "rfp_response" ? "RFP" : caseTypeLabel(c.case_type)}
                      </span>
                      <span
                        className={`text-xs px-2 py-0.5 rounded-sm shrink-0 ${statusPill(c.status)}`}
                      >
                        {c.status}
                      </span>
                    </div>
                    {(c as any).solicitation?.due_date && (
                      <p className="text-xs text-text-secondary mt-0.5">
                        Due {(c as any).solicitation.due_date}
                        {(c as any).solicitation?.set_aside && ` · ${(c as any).solicitation.set_aside}`}
                        {(c as any).solicitation?.agency && ` · ${(c as any).solicitation.agency}`}
                      </p>
                    )}
                    <p className="text-xs text-text-disabled mt-1">
                      {new Date(c.created_at).toLocaleDateString(undefined, {
                        year: "numeric",
                        month: "short",
                        day: "numeric",
                      })}
                    </p>
                    {pending.length > 0 && (
                      <div className="mt-2 flex items-center gap-1.5 text-xs text-warning">
                        <Loader2 size={12} className="animate-spin" />
                        {pending.length} job{pending.length > 1 ? "s" : ""} processing
                      </div>
                    )}
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0">
                    <button
                      onClick={() => router.push(`/cases/${c.id}`)}
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
                                 bg-surface-2 text-text-secondary border border-border
                                 hover:bg-surface-3 hover:text-text-primary hover:border-border-strong
                                 active:bg-surface-4
                                 transition-colors duration-150
                                 min-h-[44px] sm:min-h-0"
                    >
                      <FolderOpen size={14} />
                      <span className="hidden sm:inline">View Case</span>
                    </button>
                    <button
                      onClick={() => handleDelete(c.id)}
                      disabled={deleting === c.id}
                      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium
                                 text-danger border border-danger/20
                                 hover:bg-danger-bg active:bg-danger-bg/50
                                 disabled:opacity-50 disabled:cursor-not-allowed
                                 transition-colors duration-150
                                 min-h-[44px] sm:min-h-0"
                      aria-label="Delete case"
                    >
                      {deleting === c.id ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Trash2 size={14} />
                      )}
                      <span className="hidden sm:inline">Delete</span>
                    </button>
                  </div>
                </div>
              </div>
            );
          })}

          {cases.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 px-6 text-center gap-4">
              <div className="size-12 rounded-full bg-surface-2 flex items-center justify-center text-text-disabled">
                <FolderOpen size={24} />
              </div>
              <div>
                <p className="text-sm font-medium text-text-secondary">No cases yet</p>
                <p className="text-xs text-text-disabled mt-1">
                  Create your first case to get started.
                </p>
              </div>
            </div>
          )}
        </div>

        {/* === Job Queue === */}
        {jobs.length > 0 && (
          <div className="mt-8">
            <h2 className="text-sm font-medium text-text-secondary mb-3">Job Queue</h2>
            <div className="bg-surface-1 border border-border rounded-lg overflow-hidden">
              {/* Mobile: card list */}
              <div className="lg:hidden divide-y divide-border">
                {jobs.slice(0, 20).map((j) => (
                  <div key={j.id} className="p-3 flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-text-disabled">#{j.id}</span>
                        <span className="text-sm text-text-primary">{j.job_type}</span>
                      </div>
                      <p className="text-xs text-text-disabled mt-0.5 truncate">
                        {j.storage_ref?.original_name || "—"}
                      </p>
                      <div className="mt-1.5 w-full bg-surface-3 rounded-full h-1.5">
                        <div
                          className="bg-brand h-1.5 rounded-full transition-all duration-500"
                          style={{ width: `${j.progress_pct}%` }}
                        />
                      </div>
                    </div>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-sm shrink-0 ${jobStatusPill(j.status)}`}
                    >
                      {j.status}
                    </span>
                  </div>
                ))}
              </div>

              {/* Desktop: table */}
              <div className="hidden lg:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-border text-text-secondary">
                      <th className="text-left p-3 font-medium">Job</th>
                      <th className="text-left p-3 font-medium">Type</th>
                      <th className="text-left p-3 font-medium">Status</th>
                      <th className="text-left p-3 font-medium">Progress</th>
                      <th className="text-left p-3 font-medium">File</th>
                    </tr>
                  </thead>
                  <tbody>
                    {jobs.slice(0, 20).map((j) => (
                      <tr
                        key={j.id}
                        className="border-b border-border-light hover:bg-surface-2 transition-colors duration-100"
                      >
                        <td className="p-3 text-text-disabled">#{j.id}</td>
                        <td className="p-3">{j.job_type}</td>
                        <td className="p-3">
                          <span
                            className={`text-xs px-2 py-0.5 rounded-sm ${jobStatusPill(j.status)}`}
                          >
                            {j.status}
                          </span>
                        </td>
                        <td className="p-3">
                          <div className="w-24 bg-surface-3 rounded-full h-1.5">
                            <div
                              className="bg-brand h-1.5 rounded-full transition-all duration-500"
                              style={{ width: `${j.progress_pct}%` }}
                            />
                          </div>
                        </td>
                        <td className="p-3 text-xs text-text-disabled truncate max-w-[200px]">
                          {j.storage_ref?.original_name || "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
