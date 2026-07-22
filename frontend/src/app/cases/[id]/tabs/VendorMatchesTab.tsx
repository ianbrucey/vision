"use client";

import { useState, useEffect, useCallback } from "react";
import { RefreshCw, Loader2, CheckCircle2, Copy, Check, Mail, Users, MapPin, Phone, Plus, Globe } from "lucide-react";
import {
  getSolicitationByCase,
  getVendorMatches,
  triggerVendorMatching,
  type SolicitationWithDocuments,
  type VendorMatchesResponse,
  type VendorMatch,
} from "@/lib/api";
import AddVendorModal from "@/components/AddVendorModal";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface VendorMatchesTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-surface-2 text-text-disabled",
  running: "bg-warning-bg text-warning",
  complete: "bg-success-bg text-success",
  failed: "bg-danger-bg text-danger",
};

const NAICS_MATCH_COLORS: Record<string, string> = {
  exact: "bg-brand-bg text-brand",
  family: "bg-info-bg text-info",
  capability_only: "bg-surface-2 text-text-secondary",
  manual: "bg-purple-bg text-purple-700",
};

const FLAG_DEFS: { key: keyof VendorMatch; label: string; color: string }[] = [
  { key: "is_8a", label: "8(a)", color: "bg-purple-bg text-purple-700" },
  { key: "is_sdvosb", label: "SDVOSB", color: "bg-emerald-bg text-emerald-700" },
  { key: "is_woman_owned", label: "WOSB", color: "bg-pink-bg text-pink-700" },
  { key: "is_hubzone", label: "HUBZone", color: "bg-amber-bg text-amber-700" },
  { key: "is_veteran_owned", label: "VOSB", color: "bg-blue-bg text-blue-700" },
  { key: "is_small_business", label: "SB", color: "bg-info-bg text-info" },
];

const POLL_MS = 3000;

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function VendorMatchesTab({ caseId }: VendorMatchesTabProps) {
  const [sol, setSol] = useState<SolicitationWithDocuments | null>(null);
  const [matchesData, setMatchesData] = useState<VendorMatchesResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);
  const [showAddVendor, setShowAddVendor] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const s = await getSolicitationByCase(caseId);
      const m = await getVendorMatches(s.id);
      setSol(s);
      setMatchesData(m);
      setError(null);
      return s;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load vendor matches");
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

  // Poll while matching is running
  useEffect(() => {
    if (sol?.matching_status !== "running") return;
    const id = setInterval(refresh, POLL_MS);
    return () => clearInterval(id);
  }, [sol?.matching_status, refresh]);

  const handleTrigger = async () => {
    if (!sol) return;
    setTriggering(true);
    try {
      await triggerVendorMatching(sol.id);
      // triggerVendorMatching just enqueues a job and returns almost instantly,
      // so matching_status is still "pending" here. Poll briefly until the
      // background worker claims it (status leaves "pending"), otherwise the
      // spinner would vanish for a second or two with nothing visibly happening.
      for (let i = 0; i < 10; i++) {
        const s = await refresh();
        if (!s || s.matching_status !== "pending") break;
        await new Promise((r) => setTimeout(r, 500));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start vendor matching");
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

  const canTrigger =
    sol.triage_status === "complete" &&
    sol.quick_kill === false &&
    !!sol.naics_code &&
    sol.matching_status !== "running" &&
    !triggering;

  const triggerDisabledReason =
    sol.triage_status !== "complete"
      ? "Triage must complete first"
      : sol.quick_kill
        ? "Solicitation was quick-killed during triage"
        : !sol.naics_code
          ? "No NAICS code available for matching"
          : undefined;

  const matches = matchesData?.matches ?? [];

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="shrink-0 px-4 py-3 border-b border-border flex items-center gap-3 flex-wrap">
        <span
          className={`text-[11px] px-2 py-0.5 rounded-sm font-medium ${
            STATUS_COLORS[sol.matching_status] || "bg-surface-2 text-text-secondary"
          }`}
        >
          {sol.matching_status}
        </span>
        {sol.matching_status === "failed" && sol.matching_error && (
          <span className="text-[11px] text-danger truncate max-w-xs" title={sol.matching_error}>
            {sol.matching_error}
          </span>
        )}
        <button
          onClick={() => setShowAddVendor(true)}
          className="ml-auto inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border
                     bg-surface-1 hover:bg-surface-3 text-text-primary transition-colors"
        >
          <Plus size={14} />
          Add Vendor
        </button>
        <button
          onClick={handleTrigger}
          disabled={!canTrigger}
          title={triggerDisabledReason}
          className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-border
                     bg-surface-1 hover:bg-surface-3 text-text-primary transition-colors
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {triggering || sol.matching_status === "running" ? (
            <Loader2 size={14} className="animate-spin" />
          ) : (
            <RefreshCw size={14} />
          )}
          {sol.matching_status === "complete" ? "Re-run Matching" : "Run Matching"}
        </button>
      </div>

      {error && (
        <div className="shrink-0 px-4 py-2 text-xs text-danger bg-danger-bg">{error}</div>
      )}

      {/* Body */}
      {matches.length > 0 ? (
        <div className="flex-1 flex flex-col min-h-0">
          <OutreachEmailPanel subject={sol.outreach_email_subject} body={sol.outreach_email_body} />
          <div className="flex-1 overflow-auto">
            <VendorMatchList
              matches={matches}
              subject={sol.outreach_email_subject}
              body={sol.outreach_email_body}
            />
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center max-w-sm">
            {sol.matching_status === "running" ? (
              <>
                <Loader2 className="animate-spin mx-auto mb-3 text-text-disabled" size={24} />
                <p className="text-sm text-text-disabled">Finding matching vendors…</p>
              </>
            ) : sol.matching_status === "failed" ? (
              <p className="text-sm text-danger">Vendor matching failed. Try running it again.</p>
            ) : sol.matching_status === "complete" ? (
              <>
                <Users className="mx-auto mb-3 text-text-disabled" size={24} strokeWidth={1.5} />
                <p className="text-sm text-text-disabled">
                  No eligible vendors were found for this solicitation&apos;s NAICS code and
                  set-aside requirements.
                </p>
              </>
            ) : (
              <>
                <CheckCircle2 className="mx-auto mb-3 text-text-disabled" size={24} />
                <p className="text-sm text-text-disabled">
                  Vendor matching hasn&apos;t run yet for this solicitation.
                </p>
              </>
            )}
          </div>
        </div>
      )}

      <AddVendorModal
        open={showAddVendor}
        onClose={() => setShowAddVendor(false)}
        solicitationId={sol.id}
        onCreated={() => refresh()}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Outreach email panel                                               */
/* ------------------------------------------------------------------ */

function OutreachEmailPanel({ subject, body }: { subject: string | null; body: string | null }) {
  return (
    <div className="shrink-0 p-4 border-b border-border bg-surface-1">
      <div className="flex items-center gap-1.5 mb-2">
        <Mail size={12} className="text-text-disabled" />
        <p className="text-[10px] font-semibold text-text-disabled uppercase tracking-wide">
          Outreach Email Template
        </p>
      </div>
      <p className="text-sm font-medium text-text-primary mb-1">{subject}</p>
      <p className="text-xs text-text-secondary whitespace-pre-wrap line-clamp-4">{body}</p>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Vendor match list / row                                            */
/* ------------------------------------------------------------------ */

function VendorMatchList({
  matches,
  subject,
  body,
}: {
  matches: VendorMatch[];
  subject: string | null;
  body: string | null;
}) {
  return (
    <div className="p-3 md:p-4 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
      {matches.map((m) => (
        <VendorMatchCard key={m.id} match={m} subject={subject} body={body} />
      ))}
    </div>
  );
}

function VendorMatchCard({
  match,
  subject,
  body,
}: {
  match: VendorMatch;
  subject: string | null;
  body: string | null;
}) {
  return (
    <div className="border border-border rounded-md p-3 bg-surface-1 flex flex-col gap-2 min-w-0">
      {/* Header: rank + name + score */}
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[10px] text-text-disabled font-semibold">#{match.rank}</p>
          <p className="text-sm font-medium text-text-primary truncate" title={match.vendor_name}>
            {match.vendor_name}
          </p>
        </div>
        <ScoreBadge score={match.match_score} />
      </div>

      {/* Match rationale */}
      <p className="text-xs text-text-secondary line-clamp-2" title={match.match_rationale}>
        {match.match_rationale}
      </p>

      {/* Match type + set-aside flags */}
      <div className="flex flex-wrap items-center gap-1">
        <NaicsMatchTypeBadge type={match.naics_match_type} />
        <SetAsideFlags match={match} />
      </div>

      {/* Location */}
      {match.city && match.state ? (
        <div className="flex items-center gap-1 text-xs text-text-secondary">
          <MapPin size={10} className="shrink-0 text-text-disabled" />
          {match.city}, {match.state}
        </div>
      ) : null}

      {/* Contact info */}
      <div className="space-y-0.5 text-xs">
        {match.contact_email ? (
          <a
            href={`mailto:${match.contact_email}`}
            className="flex items-center gap-1 text-info hover:text-brand transition-colors truncate"
          >
            <Mail size={10} className="shrink-0" />
            <span className="truncate">{match.contact_email}</span>
          </a>
        ) : (
          <p className="flex items-center gap-1 text-text-disabled italic">
            <Mail size={10} className="shrink-0" />
            hidden
          </p>
        )}
        {match.contact_phone && (
          <p className="flex items-center gap-1 text-text-secondary">
            <Phone size={10} className="shrink-0" />
            {match.contact_phone}
          </p>
        )}
        {match.website && (
          <a
            href={match.website.startsWith("http") ? match.website : `https://${match.website}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1 text-info hover:text-brand transition-colors truncate"
          >
            <Globe size={10} className="shrink-0" />
            <span className="truncate">Website</span>
          </a>
        )}
      </div>

      {/* Action */}
      <div className="mt-auto pt-1">
        <CopyEmailButton match={match} subject={subject} body={body} />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Badges                                                             */
/* ------------------------------------------------------------------ */

function ScoreBadge({ score }: { score: number }) {
  const cls =
    score >= 80
      ? "bg-success-bg text-success"
      : score >= 50
        ? "bg-warning-bg text-warning"
        : "bg-danger-bg text-danger";
  return <span className={`text-[11px] px-2 py-0.5 rounded-sm font-medium ${cls}`}>{score}</span>;
}

function NaicsMatchTypeBadge({ type }: { type: VendorMatch["naics_match_type"] }) {
  return (
    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${NAICS_MATCH_COLORS[type]}`}>
      {type.replace(/_/g, " ")}
    </span>
  );
}

function SetAsideFlags({ match }: { match: VendorMatch }) {
  const active = FLAG_DEFS.filter((f) => match[f.key]);
  if (!active.length) return null;
  return (
    <div className="flex flex-wrap gap-1">
      {active.map((f) => (
        <span key={f.label} className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${f.color}`}>
          {f.label}
        </span>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Copy email button                                                  */
/* ------------------------------------------------------------------ */

function CopyEmailButton({
  match,
  subject,
  body,
}: {
  match: VendorMatch;
  subject: string | null;
  body: string | null;
}) {
  const [copied, setCopied] = useState(false);
  const handleCopy = async () => {
    const text = `Subject: ${subject}\n\n${(body || "")
      .replace(/\{\{vendor_name\}\}/g, match.vendor_name)
      .replace(/\{\{match_reason\}\}/g, match.match_rationale)}`;
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <button
      onClick={handleCopy}
      disabled={!body}
      className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded border border-border
                 bg-surface-1 hover:bg-surface-3 text-text-secondary transition-colors
                 disabled:opacity-50 disabled:cursor-not-allowed min-h-[44px] sm:min-h-0"
    >
      {copied ? <Check size={12} /> : <Copy size={12} />}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}
