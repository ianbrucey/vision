"use client";

import {
  useState, useEffect, useCallback,
} from "react";
import {
  Mail, Plus, Loader2, Trash2, X, Pencil, Send, Inbox, ChevronDown, ChevronRight,
} from "lucide-react";
import {
  listCorrespondenceThreads, createCorrespondenceThread,
  updateCorrespondenceThread, deleteCorrespondenceThread,
  listCorrespondenceItems, createCorrespondenceItem,
  updateCorrespondenceItem, deleteCorrespondenceItem,
  attachCorrespondenceDocument, detachCorrespondenceDocument,
  listParties, addParty,
  type CorrespondenceThread, type CorrespondenceItem,
} from "@/lib/api";
import DocumentAttachButton from "@/components/DocumentAttachButton";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

interface Party {
  id: number; name: string;
}

interface CorrespondenceTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString(undefined, {
    month: "short", day: "numeric", year: "numeric",
  });
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function CorrespondenceTab({ caseId }: CorrespondenceTabProps) {
  /* ---- threads ---- */
  const [threads, setThreads] = useState<CorrespondenceThread[]>([]);
  const [activeThreadId, setActiveThreadId] = useState<number | null>(null);
  const [threadsLoading, setThreadsLoading] = useState(true);
  const [newThreadTitle, setNewThreadTitle] = useState("");
  const [addingThread, setAddingThread] = useState(false);

  /* ---- items ---- */
  const [items, setItems] = useState<CorrespondenceItem[]>([]);
  const [itemsLoading, setItemsLoading] = useState(false);

  /* ---- parties (for selectors) ---- */
  const [parties, setParties] = useState<Party[]>([]);

  /* ---- new item form ---- */
  const [showNewItem, setShowNewItem] = useState(false);
  const [newItem, setNewItem] = useState({
    sender_party_id: null as number | null,
    receiver_party_id: null as number | null,
    direction: "sent" as "sent" | "received",
    notes: "",
    date_sent: "",
    date_received: "",
    document_ids: [] as number[],
  });

  /* ---- edit item ---- */
  const [editingId, setEditingId] = useState<number | null>(null);

  /* ---- new party inline form ---- */
  const [newPartyFor, setNewPartyFor] = useState<"sender" | "receiver" | null>(null);
  const [newPartyName, setNewPartyName] = useState("");
  const [newPartyKind, setNewPartyKind] = useState<"individual" | "organization">("individual");
  const [addingParty, setAddingParty] = useState(false);

  /* ---- mobile ---- */
  const [mobileView, setMobileView] = useState<"list" | "detail">("list");

  /* ================================================================ */
  /* Fetch threads                                                     */
  /* ================================================================ */

  const refreshThreads = useCallback(async () => {
    try {
      const res = await listCorrespondenceThreads(caseId);
      setThreads(res.threads);
    } catch {
      // silent
    } finally {
      setThreadsLoading(false);
    }
  }, [caseId]);

  useEffect(() => {
    refreshThreads();
  }, [refreshThreads]);

  /* ================================================================ */
  /* Fetch parties                                                     */
  /* ================================================================ */

  const refreshParties = useCallback(async () => {
    try {
      const res: any = await listParties(caseId);
      setParties(res as Party[]);
    } catch { /* silent */ }
  }, [caseId]);

  useEffect(() => {
    refreshParties();
  }, [refreshParties]);

  /* ---- add new party inline ---- */
  const handleAddParty = async (forField: "sender" | "receiver") => {
    if (!newPartyName.trim()) return;
    setAddingParty(true);
    try {
      const res: any = await addParty(caseId, {
        name: newPartyName.trim(),
        party_kind: newPartyKind,
        roles: [],
      });
      // The backend returns the new party; refresh full list to get consistent data
      await refreshParties();
      // Select the newly created party in the appropriate field
      if (res && res.id) {
        setNewItem((p) => ({
          ...p,
          [forField === "sender" ? "sender_party_id" : "receiver_party_id"]: res.id,
        }));
      }
      setNewPartyName("");
      setNewPartyFor(null);
    } catch { /* silent */ }
    setAddingParty(false);
  };

  /* ================================================================ */
  /* Fetch items for active thread                                     */
  /* ================================================================ */

  useEffect(() => {
    if (!activeThreadId) {
      setItems([]);
      return;
    }
    let cancelled = false;
    setItemsLoading(true);
    listCorrespondenceItems(activeThreadId)
      .then((res) => {
        if (!cancelled) setItems(res.items);
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setItemsLoading(false);
      });
    return () => { cancelled = true; };
  }, [activeThreadId]);

  /* ================================================================ */
  /* Thread actions                                                    */
  /* ================================================================ */

  const handleCreateThread = async () => {
    if (!newThreadTitle.trim()) return;
    try {
      const res = await createCorrespondenceThread(caseId, { title: newThreadTitle.trim() });
      setThreads((prev) => [res.thread, ...prev]);
      setActiveThreadId(res.thread.id);
      setNewThreadTitle("");
      setAddingThread(false);
      if (window.innerWidth < 768) setMobileView("detail");
    } catch { /* silent */ }
  };

  const handleDeleteThread = async (id: number) => {
    if (!confirm("Delete this thread and all its items?")) return;
    await deleteCorrespondenceThread(id);
    if (activeThreadId === id) setActiveThreadId(null);
    await refreshThreads();
  };

  /* ================================================================ */
  /* Item actions                                                      */
  /* ================================================================ */

  const handleCreateItem = async () => {
    if (!activeThreadId) return;
    try {
      const res = await createCorrespondenceItem(activeThreadId, {
        ...newItem,
        date_sent: newItem.date_sent || null,
        date_received: newItem.date_received || null,
      });
      setItems((prev) => [res.item, ...prev]);
      setShowNewItem(false);
      setNewItem({
        sender_party_id: null,
        receiver_party_id: null,
        direction: "sent",
        notes: "",
        date_sent: "",
        date_received: "",
        document_ids: [],
      });
      refreshThreads();
    } catch { /* silent */ }
  };

  const handleDeleteItem = async (id: number) => {
    if (!confirm("Delete this item?")) return;
    await deleteCorrespondenceItem(id);
    setItems((prev) => prev.filter((it) => it.id !== id));
    refreshThreads();
  };

  const handleAttach = async (itemId: number, docId: number) => {
    try {
      const res = await attachCorrespondenceDocument(itemId, docId);
      setItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? { ...it, attachments: [...it.attachments, res.attachment] }
            : it,
        ),
      );
    } catch { /* silent */ }
  };

  const handleDetach = async (itemId: number, docId: number) => {
    try {
      await detachCorrespondenceDocument(itemId, docId);
      setItems((prev) =>
        prev.map((it) =>
          it.id === itemId
            ? { ...it, attachments: it.attachments.filter((a) => a.document_id !== docId) }
            : it,
        ),
      );
    } catch { /* silent */ }
  };

  /* ================================================================ */
  /* Edit item                                                         */
  /* ================================================================ */

  const startEditing = (item: CorrespondenceItem) => {
    setEditingId(item.id);
    setNewItem({
      sender_party_id: item.sender_party_id,
      receiver_party_id: item.receiver_party_id,
      direction: item.direction,
      notes: item.notes || "",
      date_sent: item.date_sent || "",
      date_received: item.date_received || "",
      document_ids: [],
    });
  };

  const handleUpdateItem = async () => {
    if (editingId === null) return;
    try {
      const res = await updateCorrespondenceItem(editingId, {
        ...newItem,
        date_sent: newItem.date_sent || null,
        date_received: newItem.date_received || null,
      });
      setItems((prev) =>
        prev.map((it) => (it.id === editingId ? { ...it, ...res.item, attachments: it.attachments } : it)),
      );
      setEditingId(null);
    } catch { /* silent */ }
  };

  /* ================================================================ */
  /* Derived                                                           */
  /* ================================================================ */

  const activeThread = threads.find((t) => t.id === activeThreadId);

  /* ================================================================ */
  /* Item form (shared by create + edit)                                */
  /* ================================================================ */

  const itemForm = (onSubmit: () => void, onCancel: () => void, submitLabel: string) => (
    <div className="bg-surface-1 border border-border rounded-lg p-3 md:p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          {submitLabel}
        </h4>
        <button
          onClick={onCancel}
          className="text-text-disabled hover:text-text-secondary transition-colors"
        >
          <X size={14} />
        </button>
      </div>

      {/* Direction toggle */}
      <div>
        <label className="text-[10px] text-text-disabled block mb-1">Direction</label>
        <div className="flex gap-1">
          <button
            type="button"
            onClick={() => setNewItem((p) => ({ ...p, direction: "sent" }))}
            className={`flex-1 text-xs px-3 py-1.5 rounded border transition-colors inline-flex items-center justify-center gap-1.5 ${
              newItem.direction === "sent"
                ? "bg-brand-bg border-brand text-brand"
                : "bg-surface-2 border-border text-text-secondary"
            }`}
          >
            <Send size={12} /> Sent
          </button>
          <button
            type="button"
            onClick={() => setNewItem((p) => ({ ...p, direction: "received" }))}
            className={`flex-1 text-xs px-3 py-1.5 rounded border transition-colors inline-flex items-center justify-center gap-1.5 ${
              newItem.direction === "received"
                ? "bg-info-bg border-info text-info"
                : "bg-surface-2 border-border text-text-secondary"
            }`}
          >
            <Inbox size={12} /> Received
          </button>
        </div>
      </div>

      {/* Parties */}
      <div className="grid grid-cols-2 gap-2">
        {/* Sender */}
        <div>
          <label className="text-[10px] text-text-disabled block mb-1">
            {newItem.direction === "sent" ? "From (Sender)" : "Sender"}
          </label>
          <div className="flex gap-1">
            <select
              value={newItem.sender_party_id ?? ""}
              onChange={(e) =>
                setNewItem((p) => ({
                  ...p,
                  sender_party_id: e.target.value ? Number(e.target.value) : null,
                }))
              }
              className="flex-1 min-w-0 bg-surface-2 border border-border rounded px-2 py-1.5
                         text-xs text-text-primary focus:border-brand focus:ring-1
                         focus:ring-brand-ring focus:outline-none"
            >
              <option value="">Select...</option>
              {parties.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setNewPartyFor("sender");
                setNewPartyName("");
                setNewPartyKind("individual");
              }}
              className="shrink-0 size-[30px] flex items-center justify-center
                         rounded border border-border text-text-disabled
                         hover:text-brand hover:border-brand transition-colors"
              title="Add new party"
            >
              <Plus size={14} />
            </button>
          </div>
        </div>

        {/* Receiver */}
        <div>
          <label className="text-[10px] text-text-disabled block mb-1">
            {newItem.direction === "sent" ? "To (Receiver)" : "Receiver"}
          </label>
          <div className="flex gap-1">
            <select
              value={newItem.receiver_party_id ?? ""}
              onChange={(e) =>
                setNewItem((p) => ({
                  ...p,
                  receiver_party_id: e.target.value ? Number(e.target.value) : null,
                }))
              }
              className="flex-1 min-w-0 bg-surface-2 border border-border rounded px-2 py-1.5
                         text-xs text-text-primary focus:border-brand focus:ring-1
                         focus:ring-brand-ring focus:outline-none"
            >
              <option value="">Select...</option>
              {parties.map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => {
                setNewPartyFor("receiver");
                setNewPartyName("");
                setNewPartyKind("individual");
              }}
              className="shrink-0 size-[30px] flex items-center justify-center
                         rounded border border-border text-text-disabled
                         hover:text-brand hover:border-brand transition-colors"
              title="Add new party"
            >
              <Plus size={14} />
            </button>
          </div>
        </div>
      </div>

      {/* Inline new party form */}
      {newPartyFor && (
        <div className="bg-surface-2 border border-border rounded p-2.5 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[10px] font-semibold text-text-secondary uppercase">
              New {newPartyFor} Party
            </span>
            <button
              onClick={() => setNewPartyFor(null)}
              className="text-text-disabled hover:text-text-secondary"
            >
              <X size={12} />
            </button>
          </div>
          <input
            type="text"
            value={newPartyName}
            onChange={(e) => setNewPartyName(e.target.value)}
            placeholder="Party name..."
            className="w-full bg-surface-1 border border-border rounded px-2 py-1.5
                       text-xs text-text-primary placeholder:text-text-disabled
                       focus:border-brand focus:ring-1 focus:ring-brand-ring focus:outline-none"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") handleAddParty(newPartyFor);
              if (e.key === "Escape") setNewPartyFor(null);
            }}
          />
          <div className="flex items-center gap-2">
            <label className="flex items-center gap-1 text-[10px] text-text-secondary">
              <input
                type="radio"
                name="partyKind"
                checked={newPartyKind === "individual"}
                onChange={() => setNewPartyKind("individual")}
                className="text-brand"
              />
              Individual
            </label>
            <label className="flex items-center gap-1 text-[10px] text-text-secondary">
              <input
                type="radio"
                name="partyKind"
                checked={newPartyKind === "organization"}
                onChange={() => setNewPartyKind("organization")}
                className="text-brand"
              />
              Organization
            </label>
            <div className="flex-1" />
            <button
              onClick={() => handleAddParty(newPartyFor)}
              disabled={!newPartyName.trim() || addingParty}
              className="text-xs px-2 py-1 rounded bg-brand text-white
                         hover:bg-brand-hover disabled:opacity-50 transition-colors"
            >
              {addingParty ? "Adding..." : "Add"}
            </button>
          </div>
        </div>
      )}

      {/* Dates */}
      <div className="grid grid-cols-2 gap-2">
        <div>
          <label className="text-[10px] text-text-disabled block mb-1">Date Sent</label>
          <input
            type="date"
            value={newItem.date_sent}
            onChange={(e) => setNewItem((p) => ({ ...p, date_sent: e.target.value }))}
            className="w-full bg-surface-2 border border-border rounded px-2 py-1.5
                       text-xs text-text-primary focus:border-brand focus:ring-1
                       focus:ring-brand-ring focus:outline-none"
          />
        </div>
        <div>
          <label className="text-[10px] text-text-disabled block mb-1">Date Received</label>
          <input
            type="date"
            value={newItem.date_received}
            onChange={(e) => setNewItem((p) => ({ ...p, date_received: e.target.value }))}
            className="w-full bg-surface-2 border border-border rounded px-2 py-1.5
                       text-xs text-text-primary focus:border-brand focus:ring-1
                       focus:ring-brand-ring focus:outline-none"
          />
        </div>
      </div>

      {/* Notes */}
      <div>
        <label className="text-[10px] text-text-disabled block mb-1">Notes</label>
        <textarea
          value={newItem.notes}
          onChange={(e) => setNewItem((p) => ({ ...p, notes: e.target.value }))}
          rows={2}
          className="w-full bg-surface-2 border border-border rounded px-2 py-1.5
                     text-xs text-text-primary placeholder:text-text-disabled
                     focus:border-brand focus:ring-1 focus:ring-brand-ring
                     focus:outline-none resize-y"
          placeholder="Optional notes..."
        />
      </div>

      {/* Submit */}
      <div className="flex justify-end">
        <button
          onClick={onSubmit}
          className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5
                     rounded bg-brand text-white hover:bg-brand-hover
                     transition-colors"
        >
          {submitLabel}
        </button>
      </div>
    </div>
  );

  /* ================================================================ */
  /* Loading state                                                     */
  /* ================================================================ */

  if (threadsLoading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  /* ================================================================ */
  /* Render                                                            */
  /* ================================================================ */

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Mobile toolbar */}
      <div className="md:hidden shrink-0 bg-surface-1 border-b border-border px-4 py-2 flex items-center gap-2">
        {mobileView === "detail" && activeThread ? (
          <button onClick={() => setMobileView("list")} className="text-sm text-text-secondary">
            ← Threads
          </button>
        ) : (
          <span className="text-sm font-medium">Correspondence</span>
        )}
        <div className="flex-1" />
        {mobileView === "list" && (
          <button onClick={() => setAddingThread(true)} className="text-brand p-1">
            <Plus size={18} />
          </button>
        )}
        {mobileView === "detail" && activeThread && (
          <button onClick={() => setShowNewItem(true)} className="text-brand p-1">
            <Plus size={18} />
          </button>
        )}
      </div>

      <div className="flex-1 flex min-h-0">
        {/* Thread sidebar */}
        <aside
          className={`w-65 shrink-0 bg-surface-1 border-r border-border flex flex-col overflow-hidden
                      ${mobileView === "detail" ? "max-md:hidden" : "max-md:w-full max-md:border-r-0"}`}
        >
          <div className="hidden md:flex items-center justify-between px-4 py-3 border-b border-border">
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Threads
            </h3>
            <button
              onClick={() => setAddingThread(true)}
              className="text-brand hover:text-brand-hover p-1"
              title="New thread"
            >
              <Plus size={16} />
            </button>
          </div>

          {/* New thread inline form */}
          {addingThread && (
            <div className="p-2 border-b border-border">
              <div className="flex gap-1">
                <input
                  type="text"
                  value={newThreadTitle}
                  onChange={(e) => setNewThreadTitle(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreateThread()}
                  placeholder="Thread title..."
                  className="flex-1 bg-surface-2 border border-border rounded px-2 py-1
                             text-xs text-text-primary placeholder:text-text-disabled
                             focus:border-brand focus:outline-none"
                  autoFocus
                />
                <button
                  onClick={handleCreateThread}
                  disabled={!newThreadTitle.trim()}
                  className="text-xs px-2 py-1 rounded bg-brand text-white
                             hover:bg-brand-hover disabled:opacity-50 transition-colors"
                >
                  Add
                </button>
                <button
                  onClick={() => { setAddingThread(false); setNewThreadTitle(""); }}
                  className="p-1 text-text-disabled hover:text-text-secondary"
                >
                  <X size={14} />
                </button>
              </div>
            </div>
          )}

          {/* Thread list */}
          <div className="flex-1 overflow-y-auto p-2">
            {threads.length === 0 ? (
              <div className="text-center py-8 px-4">
                <Mail size={24} className="text-text-disabled mx-auto mb-2" />
                <p className="text-xs text-text-secondary">No threads yet</p>
                <p className="text-xs text-text-disabled mt-1">
                  Start tracking your correspondence.
                </p>
              </div>
            ) : (
              threads.map((t) => {
                const isActive = t.id === activeThreadId;
                return (
                  <div
                    key={t.id}
                    onClick={() => {
                      setActiveThreadId(t.id);
                      if (window.innerWidth < 768) setMobileView("detail");
                    }}
                    className={`p-2.5 rounded-md cursor-pointer mb-1 border
                                transition-colors hover:bg-surface-2 group
                                ${isActive ? "bg-brand-bg border-brand" : "border-transparent"}`}
                  >
                    <div className="flex items-start justify-between gap-1">
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-medium truncate">{t.title}</div>
                        <div className="flex items-center gap-1.5 mt-1">
                          <span className="text-[10px] text-text-disabled">
                            {t.item_count} item{t.item_count !== 1 ? "s" : ""}
                          </span>
                          {t.last_activity && (
                            <span className="text-[10px] text-text-disabled">
                              · {formatDate(t.last_activity)}
                            </span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteThread(t.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-0.5
                                   text-text-disabled hover:text-danger transition-all shrink-0"
                        title="Delete thread"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </aside>

        {/* Detail area */}
        <main
          className={`flex-1 flex flex-col min-w-0 overflow-hidden
                      ${mobileView === "list" ? "max-md:hidden" : ""}`}
        >
          {activeThread ? (
            <>
              {/* Thread header */}
              <div className="hidden md:flex shrink-0 items-center justify-between px-4 py-2
                              bg-surface-1 border-b border-border">
                <div className="min-w-0 mr-2">
                  <h2 className="text-sm font-semibold truncate">{activeThread.title}</h2>
                  <p className="text-[10px] text-text-disabled">
                    {activeThread.item_count} item{activeThread.item_count !== 1 ? "s" : ""}
                    {activeThread.last_activity && ` · last activity ${formatDate(activeThread.last_activity)}`}
                  </p>
                </div>
                <button
                  onClick={() => setShowNewItem(true)}
                  className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5
                             rounded bg-brand text-white hover:bg-brand-hover
                             transition-colors"
                >
                  <Plus size={14} />
                  New Item
                </button>
              </div>

              {/* Items + form */}
              <div className="flex-1 overflow-y-auto">
                <div className="px-4 py-3 md:py-4 md:max-w-3xl md:mx-auto space-y-3">
                  {/* New item form */}
                  {showNewItem &&
                    itemForm(
                      handleCreateItem,
                      () => setShowNewItem(false),
                      "Add Item",
                    )
                  }

                  {/* Edit form */}
                  {editingId !== null &&
                    itemForm(
                      handleUpdateItem,
                      () => setEditingId(null),
                      "Save Changes",
                    )
                  }

                  {/* Items list */}
                  {itemsLoading ? (
                    <div className="flex items-center justify-center py-8">
                      <Loader2 className="animate-spin text-text-disabled" size={20} />
                    </div>
                  ) : items.length === 0 && !showNewItem ? (
                    <div className="text-center py-12 px-4">
                      <Mail size={28} className="text-text-disabled mx-auto mb-2" />
                      <p className="text-xs text-text-secondary">No items in this thread</p>
                      <p className="text-xs text-text-disabled mt-1">
                        Log a correspondence to get started.
                      </p>
                    </div>
                  ) : (
                    items.map((item) => (
                      <div
                        key={item.id}
                        className="bg-surface-1 border border-border rounded-lg p-3 md:p-4
                                   group"
                      >
                        {/* Header row */}
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span
                              className={`text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase ${
                                item.direction === "sent"
                                  ? "bg-brand-bg text-brand"
                                  : "bg-info-bg text-info"
                              }`}
                            >
                              {item.direction === "sent" ? (
                                <span className="inline-flex items-center gap-1"><Send size={10} /> Sent</span>
                              ) : (
                                <span className="inline-flex items-center gap-1"><Inbox size={10} /> Received</span>
                              )}
                            </span>
                            {(item.date_sent || item.date_received) && (
                              <span className="text-[10px] text-text-disabled">
                                {item.date_sent && item.direction === "sent"
                                  ? formatDate(item.date_sent)
                                  : item.date_received
                                    ? formatDate(item.date_received)
                                    : formatDate(item.date_sent!)}
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button
                              onClick={() => startEditing(item)}
                              className="p-0.5 text-text-disabled hover:text-text-secondary"
                              title="Edit"
                            >
                              <Pencil size={12} />
                            </button>
                            <button
                              onClick={() => handleDeleteItem(item.id)}
                              className="p-0.5 text-text-disabled hover:text-danger"
                              title="Delete"
                            >
                              <Trash2 size={12} />
                            </button>
                          </div>
                        </div>

                        {/* Party line */}
                        <p className="text-xs text-text-secondary mb-2">
                          {(item.sender_name || "Unknown")}
                          {" → "}
                          {(item.receiver_name || "Unknown")}
                        </p>

                        {/* Notes */}
                        {item.notes && (
                          <p className="text-xs text-text-primary whitespace-pre-wrap mb-2">
                            {item.notes}
                          </p>
                        )}

                        {/* Attachments */}
                        {item.attachments.length > 0 && (
                          <div className="flex items-center gap-1.5 flex-wrap mb-1.5">
                            {item.attachments.map((att) => (
                              <span
                                key={att.id}
                                className="inline-flex items-center gap-1 text-[10px]
                                           bg-surface-2 border border-border rounded
                                           px-1.5 py-0.5"
                              >
                                <Mail size={10} className="text-text-disabled" />
                                {att.document_name}
                                <button
                                  onClick={() => handleDetach(item.id, att.document_id)}
                                  className="text-text-disabled hover:text-danger"
                                  title="Remove attachment"
                                >
                                  <X size={10} />
                                </button>
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Attach button */}
                        <div className="mt-1.5">
                          <DocumentAttachButton
                            caseId={caseId}
                            attachedIds={item.attachments.map((a) => a.document_id)}
                            onAttach={(docId) => handleAttach(item.id, docId)}
                          />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          ) : (
            /* No thread selected */
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center px-4">
                <Mail size={32} className="text-text-disabled mx-auto mb-3" />
                <p className="text-sm text-text-secondary font-medium">
                  {threads.length === 0
                    ? "No correspondence tracked yet"
                    : "Select a thread"}
                </p>
                <p className="text-xs text-text-disabled mt-1">
                  {threads.length === 0
                    ? "Create a thread to start logging correspondence."
                    : "Choose a thread from the sidebar or create a new one."}
                </p>
                {threads.length === 0 && (
                  <button
                    onClick={() => setAddingThread(true)}
                    className="mt-3 inline-flex items-center gap-1.5 text-xs px-3 py-1.5
                               rounded-full bg-brand text-white hover:bg-brand-hover
                               transition-colors"
                  >
                    <Plus size={12} />
                    New Thread
                  </button>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
