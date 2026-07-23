"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, Send, ArrowLeft, AlertCircle, FileText, Mail } from "lucide-react";
import {
  getVendorMatchMessages,
  createDraftMessage,
  updateDraftMessage,
  sendMessage,
  markMessagesRead,
  type VendorMatch,
  type VendorOutreachMessage,
  type OutreachStatus,
} from "@/lib/api";
import DocumentPreviewModal from "@/components/DocumentPreviewModal";

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<OutreachStatus, string> = {
  not_contacted: "bg-surface-2 text-text-disabled",
  requested: "bg-warning-bg text-warning",
  received: "bg-success-bg text-success",
  declined: "bg-danger-bg text-danger",
};

const STATUS_LABELS: Record<OutreachStatus, string> = {
  not_contacted: "Not Contacted",
  requested: "Requested",
  received: "Received",
  declined: "Declined",
};

function formatDate(iso: string | null): string {
  if (!iso) return "";
  return new Date(iso).toLocaleString(undefined, {
    month: "short", day: "numeric", year: "numeric",
    hour: "numeric", minute: "2-digit",
  });
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function VendorMatchThreadPage() {
  const params = useParams();
  const router = useRouter();
  const caseId = Number(params.id);
  const matchId = Number(params.matchId);

  const [match, setMatch] = useState<VendorMatch | null>(null);
  const [messages, setMessages] = useState<VendorOutreachMessage[]>([]);
  const [draft, setDraft] = useState<VendorOutreachMessage | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewDocId, setPreviewDocId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getVendorMatchMessages(matchId);
      setMatch(data.match);
      // Split draft from the rest — draft always renders at the bottom
      const all = data.messages;
      const d = all.find((m) => m.status === "draft") || null;
      setDraft(d);
      setMessages(all.filter((m) => m.status !== "draft"));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages");
    }
  }, [matchId]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
    markMessagesRead(matchId).catch(() => {});
  }, [refresh]); // eslint-disable-line react-hooks/exhaustive-deps

  const ensureDraft = async () => {
    if (draft) return; // already have one
    setError(null);
    try {
      await createDraftMessage(matchId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create draft");
    }
  };

  const handleBlur = async (field: "subject" | "body", value: string) => {
    if (!draft) return;
    if (value === (field === "subject" ? draft.subject : draft.body)) return;
    setError(null);
    try {
      await updateDraftMessage(draft.id, { [field]: value });
      // Optimistically update local state to avoid cursor jump
      setDraft((prev) => prev ? { ...prev, [field]: value } : null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    }
  };

  const handleSend = async () => {
    if (!draft) return;
    setSending(true);
    setError(null);
    try {
      await sendMessage(draft.id);
      setDraft(null); // draft is now sent — will reappear as a message on refresh
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send");
    }
    setSending(false);
  };

  /* ---------------------------------------------------------------- */
  /* Loading / Error                                                  */
  /* ---------------------------------------------------------------- */

  if (loading) {
    return (
      <div className="h-dvh flex items-center justify-center bg-surface-0">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  if (!match) {
    return (
      <div className="h-dvh flex items-center justify-center bg-surface-0">
        <p className="text-sm text-text-disabled">Vendor match not found.</p>
      </div>
    );
  }

  const hasAnyMessage = messages.length > 0;

  /* ---------------------------------------------------------------- */
  /* Render                                                           */
  /* ---------------------------------------------------------------- */

  return (
    <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
      {/* Header */}
      <header className="sticky top-0 shrink-0 bg-surface-1 border-b border-border z-30">
        <div className="flex items-center h-14 px-4 gap-3 max-w-3xl mx-auto">
          <button
            onClick={() => router.push(`/cases/${caseId}?tab=outreach`)}
            className="text-text-secondary hover:text-brand transition-colors shrink-0
                       min-h-[44px] min-w-[44px] flex items-center justify-center -ml-2"
            aria-label="Back to outreach"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="min-w-0 flex-1">
            <h1 className="text-sm font-semibold text-text-primary truncate">
              {match.vendor_name}
            </h1>
            <p className="text-xs text-text-disabled truncate">
              {match.contact_email || "No email on file"}
            </p>
          </div>
          <span className={`shrink-0 text-[11px] font-medium px-2 py-0.5 rounded-sm ${STATUS_COLORS[match.outreach_status]}`}>
            {STATUS_LABELS[match.outreach_status]}
          </span>
        </div>
      </header>

      {error && (
        <div className="shrink-0 bg-danger-bg border-b border-danger/20 px-4 py-2">
          <div className="max-w-3xl mx-auto flex items-center gap-2 text-xs text-danger">
            <AlertCircle size={14} />
            {error}
            <button onClick={() => setError(null)} className="ml-auto text-danger/70 hover:text-danger">
              ×
            </button>
          </div>
        </div>
      )}

      {/* Thread */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-3xl mx-auto space-y-3">

          {/* Empty state */}
          {!hasAnyMessage && !draft && (
            <div className="flex flex-col items-center justify-center gap-4 py-16 px-6 text-center">
              <div className="size-12 rounded-full bg-surface-2 flex items-center justify-center text-text-disabled">
                <Mail size={22} />
              </div>
              <div>
                <p className="text-sm font-medium text-text-secondary">No messages yet</p>
                <p className="text-xs text-text-disabled mt-1">
                  Draft an outreach email to {match.vendor_name} to get started.
                </p>
              </div>
              <button
                onClick={ensureDraft}
                className="bg-brand text-white border-brand hover:bg-brand-hover active:bg-brand-active
                           px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150"
              >
                Create Draft
              </button>
            </div>
          )}

          {/* Read-only messages (sent + received), chronological */}
          {messages.map((msg) => {
            const isOutbound = msg.direction === "outbound";
            const isFailed = msg.status === "failed";
            const isReceived = msg.status === "received";

            return (
              <div
                key={msg.id}
                className={`bg-surface-1 border rounded-lg overflow-hidden ${
                  isFailed ? "border-danger/40"
                : isReceived ? "border-success/30"
                : "border-border"
                }`}
              >
                <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border-light bg-surface-2">
                  <span className={`text-[11px] font-semibold uppercase tracking-wide ${
                    isOutbound ? "text-brand" : "text-success"
                  }`}>
                    {isOutbound ? "To Vendor" : "From Vendor"}
                  </span>
                  {msg.status === "sent" && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-sm bg-info-bg text-info">
                      Sent
                    </span>
                  )}
                  {isReceived && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-sm bg-success-bg text-success">
                      Received
                    </span>
                  )}
                  {isFailed && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-sm bg-danger-bg text-danger">
                      Failed
                    </span>
                  )}
                  <span className="text-xs text-text-disabled ml-auto">
                    {formatDate(msg.sent_at || msg.received_at)}
                  </span>
                </div>

                <div className="p-4">
                  <p className="text-sm font-semibold text-text-primary mb-2">{msg.subject}</p>
                  <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                    {msg.body}
                  </p>

                  {isFailed && msg.error_message && (
                    <p className="mt-2 text-xs text-danger">{msg.error_message}</p>
                  )}

                  {/* Attachments */}
                  {isReceived && (msg as any).metadata?.attachment_doc_ids?.length > 0 && (
                    <div className="mt-3 pt-3 border-t border-border-light">
                      <p className="text-xs font-medium text-text-secondary mb-2">Attachments</p>
                      <div className="flex flex-wrap gap-2">
                        {(msg as any).metadata.attachment_doc_ids.map((did: number) => (
                          <button
                            key={did}
                            onClick={() => setPreviewDocId(did)}
                            className="inline-flex items-center gap-1.5 bg-surface-2 text-text-primary
                                       border border-border hover:bg-surface-3 hover:border-border-strong
                                       px-3 py-1.5 rounded text-xs font-medium transition-colors"
                          >
                            <FileText size={12} />
                            Document #{did}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-light">
                    {isReceived && (
                      <button
                        onClick={ensureDraft}
                        className="inline-flex items-center gap-2 bg-brand text-white border-brand
                                   hover:bg-brand-hover active:bg-brand-active
                                   px-4 py-2 rounded-lg text-sm font-medium
                                   transition-colors duration-150"
                      >
                        <Send size={14} />
                        Reply
                      </button>
                    )}
                    {msg.document_id && (
                      <button
                        onClick={() => setPreviewDocId(msg.document_id)}
                        className="inline-flex items-center gap-2 bg-surface-2 text-text-primary border-border
                                   hover:bg-surface-3 hover:border-border-strong
                                   px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150"
                      >
                        <FileText size={14} />
                        View Document
                      </button>
                    )}
                  </div>
                </div>
              </div>
            );
          })}

          {/* Draft — always at the bottom */}
          {draft && (
            <div className="bg-surface-1 border border-warning/30 rounded-lg overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border-light bg-surface-2">
                <span className="text-[11px] font-semibold uppercase tracking-wide text-warning">
                  Draft Reply
                </span>
                <button
                  onClick={handleSend}
                  disabled={sending || !draft.subject.trim()}
                  className="ml-auto inline-flex items-center gap-1.5 bg-brand text-white
                             hover:bg-brand-hover active:bg-brand-active
                             disabled:opacity-50 disabled:cursor-not-allowed
                             px-3 py-1 rounded text-xs font-medium transition-colors"
                >
                  {sending ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />}
                  Send
                </button>
              </div>

              <div className="p-4">
                <div className="mb-3">
                  <label className="block mb-1.5 text-xs font-medium text-text-secondary">
                    Subject
                  </label>
                  <input
                    type="text"
                    defaultValue={draft.subject}
                    onBlur={(e) => handleBlur("subject", e.target.value)}
                    className="w-full px-3 py-2 text-sm text-text-primary
                               bg-surface-2 border border-border rounded-sm
                               focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                               transition-colors duration-150"
                  />
                </div>

                <div>
                  <label className="block mb-1.5 text-xs font-medium text-text-secondary">
                    Message
                  </label>
                  <textarea
                    defaultValue={draft.body}
                    onBlur={(e) => handleBlur("body", e.target.value)}
                    rows={8}
                    className="w-full px-3 py-2 text-sm text-text-primary leading-relaxed
                               bg-surface-2 border border-border rounded-sm
                               focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                               resize-y transition-colors duration-150"
                  />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Document preview modal */}
      {previewDocId && (
        <DocumentPreviewModal
          docId={previewDocId}
          docName={match.vendor_name}
          open={previewDocId !== null}
          onClose={() => setPreviewDocId(null)}
        />
      )}
    </div>
  );
}
