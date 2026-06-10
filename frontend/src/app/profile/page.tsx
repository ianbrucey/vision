"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Loader2, Pencil, Sparkles, Plus, Upload, FileText, X } from "lucide-react";
import {
  listCompanyProfiles, createCompanyProfile, updateCompanyProfile,
  synthesizeProfile, generateCapabilityStatement, getJob, listJobs,
  getDraft, updateBlock,
  type CompanyProfile,
} from "@/lib/api";
import DraftPreview from "@/components/DraftPreview";

/* ================================================================== */
/* Helpers                                                             */
/* ================================================================== */

const FIELD_GROUPS: { key: string; label: string; fields: { key: string; label: string }[] }[] = [
  {
    key: "company_info", label: "Company Info",
    fields: [
      { key: "company_name", label: "Company Name" },
      { key: "legal_name", label: "Legal Name" },
      { key: "dba", label: "DBA" },
      { key: "tax_id", label: "Tax ID" },
    ],
  },
  {
    key: "codes", label: "Codes & Identifiers",
    fields: [
      { key: "cage_code", label: "CAGE Code" },
      { key: "uei", label: "UEI" },
      { key: "psc_codes", label: "PSC Codes" },
    ],
  },
  {
    key: "naics", label: "NAICS Codes",
    fields: [
      { key: "naics_codes", label: "NAICS Codes" },
    ],
  },
  {
    key: "certifications", label: "Certifications",
    fields: [
      { key: "certifications", label: "Certifications" },
    ],
  },
  {
    key: "contact", label: "Contact",
    fields: [
      { key: "address", label: "Address" },
      { key: "phone", label: "Phone" },
      { key: "email", label: "Email" },
    ],
  },
];

const FIELD_STATUS_LABELS: Record<string, string> = {
  verified: "Verified",
  agent_filled: "Agent filled",
  uncertain: "Uncertain",
  needs_input: "Needs input",
};

const FIELD_STATUS_CLASSES: Record<string, string> = {
  verified: "bg-success-bg text-success",
  agent_filled: "bg-info-bg text-info",
  uncertain: "bg-warning-bg text-warning",
  needs_input: "bg-danger-bg text-danger",
};

function fieldStatus(content: Record<string, any>, key: string): string {
  const fs = content?.field_status as Record<string, string> | undefined;
  return fs?.[key] || "needs_input";
}

function dotClass(status: string): string {
  return status === "verified" ? "bg-success" : status === "agent_filled" ? "bg-info" : status === "uncertain" ? "bg-warning" : "bg-danger";
}

function formatValue(val: unknown): string {
  if (val === null || val === undefined || val === "") return "";
  if (Array.isArray(val)) return val.join(", ");
  return String(val);
}

/* ================================================================== */
/* Component                                                           */
/* ================================================================== */

export default function CompanyProfilePage() {
  const router = useRouter();
  const [profiles, setProfiles] = useState<CompanyProfile[]>([]);
  const [activeId, setActiveId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [editMode, setEditMode] = useState(false);
  const [editContent, setEditContent] = useState<Record<string, any>>({});
  const [editDesc, setEditDesc] = useState("");
  const [saving, setSaving] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [synthing, setSynthing] = useState(false);
  const [synthJobId, setSynthJobId] = useState<number | null>(null);
  const [synthError, setSynthError] = useState<string | null>(null);
  const [genLoading, setGenLoading] = useState(false);
  const [stmtDraft, setStmtDraft] = useState<any>(null);
  const [stmtEditMode, setStmtEditMode] = useState(false);

  // Inline add forms
  const [addPersonnel, setAddPersonnel] = useState(false);
  const [addPastPerf, setAddPastPerf] = useState(false);
  const [newPerson, setNewPerson] = useState({ name: "", title: "", years_experience: "", clearance: "" });
  const [newPP, setNewPP] = useState({ client: "", contract_value: "", description: "", period_of_performance: "" });

  const active = profiles.find((p) => p.id === activeId) || null;

  const refresh = useCallback(async () => {
    try {
      const res = await listCompanyProfiles();
      setProfiles(res.profiles);
      if (res.profiles.length > 0 && !activeId) {
        setActiveId(res.profiles[0].id);
      }
    } catch { /* silent */ }
    setLoading(false);
  }, [activeId]);

  useEffect(() => { refresh(); }, []);

  // Resume in-progress jobs on mount (survives refresh)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const jobs = await listJobs() as any[];
        const active = jobs?.find(
          (j: any) => (j.job_type === "capability_statement" || j.job_type === "profile_synthesis" || j.job_type === "synthesize")
            && (j.status === "queued" || j.status === "processing")
        );
        if (!active || cancelled) return;
        if (active.job_type === "capability_statement") setGenLoading(true);
        else setSynthing(true);

        let attempts = 0;
        while (attempts < 60) {
          await new Promise((r) => setTimeout(r, 2000));
          if (cancelled) return;
          const job = await getJob(active.id);
          if (job.status === "complete") {
            await refresh();
            if (active.job_type === "capability_statement") setGenLoading(false);
            else setSynthing(false);
            return;
          }
          if (job.status === "failed") {
            if (active.job_type === "capability_statement") setGenLoading(false);
            else setSynthing(false);
            return;
          }
          attempts++;
        }
        setGenLoading(false);
        setSynthing(false);
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, []);

  // Fetch statement draft when profile changes
  useEffect(() => {
    if (!active) return;
    const draftId = (active as any)?.statement_draft_id;
    if (!draftId) { setStmtDraft(null); return; }
    getDraft(draftId).then((res) => setStmtDraft(res.draft)).catch(() => setStmtDraft(null));
  }, [active?.id, active?.statement_draft_id]);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    try {
      const res = await createCompanyProfile(newName.trim());
      setNewName(""); setShowCreate(false);
      await refresh();
      setActiveId(res.profile.id);
    } catch { /* silent */ }
  };

  const enterEditMode = () => {
    setEditContent({ ...(active?.content || {}) });
    setEditDesc((active as any)?.description || "");
    setEditMode(true);
  };

  const exitEditMode = async () => {
    if (!active) return;
    setSaving(true);
    try {
      const updates: any = { content: editContent };
      if (editDesc !== ((active as any)?.description || "")) {
        updates.description = editDesc;
      }
      // Mark all edited fields as verified
      const fs = { ...(editContent.field_status || {}) };
      const orig = active.content || {};
      for (const key of Object.keys(editContent)) {
        if (key !== "field_status" && key !== "past_performance" && key !== "key_personnel" && key !== "contact") {
          const origVal = JSON.stringify(orig[key]);
          const newVal = JSON.stringify(editContent[key]);
          if (origVal !== newVal) fs[key] = "verified";
        }
      }
      updates.content = { ...editContent, field_status: fs };
      await updateCompanyProfile(active.id, updates);
      await refresh();
    } catch { /* silent */ }
    setSaving(false);
    setEditMode(false);
  };

  const handleUpload = async (files: FileList) => {
    if (!active) return;
    setUploading(true);
    const fileArr = Array.from(files);
    for (const file of fileArr) {
      let docId: number | null = null;
      try {
        const form = new FormData();
        form.append("file", file);
        const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8400";
        const token = localStorage.getItem("vision_token");
        // Use profile-specific upload endpoint
        const res = await fetch(`${API_BASE}/api/profiles/${active.id}/upload`, {
          method: "POST", body: form,
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!res.ok) throw new Error("Upload failed");
        const data = await res.json();
        // Poll for ingest completion
        let attempts = 0;
        let lastJob: any = null;
        while (attempts < 60) {
          await new Promise((r) => setTimeout(r, 2000));
          lastJob = await getJob(data.job_id);
          if (lastJob.status === "complete") { docId = lastJob.document_id; break; }
          if (lastJob.status === "failed") throw new Error(lastJob.error_message || "Ingestion failed");
          attempts++;
        }
        // Update source_docs with the real document_id from the completed job
        const updatedDocs = ((active.source_docs as any[]) || []).map((d: any) =>
          d.job_id === data.job_id ? { ...d, document_id: docId } : d
        );
        await updateCompanyProfile(active.id, { source_docs: updatedDocs });
        await refresh();
      } catch (err) {
        console.error("Upload failed:", err);
      }
    }
    setUploading(false);
  };

  const handleDetachDoc = async (index: number) => {
    if (!active) return;
    const updated = ((active.source_docs as any[]) || []).filter((_: any, i: number) => i !== index);
    await updateCompanyProfile(active.id, { source_docs: updated });
    await refresh();
  };

  const handleGenerateStatement = async () => {
    if (!active) return;
    setGenLoading(true);
    try {
      const { job_id } = await generateCapabilityStatement(active.id);
      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 2000));
        const job = await getJob(job_id);
        if (job.status === "complete") { await refresh(); break; }
        if (job.status === "failed") { alert("Generation failed: " + (job.error_message || "Unknown error")); break; }
        attempts++;
      }
    } catch (err: any) {
      alert(err?.message || "Generation failed");
    }
    setGenLoading(false);
  };

  const handleAddPerson = async () => {
    if (!active || !newPerson.name.trim()) return;
    const content = { ...(active.content || {}) };
    const personnel = [...((content.key_personnel as any[]) || [])];
    personnel.push({
      name: newPerson.name.trim(),
      title: newPerson.title.trim(),
      years_experience: parseInt(newPerson.years_experience) || 0,
      clearance: newPerson.clearance.trim() || null,
      resume_document_id: null,
    });
    content.key_personnel = personnel;
    content.field_status = { ...(content.field_status || {}), key_personnel: "verified" };
    await updateCompanyProfile(active.id, { content });
    setNewPerson({ name: "", title: "", years_experience: "", clearance: "" });
    setAddPersonnel(false);
    await refresh();
  };

  const handleDeletePerson = async (idx: number) => {
    if (!active) return;
    const content = { ...(active.content || {}) };
    const personnel = [...((content.key_personnel as any[]) || [])];
    personnel.splice(idx, 1);
    content.key_personnel = personnel;
    await updateCompanyProfile(active.id, { content });
    await refresh();
  };

  const handleAddPP = async () => {
    if (!active || !newPP.client.trim()) return;
    const content = { ...(active.content || {}) };
    const pp = [...((content.past_performance as any[]) || [])];
    pp.push({
      client: newPP.client.trim(),
      contract_value: newPP.contract_value.trim(),
      description: newPP.description.trim(),
      period_of_performance: newPP.period_of_performance.trim(),
    });
    content.past_performance = pp;
    content.field_status = { ...(content.field_status || {}), past_performance: "verified" };
    await updateCompanyProfile(active.id, { content });
    setNewPP({ client: "", contract_value: "", description: "", period_of_performance: "" });
    setAddPastPerf(false);
    await refresh();
  };

  const handleDeletePP = async (idx: number) => {
    if (!active) return;
    const content = { ...(active.content || {}) };
    const pp = [...((content.past_performance as any[]) || [])];
    pp.splice(idx, 1);
    content.past_performance = pp;
    await updateCompanyProfile(active.id, { content });
    await refresh();
  };

  const handleSynthesize = async () => {
    if (!active) return;
    setSynthing(true);
    setSynthError(null);
    try {
      const { job_id } = await synthesizeProfile(active.id);
      setSynthJobId(job_id);
      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 2000));
        const job = await getJob(job_id);
        if (job.status === "complete") {
          await refresh();
          break;
        }
        if (job.status === "failed") {
          setSynthError(job.error_message || "Synthesis failed");
          break;
        }
        attempts++;
      }
      if (attempts >= 60) setSynthError("Synthesis timed out");
    } catch (err: any) {
      setSynthError(err?.message || "Synthesis failed");
    }
    setSynthing(false);
    setSynthJobId(null);
  };

  if (loading) {
    return (
      <div className="min-h-dvh bg-surface-0 flex items-center justify-center">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  return (
    <div className="min-h-dvh bg-surface-0 text-text-primary">
      <header className="sticky top-0 bg-surface-1 border-b border-border z-30">
        <div className="flex items-center h-14 px-4 gap-3 max-w-4xl mx-auto">
          <button onClick={() => router.push("/")}
                  className="text-text-secondary hover:text-text-primary transition-colors shrink-0
                             min-h-[44px] min-w-[44px] flex items-center justify-center -ml-2">
            <ArrowLeft size={20} />
          </button>
          <h1 className="text-sm font-semibold">Company Profile</h1>
          <div className="flex-1" />
          {profiles.length > 1 && (
            <select value={activeId || ""} onChange={(e) => setActiveId(Number(e.target.value))}
                    className="text-xs bg-surface-2 border border-border rounded px-2 py-1 text-text-secondary">
              {profiles.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          )}
          <button onClick={() => setShowCreate(true)}
                  className="text-xs px-3 py-1.5 rounded-md bg-surface-2 text-text-secondary hover:bg-surface-3 transition-colors flex items-center gap-1">
            <Plus size={13} /> New
          </button>
        </div>
      </header>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
          <div className="bg-surface-1 border border-border rounded-xl p-6 w-[90%] max-w-sm shadow-xl">
            <h2 className="text-sm font-semibold mb-3">New Company Profile</h2>
            <input type="text" value={newName} onChange={(e) => setNewName(e.target.value)}
                   placeholder="Company name..." autoFocus
                   className="w-full bg-surface-2 border border-border rounded-md px-3 py-2 text-sm
                              outline-none focus:border-brand mb-3"
                   onKeyDown={(e) => e.key === "Enter" && handleCreate()} />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowCreate(false)}
                      className="text-xs px-3 py-1.5 rounded bg-surface-2 text-text-secondary">Cancel</button>
              <button onClick={handleCreate} disabled={!newName.trim()}
                      className="text-xs px-3 py-1.5 rounded bg-brand text-white disabled:opacity-50">Create</button>
            </div>
          </div>
        </div>
      )}

      {!active ? (
        <div className="flex items-center justify-center py-20">
          <div className="text-center">
            <p className="text-sm text-text-secondary">No company profiles yet.</p>
            <button onClick={() => setShowCreate(true)}
                    className="mt-2 text-sm text-brand hover:text-brand-hover">Create one</button>
          </div>
        </div>
      ) : (
        <div className="max-w-4xl mx-auto p-4 md:p-6">
          {/* Header */}
          <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
            <div>
              <h2 className="text-lg font-semibold">{active.name}</h2>
              <p className="text-xs text-text-disabled mt-0.5">
                {active.status === "complete" ? "Complete" : "Draft"} · last updated {new Date(active.updated_at).toLocaleDateString()}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={editMode ? exitEditMode : enterEditMode} disabled={saving}
                      className={`text-xs px-3 py-1.5 rounded-md transition-colors flex items-center gap-1 ${
                        editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                      }`}>
                {saving ? <Loader2 size={12} className="animate-spin" /> : <Pencil size={12} />}
                {saving ? "Saving..." : editMode ? "Done" : "Edit"}
              </button>
              {/* Floating edit button — visible when scrolled past header */}
              <button onClick={() => setEditMode(!editMode)}
                      className={`fixed bottom-20 right-5 z-30 size-11 rounded-full shadow-lg
                                  transition-all flex items-center justify-center md:hidden ${
                        editMode ? "bg-brand text-white" : "bg-surface-1 border border-border text-text-secondary"
                      }`}>
                <Pencil size={18} />
              </button>
              <button onClick={handleSynthesize} disabled={synthing}
                      className="text-xs px-3 py-1.5 rounded-md bg-brand text-white hover:bg-brand-hover
                                 disabled:opacity-50 transition-colors flex items-center gap-1">
                {synthing ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                {synthing ? "Synthesizing..." : "Re-synthesize"}
              </button>
            </div>
          </div>

          {/* Description — north star for synthesis */}
          <div className="bg-surface-1 border border-border rounded-xl p-5 mb-4 relative">
            <label className="text-xs font-semibold text-text-disabled uppercase tracking-wider mb-2 block">
              Profile Description
            </label>
            <button onClick={editMode ? exitEditMode : enterEditMode} disabled={saving}
                    className={`absolute top-5 right-5 text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors ${
                      editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                    }`}>
              {saving ? "..." : editMode ? "Save" : "Edit"}
            </button>
            {editMode ? (
              <textarea
                value={editDesc}
                onChange={(e) => setEditDesc(e.target.value)}
                placeholder="Describe what kind of company profile you want the agent to build. This serves as a north star for synthesis.&#10;&#10;Example: A Maryland-based IT consulting firm focused on federal health IT contracts, with emphasis on cloud migration and data analytics past performance."
                rows={3}
                className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2
                           text-sm placeholder:text-text-disabled outline-none
                           focus:border-brand resize-none leading-relaxed"
              />
            ) : (
              <p className={`text-sm leading-relaxed ${(active as any)?.description ? "text-text-primary" : "text-text-disabled italic"}`}>
                {(active as any)?.description || "No description set. Click Edit to add a north star for the synthesis agent."}
              </p>
            )}
            <p className="text-[10px] text-text-disabled mt-1.5">
              This description guides the synthesis agent — it tells the agent what story to tell about your company.
            </p>
          </div>

          {/* Upload callout — always visible at top */}
          <div className="bg-brand-bg border border-brand/30 rounded-xl p-5 mb-6">
            <div className="flex items-start gap-4 flex-wrap md:flex-nowrap">
              <div className="size-10 rounded-lg bg-brand/20 flex items-center justify-center shrink-0">
                <Upload size={20} className="text-brand" />
              </div>
              <div className="flex-1 min-w-0">
                <h3 className="text-sm font-semibold">Upload documents — let the agent do the work</h3>
                <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                  Upload your capability statement, SAM.gov printout, certifications, and
                  key personnel resumes. The agent will read them and populate this profile
                  automatically. You can edit or verify anything it fills in.
                </p>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  <label className="inline-flex items-center gap-1.5 text-xs px-3 py-2
                                    bg-brand text-white rounded-lg cursor-pointer
                                    hover:bg-brand-hover transition-colors font-medium">
                    {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
                    {uploading ? "Uploading & indexing..." : "Upload Documents"}
                    <input type="file" multiple
                           accept=".pdf,.docx,.txt,.csv,.xlsx,.jpg,.jpeg,.png"
                           className="hidden"
                           disabled={uploading}
                           onChange={(e) => {
                             const files = e.target.files;
                             if (files?.length) handleUpload(files);
                             e.target.value = "";
                           }} />
                  </label>
                  <span className="text-[10px] text-text-disabled">
                    PDF, DOCX, images — any document about your company
                  </span>
                </div>
                {synthError && (
                  <p className="text-xs text-danger mt-2 flex items-center gap-1">
                    <Sparkles size={10} /> {synthError}
                  </p>
                )}
                {/* Source docs from uploads */}
                {((active.source_docs as any[]) || []).length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {(active.source_docs as any[]).map((d: any, i: number) => (
                      <span key={i} className="inline-flex items-center gap-1 text-[10px]
                                       bg-surface-2 border border-border rounded px-1.5 py-0.5">
                        <FileText size={10} className="text-text-disabled" />
                        {d.document_name || `Doc #${d.document_id}`}
                        <button onClick={(e) => { e.stopPropagation(); handleDetachDoc(i); }}
                                className="text-text-disabled hover:text-danger" title="Remove">
                          <X size={10} />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Field cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {FIELD_GROUPS.map((group) => {
              const groupStatus = group.fields.every(
                (f) => fieldStatus(active.content, f.key) === "verified"
              ) ? "verified"
                : group.fields.some((f) => fieldStatus(active.content, f.key) === "needs_input")
                  ? "needs_input"
                  : "agent_filled";

              return (
                <div key={group.key} className="bg-surface-1 border border-border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-[11px] font-semibold uppercase tracking-wider text-text-disabled">
                      {group.label}
                    </h3>
                    <div className="flex items-center gap-1.5">
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${FIELD_STATUS_CLASSES[groupStatus]}`}>
                        {FIELD_STATUS_LABELS[groupStatus]}
                      </span>
                      <button onClick={editMode ? exitEditMode : enterEditMode} disabled={saving}
                              className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors ${
                                editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                              }`}>
                        {saving ? "..." : editMode ? "Save" : "Edit"}
                      </button>
                    </div>
                  </div>
                  {group.fields.map((f) => {
                    const status = fieldStatus(active.content, f.key);
                    const val = f.key === "contact" ? null
                      : f.key === "address" ? (active.content?.contact as any)?.address
                      : f.key === "phone" ? (active.content?.contact as any)?.phone
                      : f.key === "email" ? (active.content?.contact as any)?.email
                      : active.content?.[f.key];
                    const display = formatValue(val);

                    if (editMode) {
                      const editVal = f.key === "address" ? (editContent.contact as any)?.address
                        : f.key === "phone" ? (editContent.contact as any)?.phone
                        : f.key === "email" ? (editContent.contact as any)?.email
                        : editContent[f.key];
                      const editDisplay = Array.isArray(editVal) ? (editVal as string[]).join(", ") : String(editVal || "");
                      return (
                        <div key={f.key} className="flex items-center gap-2 py-1.5 border-b border-border last:border-0">
                          <span className="text-xs text-text-disabled w-20 shrink-0">{f.label}</span>
                          <input
                            type="text"
                            value={editDisplay}
                            onChange={(e) => {
                              const val = e.target.value;
                              let parsed: any = val;
                              if (f.key === "naics_codes" || f.key === "certifications" || f.key === "psc_codes") {
                                parsed = val.split(",").map((s: string) => s.trim()).filter(Boolean);
                              } else if (f.key === "address" || f.key === "phone" || f.key === "email") {
                                setEditContent(prev => {
                                  const contact = { ...((prev.contact as any) || {}) };
                                  contact[f.key] = val;
                                  return { ...prev, contact };
                                });
                                return;
                              }
                              setEditContent(prev => ({ ...prev, [f.key]: parsed }));
                            }}
                            className="flex-1 min-w-0 bg-surface-2 border border-border rounded px-2 py-1 text-xs
                                       outline-none focus:border-brand"
                            placeholder="Enter value..."
                          />
                          <div className={`w-2 h-2 rounded-full shrink-0 ${dotClass(status)}`} />
                        </div>
                      );
                    }

                    return (
                      <div key={f.key} className="flex items-center justify-between py-1.5 border-b border-border last:border-0">
                        <span className="text-xs text-text-disabled">{f.label}</span>
                        <div className="flex items-center gap-2">
                          {display ? (
                            <span className="text-xs font-medium">{display}</span>
                          ) : (
                            <span className="text-xs text-danger italic">Not set</span>
                          )}
                          <div className={`w-2 h-2 rounded-full shrink-0 ${dotClass(status)}`} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              );
            })}

            {/* Past Performance */}
            <div className="bg-surface-1 border border-border rounded-lg p-4 md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-text-disabled">Past Performance</h3>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => { setAddPastPerf(true); setNewPP({ client: "", contract_value: "", description: "", period_of_performance: "" }); }}
                          className="text-[10px] px-2 py-1 rounded border border-border text-text-secondary hover:bg-surface-2 transition-colors flex items-center gap-1">
                    <Plus size={10} /> Add
                  </button>
                  <button onClick={editMode ? exitEditMode : enterEditMode} disabled={saving}
                          className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors ${
                            editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                          }`}>
                    {saving ? "..." : editMode ? "Save" : "Edit"}
                  </button>
                </div>
              </div>
              {addPastPerf && (
                <div className="mb-3 p-3 bg-surface-2 border border-border rounded-lg space-y-2">
                  <input type="text" placeholder="Client name" value={newPP.client}
                         onChange={(e) => setNewPP({ ...newPP, client: e.target.value })}
                         className="w-full bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                  <div className="flex gap-2">
                    <input type="text" placeholder="Contract value" value={newPP.contract_value}
                           onChange={(e) => setNewPP({ ...newPP, contract_value: e.target.value })}
                           className="flex-1 bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                    <input type="text" placeholder="Period (e.g. 2023-2024)" value={newPP.period_of_performance}
                           onChange={(e) => setNewPP({ ...newPP, period_of_performance: e.target.value })}
                           className="flex-1 bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                  </div>
                  <input type="text" placeholder="Description" value={newPP.description}
                         onChange={(e) => setNewPP({ ...newPP, description: e.target.value })}
                         className="w-full bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                  <div className="flex justify-end gap-2">
                    <button onClick={() => setAddPastPerf(false)} className="text-[10px] px-2 py-1 rounded bg-surface-3 text-text-secondary">Cancel</button>
                    <button onClick={handleAddPP} disabled={!newPP.client.trim()}
                            className="text-[10px] px-2 py-1 rounded bg-brand text-white disabled:opacity-50">Save</button>
                  </div>
                </div>
              )}
              {((active.content?.past_performance as any[]) || []).length === 0 && !addPastPerf ? (
                <p className="text-xs text-text-disabled italic">No past performance references yet.</p>
              ) : (
                (active.content?.past_performance as any[])?.map((pp: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 py-1.5 border-b border-border last:border-0 text-xs">
                    <span className="font-medium">{pp.client}</span>
                    <span className="text-text-disabled">{pp.description?.slice(0, 60)}{pp.description?.length > 60 ? "..." : ""}</span>
                    <span className="text-text-disabled ml-auto shrink-0">{pp.period_of_performance}</span>
                    <button onClick={() => handleDeletePP(i)} className="text-text-disabled hover:text-danger shrink-0">
                      <X size={10} />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Key Personnel */}
            <div className="bg-surface-1 border border-border rounded-lg p-4 md:col-span-2">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-text-disabled">Key Personnel</h3>
                <div className="flex items-center gap-1.5">
                  <button onClick={() => { setAddPersonnel(true); setNewPerson({ name: "", title: "", years_experience: "", clearance: "" }); }}
                          className="text-[10px] px-2 py-1 rounded border border-border text-text-secondary hover:bg-surface-2 transition-colors flex items-center gap-1">
                    <Plus size={10} /> Add
                  </button>
                  <button onClick={editMode ? exitEditMode : enterEditMode} disabled={saving}
                          className={`text-[10px] px-1.5 py-0.5 rounded font-medium transition-colors ${
                            editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                          }`}>
                    {saving ? "..." : editMode ? "Save" : "Edit"}
                  </button>
                </div>
              </div>
              {addPersonnel && (
                <div className="mb-3 p-3 bg-surface-2 border border-border rounded-lg space-y-2">
                  <div className="flex gap-2">
                    <input type="text" placeholder="Name" value={newPerson.name}
                           onChange={(e) => setNewPerson({ ...newPerson, name: e.target.value })}
                           className="flex-1 bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                    <input type="text" placeholder="Title" value={newPerson.title}
                           onChange={(e) => setNewPerson({ ...newPerson, title: e.target.value })}
                           className="flex-1 bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                  </div>
                  <div className="flex gap-2">
                    <input type="text" placeholder="Years experience" value={newPerson.years_experience}
                           onChange={(e) => setNewPerson({ ...newPerson, years_experience: e.target.value })}
                           className="w-32 bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                    <input type="text" placeholder="Clearance (optional)" value={newPerson.clearance}
                           onChange={(e) => setNewPerson({ ...newPerson, clearance: e.target.value })}
                           className="flex-1 bg-surface-1 border border-border rounded px-2 py-1.5 text-xs outline-none focus:border-brand" />
                  </div>
                  <div className="flex justify-end gap-2">
                    <button onClick={() => setAddPersonnel(false)} className="text-[10px] px-2 py-1 rounded bg-surface-3 text-text-secondary">Cancel</button>
                    <button onClick={handleAddPerson} disabled={!newPerson.name.trim()}
                            className="text-[10px] px-2 py-1 rounded bg-brand text-white disabled:opacity-50">Save</button>
                  </div>
                </div>
              )}
              {((active.content?.key_personnel as any[]) || []).length === 0 && !addPersonnel ? (
                <p className="text-xs text-text-disabled italic">No key personnel added yet.</p>
              ) : (
                (active.content?.key_personnel as any[])?.map((kp: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 py-1.5 border-b border-border last:border-0 text-xs">
                    <span className="font-medium">{kp.name}</span>
                    <span className="text-text-disabled">{kp.title} · {kp.years_experience} yrs</span>
                    {kp.resume_document_id ? (
                      <span className="text-success text-[10px] shrink-0">resume ✓</span>
                    ) : (
                      <span className="text-danger text-[10px] shrink-0">no resume</span>
                    )}
                    {kp.clearance && <span className="text-text-disabled shrink-0">· {kp.clearance}</span>}
                    <button onClick={() => handleDeletePerson(i)} className="text-text-disabled hover:text-danger shrink-0 ml-auto">
                      <X size={10} />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Capability Statement */}
            <div className="bg-surface-1 border border-border rounded-lg p-4 md:col-span-2">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-[11px] font-semibold uppercase tracking-wider text-text-disabled">Capability Statement</h3>
                {stmtDraft && (
                  <button onClick={() => setStmtEditMode(!stmtEditMode)}
                          className={`text-xs px-3 py-1.5 rounded-md transition-colors flex items-center gap-1 ${
                            stmtEditMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                          }`}>
                    <Pencil size={12} />
                    {stmtEditMode ? "Done" : "Edit"}
                  </button>
                )}
                <button onClick={handleGenerateStatement} disabled={genLoading}
                        className="text-xs px-3 py-1.5 rounded-md bg-brand text-white hover:bg-brand-hover
                                   disabled:opacity-50 transition-colors flex items-center gap-1">
                  {genLoading ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                  {genLoading ? "Generating..." : stmtDraft ? "Regenerate" : "Generate"}
                </button>
              </div>
              {stmtDraft ? (
                <div className="max-h-[500px] overflow-y-auto">
                  <DraftPreview
                    blocks={stmtDraft.content}
                    editMode={stmtEditMode}
                    onBlockUpdate={async (blockId, content) => {
                      await updateBlock(stmtDraft.id, blockId, content);
                      const updated = await getDraft(stmtDraft.id);
                      setStmtDraft(updated.draft);
                    }}
                    className="py-4"
                  />
                </div>
              ) : (
                <p className="text-xs text-text-secondary p-4 pt-0">
                  No capability statement yet. Click Generate to create one from your profile data.
                </p>
              )}
            </div>

          </div>
        </div>
      )}
    </div>
  );
}
