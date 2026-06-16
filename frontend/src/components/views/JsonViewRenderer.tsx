"use client";

import { useState, useEffect, useMemo } from "react";
import { FileText, AlertTriangle } from "lucide-react";
import type { ViewEnvelope } from "./types";
import ViewComposer from "./ViewComposer";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface JsonViewRendererProps {
  /** Raw content from drafts.content — trusted to be a ViewEnvelope after
   *  backend validation, but we guard against malformed data. */
  content: unknown;
  itemId: number;
  editMode: boolean;
}

/* ------------------------------------------------------------------ */
/* Validation (lightweight structural check)                          */
/* ------------------------------------------------------------------ */

interface ValidationResult {
  valid: false;
  error: string;
}

function validateEnvelope(content: unknown): content is ViewEnvelope {
  if (!content || typeof content !== "object" || Array.isArray(content)) {
    return false;
  }
  const c = content as Record<string, unknown>;
  if (!c.documentMetadata || typeof c.documentMetadata !== "object") {
    return false;
  }
  if (!Array.isArray(c.views)) {
    return false;
  }
  if (c.views.length === 0) {
    return false;
  }
  // Check each view has required fields
  for (const view of c.views) {
    if (!view || typeof view !== "object") return false;
    const v = view as Record<string, unknown>;
    if (!v.viewType || !v.title || !v.data) return false;
    if (!["table", "list", "cards", "chart"].includes(v.viewType as string)) return false;
  }
  return true;
}

function getValidationError(content: unknown): string | null {
  if (!content || typeof content !== "object") {
    return "Content is not a valid JSON object";
  }
  if (Array.isArray(content)) {
    return "Content is an array — json_view expects a direct object {documentMetadata, views}, not array-wrapped";
  }
  const c = content as Record<string, unknown>;
  if (!c.documentMetadata || typeof c.documentMetadata !== "object") {
    return "Missing or invalid 'documentMetadata'";
  }
  if (!Array.isArray(c.views)) {
    return "Missing or invalid 'views' array";
  }
  if (c.views.length === 0) {
    return "'views' array is empty — at least one view is required";
  }
  for (let i = 0; i < c.views.length; i++) {
    const v = c.views[i] as Record<string, unknown> | null;
    if (!v || typeof v !== "object") {
      return `views[${i}] is not a valid object`;
    }
    if (!v.viewType) {
      return `views[${i}] is missing 'viewType'`;
    }
    if (!["table", "list", "cards", "chart"].includes(v.viewType as string)) {
      return `views[${i}] has unknown viewType '${v.viewType}'. Expected: table, list, cards, or chart`;
    }
    if (!v.title) {
      return `views[${i}] is missing 'title'`;
    }
    if (!v.data || typeof v.data !== "object") {
      return `views[${i}] is missing 'data'`;
    }
  }
  return null;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

/**
 * Entry point for json_view workspace items.
 * Validates content, then dispatches to ViewComposer.
 */
export default function JsonViewRenderer({
  content,
  itemId,
  editMode,
}: JsonViewRendererProps) {
  const [localEnvelope, setLocalEnvelope] = useState<ViewEnvelope | null>(() => {
    if (validateEnvelope(content)) return content;
    return null;
  });

  // Sync from external content changes (item re-selection, agent updates)
  useEffect(() => {
    if (validateEnvelope(content)) {
      setLocalEnvelope(content);
    } else {
      setLocalEnvelope(null);
    }
  }, [content]);

  const validationError = useMemo(() => {
    if (localEnvelope) return null;
    return getValidationError(content);
  }, [content, localEnvelope]);

  /* ---- content change from child components ---- */
  const handleContentChange = (updated: ViewEnvelope) => {
    setLocalEnvelope(updated);
  };

  /* ---- error state ---- */
  if (validationError) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-md text-center">
          <AlertTriangle
            size={32}
            className="mx-auto mb-3 text-[--danger] opacity-60"
          />
          <p className="font-medium text-[--text-primary] mb-2">
            Invalid View Envelope
          </p>
          <p className="text-sm text-[--text-secondary] mb-4">
            {validationError}
          </p>
          <p className="text-xs text-[--text-disabled]">
            The content of this workspace item does not conform to the json_view
            envelope schema. Ask the agent to regenerate the view, or edit the
            raw JSON to fix the issue.
          </p>
        </div>
      </div>
    );
  }

  /* ---- loading (initial validation) ---- */
  if (!localEnvelope) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="max-w-md text-center">
          <FileText
            size={32}
            className="mx-auto mb-3 text-[--text-disabled] opacity-40"
          />
          <p className="text-sm text-[--text-disabled]">
            Loading view...
          </p>
        </div>
      </div>
    );
  }

  /* ---- render ---- */
  return (
    <div className="flex-1 min-h-0 overflow-y-auto">
      <div className="flex flex-col gap-6 p-6">
      {/* Document-level title */}
      <div>
        <h1 className="text-xl font-semibold text-[--text-primary]">
          {localEnvelope.documentMetadata.title}
        </h1>
        {localEnvelope.documentMetadata.sourceId && (
          <p className="text-xs text-[--text-disabled] mt-1">
            Source: {localEnvelope.documentMetadata.sourceId}
          </p>
        )}
      </div>

      {/* Views */}
      <ViewComposer
        envelope={localEnvelope}
        itemId={itemId}
        editMode={editMode}
        onContentChange={handleContentChange}
      />
    </div>
    </div>
  );
}
