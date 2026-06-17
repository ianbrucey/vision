"use client";

import { useState, useCallback } from "react";
import { Printer } from "lucide-react";
import type { Block } from "@/lib/api";
import "./drafting/draftStyles.css";
import PleadingRenderer from "./drafting/PleadingRenderer";
import LetterRenderer from "./drafting/LetterRenderer";
import ContractRenderer from "./drafting/ContractRenderer";
import MemoRenderer from "./drafting/MemoRenderer";
import { printDraft } from "./drafting/printUtils";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface DraftPreviewProps {
  blocks: Block[];
  editMode: boolean;
  onBlockUpdate: (blockId: string, content: string) => Promise<void>;
  onBlocksChange?: (blocks: Block[]) => Promise<void>;
  onMetadataChange?: (metadata: Record<string, unknown>) => Promise<void>;
  documentType?: string;
  metadata?: Record<string, unknown> | null;
  className?: string;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

let _counter = 0;
function nextBlockId(): string {
  _counter++;
  return `b${Date.now().toString(36)}-${_counter}`;
}

const PLACEHOLDER: Record<string, string> = {
  section_heading: "New Section",
  numbered_paragraph: "Start writing here...",
  unnumbered_paragraph: "Start writing here...",
  block_quote: "Quoted text...",
  list_item: "List item...",
  signature_row: "Your Name",
  section_divider: "",
  raw_html: "",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DraftPreview({
  blocks, editMode, onBlockUpdate, onBlocksChange, onMetadataChange,
  documentType, metadata, className,
}: DraftPreviewProps) {
  const [editingBlockId, setEditingBlockId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const handleBlockClick = useCallback((block: Block) => {
    setEditingBlockId(block.id);
    setEditText(block.content);
  }, []);

  const handleBlockSave = useCallback(async (blockId: string) => {
    await onBlockUpdate(blockId, editText);
    setEditingBlockId(null);
  }, [editText, onBlockUpdate]);

  const handleBlockCancel = useCallback(() => {
    setEditingBlockId(null);
    setEditText("");
  }, []);

  const handleInsertBlock = useCallback(async (
    afterIdx: number, blockType: Block["type"],
  ) => {
    if (!onBlocksChange) return;
    const b: Block = { id: nextBlockId(), type: blockType, content: PLACEHOLDER[blockType] || "" };
    const updated = [...blocks];
    updated.splice(afterIdx + 1, 0, b);
    await onBlocksChange(updated);
    setEditingBlockId(b.id);
    setEditText(b.content);
  }, [blocks, onBlocksChange]);

  const handlePrint = () => {
    const el = document.querySelector(".draft-preview-shell");
    if (!el) return;
    printDraft(el.innerHTML);
  };

  /* ---- shared renderer props ---- */
  const rp = {
    blocks, editMode, editingBlockId, editText,
    onBlockClick: handleBlockClick,
    onBlockSave: handleBlockSave,
    onBlockCancel: handleBlockCancel,
    onEditTextChange: setEditText,
    onInsertBlock: handleInsertBlock,
  };

  const docType = documentType || "letter";
  const title = metadata ? String((metadata as Record<string, unknown>).title || "") : "";

  if (!blocks || blocks.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <p className="text-sm text-[--text-disabled]">No content yet.</p>
      </div>
    );
  }

  return (
    <div className={`flex-1 flex flex-col min-h-0 ${className || ""}`}>
      {/* Toolbar */}
      <div className="shrink-0 flex items-center justify-between px-4 py-2 bg-[--surface-1] border-b border-[--border]">
        <span className="text-xs text-[--text-secondary]">
          {docType.charAt(0).toUpperCase() + docType.slice(1)}
          {title ? ` — ${title}` : ""}
        </span>
        <button
          onClick={handlePrint}
          className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded border border-[--border] bg-[--surface-1] hover:bg-[--surface-3] text-[--text-primary] transition-colors"
        >
          <Printer size={14} />
          <span className="hidden sm:inline">Print</span>
        </button>
      </div>

      {/* Document */}
      <div className="flex-1 overflow-y-auto bg-[#f5f5f5] p-4">
        <div className="draft-preview-shell">
          {docType === "pleading" && (
            <PleadingRenderer
              {...rp}
              caption={metadata?.caption as PleadingRenderer["caption"]}
              signature={metadata?.signature as PleadingRenderer["signature"]}
              onCaptionChange={async (field, value) => {
                const currentMeta = (metadata || {}) as Record<string, unknown>;
                const currentCaption = (currentMeta.caption || {}) as Record<string, string>;
                const updated = {
                  ...currentMeta,
                  caption: { ...currentCaption, [field]: value },
                };
                try {
                  await onMetadataChange?.(updated);
                } catch (e) {
                  console.error("Failed to save caption:", e);
                }
              }}
            />
          )}
          {docType === "letter" && (
            <LetterRenderer
              {...rp}
              header={metadata as LetterRenderer["header"]}
              footer={metadata as LetterRenderer["footer"]}
            />
          )}
          {(docType === "contract" || docType === "settlement") && (
            <ContractRenderer
              {...rp}
              header={metadata as ContractRenderer["header"]}
            />
          )}
          {docType === "memo" && (
            <MemoRenderer {...rp} header={metadata as MemoRenderer["header"]} />
          )}
          {!["pleading", "letter", "contract", "settlement", "memo"].includes(docType) && (
            <LetterRenderer {...rp} />
          )}
        </div>
      </div>
    </div>
  );
}
