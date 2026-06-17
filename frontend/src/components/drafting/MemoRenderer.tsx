"use client";

import type { Block } from "@/lib/api";
import UniversalBodyRenderer from "./UniversalBodyRenderer";

interface MemoHeader {
  to?: string;
  from?: string;
  date?: string;
  re?: string;
}

interface MemoRendererProps {
  blocks: Block[];
  editMode: boolean;
  editingBlockId: string | null;
  editText: string;
  onBlockClick: (block: Block) => void;
  onBlockSave: (blockId: string) => void;
  onBlockCancel: () => void;
  onEditTextChange: (text: string) => void;
  onInsertBlock: (afterIdx: number, blockType: Block["type"]) => void;
  header?: MemoHeader;
}

export default function MemoRenderer({
  blocks, editMode, editingBlockId, editText,
  onBlockClick, onBlockSave, onBlockCancel, onEditTextChange, onInsertBlock,
  header,
}: MemoRendererProps) {
  const h = header || {};

  return (
    <div className="draft-document">
      <div className="document-title">MEMORANDUM</div>

      <table className="memo-header-table">
        <tbody>
          {h.to && (
            <tr>
              <td className="memo-header-label">TO:</td>
              <td>{h.to}</td>
            </tr>
          )}
          {h.from && (
            <tr>
              <td className="memo-header-label">FROM:</td>
              <td>{h.from}</td>
            </tr>
          )}
          {h.date && (
            <tr>
              <td className="memo-header-label">DATE:</td>
              <td>{h.date}</td>
            </tr>
          )}
          {h.re && (
            <tr>
              <td className="memo-header-label">RE:</td>
              <td>{h.re}</td>
            </tr>
          )}
        </tbody>
      </table>

      <UniversalBodyRenderer
        blocks={blocks} editMode={editMode}
        editingBlockId={editingBlockId} editText={editText}
        onBlockClick={onBlockClick} onBlockSave={onBlockSave}
        onBlockCancel={onBlockCancel} onEditTextChange={onEditTextChange}
        onInsertBlock={onInsertBlock}
      />
    </div>
  );
}
