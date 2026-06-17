"use client";

import type { Block } from "@/lib/api";
import UniversalBodyRenderer from "./UniversalBodyRenderer";

interface ContractHeader {
  party_a_name?: string;
  party_b_name?: string;
  effective_date?: string;
  document_title?: string;
}

interface ContractRendererProps {
  blocks: Block[];
  editMode: boolean;
  editingBlockId: string | null;
  editText: string;
  onBlockClick: (block: Block) => void;
  onBlockSave: (blockId: string) => void;
  onBlockCancel: () => void;
  onEditTextChange: (text: string) => void;
  onInsertBlock: (afterIdx: number, blockType: Block["type"]) => void;
  header?: ContractHeader;
}

export default function ContractRenderer({
  blocks, editMode, editingBlockId, editText,
  onBlockClick, onBlockSave, onBlockCancel, onEditTextChange, onInsertBlock,
  header,
}: ContractRendererProps) {
  const h = header || {};

  return (
    <div className="draft-document">
      {h.document_title && (
        <div className="document-title">{h.document_title}</div>
      )}

      {h.effective_date && (
        <p className="document-meta">
          This Agreement is made and entered into as of {h.effective_date} by and between:
        </p>
      )}

      <div className="contract-parties">
        <div>
          <strong>{h.party_a_name || "Party A"}</strong>
          <div className="contract-party-label">(&quot;Party A&quot;)</div>
        </div>
        <div>
          <strong>{h.party_b_name || "Party B"}</strong>
          <div className="contract-party-label">(&quot;Party B&quot;)</div>
        </div>
      </div>

      <UniversalBodyRenderer
        blocks={blocks} editMode={editMode}
        editingBlockId={editingBlockId} editText={editText}
        onBlockClick={onBlockClick} onBlockSave={onBlockSave}
        onBlockCancel={onBlockCancel} onEditTextChange={onEditTextChange}
        onInsertBlock={onInsertBlock}
      />

      <div className="contract-parties" style={{ marginTop: "3em" }}>
        <div className="signature-row">
          <div className="signature-line" />
          <div className="signature-name">{h.party_a_name || "Party A"}</div>
        </div>
        <div className="signature-row">
          <div className="signature-line" />
          <div className="signature-name">{h.party_b_name || "Party B"}</div>
        </div>
      </div>
    </div>
  );
}
