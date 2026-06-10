"use client";

import { useState, useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Loader2 } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface MarkdownRendererProps {
  content: { markdown: string };
  editMode: boolean;
  onChange: (markdown: string) => void;
  onSave: () => Promise<void>;
  onBlur?: () => void;
  saveStatus?: "idle" | "saving" | "saved" | "error";
  readOnly?: boolean;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function MarkdownRenderer({
  content,
  editMode,
  onChange,
  onSave,
  onBlur,
  saveStatus,
  readOnly = false,
}: MarkdownRendererProps) {
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const markdownText = content?.markdown || "";

  // Focus textarea when entering edit mode
  useEffect(() => {
    if (editMode && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [editMode]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await onSave();
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    // Cmd/Ctrl+Enter to save
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      handleSave();
    }
  };

  const statusLabel =
    saveStatus === "saving" ? "Saving..."
    : saveStatus === "saved" ? "Saved"
    : saveStatus === "error" ? "Save failed"
    : saving ? "Saving..."
    : "⌘↵ to save";

  /* ---- source editor ---- */
  if (editMode) {
    return (
      <div className="flex flex-col h-full">
        <textarea
          ref={textareaRef}
          value={markdownText}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={onBlur}
          className="flex-1 w-full bg-surface-0 text-text-primary font-mono text-sm
                     p-6 resize-none outline-none border-0
                     placeholder:text-text-disabled"
          placeholder="# Start writing markdown..."
          spellCheck={false}
        />
        {/* Save bar */}
        <div className="shrink-0 flex items-center justify-end gap-2 px-4 py-2
                        bg-surface-1 border-t border-border">
          <span className={`text-[10px] mr-auto ${
            saveStatus === "error" ? "text-danger"
            : saveStatus === "saved" ? "text-success"
            : "text-text-disabled"
          }`}>
            {statusLabel}
          </span>
          <button
            onClick={handleSave}
            disabled={saving || saveStatus === "saving"}
            className="text-xs px-3 py-1.5 rounded-md font-medium
                       bg-brand text-white hover:bg-brand-hover
                       disabled:opacity-50 transition-colors flex items-center gap-1.5"
          >
            {(saving || saveStatus === "saving") && <Loader2 size={12} className="animate-spin" />}
            Save
          </button>
        </div>
      </div>
    );
  }

  /* ---- rendered view ---- */
  if (!markdownText.trim()) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-disabled text-sm">
        <p>Empty document.</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      <article className="p-6 max-w-[680px] mx-auto
                        prose prose-invert prose-sm
                        prose-headings:text-text-primary
                        prose-p:text-text-primary prose-p:leading-relaxed
                        prose-a:text-info prose-a:no-underline hover:prose-a:underline
                        prose-strong:text-text-primary
                        prose-code:text-text-primary prose-code:bg-surface-2 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                        prose-pre:bg-surface-2 prose-pre:border prose-pre:border-border
                        prose-blockquote:border-brand prose-blockquote:text-text-secondary
                        prose-ul:text-text-primary prose-ol:text-text-primary
                        prose-li:text-text-primary
                        prose-hr:border-border
                        prose-img:rounded-md">
        <ReactMarkdown>{markdownText}</ReactMarkdown>
      </article>
    </div>
  );
}
