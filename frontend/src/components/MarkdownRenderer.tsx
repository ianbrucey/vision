"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { Loader2, Printer } from "lucide-react";

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
    <div className="flex-1 overflow-y-auto bg-[--surface-0] p-4 md:p-8">
      <article className="max-w-[8.5in] mx-auto bg-white rounded-lg shadow-lg p-8 md:p-12
                        prose prose-sm
                        prose-headings:text-gray-900
                        prose-p:text-gray-800 prose-p:leading-relaxed
                        prose-a:text-[--info] prose-a:no-underline hover:prose-a:underline
                        prose-strong:text-gray-900
                        prose-code:text-gray-800 prose-code:bg-gray-100 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                        prose-pre:bg-gray-50 prose-pre:border prose-pre:border-gray-200
                        prose-blockquote:border-[--brand] prose-blockquote:text-gray-600
                        prose-ul:text-gray-800 prose-ol:text-gray-800
                        prose-li:text-gray-800
                        prose-hr:border-gray-200
                        prose-img:rounded-md">
        <ReactMarkdown>{markdownText}</ReactMarkdown>
      </article>
    </div>
  );
}
