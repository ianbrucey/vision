"use client";

import { useState, useRef, useEffect } from "react";
import type { Block } from "@/lib/api";
import UniversalBodyRenderer from "./UniversalBodyRenderer";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

export interface PleadingCaption {
  court_name?: string;
  plaintiff?: string;
  defendant?: string;
  case_number?: string;
  document_title?: string;
}

export interface PleadingSignature {
  attorney_name?: string;
  bar_number?: string;
  firm_name?: string;
}

interface PleadingRendererProps {
  blocks: Block[];
  editMode: boolean;
  editingBlockId: string | null;
  editText: string;
  onBlockClick: (block: Block) => void;
  onBlockSave: (blockId: string) => void;
  onBlockCancel: () => void;
  onEditTextChange: (text: string) => void;
  onInsertBlock: (afterIdx: number, blockType: Block["type"]) => void;
  caption?: PleadingCaption;
  signature?: PleadingSignature;
  onCaptionChange?: (field: string, value: string) => Promise<void> | void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

function nl2br(text: string | undefined, fallback: string): string {
  return (text || fallback).replace(/\n/g, "<br>");
}

/* ------------------------------------------------------------------ */
/* InlineEditableField — uncontrolled input to preserve cursor pos    */
/* ------------------------------------------------------------------ */

function InlineEditableField({
  value: initialValue,
  fallback,
  multiline,
  editing,
  onSave,
  onCancel,
}: {
  value: string | undefined;
  fallback: string;
  multiline?: boolean;
  editing: boolean;
  onSave: (val: string) => void;
  onCancel: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (editing) {
      if (multiline) textareaRef.current?.focus();
      else inputRef.current?.focus();
    }
  }, [editing, multiline]);

  if (editing) {
    const handleSave = () => {
      const val = multiline
        ? textareaRef.current?.value ?? ""
        : inputRef.current?.value ?? "";
      onSave(val);
    };

    if (multiline) {
      return (
        <div>
          <textarea
            ref={textareaRef}
            defaultValue={initialValue || ""}
            onKeyDown={(e) => {
              if (e.key === "Escape") { e.preventDefault(); onCancel(); }
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") { e.preventDefault(); handleSave(); }
            }}
            className="edit-textarea"
            rows={3}
          />
          <div className="edit-actions">
            <button onClick={onCancel} className="btn-cancel">Cancel</button>
            <button onClick={handleSave} className="btn-save">Save</button>
          </div>
        </div>
      );
    }

    return (
      <div>
        <input
          ref={inputRef}
          type="text"
          defaultValue={initialValue || ""}
          onKeyDown={(e) => {
            if (e.key === "Escape") { e.preventDefault(); onCancel(); }
            if (e.key === "Enter") { e.preventDefault(); handleSave(); }
          }}
          className="edit-textarea"
        />
        <div className="edit-actions">
          <button onClick={onCancel} className="btn-cancel">Cancel</button>
          <button onClick={handleSave} className="btn-save">Save</button>
        </div>
      </div>
    );
  }

  return (
    <span dangerouslySetInnerHTML={{ __html: nl2br(initialValue, fallback) }} />
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function PleadingRenderer({
  blocks, editMode, editingBlockId, editText,
  onBlockClick, onBlockSave, onBlockCancel, onEditTextChange, onInsertBlock,
  caption, signature, onCaptionChange,
}: PleadingRendererProps) {
  const [editingField, setEditingField] = useState<string | null>(null);

  const cap = caption || {};

  const saveField = (field: string, value: string) => {
    setEditingField(null);
    if (onCaptionChange) onCaptionChange(field, value);
  };

  const rp = {
    blocks, editMode, editingBlockId, editText,
    onBlockClick, onBlockSave, onBlockCancel, onEditTextChange, onInsertBlock,
  };

  return (
    <div className="draft-document">
      {/* Court Name */}
      <div className="court-caption">
        <span
          className={editMode && editingField !== "caption.court_name" ? "editable-caption-field" : ""}
          onClick={() => editMode && setEditingField("caption.court_name")}
          title={editMode ? "Click to edit" : undefined}
        >
          <InlineEditableField
            value={cap.court_name}
            fallback="[COURT NAME]"
            multiline
            editing={editMode && editingField === "caption.court_name"}
            onSave={(v) => saveField("court_name", v)}
            onCancel={() => setEditingField(null)}
          />
        </span>
      </div>

      {/* Case Caption Table */}
      <table className="case-caption">
        <tbody>
          <tr>
            <td className="case-left">
              <span
                className={editMode && editingField !== "caption.plaintiff" ? "editable-caption-field" : ""}
                onClick={() => editMode && setEditingField("caption.plaintiff")}
                title={editMode ? "Click to edit" : undefined}
              >
                <InlineEditableField
                  value={cap.plaintiff}
                  fallback="[PLAINTIFF]"
                  multiline
                  editing={editMode && editingField === "caption.plaintiff"}
                  onSave={(v) => saveField("plaintiff", v)}
                  onCancel={() => setEditingField(null)}
                />
              </span>
              ,<br /><br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Plaintiff,<br /><br />
              v.<br /><br />
              <span
                className={editMode && editingField !== "caption.defendant" ? "editable-caption-field" : ""}
                onClick={() => editMode && setEditingField("caption.defendant")}
                title={editMode ? "Click to edit" : undefined}
              >
                <InlineEditableField
                  value={cap.defendant}
                  fallback="[DEFENDANT]"
                  multiline
                  editing={editMode && editingField === "caption.defendant"}
                  onSave={(v) => saveField("defendant", v)}
                  onCancel={() => setEditingField(null)}
                />
              </span>
              ,<br /><br />
              &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;Defendant.
            </td>
            <td className="case-right">
              <br /><br /><br /><br />
              <span
                className={editMode && editingField !== "caption.case_number" ? "editable-caption-field" : ""}
                onClick={() => editMode && setEditingField("caption.case_number")}
                title={editMode ? "Click to edit" : undefined}
              >
                <InlineEditableField
                  value={cap.case_number}
                  fallback="[CASE NUMBER]"
                  editing={editMode && editingField === "caption.case_number"}
                  onSave={(v) => saveField("case_number", v)}
                  onCancel={() => setEditingField(null)}
                />
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      {/* Motion Title */}
      <div className="motion-title">
        <span
          className={editMode && editingField !== "caption.document_title" ? "editable-caption-field" : ""}
          onClick={() => editMode && setEditingField("caption.document_title")}
          title={editMode ? "Click to edit" : undefined}
        >
          <InlineEditableField
            value={cap.document_title}
            fallback="[DOCUMENT TITLE]"
            editing={editMode && editingField === "caption.document_title"}
            onSave={(v) => saveField("document_title", v)}
            onCancel={() => setEditingField(null)}
          />
        </span>
      </div>

      {/* Body */}
      <UniversalBodyRenderer {...rp} />

      {/* Signature Block */}
      {signature && (
        <div className="signature-row">
          <div className="signature-line" />
          <div className="signature-name">
            {signature.attorney_name || ""}
          </div>
          {signature.bar_number && <div>{signature.bar_number}</div>}
          {signature.firm_name && <div>{signature.firm_name}</div>}
        </div>
      )}
    </div>
  );
}
