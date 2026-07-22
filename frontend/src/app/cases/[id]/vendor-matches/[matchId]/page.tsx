"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Loader2, Send, ArrowLeft, AlertCircle, FileText, Mail } from "lucide-react";
import {
  getVendorMatchMessages,
  createDraftMessage,
  updateDraftMessage,
  sendMessage,
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
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<number | null>(null);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [previewDocId, setPreviewDocId] = useState<number | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await getVendorMatchMessages(matchId);
      setMatch(data.match);
      setMessages(data.messages);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load messages");
    }
  }, [matchId]);

  useEffect(() => {
    refresh().finally(() => setLoading(false));
  }, [refresh]);

  const handleCreateDraft = async () => {
    setError(null);
    try {
      await createDraftMessage(matchId);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create draft");
    }
  };

  const handleBlur = async (messageId: number, field: "subject" | "body", value: string) => {
    setSaving(messageId);
    try {
      await updateDraftMessage(messageId, { [field]: value });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save");
    }
    setSaving(null);
  };

  const handleSend = async (messageId: number) => {
    setSending(true);
    setError(null);
    try {
      await sendMessage(messageId);
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

  const hasDraft = messages.some((m) => m.status === "draft");
  const hasSent = messages.some((m) => m.status === "sent");

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
          {messages.length === 0 && !hasDraft && (
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
              {!hasSent && (
                <button
                  onClick={handleCreateDraft}
                  className="bg-brand text-white border-brand hover:bg-brand-hover active:bg-brand-active
                             px-4 py-2 rounded-lg text-sm font-medium transition-colors duration-150"
                >
                  Create Draft
                </button>
              )}
            </div>
          )}

          {messages.map((msg) => {
            const isOutbound = msg.direction === "outbound";
            const isDraft = msg.status === "draft";
            const isFailed = msg.status === "failed";

            return (
              <div
                key={msg.id}
                className={`bg-surface-1 border rounded-lg overflow-hidden ${
                  isFailed ? "border-danger/40" : "border-border"
                }`}
              >
                {/* Message header bar */}
                <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border-light bg-surface-2">
                  <span className={`text-[11px] font-semibold uppercase tracking-wide ${
                    isOutbound ? "text-brand" : "text-info"
                  }`}>
                    {isOutbound ? "To Vendor" : "From Vendor"}
                  </span>
                  {isDraft && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-sm bg-warning-bg text-warning">
                      Draft
                    </span>
                  )}
                  {msg.status === "sent" && (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-sm bg-success-bg text-success">
                      Sent
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
                  {/* Subject */}
                  {isDraft ? (
                    <div className="mb-3">
                      <label className="block mb-1.5 text-xs font-medium text-text-secondary">
                        Subject
                      </label>
                      <input
                        type="text"
                        defaultValue={msg.subject}
                        onBlur={(e) => {
                          if (e.target.value !== msg.subject) {
                            handleBlur(msg.id, "subject", e.target.value);
                          }
                        }}
                        className="w-full px-3 py-2 text-sm text-text-primary
                                   bg-surface-2 border border-border rounded-sm
                                   focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                                   transition-colors duration-150"
                      />
                    </div>
                  ) : (
                    <p className="text-sm font-semibold text-text-primary mb-2">{msg.subject}</p>
                  )}

                  {/* Body */}
                  {isDraft ? (
                    <div>
                      <label className="block mb-1.5 text-xs font-medium text-text-secondary">
                        Message
                      </label>
                      <textarea
                        defaultValue={msg.body}
                        onBlur={(e) => {
                          if (e.target.value !== msg.body) {
                            handleBlur(msg.id, "body", e.target.value);
                          }
                        }}
                        rows={8}
                        className="w-full px-3 py-2 text-sm text-text-primary leading-relaxed
                                   bg-surface-2 border border-border rounded-sm
                                   focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                                   resize-y transition-colors duration-150"
                      />
                    </div>
                  ) : (
                    <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
                      {msg.body}
                    </p>
                  )}

                  {/* Error message */}
                  {isFailed && msg.error_message && (
                    <p className="mt-2 text-xs text-danger">{msg.error_message}</p>
                  )}

                  {/* Actions */}
                  {(isDraft || (!isDraft && msg.document_id) || saving === msg.id) && (
                    <div className="flex items-center gap-2 mt-3 pt-3 border-t border-border-light">
                      {isDraft && (
                        <button
                          onClick={() => handleSend(msg.id)}
                          disabled={sending}
                          className="inline-flex items-center gap-2 bg-brand text-white border-brand
                                     hover:bg-brand-hover active:bg-brand-active
                                     px-4 py-2 rounded-lg text-sm font-medium
                                     transition-colors duration-150
                                     disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                          {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                          Send
                        </button>
                      )}
                      {!isDraft && msg.document_id && (
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
                      {saving === msg.id && (
                        <span className="inline-flex items-center gap-1.5 text-xs text-text-disabled">
                          <Loader2 size={12} className="animate-spin" />
                          Saving…
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {/* Create Draft button (shown when messages exist but none are draft) */}
          {messages.length > 0 && !hasDraft && !hasSent && (
            <div className="pt-1">
              <button
                onClick={handleCreateDraft}
                className="w-full bg-surface-2 text-text-primary border-border
                           hover:bg-surface-3 hover:border-border-strong
                           px-4 py-2.5 rounded-lg text-sm font-medium transition-colors duration-150"
              >
                Create Draft
              </button>
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
