"use client";

import { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { X, Loader2, Download, AlertCircle, FileText } from "lucide-react";
import { getDocumentPreviewUrl } from "@/lib/api";

interface PreviewData {
  url: string | null;
  name: string;
  type: string;
  content?: string;
}

interface DocumentPreviewModalProps {
  docId: number;
  docName: string;
  open: boolean;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                            */
/* ------------------------------------------------------------------ */

function isSpreadsheet(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase();
  return ext === "csv" || ext === "xlsx" || ext === "xls";
}

function isDocument(name: string): boolean {
  const ext = name.split(".").pop()?.toLowerCase();
  return ext === "docx" || ext === "doc";
}

/** Parse CSV/XLSX block text into rows. Handles comma-separated and
 *  tab-separated content. */
function parseRows(text: string): string[][] {
  const lines = text.split("\n").filter((l) => l.trim());
  const separator = lines[0]?.includes("\t") ? "\t" : ",";
  return lines.map((line) =>
    line.split(separator).map((cell) => cell.trim().replace(/^"|"$/g, "")),
  );
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DocumentPreviewModal({
  docId,
  docName,
  open,
  onClose,
}: DocumentPreviewModalProps) {
  const [data, setData] = useState<PreviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [textContent, setTextContent] = useState<string | null>(null);
  const previousFocus = useRef<HTMLElement | null>(null);

  /* ---- fetch preview URL ---- */

  useEffect(() => {
    if (!open) return;
    previousFocus.current = document.activeElement as HTMLElement;
    document.body.style.overflow = "hidden";

    setLoading(true);
    setError(null);
    setData(null);
    setTextContent(null);

    getDocumentPreviewUrl(docId)
      .then((d) => {
        setData(d);
        if (d.content !== undefined) {
          setTextContent(d.content);
          return;
        }
        if (d.url && (d.type === "text" || d.type === "unknown")) {
          return fetch(d.url)
            .then((r) => r.text())
            .then((t) => setTextContent(t))
            .catch(() => setTextContent("[Could not load text content]"));
        }
      })
      .catch((err: unknown) =>
        setError(err instanceof Error ? err.message : "Failed to load preview"),
      )
      .finally(() => setLoading(false));

    return () => {
      document.body.style.overflow = "";
      previousFocus.current?.focus();
    };
  }, [open, docId]);

  /* ---- keyboard ---- */

  const onKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose],
  );

  useEffect(() => {
    if (!open) return;
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open, onKeyDown]);

  /* ---- parsed table ---- */

  const sheetRows = useMemo(() => {
    if (!textContent) return null;
    const displayName = data?.name || docName;
    if (!isSpreadsheet(displayName)) return null;
    return parseRows(textContent);
  }, [textContent, data, docName]);

  const showAsDoc = useMemo(() => {
    if (!data) return false;
    return isDocument(data.name) && !!textContent;
  }, [data, textContent]);

  /* ---- render ---- */

  const displayName = data?.name || docName;

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-2 sm:p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="bg-surface-1 border border-border rounded-t-xl sm:rounded-xl shadow-md
                      w-full h-[95dvh] sm:h-[90vh] sm:max-w-4xl
                      flex flex-col overflow-hidden
                      animate-in fade-in zoom-in-95 duration-200"
      >
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 sm:px-6 py-3 border-b border-border">
          <div className="min-w-0 mr-2">
            <h2 className="text-sm font-semibold truncate">{displayName}</h2>
            {data && (
              <p className="text-xs text-text-disabled capitalize">{data.type}</p>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {data?.url && (
              <a
                href={data.url}
                download={data.name}
                className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg
                           border border-border text-text-secondary
                           hover:bg-surface-2 hover:text-text-primary
                           transition-colors min-h-[36px]"
              >
                <Download size={14} />
                <span className="hidden sm:inline">Download</span>
              </a>
            )}
            <button
              onClick={onClose}
              className="size-9 rounded-lg inline-flex items-center justify-center
                         text-text-secondary hover:bg-surface-2 hover:text-text-primary
                         transition-colors"
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-hidden flex items-center justify-center bg-surface-3/50">
          {loading && (
            <div className="flex flex-col items-center gap-3 text-text-secondary">
              <Loader2 size={32} className="animate-spin" />
              <p className="text-sm">Loading preview...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center gap-3 text-center px-4">
              <AlertCircle size={32} className="text-danger" />
              <p className="text-sm text-danger">{error}</p>
            </div>
          )}

          {data && !loading && !error && (
            <>
              {/* PDF */}
              {data.type === "pdf" && (
                <iframe
                  src={data.url ?? undefined}
                  className="w-full h-full"
                  title={data.name}
                />
              )}

              {/* Image */}
              {data.type === "image" && (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img
                  src={data.url ?? undefined}
                  alt={data.name}
                  className="max-w-full max-h-full object-contain"
                />
              )}

              {/* Audio */}
              {data.type === "audio" && (
                <div className="flex flex-col items-center gap-4 p-8">
                  <FileText size={48} className="text-text-disabled" />
                  <p className="text-sm font-medium">{data.name}</p>
                  <audio controls autoPlay className="w-full max-w-md">
                    <source src={data.url ?? undefined} />
                    Your browser does not support audio playback.
                  </audio>
                </div>
              )}

              {/* Spreadsheet — rendered as an HTML table */}
              {sheetRows && (
                <div className="w-full h-full overflow-auto">
                  <table className="w-full text-xs border-collapse">
                    <thead className="sticky top-0 z-10">
                      <tr className="bg-surface-2">
                        {sheetRows[0]?.map((h, i) => (
                          <th
                            key={i}
                            className="px-3 py-2 text-left font-semibold text-text-primary
                                       border-b border-border whitespace-nowrap"
                          >
                            {h || `Col ${i + 1}`}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {sheetRows.slice(1).map((row, ri) => (
                        <tr
                          key={ri}
                          className={ri % 2 === 0 ? "bg-surface-1" : "bg-surface-0"}
                        >
                          {row.map((cell, ci) => (
                            <td
                              key={ci}
                              className="px-3 py-1.5 text-text-secondary border-b
                                         border-border-light whitespace-nowrap"
                            >
                              {cell}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* Document (DOCX) — styled text, not monospace */}
              {showAsDoc && !sheetRows && (
                <div className="w-full h-full overflow-auto p-6 sm:p-8 bg-white">
                  <div
                    className="max-w-[7in] mx-auto text-sm leading-relaxed
                               text-gray-900 font-sans whitespace-pre-wrap"
                  >
                    {textContent}
                  </div>
                </div>
              )}

              {/* Plain text (not a spreadsheet or doc) */}
              {textContent && !sheetRows && !showAsDoc && (
                <pre
                  className="w-full h-full overflow-auto p-4 sm:p-6 text-sm leading-relaxed
                             whitespace-pre-wrap font-mono text-text-primary bg-surface-1"
                >
                  {textContent}
                </pre>
              )}

              {/* Unsupported — only download */}
              {!textContent && data.type !== "pdf" && data.type !== "image" && data.type !== "audio" && (
                <div className="flex flex-col items-center gap-4 text-center p-8">
                  <FileText size={48} className="text-text-disabled" />
                  <div>
                    <p className="text-sm font-medium">{data.name}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      Preview not available for this file type.
                    </p>
                  </div>
                  {data.url && (
                    <a
                      href={data.url}
                      download={data.name}
                      className="inline-flex items-center gap-2 bg-brand hover:bg-brand-hover
                                 text-white px-4 py-2 rounded-lg text-sm font-medium
                                 transition-colors"
                    >
                      <Download size={16} />
                      Download File
                    </a>
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
