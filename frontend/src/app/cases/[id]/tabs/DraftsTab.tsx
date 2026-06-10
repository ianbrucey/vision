"use client";

import { useState, useEffect, useCallback } from "react";
import { FileText, Plus, Loader2, Trash2 } from "lucide-react";
import {
  listDrafts, getDraft, createDraft, updateDraft, updateBlock, deleteDraft,
  type DraftSummary, type Draft,
} from "@/lib/api";
import DraftPreview from "@/components/DraftPreview";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface DraftsTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DraftsTab({ caseId }: DraftsTabProps) {
  const [drafts, setDrafts] = useState<DraftSummary[]>([]);
  const [activeDraft, setActiveDraft] = useState<Draft | null>(null);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<"list" | "preview">("list");

  /* ---- fetch ---- */

  const refreshList = useCallback(async () => {
    try {
      const res = await listDrafts(caseId);
      setDrafts(res.drafts);
      setError(null);
      return res.drafts;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load drafts");
      return [];
    }
  }, [caseId]);

  useEffect(() => {
    let cancelled = false;
    refreshList().then((list) => {
      if (cancelled) return;
      setLoading(false);
      if (list.length > 0 && !activeDraft) {
        selectDraft(list[0].id);
      }
    });
    return () => { cancelled = true; };
  }, [refreshList]);

  const selectDraft = async (id: number) => {
    setContentLoading(true);
    setEditMode(false);
    try {
      const res = await getDraft(id);
      setActiveDraft(res.draft);
      if (window.innerWidth < 768) setMobileView("preview");
    } catch {
      refreshList();
    } finally {
      setContentLoading(false);
    }
  };

  /* ---- actions ---- */

  const handleNewDraft = async () => {
    try {
      const res = await createDraft({
        case_id: caseId,
        name: "Untitled Draft",
        document_type: "letter",
        content: [
          { id: "h1", type: "section_heading", content: "New Section" },
          { id: "p1", type: "numbered_paragraph", content: "Start writing here..." },
        ],
      });
      await refreshList();
      setActiveDraft(res.draft);
      setEditMode(true);
      if (window.innerWidth < 768) setMobileView("preview");
    } catch { /* silent */ }
  };

  const handleBlockUpdate = async (blockId: string, content: string) => {
    if (!activeDraft) return;
    await updateBlock(activeDraft.id, blockId, content);
    setActiveDraft((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        content: prev.content.map((b) => b.id === blockId ? { ...b, content } : b),
      };
    });
    refreshList();
  };

  const handleDelete = async (draftId: number) => {
    await deleteDraft(draftId);
    if (activeDraft?.id === draftId) setActiveDraft(null);
    await refreshList();
  };

  const handleStatusChange = async (status: string) => {
    if (!activeDraft) return;
    await updateDraft(activeDraft.id, { status });
    setActiveDraft((prev) => prev ? { ...prev, status } : prev);
    refreshList();
  };

  /* ---- helpers ---- */

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString(undefined, {
      month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
    });

  const badgeClass = (type: string) => {
    const m: Record<string, string> = {
      letter: "bg-info-bg text-info", pleading: "bg-warning-bg text-warning",
      contract: "bg-success-bg text-success", memo: "bg-brand-bg text-brand",
    };
    return m[type] || "bg-surface-2 text-text-disabled";
  };

  const statusBadge = (s: string) =>
    s === "final" ? "bg-success-bg text-success"
      : s === "review" ? "bg-warning-bg text-warning"
      : "bg-surface-2 text-text-disabled";

  /* ---- loading ---- */
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  /* ---- error ---- */
  if (error && drafts.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center px-4">
          <p className="text-sm text-danger">{error}</p>
          <button onClick={refreshList} className="text-xs text-info mt-2">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Mobile toolbar */}
      <div className="md:hidden shrink-0 bg-surface-1 border-b border-border px-4 py-2 flex items-center gap-2">
        {mobileView === "preview" ? (
          <button onClick={() => setMobileView("list")} className="text-sm text-text-secondary">
            ← Drafts
          </button>
        ) : (
          <span className="text-sm font-medium">Drafts</span>
        )}
        <div className="flex-1" />
        {mobileView === "preview" && activeDraft && (
          <button
            onClick={() => setEditMode(!editMode)}
            className={`text-xs px-3 py-1 rounded-md font-medium ${
              editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary"
            }`}
          >
            {editMode ? "Done" : "Edit"}
          </button>
        )}
        <button onClick={handleNewDraft} className="text-brand p-1">
          <Plus size={18} />
        </button>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* Draft list */}
        <aside className={`w-[260px] flex-shrink-0 bg-surface-1 border-r border-border flex flex-col
                           overflow-hidden ${mobileView === "preview" ? "max-md:hidden" : "max-md:w-full max-md:border-r-0"}`}>
          <div className="hidden md:flex items-center justify-between px-4 py-3 border-b border-border">
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">Drafts</h3>
            <button onClick={handleNewDraft} className="text-brand hover:text-brand-hover p-1" title="New draft">
              <Plus size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {drafts.length === 0 ? (
              <div className="text-center py-8 px-4">
                <FileText size={24} className="text-text-disabled mx-auto mb-2" />
                <p className="text-xs text-text-secondary">No drafts yet</p>
                <p className="text-xs text-text-disabled mt-1">Ask the agent to create one in the chat.</p>
              </div>
            ) : (
              drafts.map((d) => (
                <div
                  key={d.id}
                  onClick={() => selectDraft(d.id)}
                  className={`p-2.5 rounded-md cursor-pointer mb-1 border border-transparent
                              transition-colors hover:bg-surface-2
                              ${d.id === activeDraft?.id ? "bg-brand-bg border-brand" : ""}`}
                >
                  <div className="text-xs font-medium truncate">{d.name}</div>
                  <div className="flex items-center gap-1.5 mt-1 flex-wrap">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-sm font-medium ${badgeClass(d.document_type)}`}>
                      {d.document_type}
                    </span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded-sm font-medium ${statusBadge(d.status)}`}>
                      {d.status}
                    </span>
                    <span className="text-[10px] text-text-disabled ml-auto">{d.block_count} blocks</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </aside>

        {/* Preview */}
        <main className={`flex-1 flex flex-col min-w-0 overflow-hidden ${mobileView === "list" ? "max-md:hidden" : ""}`}>
          {activeDraft ? (
            <>
              {/* Desktop toolbar */}
              <div className="hidden md:flex shrink-0 items-center justify-between px-4 py-2
                              bg-surface-1 border-b border-border">
                <div className="min-w-0 mr-2">
                  <h2 className="text-sm font-semibold truncate">{activeDraft.name}</h2>
                  <p className="text-[10px] text-text-disabled">
                    {activeDraft.document_type} · {activeDraft.status} · updated {formatDate(activeDraft.updated_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={activeDraft.status}
                    onChange={(e) => handleStatusChange(e.target.value)}
                    className="text-[10px] bg-surface-2 border border-border rounded px-2 py-1
                               text-text-secondary cursor-pointer"
                  >
                    <option value="draft">Draft</option>
                    <option value="review">Review</option>
                    <option value="final">Final</option>
                  </select>
                  <button
                    onClick={() => setEditMode(!editMode)}
                    className={`text-xs px-3 py-1 rounded font-medium transition-colors ${
                      editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary hover:text-text-primary"
                    }`}
                  >
                    {editMode ? "Done" : "Edit"}
                  </button>
                  <button
                    onClick={() => handleDelete(activeDraft.id)}
                    className="text-text-disabled hover:text-danger p-1 transition-colors"
                    title="Delete draft"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto bg-surface-0">
                {contentLoading ? (
                  <div className="flex items-center justify-center h-full">
                    <Loader2 className="animate-spin text-text-disabled" size={24} />
                  </div>
                ) : (
                  <DraftPreview
                    blocks={activeDraft.content}
                    editMode={editMode}
                    onBlockUpdate={handleBlockUpdate}
                    className="py-6"
                  />
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center px-4">
                <FileText size={32} className="text-text-disabled mx-auto mb-3" />
                <p className="text-sm text-text-secondary font-medium">No draft selected</p>
                <p className="text-xs text-text-disabled mt-1">
                  Select a draft or ask the agent to create one.
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
