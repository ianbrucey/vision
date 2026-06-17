"use client";

import { useRef, useEffect, useCallback } from "react";
import { Bold, Italic, Underline } from "lucide-react";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface RichTextEditorProps {
  value: string;
  onChange: (html: string) => void;
  onSave: () => void;
  onCancel: () => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function RichTextEditor({
  value, onChange, onSave, onCancel,
}: RichTextEditorProps) {
  const editorRef = useRef<HTMLDivElement>(null);
  const initializedRef = useRef(false);

  /* Set initial content once */
  useEffect(() => {
    if (editorRef.current && !initializedRef.current) {
      editorRef.current.innerHTML = value;
      initializedRef.current = true;
      editorRef.current.focus();
    }
  }, [value]);

  /* Emit changes back to parent */
  const handleInput = useCallback(() => {
    if (editorRef.current) {
      onChange(editorRef.current.innerHTML);
    }
  }, [onChange]);

  /* Toolbar actions */
  const exec = useCallback((command: string) => {
    editorRef.current?.focus();
    document.execCommand(command, false);
    handleInput();
  }, [handleInput]);

  /* Keyboard shortcuts */
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
      e.preventDefault();
      onSave();
    }
    // Tab inserts spaces, doesn't move focus
    if (e.key === "Tab") {
      e.preventDefault();
      document.execCommand("insertHTML", false, "&#009;");
    }
  }, [onSave, onCancel]);

  return (
    <div style={{ border: "1px solid #B8860B", borderRadius: "6px", overflow: "hidden" }}>
      {/* Toolbar */}
      <div style={{
        display: "flex", gap: "2px", padding: "4px 6px",
        background: "#fafafa", borderBottom: "1px solid #e5e5e5",
      }}>
        <ToolBtn command="bold" title="Bold (⌘B)"><Bold size={14} /></ToolBtn>
        <ToolBtn command="italic" title="Italic (⌘I)"><Italic size={14} /></ToolBtn>
        <ToolBtn command="underline" title="Underline (⌘U)"><Underline size={14} /></ToolBtn>
        <div style={{ flex: 1 }} />
        <span style={{ fontSize: "10px", color: "#999", alignSelf: "center" }}>
          ⌘↵ Save · Esc Cancel
        </span>
      </div>

      {/* Editor */}
      <div
        ref={editorRef}
        contentEditable
        suppressContentEditableWarning
        onInput={handleInput}
        onKeyDown={handleKeyDown}
        style={{
          minHeight: "80px",
          padding: "10px 12px",
          fontFamily: "Times New Roman, Georgia, serif",
          fontSize: "14pt",
          lineHeight: "2.0",
          outline: "none",
          background: "white",
        }}
      />

      {/* Actions */}
      <div className="edit-actions" style={{ padding: "4px 8px", background: "#fafafa", borderTop: "1px solid #e5e5e5" }}>
        <button onClick={onCancel} className="btn-cancel">Cancel</button>
        <button onClick={onSave} className="btn-save">Save</button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Toolbar Button                                                      */
/* ------------------------------------------------------------------ */

function ToolBtn({
  command, title, children,
}: {
  command: string; title: string; children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      title={title}
      onMouseDown={(e) => {
        e.preventDefault();
        document.execCommand(command, false);
      }}
      style={{
        display: "flex", alignItems: "center", justifyContent: "center",
        width: "28px", height: "26px",
        border: "none", borderRadius: "4px",
        background: "transparent", cursor: "pointer",
        color: "#555",
      }}
      onMouseEnter={(e) => { (e.target as HTMLElement).style.background = "#e8e8e8"; }}
      onMouseLeave={(e) => { (e.target as HTMLElement).style.background = "transparent"; }}
    >
      {children}
    </button>
  );
}
