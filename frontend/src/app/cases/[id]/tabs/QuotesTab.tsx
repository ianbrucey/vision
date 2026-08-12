"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus, Loader2, X, Check, Pencil, Trash2, User, Mail, Phone } from "lucide-react";
import { createQuote, listQuotes, updateQuote, deleteQuote, getSolicitationByCase, type Quote } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface QuotesTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  draft: { label: "Draft", color: "bg-surface-2 text-text-secondary" },
  pending_site_visit: { label: "Pending Site Visit", color: "bg-warning-bg text-warning" },
  submitted: { label: "Submitted", color: "bg-info-bg text-info" },
  awarded: { label: "Awarded", color: "bg-success-bg text-success" },
  lost: { label: "Lost", color: "bg-danger-bg text-danger" },
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function QuotesTab({ caseId }: QuotesTabProps) {
  const [quotes, setQuotes] = useState<Quote[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [solicitationId, setSolicitationId] = useState<number | null>(null);

  // Add form
  const [showAdd, setShowAdd] = useState(false);
  const [newNotes, setNewNotes] = useState("");
  const [newAmount, setNewAmount] = useState("");
  const [newPocName, setNewPocName] = useState("");
  const [newPocEmail, setNewPocEmail] = useState("");
  const [newPocPhone, setNewPocPhone] = useState("");
  const [saving, setSaving] = useState(false);

  // Edit
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editNotes, setEditNotes] = useState("");
  const [editAmount, setEditAmount] = useState("");
  const [editPocName, setEditPocName] = useState("");
  const [editPocEmail, setEditPocEmail] = useState("");
  const [editPocPhone, setEditPocPhone] = useState("");

  /* ---- fetch ---- */
  const fetchQuotes = useCallback(async () => {
    if (!solicitationId) return;
    try {
      const data = await listQuotes(solicitationId);
      setQuotes(data.quotes);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load quotes");
    } finally {
      setLoading(false);
    }
  }, [solicitationId]);

  useEffect(() => {
    getSolicitationByCase(caseId)
      .then((sol) => setSolicitationId(sol.id))
      .catch(() => setLoading(false));
  }, [caseId]);

  useEffect(() => {
    if (solicitationId) fetchQuotes();
  }, [solicitationId, fetchQuotes]);

  /* ---- handlers ---- */
  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!solicitationId) return;
    setSaving(true);
    try {
      await createQuote(solicitationId, {
        notes: newNotes.trim() || undefined,
        amount: newAmount ? parseFloat(newAmount) : undefined,
        poc_name: newPocName.trim() || undefined,
        poc_email: newPocEmail.trim() || undefined,
        poc_phone: newPocPhone.trim() || undefined,
      });
      setShowAdd(false);
      setNewNotes(""); setNewAmount(""); setNewPocName(""); setNewPocEmail(""); setNewPocPhone("");
      fetchQuotes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create quote");
    } finally {
      setSaving(false);
    }
  };

  const handleStatus = async (quoteId: number, status: string) => {
    if (!solicitationId) return;
    try {
      await updateQuote(solicitationId, quoteId, { status });
      fetchQuotes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  };

  const startEdit = (q: Quote) => {
    setEditingId(q.id);
    setEditNotes(q.notes || "");
    setEditAmount(q.amount?.toString() || "");
    setEditPocName(q.poc_name || "");
    setEditPocEmail(q.poc_email || "");
    setEditPocPhone(q.poc_phone || "");
  };

  const saveEdit = async (quoteId: number) => {
    if (!solicitationId) return;
    try {
      await updateQuote(solicitationId, quoteId, {
        notes: editNotes.trim() || undefined,
        amount: editAmount ? parseFloat(editAmount) : undefined,
        poc_name: editPocName.trim() || undefined,
        poc_email: editPocEmail.trim() || undefined,
        poc_phone: editPocPhone.trim() || undefined,
      });
      setEditingId(null);
      fetchQuotes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update quote");
    }
  };

  const handleDelete = async (quoteId: number) => {
    if (!confirm("Delete this quote?")) return;
    if (!solicitationId) return;
    try {
      await deleteQuote(solicitationId, quoteId);
      fetchQuotes();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  const formatAmount = (amt: number | null) => {
    if (amt == null) return null;
    return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(amt);
  };

  /* ---- render ---- */
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-4 py-4 md:py-6 md:max-w-3xl md:mx-auto space-y-3">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-text-primary">Quotes</h2>
            <p className="text-xs text-text-disabled mt-0.5">
              Track subcontractor quotes and site visit status.
            </p>
          </div>
          <button
            onClick={() => setShowAdd(true)}
            className="inline-flex items-center gap-1 px-3 py-1.5 text-xs bg-brand text-white rounded-lg hover:opacity-90"
          >
            <Plus size={13} />
            Add Quote
          </button>
        </div>

        {error && (
          <div className="px-3 py-2 text-xs text-danger bg-danger-bg rounded">{error}</div>
        )}

        {/* Add form */}
        {showAdd && (
          <div className="bg-surface-1 border border-border rounded-lg p-4">
            <form onSubmit={handleAdd} className="space-y-3">
              <label className="block">
                <span className="text-xs text-text-secondary">Notes</span>
                <textarea
                  value={newNotes}
                  onChange={e => setNewNotes(e.target.value)}
                  rows={3}
                  className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand resize-none"
                  placeholder="What did the sub say? What do they need?"
                />
              </label>
              <div className="grid grid-cols-2 gap-3">
                <label className="block">
                  <span className="text-xs text-text-secondary">Amount ($)</span>
                  <input
                    type="number"
                    value={newAmount}
                    onChange={e => setNewAmount(e.target.value)}
                    className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-text-secondary">POC Name</span>
                  <input
                    type="text"
                    value={newPocName}
                    onChange={e => setNewPocName(e.target.value)}
                    className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-text-secondary">POC Email</span>
                  <input
                    type="email"
                    value={newPocEmail}
                    onChange={e => setNewPocEmail(e.target.value)}
                    className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                  />
                </label>
                <label className="block">
                  <span className="text-xs text-text-secondary">POC Phone</span>
                  <input
                    type="text"
                    value={newPocPhone}
                    onChange={e => setNewPocPhone(e.target.value)}
                    className="mt-1 w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded-lg text-text-primary outline-none focus:border-brand"
                  />
                </label>
              </div>
              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => setShowAdd(false)} className="px-3 py-1.5 text-xs border border-border rounded-lg text-text-secondary">Cancel</button>
                <button type="submit" disabled={saving} className="px-3 py-1.5 text-xs bg-brand text-white rounded-lg hover:opacity-90 disabled:opacity-50">
                  {saving ? "Saving..." : "Save Quote"}
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Quote cards */}
        {quotes.length === 0 && !loading && (
          <div className="text-center py-12 text-text-disabled text-sm">
            No quotes yet. Click "Add Quote" to start tracking.
          </div>
        )}

        {quotes.map((q) => (
          <div key={q.id} className="bg-surface-1 border border-border rounded-lg p-4">
            {editingId === q.id ? (
              /* Edit mode */
              <div className="space-y-3">
                <textarea
                  value={editNotes}
                  onChange={e => setEditNotes(e.target.value)}
                  rows={3}
                  className="w-full px-3 py-2 text-sm bg-surface-2 border border-border rounded text-text-primary outline-none focus:border-brand resize-none"
                />
                <div className="grid grid-cols-2 gap-3">
                  <input type="number" value={editAmount} onChange={e => setEditAmount(e.target.value)} className="px-2 py-1.5 text-sm bg-surface-2 border border-border rounded" placeholder="Amount" />
                  <input type="text" value={editPocName} onChange={e => setEditPocName(e.target.value)} className="px-2 py-1.5 text-sm bg-surface-2 border border-border rounded" placeholder="POC Name" />
                  <input type="email" value={editPocEmail} onChange={e => setEditPocEmail(e.target.value)} className="px-2 py-1.5 text-sm bg-surface-2 border border-border rounded" placeholder="POC Email" />
                  <input type="text" value={editPocPhone} onChange={e => setEditPocPhone(e.target.value)} className="px-2 py-1.5 text-sm bg-surface-2 border border-border rounded" placeholder="POC Phone" />
                </div>
                <div className="flex justify-end gap-2">
                  <button onClick={() => setEditingId(null)} className="px-2 py-1 text-xs border border-border rounded text-text-secondary"><X size={12} className="inline mr-1"/>Cancel</button>
                  <button onClick={() => saveEdit(q.id)} className="px-2 py-1 text-xs bg-brand text-white rounded"><Check size={12} className="inline mr-1"/>Save</button>
                </div>
              </div>
            ) : (
              /* Display mode */
              <>
                <div className="flex items-start justify-between mb-2">
                  <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${STATUS_CONFIG[q.status]?.color || ""}`}>
                    {STATUS_CONFIG[q.status]?.label || q.status}
                  </span>
                  <div className="flex items-center gap-1">
                    {q.status === "draft" && (
                      <>
                        <button onClick={() => handleStatus(q.id, "pending_site_visit")} className="px-2 py-0.5 text-[10px] text-warning border border-warning/30 rounded hover:bg-warning-bg">
                          Site Visit Needed
                        </button>
                        <button onClick={() => handleStatus(q.id, "submitted")} className="px-2 py-0.5 text-[10px] text-info border border-info/30 rounded hover:bg-info-bg">
                          Submit
                        </button>
                      </>
                    )}
                    {q.status === "pending_site_visit" && (
                      <button onClick={() => handleStatus(q.id, "submitted")} className="px-2 py-0.5 text-[10px] text-info border border-info/30 rounded hover:bg-info-bg">
                        Submit Quote
                      </button>
                    )}
                    {q.status === "submitted" && (
                      <>
                        <button onClick={() => handleStatus(q.id, "awarded")} className="px-2 py-0.5 text-[10px] text-success border border-success/30 rounded hover:bg-success-bg">
                          Award
                        </button>
                        <button onClick={() => handleStatus(q.id, "lost")} className="px-2 py-0.5 text-[10px] text-danger border border-danger/30 rounded hover:bg-danger-bg">
                          Lost
                        </button>
                      </>
                    )}
                    <button onClick={() => startEdit(q)} className="p-1 text-text-disabled hover:text-text-primary" title="Edit"><Pencil size={12} /></button>
                    {q.status === "draft" && (
                      <button onClick={() => handleDelete(q.id)} className="p-1 text-text-disabled hover:text-danger" title="Delete"><Trash2 size={12} /></button>
                    )}
                  </div>
                </div>
                {q.notes && <p className="text-sm text-text-primary mb-2 whitespace-pre-wrap">{q.notes}</p>}
                <div className="flex items-center gap-3 text-xs text-text-secondary flex-wrap">
                  {q.amount != null && <span className="font-medium text-text-primary">{formatAmount(q.amount)}</span>}
                  {q.poc_name && <span className="inline-flex items-center gap-1"><User size={10} />{q.poc_name}</span>}
                  {q.poc_email && <span className="inline-flex items-center gap-1"><Mail size={10} />{q.poc_email}</span>}
                  {q.poc_phone && <span className="inline-flex items-center gap-1"><Phone size={10} />{q.poc_phone}</span>}
                  {q.created_by_username && <span className="text-text-disabled">by {q.created_by_username}</span>}
                </div>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
