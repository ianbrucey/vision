"use client";

import { useState, useRef, useEffect } from "react";
import { Check, X, Loader2 } from "lucide-react";
import type { Block } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface DraftPreviewProps {
  blocks: Block[];
  editMode: boolean;
  onBlockUpdate: (blockId: string, content: string) => Promise<void>;
  className?: string;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

function countNumBefore(blocks: Block[], idx: number): number {
  let c = 0;
  for (let i = 0; i < idx; i++) {
    if (blocks[i].type === "numbered_paragraph") c++;
  }
  return c;
}

function countListBefore(blocks: Block[], idx: number): number {
  let c = 0;
  for (let i = idx - 1; i >= 0; i--) {
    if (blocks[i].type === "list_item") c++;
    else break;
  }
  return c;
}

const LIST_LABELS = "abcdefghijklmnopqrstuvwxyz";

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DraftPreview({
  blocks,
  editMode,
  onBlockUpdate,
  className,
}: DraftPreviewProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");
  const [saving, setSaving] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  /* Auto-focus textarea when editing starts */
  useEffect(() => {
    if (editingId) textareaRef.current?.focus();
  }, [editingId]);

  const startEdit = (block: Block) => {
    if (!editMode || saving) return;
    setEditingId(block.id);
    setEditText(block.content);
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditText("");
  };

  const saveEdit = async () => {
    if (!editingId || saving) return;
    setSaving(true);
    try {
      await onBlockUpdate(editingId, editText);
      setEditingId(null);
    } catch {
      // keep editor open on failure
    } finally {
      setSaving(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") cancelEdit();
    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") saveEdit();
  };

  return (
    <div className={className}>
      <div className="bg-white text-gray-900 font-serif text-sm leading-relaxed
                      shadow-lg rounded-sm px-8 py-14 md:px-16 md:py-14
                      max-w-[680px] mx-auto min-h-full
                      md:border md:border-gray-200
                      max-md:bg-transparent max-md:text-text-primary max-md:shadow-none
                      max-md:px-4 max-md:py-4 max-md:max-w-none max-md:font-sans">
        {blocks.map((block, i) => {
          if (editingId === block.id) {
            return (
              <div key={block.id} className="my-2 rounded ring-2 ring-brand ring-offset-2">
                <textarea
                  ref={textareaRef}
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-transparent font-inherit text-inherit leading-inherit
                             resize-y outline-none p-3 min-h-[100px] text-sm"
                  rows={4}
                />
                <div className="flex justify-end gap-1.5 px-2 pb-2">
                  <button
                    onClick={cancelEdit}
                    disabled={saving}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-xs
                               bg-gray-100 text-gray-600 hover:bg-gray-200
                               disabled:opacity-50 font-sans"
                  >
                    <X size={12} /> Cancel
                  </button>
                  <button
                    onClick={saveEdit}
                    disabled={saving}
                    className="flex items-center gap-1 px-2.5 py-1 rounded text-xs
                               bg-brand text-white hover:bg-brand-hover
                               disabled:opacity-50 font-sans"
                  >
                    {saving ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                    Save
                  </button>
                </div>
              </div>
            );
          }

          const editClass = editMode && block.type !== "signature"
            ? "cursor-text hover:bg-brand-bg hover:outline hover:outline-1 hover:outline-dashed hover:outline-brand/30 rounded-sm px-1 -mx-1"
            : "";

          switch (block.type) {
            case "section_heading":
              return (
                <div
                  key={block.id}
                  onClick={() => startEdit(block)}
                  className={`text-center font-bold text-sm underline mt-8 mb-4 first:mt-0 ${editClass}`}
                >
                  {block.content}
                </div>
              );

            case "numbered_paragraph": {
              const num = countNumBefore(blocks, i) + 1;
              return (
                <p
                  key={block.id}
                  onClick={() => startEdit(block)}
                  className={`mb-0 ${editClass}`}
                  style={{ textIndent: "-24px", paddingLeft: "28px" }}
                >
                  <span className="font-semibold mr-1">{num}.</span>
                  {block.content}
                </p>
              );
            }

            case "list_item": {
              const labelIdx = countListBefore(blocks, i);
              const label = LIST_LABELS[labelIdx] || "?";
              return (
                <p
                  key={block.id}
                  onClick={() => startEdit(block)}
                  className={`mb-0 ${editClass}`}
                  style={{ textIndent: "-20px", paddingLeft: "24px" }}
                >
                  <span className="font-medium mr-1.5">({label})</span>
                  {block.content}
                </p>
              );
            }

            case "signature":
              return (
                <div key={block.id} className="mt-10 pt-1 border-t border-current inline-block min-w-[180px]">
                  <span className="font-semibold text-sm whitespace-pre-wrap">{block.content}</span>
                </div>
              );

            default:
              return (
                <p key={block.id} onClick={() => startEdit(block)} className={editClass}>
                  {block.content}
                </p>
              );
          }
        })}
      </div>
    </div>
  );
}
