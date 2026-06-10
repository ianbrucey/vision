"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Plus, Loader2, Calendar, FileText,
  ChevronDown, ChevronRight, Check, Circle, Clock, AlertCircle,
  Paperclip, X, Trash2,
} from "lucide-react";
import {
  listTasks, getTask, createTask, updateTask, deleteTask,
  attachTaskDocuments, detachTaskDocument,
  type Task, type TaskDocument,
} from "@/lib/api";
import DocumentAttachButton from "@/components/DocumentAttachButton";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface TasksTabProps {
  caseId: number;
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

function formatDeadline(d: string | null) {
  if (!d) return null;
  const date = new Date(d + "T12:00:00");
  const now = new Date();
  const diff = date.getTime() - now.getTime();
  const days = Math.ceil(diff / (1000 * 60 * 60 * 24));
  const label = date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  if (days < 0) return { text: `Overdue · ${label}`, urgent: true };
  if (days === 0) return { text: `Today · ${label}`, urgent: true };
  if (days === 1) return { text: `Tomorrow · ${label}`, urgent: false };
  return { text: label, urgent: false };
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function TasksTab({ caseId }: TasksTabProps) {
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

  // Note editing
  const [editingNotesId, setEditingNotesId] = useState<number | null>(null);
  const [editingNotesText, setEditingNotesText] = useState("");

  const refresh = useCallback(async () => {
    try {
      const res = await listTasks(caseId, statusFilter ? { status: statusFilter } : undefined);
      setTasks(res.tasks);
    } catch { /* silent */ }
    setLoading(false);
  }, [caseId, statusFilter]);

  useEffect(() => { refresh(); }, [refresh]);

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
    // Fetch full task with documents
    try {
      const res = await getTask(taskId);
      setTasks((prev) => prev.map((t) => t.id === taskId ? { ...t, documents: res.task.documents } : t));
    } catch { /* keep existing data */ }
  };

  const handleDelete = async (taskId: number) => {
    await deleteTask(taskId);
    if (expandedId === taskId) setExpandedId(null);
    refresh();
  };

  const handleAttach = async (taskId: number, documentId: number) => {
    try {
      await attachTaskDocuments(taskId, [documentId]);
      const res = await getTask(taskId);
      setTasks((prev) =>
        prev.map((t) => t.id === taskId
          ? { ...t, documents: res.task.documents, document_count: res.task.documents?.length || 0 }
          : t
        ),
      );
    } catch { /* silent */ }
  };

  const startEditNotes = (t: Task) => {
    setEditingNotesId(t.id);
    setEditingNotesText(t.notes || "");
  };

  const saveNotes = async (taskId: number) => {
    try {
      await updateTask(taskId, { notes: editingNotesText });
      setTasks((prev) => prev.map((t) =>
        t.id === taskId ? { ...t, notes: editingNotesText } : t
      ));
    } catch { /* silent */ }
    setEditingNotesId(null);
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

  const cycleStatus = (t: Task) => {
    const next = t.status === "complete" ? "open"
      : t.status === "open" ? "in_progress"
      : t.status === "in_progress" ? "complete"
      : "open";
    handleStatusChange(t.id, next);
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 bg-surface-1 border-b border-border px-4 py-3
                      flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold">Tasks</h2>
          <p className="text-[10px] text-text-disabled">
            {tasks.filter((t) => t.status !== "complete").length} open ·{" "}
            {tasks.filter((t) => t.status === "complete").length} complete
          </p>
        </div>
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
        </div>
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="shrink-0 bg-surface-1 border-b border-border px-4 py-4 space-y-3">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Task title..."
            className="w-full bg-surface-2 border border-border rounded-md px-3 py-2
                       text-sm placeholder:text-text-disabled outline-none focus:border-brand"
            autoFocus
            onKeyDown={(e) => e.key === "Enter" && handleCreate()}
          />
          <textarea
            value={newNotes}
            onChange={(e) => setNewNotes(e.target.value)}
            placeholder="Notes (optional)"
            rows={2}
            className="w-full bg-surface-2 border border-border rounded-md px-3 py-2
                       text-xs placeholder:text-text-disabled outline-none focus:border-brand resize-none"
          />
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={newDeadline}
              onChange={(e) => setNewDeadline(e.target.value)}
              className="bg-surface-2 border border-border rounded-md px-2 py-1.5
                         text-xs text-text-secondary outline-none focus:border-brand"
            />
            <select
              value={newPriority}
              onChange={(e) => setNewPriority(e.target.value)}
              className="bg-surface-2 border border-border rounded-md px-2 py-1.5
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
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="animate-spin text-text-disabled" size={24} />
          </div>
        ) : tasks.length === 0 ? (
          <div className="flex items-center justify-center py-12">
            <div className="text-center px-4">
              <p className="text-sm text-text-secondary">No tasks yet</p>
              <p className="text-xs text-text-disabled mt-1">
                Create one above or ask the agent to create follow-ups.
              </p>
            </div>
          </div>
        ) : (
          <div className="p-4 space-y-2">
            {tasks.map((t) => {
              const dl = formatDeadline(t.deadline);
              const StatusIcon = STATUS_ICONS[t.status];
              const isExpanded = expandedId === t.id;
              return (
                <div
                  key={t.id}
                  className="bg-surface-1 border border-border rounded-lg overflow-hidden"
                >
                  {/* Row */}
                  <div
                    onClick={() => handleExpand(t.id)}
                    className="flex items-center gap-2 p-3 cursor-pointer hover:bg-surface-2 transition-colors"
                  >
                    <button
                      onClick={(e) => { e.stopPropagation(); cycleStatus(t); }}
                      className={`${STATUS_COLORS[t.status]} p-0.5`}
                      title={`Status: ${t.status.replace(/_/g, " ")}`}
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
                    <div className="px-4 pb-4 space-y-4 border-t border-border pt-4">
                      {/* Notes */}
                      <div>
                        <p className="text-[10px] font-medium text-text-disabled uppercase tracking-wider mb-1.5">
                          Notes
                        </p>
                        {editingNotesId === t.id ? (
                          <div className="space-y-2">
                            <textarea
                              value={editingNotesText}
                              onChange={(e) => setEditingNotesText(e.target.value)}
                              className="w-full bg-surface-2 border border-border rounded-md px-3 py-2.5
                                         text-xs text-text-primary placeholder:text-text-disabled
                                         outline-none focus:border-brand resize-none leading-relaxed"
                              rows={4}
                              autoFocus
                              onKeyDown={(e) => {
                                if (e.key === "Escape") setEditingNotesId(null);
                                if ((e.metaKey || e.ctrlKey) && e.key === "Enter") saveNotes(t.id);
                              }}
                            />
                            <div className="flex justify-end gap-1.5">
                              <button
                                onClick={() => setEditingNotesId(null)}
                                className="text-[10px] px-2.5 py-1 rounded bg-surface-2 text-text-secondary
                                           hover:bg-surface-3 transition-colors"
                              >
                                Cancel
                              </button>
                              <button
                                onClick={() => saveNotes(t.id)}
                                className="text-[10px] px-2.5 py-1 rounded bg-brand text-white
                                           hover:bg-brand-hover transition-colors"
                              >
                                Save
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div
                            onClick={() => startEditNotes(t)}
                            className="bg-surface-2 border border-border rounded-md px-3 py-2.5
                                       cursor-pointer hover:border-border-strong hover:bg-surface-3
                                       transition-colors min-h-[36px]"
                          >
                            {t.notes ? (
                              <p className="text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
                                {t.notes}
                              </p>
                            ) : (
                              <p className="text-xs text-text-disabled italic">
                                Click to add notes...
                              </p>
                            )}
                          </div>
                        )}
                      </div>

                      {/* Attached documents */}
                      {t.documents && t.documents.length > 0 && (
                        <div className="flex items-center gap-1.5 flex-wrap">
                          {t.documents.map((d: TaskDocument) => (
                            <span
                              key={d.id}
                              className="inline-flex items-center gap-1 text-[10px]
                                         bg-surface-2 border border-border rounded
                                         px-1.5 py-0.5"
                            >
                              <FileText size={10} className="text-text-disabled" />
                              {d.name}
                              <button
                                onClick={() => handleDetachDoc(t.id, d.id)}
                                className="text-text-disabled hover:text-danger"
                                title="Remove attachment"
                              >
                                <X size={10} />
                              </button>
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Actions */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <select
                          value={t.status}
                          onChange={(e) => handleStatusChange(t.id, e.target.value)}
                          className="text-[10px] bg-surface-2 border border-border rounded px-2 py-1
                                     text-text-secondary cursor-pointer"
                        >
                          <option value="open">Open</option>
                          <option value="in_progress">In Progress</option>
                          <option value="blocked">Blocked</option>
                          <option value="complete">Complete</option>
                        </select>
                        <DocumentAttachButton
                          caseId={caseId}
                          attachedIds={(t.documents || []).map((d) => d.id)}
                          onAttach={(docId) => handleAttach(t.id, docId)}
                        />
                        <button
                          onClick={() => handleDelete(t.id)}
                          className="text-[10px] px-2 py-1 rounded text-danger
                                     hover:bg-danger-bg transition-colors ml-auto
                                     flex items-center gap-1"
                        >
                          <Trash2 size={10} />
                          Delete
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}
