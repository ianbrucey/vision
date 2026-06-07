"use client";

import { useState, useEffect } from "react";
import {
  AlertCircle,
  CheckCircle2,
  Upload,
  MessageCircle,
  ChevronRight,
  Pencil,
  Loader2,
} from "lucide-react";
import type { TabId } from "../TabNav";

/* ------------------------------------------------------------------ */
/*  State machine                                                      */
/* ------------------------------------------------------------------ */

type NarrativeState = "unsaved" | "clean" | "editing" | "saving";

interface OverviewTabProps {
  /** The last narrative persisted to the backend (empty string if never saved). */
  savedNarrative: string;
  /** ISO timestamp from the server (null if never saved). */
  lastSavedAt: string | null;
  /** Called when the user clicks Save. Parent persists via API and returns updated timestamp. */
  onSave: (narrative: string) => Promise<string>;
  /** Navigate to another tab. */
  onNavigate: (tab: TabId) => void;
}

/* ------------------------------------------------------------------ */

export default function OverviewTab({
  savedNarrative,
  lastSavedAt,
  onSave,
  onNavigate,
}: OverviewTabProps) {
  const [draft, setDraft] = useState(savedNarrative);
  const [state, setState] = useState<NarrativeState>(
    savedNarrative ? "clean" : "unsaved",
  );
  const [savedAt, setSavedAt] = useState<string | null>(lastSavedAt);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Sync when parent reloads (e.g. after navigating back)
  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    setDraft(savedNarrative);
    setSavedAt(lastSavedAt);
    setState(savedNarrative ? "clean" : "unsaved");
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [savedNarrative, lastSavedAt]);

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

  const isExpanded = state === "unsaved" || state === "editing" || state === "saving";
  const isSaving = state === "saving";
  const grounded = savedAt !== null;

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
                answer questions, or identify parties.
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
    </div>
  );
}
