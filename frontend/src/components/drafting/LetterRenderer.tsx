"use client";

import type { Block } from "@/lib/api";
import UniversalBodyRenderer from "./UniversalBodyRenderer";

interface LetterHeader {
  date?: string;
  recipient_name?: string;
  recipient_address?: string;
  salutation?: string;
  subject_line?: string;
}

interface LetterFooter {
  sign_off?: string;
  sender_name?: string;
  sender_title?: string;
}

interface LetterRendererProps {
  blocks: Block[];
  editMode: boolean;
  editingBlockId: string | null;
  editText: string;
  onBlockClick: (block: Block) => void;
  onBlockSave: (blockId: string) => void;
  onBlockCancel: () => void;
  onEditTextChange: (text: string) => void;
  onInsertBlock: (afterIdx: number, blockType: Block["type"]) => void;
  header?: LetterHeader;
  footer?: LetterFooter;
}

function nl2br(text: string | undefined): string {
  return (text || "").replace(/\n/g, "<br>");
}

export default function LetterRenderer({
  blocks, editMode, editingBlockId, editText,
  onBlockClick, onBlockSave, onBlockCancel, onEditTextChange, onInsertBlock,
  header, footer,
}: LetterRendererProps) {
  const h = header || {};
  const f = footer || {};

  return (
    <div className="draft-document draft-letter">
      {/* Date */}
      {h.date && <p className="letter-date">{h.date}</p>}

      {/* Recipient */}
      {h.recipient_name && (
        <div className="letter-recipient">
          <div dangerouslySetInnerHTML={{ __html: nl2br(h.recipient_name) }} />
          {h.recipient_address && (
            <div dangerouslySetInnerHTML={{ __html: nl2br(h.recipient_address) }} />
          )}
        </div>
      )}

      {/* Salutation */}
      {h.salutation && <p className="letter-salutation">{h.salutation}</p>}

      {/* Subject */}
      {h.subject_line && (
        <p className="letter-subject">Re: {h.subject_line}</p>
      )}

      {/* Body */}
      <UniversalBodyRenderer
        blocks={blocks} editMode={editMode}
        editingBlockId={editingBlockId} editText={editText}
        onBlockClick={onBlockClick} onBlockSave={onBlockSave}
        onBlockCancel={onBlockCancel} onEditTextChange={onEditTextChange}
        onInsertBlock={onInsertBlock}
      />

      {/* Sign-off */}
      {f.sign_off && <p className="letter-signoff">{f.sign_off}</p>}

      {/* Signature */}
      <div className="signature-row">
        <div className="signature-line" />
        {f.sender_name && <div className="signature-name">{f.sender_name}</div>}
        {f.sender_title && <div>{f.sender_title}</div>}
      </div>
    </div>
  );
}
