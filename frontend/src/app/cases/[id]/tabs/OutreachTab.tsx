"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Send, FileText, X, MessageSquare } from "lucide-react";
import {
  getSolicitationByCase,
  getVendorMatches,
  updateVendorMatchOutreach,
  type SolicitationWithDocuments,
  type VendorMatch,
  type OutreachStatus,
} from "@/lib/api";
import DocumentAttachButton from "@/components/DocumentAttachButton";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface OutreachTabProps {
  caseId: number;
}

const STATUS_OPTIONS: { value: OutreachStatus; label: string }[] = [
  { value: "not_contacted", label: "Not Contacted" },
  { value: "requested", label: "Requested" },
  { value: "received", label: "Received" },
  { value: "declined", label: "Declined" },
];

const STATUS_COLORS: Record<OutreachStatus, string> = {
  not_contacted: "bg-surface-2 text-text-disabled",
  requested: "bg-warning-bg text-warning",
  received: "bg-success-bg text-success",
  declined: "bg-danger-bg text-danger",
};

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function OutreachTab({ caseId }: OutreachTabProps) {
  const [sol, setSol] = useState<SolicitationWithDocuments | null>(null);
  const [matches, setMatches] = useState<VendorMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const s = await getSolicitationByCase(caseId);
      const m = await getVendorMatches(s.id);
      setSol(s);
      setMatches(m.matches);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load outreach data");
    }
  }, [caseId]);

  useEffect(() => {
    let cancelled = false;
    refresh().finally(() => {
      if (!cancelled) setLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [refresh]);

  const applyUpdate = (updated: VendorMatch) => {
    setMatches((prev) => prev.map((m) => (m.id === updated.id ? updated : m)));
  };

  const handleStatusChange = async (matchId: number, outreach_status: OutreachStatus) => {
    try {
      const updated = await updateVendorMatchOutreach(matchId, { outreach_status });
      applyUpdate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update status");
    }
  };

  const handleAttachDoc = async (matchId: number, documentId: number) => {
    try {
      const updated = await updateVendorMatchOutreach(matchId, { outreach_doc_id: documentId });
      applyUpdate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to attach document");
    }
  };

  const handleRemoveDoc = async (matchId: number) => {
    try {
      const updated = await updateVendorMatchOutreach(matchId, { clear_outreach_doc: true });
      applyUpdate(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to remove document");
    }
  };

  const router = useRouter();

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  if (!sol) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <p className="text-sm text-text-disabled text-center">
          {error || "This case has no associated solicitation."}
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="shrink-0 px-4 py-3 border-b border-border">
        <p className="text-sm font-medium text-text-primary">Vendor Outreach</p>
        <p className="text-xs text-text-disabled">
          Track quote requests and responses per matched vendor.
        </p>
      </div>

      {error && (
        <div className="shrink-0 px-4 py-2 text-xs text-danger bg-danger-bg">{error}</div>
      )}

      {matches.length === 0 ? (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-sm">
            <Send className="mx-auto mb-3 text-text-disabled" size={24} strokeWidth={1.5} />
            <p className="text-sm text-text-disabled">
              No vendor matches yet. Add or match vendors first, then track outreach here.
            </p>
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-auto">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-surface-1 border-b border-border">
              <tr className="text-left text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
                <th className="px-3 py-2">Vendor</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 hidden sm:table-cell">Requested</th>
                <th className="px-3 py-2 hidden sm:table-cell">Received</th>
                <th className="px-3 py-2">Document</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {matches.map((m) => (
                <tr key={m.id} className="hover:bg-surface-2 transition-colors">
                  <td className="px-3 py-2 max-w-[200px]">
                    <p className="font-medium text-text-primary truncate" title={m.vendor_name}>
                      {m.vendor_name}
                    </p>
                  </td>
                  <td className="px-3 py-2">
                    <select
                      value={m.outreach_status}
                      onChange={(e) => handleStatusChange(m.id, e.target.value as OutreachStatus)}
                      className={`text-[11px] font-medium px-2 py-1 rounded-sm border border-border
                                  cursor-pointer ${STATUS_COLORS[m.outreach_status]}`}
                    >
                      {STATUS_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => router.push(`/cases/${caseId}/vendor-matches/${m.id}`)}
                      className="ml-1.5 inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-border
                                 bg-surface-1 hover:bg-surface-3 text-text-primary transition-colors"
                    >
                      <MessageSquare size={10} />
                      Messages
                    </button>
                  </td>
                  <td className="px-3 py-2 hidden sm:table-cell text-xs text-text-secondary">
                    {formatDate(m.outreach_requested_at)}
                  </td>
                  <td className="px-3 py-2 hidden sm:table-cell text-xs text-text-secondary">
                    {formatDate(m.outreach_received_at)}
                  </td>
                  <td className="px-3 py-2">
                    {m.outreach_doc_id && m.outreach_doc_name ? (
                      <span className="inline-flex items-center gap-1 text-[11px] bg-surface-2
                                       border border-border rounded px-1.5 py-0.5 max-w-[160px]">
                        <FileText size={10} className="text-text-disabled shrink-0" />
                        <span className="truncate">{m.outreach_doc_name}</span>
                        <button
                          onClick={() => handleRemoveDoc(m.id)}
                          className="text-text-disabled hover:text-danger shrink-0"
                          title="Remove attachment"
                        >
                          <X size={10} />
                        </button>
                      </span>
                    ) : (
                      <DocumentAttachButton
                        caseId={caseId}
                        attachedIds={[]}
                        onAttach={(docId) => handleAttachDoc(m.id, docId)}
                      />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
