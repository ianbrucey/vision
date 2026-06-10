"use client";

import { useState, useEffect, useCallback } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Upload,
  MessageCircle,
  ChevronRight,
  ChevronDown,
  Pencil,
  Loader2,
  Sparkles,
  User,
  Scale,
  X,
  Mail,
} from "lucide-react";
import { synthesizeCase, getJob, getCase, listJobs, listCorrespondenceThreads, listTasks, type CorrespondenceThread, type Task } from "@/lib/api";
import type { TabId } from "../TabNav";

/* ------------------------------------------------------------------ */
/*  State machine                                                      */
/* ------------------------------------------------------------------ */

type NarrativeState = "unsaved" | "clean" | "editing" | "saving";

interface Party {
  id: number; name: string; party_kind: string; roles: string[];
}
interface Allegation {
  id: number; allegation_id: string; text: string; category: string | null;
}

interface OverviewTabProps {
  caseId: number;
  savedNarrative: string;
  lastSavedAt: string | null;
  hasDocuments: boolean;
  existingParties: Party[];
  existingAllegations: Allegation[];
  onSave: (narrative: string) => Promise<string>;
  onNavigate: (tab: TabId) => void;
}

/* ------------------------------------------------------------------ */

export default function OverviewTab({
  caseId,
  savedNarrative,
  lastSavedAt,
  hasDocuments,
  existingParties,
  existingAllegations,
  onSave,
  onNavigate,
}: OverviewTabProps) {
  const [draft, setDraft] = useState(savedNarrative);
  const [state, setState] = useState<NarrativeState>(
    savedNarrative ? "clean" : "unsaved",
  );
  const [savedAt, setSavedAt] = useState<string | null>(lastSavedAt);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Synthesis state — seed from existing data so it survives refresh
  const hasExisting = existingParties.length > 0 || existingAllegations.length > 0;
  const [synthLoading, setSynthLoading] = useState(false);
  const [synthError, setSynthError] = useState<string | null>(null);
  const [synthResult, setSynthResult] = useState<{
    parties: Party[];
    allegations: Allegation[];
  } | null>(hasExisting ? { parties: existingParties, allegations: existingAllegations } : null);

  // Collapse toggles
  const [partiesOpen, setPartiesOpen] = useState(true);
  const [issuesOpen, setIssuesOpen] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  // Correspondence preview
  const [corrThreads, setCorrThreads] = useState<CorrespondenceThread[]>([]);

  useEffect(() => {
    listCorrespondenceThreads(caseId)
      .then((res) => setCorrThreads(res.threads.slice(0, 3)))
      .catch(() => {});
  }, [caseId]);

  // Task preview
  const [tasks, setTasks] = useState<Task[]>([]);

  useEffect(() => {
    listTasks(caseId, { status: "complete", limit: 99 })
      .then((res) => {
        // Get non-complete tasks (open, in_progress, blocked)
        return listTasks(caseId);
      })
      .then((res) => setTasks(res.tasks.filter((t) => t.status !== "complete").slice(0, 4)))
      .catch(() => {});
  }, [caseId]);

  // Sync when parent reloads (e.g. after navigating back)
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    setDraft(savedNarrative);
    setSavedAt(lastSavedAt);
    setState(savedNarrative ? "clean" : "unsaved");
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [savedNarrative, lastSavedAt]);

  // Resume in-progress analysis on mount (survives refresh)
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const jobs = await listJobs({ case_id: caseId }) as any[];
        const active = jobs?.find(
          (j: any) => j.job_type === "synthesize" && (j.status === "queued" || j.status === "processing")
        );
        if (!active) return;
        if (cancelled) return;

        setSynthLoading(true);
        let attempts = 0;
        while (attempts < 60) {
          await new Promise((r) => setTimeout(r, 2000));
          if (cancelled) return;
          const job = await getJob(active.id);
          if (job.status === "complete") {
            const updated = await getCase(caseId);
            if (!cancelled) {
              setSynthResult({
                parties: (updated as any).parties || [],
                allegations: (updated as any).allegations || [],
              });
              setSynthLoading(false);
            }
            return;
          }
          if (job.status === "failed") {
            if (!cancelled) {
              setSynthError(job.error_message || "Analysis failed");
              setSynthLoading(false);
            }
            return;
          }
          attempts++;
        }
        if (!cancelled) {
          setSynthError("Analysis timed out");
          setSynthLoading(false);
        }
      } catch {
        // job endpoint unavailable — ignore
      }
    })();
    return () => { cancelled = true; };
  }, [caseId]);

  /* ---- handlers ---- */

  const handleEdit = () => setState("editing");

  const handleSave = async () => {
    if (!draft.trim()) return;
    setSaveError(null);
    setState("saving");
    try {
      const updatedAt = await onSave(draft);
      setSavedAt(updatedAt);
      setState("clean");
    } catch (err: unknown) {
      setState("editing");
      setSaveError(err instanceof Error ? err.message : "Failed to save");
    }
  };

  const handleChange = (value: string) => {
    setDraft(value);
    if (state === "clean") setState("editing");
  };

  const isSaving = state === "saving";
  const grounded = savedAt !== null;

  /* ---- synthesis ---- */

  const handleSynthesize = useCallback(async () => {
    setSynthLoading(true);
    setSynthError(null);
    setSynthResult(null);
    try {
      const { job_id } = await synthesizeCase(caseId);

      // Poll for completion
      let attempts = 0;
      while (attempts < 60) {
        await new Promise((r) => setTimeout(r, 2000));
        const job = await getJob(job_id);
        if (job.status === "complete") {
          // Reload case to get extracted parties + allegations
          const updated = await getCase(caseId);
          setSynthResult({
            parties: (updated as any).parties || [],
            allegations: (updated as any).allegations || [],
          });
          break;
        }
        if (job.status === "failed") {
          setSynthError(job.error_message || "Analysis failed");
          break;
        }
        attempts++;
      }
      if (attempts >= 60) {
        setSynthError("Analysis timed out — try again");
      }
    } catch (err: unknown) {
      setSynthError(err instanceof Error ? err.message : "Analysis failed");
    } finally {
      setSynthLoading(false);
    }
  }, [caseId]);

  const showExtract = grounded && hasDocuments && !synthLoading;

  const isExpanded = state === "unsaved" || state === "editing" || state === "saving";

  /* ---- formatting ---- */

  const formatDate = (iso: string | null) => {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    }) + " at " + d.toLocaleTimeString(undefined, {
      hour: "numeric",
      minute: "2-digit",
    });
  };

  /* ---- render ---- */

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-4 py-4 md:py-6 md:max-w-3xl md:mx-auto space-y-4 md:space-y-6">

        {/* ================================================================ */}
        {/* Grounding banner                                                  */}
        {/* ================================================================ */}
        {!grounded ? (
          /* --- Ungrounded --- */
          <div className="bg-warning-bg border border-warning/20 rounded-lg p-3 md:p-4 flex gap-2 md:gap-3">
            <AlertCircle className="text-warning shrink-0 mt-0.5" size={18} />
            <div>
              <p className="text-sm font-medium text-warning">Case not grounded</p>
              <p className="text-xs md:text-sm text-text-secondary mt-0.5">
                A case narrative is required before the agent can analyze documents,
                answer questions, or analyze evidence.
              </p>
            </div>
          </div>
        ) : state === "editing" ? (
          /* --- Has unsaved changes --- */
          <div className="bg-warning-bg border border-warning/20 rounded-lg p-3 md:p-4 flex gap-2 md:gap-3">
            <AlertCircle className="text-warning shrink-0 mt-0.5" size={18} />
            <div className="flex-1">
              <p className="text-sm font-medium text-warning">Unsaved changes</p>
              <p className="text-xs md:text-sm text-text-secondary mt-0.5">
                You have edited the narrative. Save to update the case.
              </p>
            </div>
          </div>
        ) : (
          /* --- Grounded & clean --- */
          <div className="bg-success-bg border border-success/20 rounded-lg p-3 md:p-4 flex gap-2 md:gap-3">
            <CheckCircle2 className="text-success shrink-0 mt-0.5" size={18} />
            <div>
              <p className="text-sm font-medium text-success">Case grounded</p>
              <p className="text-xs md:text-sm text-text-secondary mt-0.5">
                The agent can analyze this case.{" "}
                {savedAt && (
                  <span className="text-text-disabled">
                    Last updated {formatDate(savedAt)}.
                  </span>
                )}
              </p>
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* Narrative section                                                 */}
        {/* ================================================================ */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-sm font-medium text-text-secondary">
              Case Narrative <span className="text-danger">*</span>
            </label>
            {!isExpanded && (
              <button
                onClick={handleEdit}
                className="inline-flex items-center gap-1.5 text-xs text-text-secondary
                           hover:text-text-primary transition-colors min-h-[36px] px-2"
              >
                <Pencil size={14} />
                Edit
              </button>
            )}
          </div>

          {/* --- Expanded: editable textarea --- */}
          {isExpanded ? (
            <>
              <textarea
                className="w-full h-40 md:h-48 bg-surface-1 border border-border rounded-lg p-3 md:p-4
                           text-sm md:text-base leading-relaxed resize-y
                           placeholder:text-text-disabled
                           focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                           transition-colors disabled:opacity-60"
                placeholder={
                  "Tell the agent everything about this case.\n\n" +
                  "Who is involved? What happened? What are the key facts? " +
                  "What records do you have? What outcome are you seeking?\n\n" +
                  "The more detail you provide, the better the agent can work."
                }
                value={draft}
                onChange={(e) => handleChange(e.target.value)}
                disabled={isSaving}
              />

              {/* Save button + error */}
              <div className="flex items-center gap-3 mt-3">
                <button
                  onClick={handleSave}
                  disabled={isSaving || !draft.trim()}
                  className="inline-flex items-center gap-2 bg-brand hover:bg-brand-hover
                             active:bg-brand-active text-white px-4 py-2 rounded-lg
                             text-sm font-medium transition-colors
                             disabled:opacity-50 disabled:cursor-not-allowed
                             min-h-[44px]"
                >
                  {isSaving && <Loader2 size={15} className="animate-spin" />}
                  {isSaving ? "Saving..." : "Save Narrative"}
                </button>
                {saveError && (
                  <p className="text-xs text-danger">{saveError}</p>
                )}
              </div>

              <p className="text-xs text-text-disabled mt-2">
                {grounded
                  ? "Save to update the case. The agent will re-process on the next interaction."
                  : "Once saved, the agent can begin processing your case."}
              </p>
            </>
          ) : (
            /* --- Collapsed: preview --- */
            <div
              onClick={handleEdit}
              className="bg-surface-1 border border-border rounded-lg p-3 md:p-4
                         cursor-pointer hover:border-border-strong active:border-brand
                         transition-colors group"
            >
              <p className="text-sm text-text-primary leading-relaxed line-clamp-3 whitespace-pre-wrap">
                {draft}
              </p>
              <p className="text-xs text-text-disabled mt-2 group-hover:text-text-secondary transition-colors">
                Click to edit
              </p>
            </div>
          )}
        </div>

        {/* ================================================================ */}
        {/* Synthesis — analyze narrative                                      */}
        {/* ================================================================ */}
        {grounded && (
          <div>
            {showExtract && !synthResult && (
              <button
                onClick={handleSynthesize}
                className="w-full bg-surface-1 border border-border rounded-lg p-4
                           flex items-center gap-3 text-left
                           hover:border-brand active:border-brand
                           transition-colors min-h-[52px]"
              >
                <div className="size-9 rounded-lg bg-brand-bg flex items-center justify-center text-brand shrink-0">
                  <Sparkles size={18} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium">Analyze Narrative</p>
                  <p className="text-xs text-text-secondary">
                    The agent will read your narrative and identify parties, key
                    issues, and what to look for in the evidence.
                  </p>
                </div>
              </button>
            )}

            {synthLoading && (
              <div className="bg-surface-1 border border-border rounded-lg p-4
                              flex items-center gap-3">
                <Loader2 size={18} className="text-brand animate-spin shrink-0" />
                <div>
                  <p className="text-sm font-medium">Analyzing narrative...</p>
                  <p className="text-xs text-text-secondary">
                    Reading your narrative and identifying what matters. About 30 seconds.
                  </p>
                </div>
              </div>
            )}

            {synthError && (
              <div className="bg-danger-bg border border-danger/20 rounded-lg p-4
                              flex items-center gap-3">
                <AlertCircle className="text-danger shrink-0 mt-0.5" size={18} />
                <div>
                  <p className="text-sm font-medium text-danger">Analysis failed</p>
                  <p className="text-xs text-text-secondary mt-0.5">{synthError}</p>
                  <button
                    onClick={handleSynthesize}
                    className="text-xs text-info hover:text-brand mt-1 transition-colors"
                  >
                    Try again
                  </button>
                </div>
              </div>
            )}

            {synthResult && (
              <div className="bg-surface-1 border border-border rounded-lg p-4
                              flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="flex items-center gap-1.5 text-sm">
                    <User size={14} className="text-brand shrink-0" />
                    <span className="font-medium">{synthResult.parties.length}</span>
                    <span className="text-text-secondary hidden sm:inline">parties</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Scale size={14} className="text-brand shrink-0" />
                    <span className="font-medium">{synthResult.allegations.length}</span>
                    <span className="text-text-secondary hidden sm:inline">issues</span>
                  </div>
                </div>
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={handleSynthesize}
                    className="text-xs text-info hover:text-brand transition-colors
                               min-h-[36px] px-2 flex items-center gap-1"
                  >
                    <Sparkles size={13} />
                    Re-analyze
                  </button>
                  <button
                    onClick={() => setModalOpen(true)}
                    className="text-xs text-text-secondary hover:text-text-primary
                               transition-colors min-h-[36px] px-2"
                  >
                    View
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ================================================================ */}
        {/* Quick actions                                                    */}
        {/* ================================================================ */}
        <div>
          <h3 className="text-xs font-semibold text-text-disabled uppercase tracking-wider mb-2">
            Get Started
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <button
              onClick={() => onNavigate("documents")}
              className="bg-surface-1 border border-border rounded-lg p-3 flex items-center gap-3
                         text-left hover:border-brand active:border-brand
                         transition-colors min-h-[52px]"
            >
              <div className="size-9 rounded-lg bg-info-bg flex items-center justify-center text-info shrink-0">
                <Upload size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">Upload Documents</p>
                <p className="text-xs text-text-secondary">PDF, DOCX, TXT — multiple files</p>
              </div>
              <ChevronRight size={16} className="text-text-disabled shrink-0" />
            </button>
            <button
              onClick={() => onNavigate("chat")}
              className="bg-surface-1 border border-border rounded-lg p-3 flex items-center gap-3
                         text-left hover:border-brand active:border-brand
                         transition-colors min-h-[52px]"
            >
              <div className="size-9 rounded-lg bg-brand-bg flex items-center justify-center text-brand shrink-0">
                <MessageCircle size={18} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">Ask the Agent</p>
                <p className="text-xs text-text-secondary">Chat about your case</p>
              </div>
              <ChevronRight size={16} className="text-text-disabled shrink-0" />
            </button>
          </div>
        </div>

        {/* ================================================================ */}
        {/* Correspondence preview                                            */}
        {/* ================================================================ */}
        {corrThreads.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-text-disabled uppercase tracking-wider">
                Correspondence
              </h3>
              <button
                onClick={() => onNavigate("correspondence")}
                className="text-xs text-info hover:text-brand transition-colors"
              >
                View all
              </button>
            </div>
            <div className="bg-surface-1 border border-border rounded-lg divide-y divide-border">
              {corrThreads.map((t) => (
                <div
                  key={t.id}
                  onClick={() => onNavigate("correspondence")}
                  className="p-3 flex items-center gap-3 hover:bg-surface-2 cursor-pointer
                             transition-colors"
                >
                  <Mail size={16} className="text-text-disabled shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{t.title}</p>
                    <p className="text-xs text-text-disabled">
                      {t.item_count} item{t.item_count !== 1 ? "s" : ""}
                      {t.last_activity && (
                        <> · last activity {formatDate(t.last_activity)}</>
                      )}
                    </p>
                  </div>
                  <ChevronRight size={14} className="text-text-disabled shrink-0" />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ================================================================ */}
        {/* Tasks preview                                                     */}
        {/* ================================================================ */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-text-disabled uppercase tracking-wider">
              Tasks
            </h3>
            <button
              onClick={() => onNavigate("tasks")}
              className="text-xs text-info hover:text-brand transition-colors"
            >
              View all
            </button>
          </div>
          {tasks.length === 0 ? (
            <div
              onClick={() => onNavigate("tasks")}
              className="bg-surface-1 border border-border rounded-lg p-4
                         cursor-pointer hover:bg-surface-2 transition-colors text-center"
            >
              <p className="text-xs text-text-secondary">No open tasks</p>
              <p className="text-[10px] text-text-disabled mt-0.5">
                Tap to create one
              </p>
            </div>
          ) : (
            <div className="bg-surface-1 border border-border rounded-lg divide-y divide-border">
              {tasks.map((t) => {
                const isOverdue = t.deadline && new Date(t.deadline + "T12:00:00") < new Date();
                const dl = t.deadline
                  ? new Date(t.deadline + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" })
                  : null;
                return (
                  <div
                    key={t.id}
                    onClick={() => onNavigate("tasks")}
                    className="p-3 flex items-center gap-2 hover:bg-surface-2 cursor-pointer transition-colors"
                  >
                    <div className={`size-2 rounded-full shrink-0 ${
                      t.status === "in_progress" ? "bg-warning"
                        : t.status === "blocked" ? "bg-danger"
                        : "bg-text-disabled"
                    }`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm truncate">{t.title}</p>
                      <p className="text-xs text-text-disabled">
                        {isOverdue && <span className="text-danger">Overdue</span>}
                        {dl && !isOverdue && <span>{dl}</span>}
                        {(dl || isOverdue) && " · "}
                        {t.priority !== "medium" && (
                          <span className={`px-1 rounded-sm text-[10px] ${
                            t.priority === "urgent" ? "bg-danger-bg text-danger"
                              : t.priority === "high" ? "bg-warning-bg text-warning"
                              : "bg-surface-2 text-text-disabled"
                          }`}>{t.priority}</span>
                        )}
                      </p>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ================================================================ */}
        {/* Activity                                                         */}
        {/* ================================================================ */}
        <div>
          <h3 className="text-xs font-semibold text-text-disabled uppercase tracking-wider mb-2">
            Activity
          </h3>
          <div className="bg-surface-1 border border-border rounded-lg divide-y divide-border">
            {savedAt && (
              <div className="p-3 flex items-center gap-3">
                <span className="size-2 rounded-full bg-success shrink-0" />
                <span className="text-sm flex-1">Narrative saved</span>
                <span className="text-xs text-text-disabled">
                  {new Date(savedAt).toLocaleDateString(undefined, {
                    month: "short",
                    day: "numeric",
                  })}
                </span>
              </div>
            )}
            <div className="p-3 flex items-center gap-3">
              <span className="size-2 rounded-full bg-success shrink-0" />
              <span className="text-sm flex-1">Case created</span>
              <span className="text-xs text-text-disabled">June 4</span>
            </div>
          </div>
        </div>

      </div>

      {/* ================================================================ */}
      {/* Results Modal                                                     */}
      {/* ================================================================ */}
      {modalOpen && synthResult && (
        <div className="fixed inset-0 z-50 flex items-end md:items-center justify-center">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setModalOpen(false)}
          />
          {/* Panel */}
          <div className="relative bg-surface-1 rounded-t-2xl md:rounded-2xl
                          w-full md:max-w-lg md:mx-4 max-h-[85dvh] overflow-y-auto
                          shadow-xl">
            {/* Header */}
            <div className="sticky top-0 bg-surface-1 border-b border-border
                            flex items-center justify-between px-4 py-3
                            rounded-t-2xl z-10">
              <h2 className="text-sm font-semibold">Analysis Results</h2>
              <button
                onClick={() => setModalOpen(false)}
                className="text-text-disabled hover:text-text-primary
                           transition-colors min-h-[36px] min-w-[36px]
                           flex items-center justify-center"
              >
                <X size={18} />
              </button>
            </div>

            {/* Body — same collapsible sections */}
            <div className="p-4 space-y-3">
              {/* Parties */}
              <div className="bg-surface-2 border border-border rounded-lg">
                <button
                  onClick={() => setPartiesOpen(!partiesOpen)}
                  className="w-full flex items-center gap-2 p-3 text-left"
                >
                  <User size={16} className="text-brand shrink-0" />
                  <span className="text-sm font-medium flex-1">
                    Parties ({synthResult.parties.length})
                  </span>
                  <ChevronDown
                    size={16}
                    className={`text-text-disabled shrink-0 transition-transform ${partiesOpen ? "" : "-rotate-90"}`}
                  />
                </button>
                {partiesOpen && (
                  <div className="px-3 pb-3">
                    {synthResult.parties.length === 0 ? (
                      <p className="text-xs text-text-disabled">No parties identified.</p>
                    ) : (
                      <div className="space-y-2">
                        {synthResult.parties.map((p) => (
                          <div key={p.id} className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-medium">{p.name}</span>
                            <span className="text-xs px-1.5 py-0.5 rounded-sm bg-surface-3 text-text-secondary">
                              {p.party_kind}
                            </span>
                            {p.roles?.map((r: string) => (
                              <span key={r} className="text-xs px-1.5 py-0.5 rounded-sm bg-info-bg text-info">
                                {r.replace(/_/g, " ")}
                              </span>
                            ))}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Issues */}
              <div className="bg-surface-2 border border-border rounded-lg">
                <button
                  onClick={() => setIssuesOpen(!issuesOpen)}
                  className="w-full flex items-center gap-2 p-3 text-left"
                >
                  <Scale size={16} className="text-brand shrink-0" />
                  <span className="text-sm font-medium flex-1">
                    Issues ({synthResult.allegations.length})
                  </span>
                  <ChevronDown
                    size={16}
                    className={`text-text-disabled shrink-0 transition-transform ${issuesOpen ? "" : "-rotate-90"}`}
                  />
                </button>
                {issuesOpen && (
                  <div className="px-3 pb-3">
                    {synthResult.allegations.length === 0 ? (
                      <p className="text-xs text-text-disabled">No issues identified.</p>
                    ) : (
                      <div className="space-y-2">
                        {synthResult.allegations.map((a) => (
                          <div key={a.id} className="flex items-start gap-2">
                            <span className="text-xs font-mono font-medium text-brand shrink-0 mt-0.5">
                              {a.allegation_id}
                            </span>
                            <div className="min-w-0">
                              <p className="text-sm">{a.text}</p>
                              {a.category && (
                                <span className="text-xs px-1.5 py-0.5 rounded-sm bg-surface-3 text-text-secondary">
                                  {a.category.replace(/_/g, " ")}
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>

              <button
                onClick={handleSynthesize}
                className="text-xs text-info hover:text-brand transition-colors
                           flex items-center gap-1"
              >
                <Sparkles size={12} />
                Re-analyze
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
