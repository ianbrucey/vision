"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Loader2, ClipboardList, FileSearch, FileText, Clock, ChevronRight } from "lucide-react";
import { getMySolicitations, type Solicitation } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";

export default function MyWorkPage() {
  const { user, ready } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<Awaited<ReturnType<typeof getMySolicitations>> | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      setData(await getMySolicitations());
    } catch {} finally { setLoading(false); }
  }, []);

  useEffect(() => { if (user) fetchData(); }, [user, fetchData]);

  if (!ready || loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  if (!user) {
    router.replace("/login");
    return null;
  }

  const { solicitations, summary } = data ?? { solicitations: [], summary: { total_assigned: 0, needs_triage: 0, needs_quote: 0, quotes_in_progress: 0 } };

  const formatDate = (d: string | null) => {
    if (!d) return null;
    try { return new Date(d).toLocaleDateString(); } catch { return d; }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-lg font-semibold text-text-primary mb-6">My Queue</h1>

      {/* Stat tiles */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
        <StatTile icon={ClipboardList} label="Assigned" value={summary.total_assigned} color="text-brand" bg="bg-brand-bg" />
        <StatTile icon={FileSearch} label="Needs Triage" value={summary.needs_triage} color="text-warning" bg="bg-warning-bg" />
        <StatTile icon={FileText} label="Needs Quote" value={summary.needs_quote} color="text-info" bg="bg-info-bg" />
        <StatTile icon={Clock} label="Quotes in Progress" value={summary.quotes_in_progress} color="text-text-secondary" bg="bg-surface-2" />
      </div>

      {/* Solicitations */}
      {solicitations.length === 0 ? (
        <div className="text-center py-16 text-text-disabled">
          <ClipboardList size={32} className="mx-auto mb-3" strokeWidth={1.5} />
          <p className="text-sm">No assigned solicitations.</p>
          <p className="text-xs mt-1">Claim a solicitation from the main list to see it here.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {solicitations.map((s) => (
            <div
              key={s.id}
              onClick={() => router.push(`/cases/${s.case_id}`)}
              className="bg-surface-1 border border-border rounded-lg p-4 hover:bg-surface-2 cursor-pointer transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{s.title}</p>
                  <p className="text-xs text-text-disabled mt-0.5">
                    {s.agency && <span>{s.agency} · </span>}
                    {s.notice_id && <span className="font-mono">{s.notice_id}</span>}
                  </p>
                </div>
                <ChevronRight size={16} className="text-text-disabled shrink-0 ml-2" />
              </div>
              <div className="flex items-center gap-2 mt-2 flex-wrap">
                {s.response_deadline && (
                  <span className="text-[10px] text-text-secondary flex items-center gap-1">
                    <Clock size={10} />
                    Due {formatDate(s.response_deadline)}
                  </span>
                )}
                <StatusBadge label="ingestion" status={s.ingestion_status} />
                <StatusBadge label="triage" status={s.triage_status} />
                {(s.quotes_submitted ?? 0) > 0 && (
                  <span className="text-[10px] px-2 py-0.5 rounded font-medium bg-success-bg text-success">
                    {s.quotes_submitted} quote{s.quotes_submitted !== 1 ? "s" : ""}
                  </span>
                )}
                {(s.quotes_draft ?? 0) > 0 && (
                  <span className="text-[10px] px-2 py-0.5 rounded font-medium bg-warning-bg text-warning">
                    {s.quotes_draft} draft
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Mini components                                                    */
/* ------------------------------------------------------------------ */

function StatTile({ icon: Icon, label, value, color, bg }: { icon: typeof ClipboardList; label: string; value: number; color: string; bg: string }) {
  return (
    <div className={`${bg} rounded-lg p-4`}>
      <div className="flex items-center gap-2 mb-1">
        <Icon size={16} className={color} />
        <span className="text-xs text-text-secondary">{label}</span>
      </div>
      <span className={`text-2xl font-bold ${color}`}>{value}</span>
    </div>
  );
}

function StatusBadge({ label, status }: { label: string; status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-surface-2 text-text-disabled",
    fetching: "bg-warning-bg text-warning",
    running: "bg-warning-bg text-warning",
    complete: "bg-success-bg text-success",
    failed: "bg-danger-bg text-danger",
  };
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded font-medium ${colors[status] || "bg-surface-2 text-text-disabled"}`}>
      {label}: {status}
    </span>
  );
}
