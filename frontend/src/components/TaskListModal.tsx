"use client";

import { useState, useEffect, useCallback } from "react";
import {
  X, Plus, Loader2, Calendar, User, FileText,
  ChevronDown, ChevronRight, Check, Circle, Clock, AlertCircle,
  Paperclip, Upload,
} from "lucide-react";
import {
  listTasks, getTask, createTask, updateTask, deleteTask,
  attachTaskDocuments, detachTaskDocument,
  listDocuments, uploadFile,
  type Task, type TaskDocument,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface TaskListModalProps {
  caseId: number;
  open: boolean;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

const STATUS_ICONS: Record<string, typeof Circle> = {
  open: Circle,
  in_progress: Clock,
  blocked: AlertCircle,
  complete: Check,
};

const STATUS_COLORS: Record<string, string> = {
  open: "text-text-disabled",
  in_progress: "text-warning",
  blocked: "text-danger",
  complete: "text-success",
};

const PRIORITY_COLORS: Record<string, string> = {
  low: "bg-surface-2 text-text-disabled",
  medium: "bg-info-bg text-info",
  high: "bg-warning-bg text-warning",
  urgent: "bg-danger-bg text-danger",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function TaskListModal({ caseId, open, onClose }: TaskListModalProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showCreate, setShowCreate] = useState(false);

  // Create form
  const [newTitle, setNewTitle] = useState("");
  const [newNotes, setNewNotes] = useState("");
  const [newDeadline, setNewDeadline] = useState("");
  const [newPriority, setNewPriority] = useState("medium");
  const [saving, setSaving] = useState(false);

  // Document picker
  const [showDocPicker, setShowDocPicker] = useState(false);
  const [availableDocs, setAvailableDocs] = useState<any[]>([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await listTasks(caseId, statusFilter ? { status: statusFilter } : undefined);
      setTasks(res.tasks);
    } catch { /* silent */ }
    setLoading(false);
  }, [caseId, statusFilter]);

  useEffect(() => {
    if (!open) return;
    refresh();
  }, [open, refresh]);

  const handleCreate = async () => {
    if (!newTitle.trim() || saving) return;
    setSaving(true);
    try {
      await createTask(caseId, {
        title: newTitle.trim(),
        notes: newNotes.trim() || undefined,
        deadline: newDeadline || undefined,
        priority: newPriority,
      });
      setNewTitle(""); setNewNotes(""); setNewDeadline(""); setNewPriority("medium");
      setShowCreate(false);
      refresh();
    } catch { /* silent */ }
    setSaving(false);
  };

  const handleStatusChange = async (taskId: number, status: string) => {
    await updateTask(taskId, { status });
    refresh();
  };

  const handleExpand = async (taskId: number) => {
    if (expandedId === taskId) { setExpandedId(null); return; }
    setExpandedId(taskId);
    try {
      const res = await getTask(taskId);
      setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, documents: res.task.documents } : t));
    } catch { /* keep existing */ }
  };

  const handleDelete = async (taskId: number) => {
    await deleteTask(taskId);
    if (expandedId === taskId) setExpandedId(null);
    refresh();
  };

  const loadDocs = async () => {
    try {
      const docs = await listDocuments(caseId) as any[];
      setAvailableDocs(docs || []);
    } catch { setAvailableDocs([]); }
    setShowDocPicker(true);
  };

  const handleAttachDocs = async (taskId: number, docIds: number[]) => {
    await attachTaskDocuments(taskId, docIds);
    setShowDocPicker(false);
    refresh();
  };

  const handleDetachDoc = async (taskId: number, docId: number) => {
    try {
      await detachTaskDocument(taskId, docId);
      setTasks((prev) =>
        prev.map((t) =>
          t.id === taskId
            ? {
                ...t,
                document_count: (t.document_count || 1) - 1,
                documents: (t.documents || []).filter((d) => d.id !== docId),
              }
            : t,
        ),
      );
    } catch { /* silent */ }
  };

  const handleUploadAndAttach = async (taskId: number, file: File) => {
    setUploading(true);
    setUploadError(null);
    setTasks((prev) => prev.map((t) =>
      t.id === taskId ? { ...t, document_count: (t.document_count || 0) + 1 } : t
    ));
    let docId: number | null = null;
    try {
      const result = await uploadFile(caseId, file);
      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 2000));
        const { getJob } = await import("@/lib/api");
        const job = await getJob(result.job_id);
        if (job.status === "complete" && job.document_id) {
          docId = job.document_id; break;
        }
        if (job.status === "failed") {
          setUploadError(job.error_message || "Ingestion failed"); break;
        }
        attempts++;
      }
      if (!docId && attempts >= 60) setUploadError("Upload timed out");
      if (docId) await attachTaskDocuments(taskId, [docId]);
    } catch (err: any) {
      setUploadError(err?.message || "Upload failed");
    }
    setUploading(false);
    if (docId) {
      try {
        const res = await getTask(taskId);
        setTasks((prev) =>
          prev.map((t) => t.id === taskId
            ? { ...t, documents: res.task.documents, document_count: res.task.documents?.length || 0 }
            : t
          ),
        );
      } catch { refresh(); }
    }
  };

  if (!open) return null;

  const formatDeadline = (d: string | null) => {
    if (!d) return null;
    const date = new Date(d + "T12:00:00");
    const now = new Date();
    const diff = date.getTime() - now.getTime();
    const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
    const label = date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
    if (days < 0) return { text: `Overdue · ${label}`, urgent: true };
    if (days === 0) return { text: `Today · ${label}`, urgent: true };
    if (days === 1) return { text: `Tomorrow · ${label}`, urgent: false };
    return { text: `${label}`, urgent: false };
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center">
      <div className="absolute inset-0 bg-black/40" onClick={onClose} />
      <div className="relative bg-surface-1 rounded-t-2xl md:rounded-2xl
                      w-full md:max-w-2xl md:mx-4 max-h-[85dvh] flex flex-col shadow-xl">
        {/* Header */}
        <div className="sticky top-0 bg-surface-1 border-b border-border
                        flex items-center justify-between px-4 py-3 rounded-t-2xl z-10">
          <h2 className="text-sm font-semibold">Tasks</h2>
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-[10px] bg-surface-2 border border-border rounded px-2 py-1
                         text-text-secondary cursor-pointer"
            >
              <option value="">All</option>
              <option value="open">Open</option>
              <option value="in_progress">In Progress</option>
              <option value="blocked">Blocked</option>
              <option value="complete">Complete</option>
            </select>
            <button
              onClick={() => setShowCreate(true)}
              className="text-xs px-3 py-1.5 rounded-md bg-brand text-white
                         hover:bg-brand-hover transition-colors flex items-center gap-1"
            >
              <Plus size={13} /> New
            </button>
            <button onClick={onClose} className="text-text-disabled hover:text-text-primary p-1">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="animate-spin text-text-disabled" size={24} />
            </div>
          ) : (
            <>
              {/* Create form */}
              {showCreate && (
                <div className="bg-surface-2 border border-border rounded-lg p-4 space-y-3">
                  <input
                    type="text"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    placeholder="Task title..."
                    className="w-full bg-surface-1 border border-border rounded-md px-3 py-2
                               text-sm placeholder:text-text-disabled outline-none focus:border-brand"
                    autoFocus
                    onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  />
                  <textarea
                    value={newNotes}
                    onChange={(e) => setNewNotes(e.target.value)}
                    placeholder="Notes (optional)"
                    rows={2}
                    className="w-full bg-surface-1 border border-border rounded-md px-3 py-2
                               text-xs placeholder:text-text-disabled outline-none focus:border-brand resize-none"
                  />
                  <div className="flex items-center gap-2">
                    <input
                      type="date"
                      value={newDeadline}
                      onChange={(e) => setNewDeadline(e.target.value)}
                      className="bg-surface-1 border border-border rounded-md px-2 py-1.5
                                 text-xs text-text-secondary outline-none focus:border-brand"
                    />
                    <select
                      value={newPriority}
                      onChange={(e) => setNewPriority(e.target.value)}
                      className="bg-surface-1 border border-border rounded-md px-2 py-1.5
                                 text-xs text-text-secondary cursor-pointer"
                    >
                      <option value="low">Low</option>
                      <option value="medium">Medium</option>
                      <option value="high">High</option>
                      <option value="urgent">Urgent</option>
                    </select>
                    <div className="flex-1" />
                    <button
                      onClick={() => setShowCreate(false)}
                      className="text-xs text-text-secondary hover:text-text-primary px-2 py-1"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={handleCreate}
                      disabled={!newTitle.trim() || saving}
                      className="text-xs px-3 py-1.5 rounded-md bg-brand text-white
                                 hover:bg-brand-hover disabled:opacity-50 transition-colors
                                 flex items-center gap-1"
                    >
                      {saving && <Loader2 size={12} className="animate-spin" />}
                      Create
                    </button>
                  </div>
                </div>
              )}

              {/* Task list */}
              {tasks.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-sm text-text-secondary">No tasks yet</p>
                  <p className="text-xs text-text-disabled mt-1">
                    Create one above or ask the agent to create follow-up tasks.
                  </p>
                </div>
              ) : (
                tasks.map((t) => {
                  const dl = formatDeadline(t.deadline);
                  const StatusIcon = STATUS_ICONS[t.status];
                  const isExpanded = expandedId === t.id;
                  return (
                    <div
                      key={t.id}
                      className="bg-surface-2 border border-border rounded-lg overflow-hidden"
                    >
                      {/* Row */}
                      <div
                        onClick={() => handleExpand(t.id)}
                        className="flex items-center gap-2 p-3 cursor-pointer hover:bg-surface-3/50 transition-colors"
                      >
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            const next = t.status === "complete" ? "open"
                              : t.status === "open" ? "in_progress"
                              : t.status === "in_progress" ? "complete"
                              : "open";
                            handleStatusChange(t.id, next);
                          }}
                          className={`${STATUS_COLORS[t.status]} p-0.5`}
                          title={`Status: ${t.status}`}
                        >
                          <StatusIcon size={16} />
                        </button>
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm ${t.status === "complete" ? "line-through text-text-disabled" : ""}`}>
                            {t.title}
                          </p>
                          <div className="flex items-center gap-2 flex-wrap text-[10px] text-text-disabled mt-0.5">
                            {dl && (
                              <span className={dl.urgent ? "text-danger" : ""}>
                                <Calendar size={10} className="inline mr-0.5" />
                                {dl.text}
                              </span>
                            )}
                            {t.document_count > 0 && (
                              <span>
                                <Paperclip size={10} className="inline mr-0.5" />
                                {t.document_count} doc{t.document_count > 1 ? "s" : ""}
                              </span>
                            )}
                            <span className={`px-1 rounded ${PRIORITY_COLORS[t.priority]}`}>
                              {t.priority}
                            </span>
                          </div>
                        </div>
                        {isExpanded ? <ChevronDown size={14} className="text-text-disabled shrink-0" />
                                     : <ChevronRight size={14} className="text-text-disabled shrink-0" />}
                      </div>

                      {/* Expanded detail */}
                      {isExpanded && (
                        <div className="px-4 pb-4 space-y-3 border-t border-border pt-3">
                          {t.notes && (
                            <p className="text-xs text-text-secondary whitespace-pre-wrap">{t.notes}</p>
                          )}

                          {/* Attached documents */}
                          {t.documents && t.documents.length > 0 && (
                            <div className="space-y-1">
                              <p className="text-[10px] font-medium text-text-disabled uppercase">Documents</p>
                              {t.documents.map((d: TaskDocument) => (
                                <div key={d.id} className="flex items-center gap-2 text-xs">
                                  <FileText size={12} className="text-text-disabled shrink-0" />
                                  <span className="flex-1 truncate">{d.name}</span>
                                  {d.page_count && <span className="text-text-disabled">{d.page_count}pp</span>}
                                  <button
                                    onClick={() => handleDetachDoc(t.id, d.id)}
                                    className="text-text-disabled hover:text-danger"
                                  >
                                    <X size={12} />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Actions */}
                          <div className="flex items-center gap-2 flex-wrap">
                            <select
                              value={t.status}
                              onChange={(e) => handleStatusChange(t.id, e.target.value)}
                              className="text-[10px] bg-surface-1 border border-border rounded px-2 py-1
                                         text-text-secondary cursor-pointer"
                            >
                              <option value="open">Open</option>
                              <option value="in_progress">In Progress</option>
                              <option value="blocked">Blocked</option>
                              <option value="complete">Complete</option>
                            </select>
                            <button
                              onClick={loadDocs}
                              className="text-[10px] px-2 py-1 rounded border border-border
                                         text-text-secondary hover:bg-surface-3 transition-colors
                                         flex items-center gap-1"
                            >
                              <Paperclip size={10} />
                              Attach docs
                            </button>
                            <label className="text-[10px] px-2 py-1 rounded border border-border
                                              text-text-secondary hover:bg-surface-3 transition-colors
                                              flex items-center gap-1 cursor-pointer">
                              <Upload size={10} />
                              {uploading ? "Processing..." : "Upload file"}
                              <input
                                type="file"
                                className="hidden"
                                accept=".pdf,.docx,.txt,.csv,.xlsx,.jpg,.jpeg,.png,.m4a,.mp3,.wav"
                                onChange={(e) => {
                                  const file = e.target.files?.[0];
                                  if (file) handleUploadAndAttach(t.id, file);
                                  e.target.value = "";
                                }}
                                disabled={uploading}
                              />
                            </label>
                            {uploadError && (
                              <span className="text-[10px] text-danger ml-2">{uploadError}</span>
                            )}
                            <button
                              onClick={() => handleDelete(t.id)}
                              className="text-[10px] px-2 py-1 rounded text-danger
                                         hover:bg-danger-bg transition-colors ml-auto"
                            >
                              Delete
                            </button>
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </>
          )}
        </div>

        {/* Document picker modal */}
        {showDocPicker && (
          <div className="absolute inset-0 bg-black/50 rounded-2xl flex items-center justify-center z-20">
            <div className="bg-surface-1 border border-border rounded-xl p-4 w-[90%] max-w-sm max-h-[60%] overflow-y-auto">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium">Attach Documents</h3>
                <button onClick={() => setShowDocPicker(false)} className="text-text-disabled hover:text-text-primary">
                  <X size={16} />
                </button>
              </div>
              {availableDocs.length === 0 ? (
                <p className="text-xs text-text-disabled">No documents in this case yet.</p>
              ) : (
                <div className="space-y-1">
                  {availableDocs.map((d: any) => (
                    <button
                      key={d.id}
                      onClick={() => {
                        if (expandedId) handleAttachDocs(expandedId, [d.id]);
                      }}
                      className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded
                                 hover:bg-surface-2 text-xs transition-colors"
                    >
                      <FileText size={12} className="text-text-disabled shrink-0" />
                      <span className="truncate">{d.name}</span>
                      {d.page_count && <span className="text-text-disabled shrink-0">{d.page_count}pp</span>}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
