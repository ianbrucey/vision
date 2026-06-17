"use client";

import { useState, useRef, useEffect } from "react";
import type { Block } from "@/lib/api";
import RichTextEditor from "./RichTextEditor";

interface UniversalBodyRendererProps {
  blocks: Block[];
  editMode: boolean;
  editingBlockId: string | null;
  editText: string;
  onBlockClick: (block: Block) => void;
  onBlockSave: (blockId: string) => void;
  onBlockCancel: () => void;
  onEditTextChange: (text: string) => void;
  onInsertBlock: (afterIdx: number, blockType: Block["type"]) => void;
}

/* ------------------------------------------------------------------ */
/* Live Numbering (computed at render time, never stored)             */
/* ------------------------------------------------------------------ */

function getParagraphNumber(blocks: Block[], blockId: string): number {
  let count = 0;
  for (const b of blocks) {
    if (b.type === "numbered_paragraph") count++;
    if (b.id === blockId) return count;
  }
  return count;
}

function getListItemLabel(
  blocks: Block[],
  blockId: string,
  style: "letter" | "roman" | "bullet",
): string {
  const ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"];
  let count = 0;
  for (const b of blocks) {
    if (b.type !== "list_item") { count = 0; continue; }
    count++;
    if (b.id === blockId) {
      if (style === "bullet") return "•";
      if (style === "roman") return `(${ROMAN[Math.min(count - 1, ROMAN.length - 1)]})`;
      return `(${String.fromCharCode(96 + count)})`;
    }
  }
  return "(a)";
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function UniversalBodyRenderer(props: UniversalBodyRendererProps) {
  const { blocks } = props;

  if (!blocks || blocks.length === 0) {
    return (
      <p style={{ textAlign: "center", color: "#999", padding: "3em 0" }}>
        No content yet.
      </p>
    );
  }

  return (
    <div>
      {blocks.map((block, idx) => (
        <div key={block.id}>
          <BlockRenderer {...props} block={block} idx={idx} />
          {props.editMode && idx < blocks.length - 1 && (
            <InsertRow afterIdx={idx} onInsert={props.onInsertBlock} />
          )}
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Block Renderer                                                     */
/* ------------------------------------------------------------------ */

function BlockRenderer({
  blocks, block, editMode, editingBlockId, editText,
  onBlockClick, onBlockSave, onBlockCancel, onEditTextChange,
}: UniversalBodyRendererProps & { block: Block; idx: number }) {
  const isEditing = editMode && editingBlockId === block.id;

  /* ---- section_divider ---- */
  if (block.type === "section_divider") {
    return <hr className="section-divider" />;
  }

  /* ---- editing mode ---- */
  if (isEditing) {
    return (
      <RichTextEditor
        value={editText}
        onChange={onEditTextChange}
        onSave={() => onBlockSave(block.id)}
        onCancel={onBlockCancel}
      />
    );
  }

  const editClass = editMode ? "editable-block" : "";

  /* ---- section_heading ---- */
  if (block.type === "section_heading") {
    return (
      <div
        className={`section-header ${editClass}`}
        onClick={() => editMode && onBlockClick(block)}
        title={editMode ? "Click to edit" : undefined}
        dangerouslySetInnerHTML={{ __html: block.content }}
      />
    );
  }

  /* ---- numbered_paragraph ---- */
  if (block.type === "numbered_paragraph") {
    const num = getParagraphNumber(blocks, block.id);
    return (
      <p
        className={`numbered ${editClass}`}
        onClick={() => editMode && onBlockClick(block)}
        title={editMode ? "Click to edit" : undefined}
      >
        <span className="para-num">{num}.</span>
        <span dangerouslySetInnerHTML={{ __html: block.content }} />
      </p>
    );
  }

  /* ---- unnumbered_paragraph ---- */
  if (block.type === "unnumbered_paragraph") {
    return (
      <p
        className={`unnumbered ${editClass}`}
        onClick={() => editMode && onBlockClick(block)}
        title={editMode ? "Click to edit" : undefined}
        dangerouslySetInnerHTML={{ __html: block.content }}
      />
    );
  }

  /* ---- block_quote ---- */
  if (block.type === "block_quote") {
    return (
      <blockquote
        className={editClass}
        onClick={() => editMode && onBlockClick(block)}
        title={editMode ? "Click to edit" : undefined}
        dangerouslySetInnerHTML={{ __html: block.content }}
      />
    );
  }

  /* ---- list_item ---- */
  if (block.type === "list_item") {
    const style = block.list_style || "letter";
    const label = getListItemLabel(blocks, block.id, style);
    return (
      <p
        className={`draft-list-item ${editClass}`}
        onClick={() => editMode && onBlockClick(block)}
        title={editMode ? "Click to edit" : undefined}
      >
        <span className="list-label">{label}</span>
        <span dangerouslySetInnerHTML={{ __html: block.content }} />
      </p>
    );
  }

  /* ---- signature_row ---- */
  if (block.type === "signature_row") {
    return (
      <div
        className={`signature-row ${editClass}`}
        onClick={() => editMode && onBlockClick(block)}
        title={editMode ? "Click to edit" : undefined}
      >
        <div className="signature-line" />
        <div
          className="signature-name"
          dangerouslySetInnerHTML={{ __html: block.content }}
        />
        {block.printed_name && <div>{block.printed_name}</div>}
      </div>
    );
  }

  /* ---- raw_html ---- */
  if (block.type === "raw_html") {
    return (
      <div
        className={`raw-html-block ${editClass}`}
        onClick={() => editMode && onBlockClick(block)}
        title={editMode ? "Click to edit" : undefined}
        dangerouslySetInnerHTML={{ __html: block.content }}
      />
    );
  }

  return null;
}

/* ------------------------------------------------------------------ */
/* Insert Row                                                         */
/* ------------------------------------------------------------------ */

const INSERT_OPTIONS: { type: Block["type"]; label: string }[] = [
  { type: "numbered_paragraph", label: "¶ Numbered Paragraph" },
  { type: "unnumbered_paragraph", label: "¶ Plain Paragraph" },
  { type: "section_heading", label: "§ Section Heading" },
  { type: "list_item", label: "⒜ List Item" },
  { type: "block_quote", label: "  Block Quote" },
  { type: "section_divider", label: "—— Divider" },
];

function InsertRow({
  afterIdx,
  onInsert,
}: {
  afterIdx: number;
  onInsert: (afterIdx: number, blockType: Block["type"]) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} className="insert-row">
      <div className="insert-row-line" />
      <button onClick={() => setOpen(!open)} className="insert-row-btn">
        + Insert
      </button>
      {open && (
        <div className="insert-menu">
          {INSERT_OPTIONS.map((opt) => (
            <button
              key={opt.type}
              onClick={() => { onInsert(afterIdx, opt.type); setOpen(false); }}
            >
              {opt.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
