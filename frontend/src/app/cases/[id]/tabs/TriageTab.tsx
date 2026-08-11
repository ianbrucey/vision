"use client";

import { useState, useEffect, useCallback } from "react";
import { RefreshCw, Loader2, AlertTriangle, Ban, CheckCircle2 } from "lucide-react";
import {
  getSolicitationByCase,
  triggerTriage,
  type SolicitationWithDocuments,
} from "@/lib/api";
import HtmlRenderer from "@/components/HtmlRenderer";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface TriageTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const ARTIFACTS = [
  { key: "artifact_scope_of_work", label: "Scope of Work & Tech" },
  { key: "artifact_submission_checklist", label: "Submission Requirements" },
  { key: "artifact_evaluation_criteria", label: "Sourcing Script" },
] as const;

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-surface-2 text-text-disabled",
  running: "bg-warning-bg text-warning",
  complete: "bg-success-bg text-success",
  failed: "bg-danger-bg text-danger",
};

const POLL_MS = 3000;

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function TriageTab({ caseId }: TriageTabProps) {
  const [sol, setSol] = useState<SolicitationWithDocuments | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [activeArtifact, setActiveArtifact] = useState<(typeof ARTIFACTS)[number]["key"]>(
    ARTIFACTS[0].key,
  );

  const refresh = useCallback(async () => {
    try {
      const s = await getSolicitationByCase(caseId);
      setSol(s);
      setError(null);
      return s;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load triage status");
      return null;
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

  // Poll while triage is running
  useEffect(() => {
    if (sol?.triage_status !== "running") return;
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [sol?.triage_status, refresh]);

  const handleTrigger = async () => {
    if (!sol) return;
    setTriggering(true);
    try {
      await triggerTriage(sol.id);
      // triggerTriage just enqueues a job and returns almost instantly, so
      // triage_status is still "pending" here. Poll briefly until the
      // background worker claims it (status leaves "pending"), otherwise the
      // spinner would vanish for a second or two with nothing visibly happening.
      for (let i = 0; i < 10; i++) {
        const s = await refresh();
        if (!s || s.triage_status !== "pending") break;
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start triage");
    } finally {
      setTriggering(false);
    }
  };

  /* ---- loading / error / no-solicitation ---- */

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

  const noDocuments = (sol.documents?.length ?? 0) === 0;
  const canTrigger = !noDocuments && sol.triage_status !== "running" && !triggering;
  const activeHtml = (sol[activeArtifact] as string | null) || "";

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-border flex items-center gap-3 flex-wrap">
        <span
          className={`text-[11px] px-2 py-0.5 rounded-sm font-medium ${
            STATUS_COLORS[sol.triage_status] || "bg-surface-2 text-text-secondary"
          }`}
        >
          {sol.triage_status}
        </span>
        {sol.notice_type && (
          <span className="text-[11px] px-2 py-0.5 rounded-sm font-medium bg-info-bg text-info uppercase">
            {sol.notice_type.replace(/_/g, " ")}
          </span>
        )}
        {sol.has_partial_artifacts && (
          <span
            title={sol.triage_error || "Some artifacts failed to generate"}
            className="inline-flex items-center gap-1 text-[11px] text-warning"
          >
            <AlertTriangle size={12} /> partial
          </span>
        )}
        {sol.triage_status === "failed" && sol.triage_error && (
          <span className="text-[11px] text-danger truncate max-w-xs" title={sol.triage_error}>
            {sol.triage_error}
          </span>
        )}
        <button
          onClick={handleTrigger}
          disabled={!canTrigger}
          title={noDocuments ? "Attach documents before running triage" : undefined}
          className="ml-auto inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border
                     bg-surface-1 hover:bg-surface-3 text-text-primary transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {triggering || sol.triage_status === "running" ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <RefreshCw size={14} />
          )}
          {sol.triage_status === "complete" ? "Re-run Triage" : "Run Triage"}
        </button>
      </div>

      {error && (
        <div className="shrink-0 px-4 py-2 text-xs text-danger bg-danger-bg">{error}</div>
      )}

      {/* Quick-kill notice — informational only, does not block artifact view */}
      {sol.quick_kill && (
        <div className="shrink-0 px-4 py-2 text-xs bg-warning-bg text-warning border-b border-warning/20 flex items-center gap-2">
          <AlertTriangle size={14} />
          <span>Quick-Kill flagged: {sol.quick_kill_reason}</span>
          <span className="text-text-disabled">— artifacts & vendor matching still proceed.</span>
        </div>
      )}

      {/* Body */}
      {sol.triage_status === "complete" && sol.artifact_scope_of_work ? (
        <div className="flex-1 flex flex-col min-h-0">
          <div className="shrink-0 flex overflow-x-auto border-b border-border bg-surface-1">
            {ARTIFACTS.map((a) => (
              <button
                key={a.key}
                onClick={() => setActiveArtifact(a.key)}
                className={`px-3 py-2 text-xs font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeArtifact === a.key
                    ? "border-brand text-brand"
                    : "border-transparent text-text-secondary hover:text-text-primary"
                }`}
              >
                {a.label}
                {!sol[a.key] && <span className="ml-1 text-text-disabled">·</span>}
              </button>
            ))}
          </div>
          <HtmlRenderer html={activeHtml} />
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-sm">
            {noDocuments ? (
              <p className="text-sm text-text-disabled">
                Attach documents in the Documents tab, then run triage.
              </p>
            ) : sol.triage_status === "running" ? (
              <>
                <Loader2 className="animate-spin mx-auto mb-3 text-text-disabled" size={24} />
                <p className="text-sm text-text-disabled">Triage is running…</p>
              </>
            ) : sol.triage_status === "failed" ? (
              <p className="text-sm text-danger">Triage failed. Try running it again.</p>
            ) : (
              <>
                <CheckCircle2 className="mx-auto mb-3 text-text-disabled" size={24} />
                <p className="text-sm text-text-disabled">
                  Triage hasn&apos;t run yet for this solicitation.
                </p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
