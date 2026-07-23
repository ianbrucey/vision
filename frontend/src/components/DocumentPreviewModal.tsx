"use client";

import { useEffect, useState, useCallback, useRef } from "react";
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

function fileExt(name: string): string {
  return (name.split(".").pop() || "").toLowerCase();
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
  const docxRef = useRef<HTMLDivElement>(null);
  const xlsxRef = useRef<HTMLDivElement>(null);
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

  /* ---- DOCX: render with docx-preview ---- */

  useEffect(() => {
    if (!data?.url || loading || error) return;
    const ext = fileExt(data.name);
    if (ext !== "docx" && ext !== "doc") return;
    const container = docxRef.current;
    if (!container) return;

    let cancelled = false;
    (async () => {
      try {
        const { renderAsync } = await import("docx-preview");
        const resp = await fetch(data.url!);
        const blob = await resp.blob();
        if (cancelled) return;
        container.innerHTML = "";
        await renderAsync(blob, container, undefined, {
          className: "docx-preview",
          inWrapper: true,
          ignoreWidth: false,
        });
      } catch (e) {
        if (!cancelled) setError("Failed to render document");
      }
    })();
    return () => { cancelled = true; };
  }, [data?.url, loading, error]);

  /* ---- XLSX / CSV: render with SheetJS ---- */

  useEffect(() => {
    if (!data?.url || loading || error) return;
    const ext = fileExt(data.name);
    if (ext !== "xlsx" && ext !== "xls" && ext !== "csv") return;
    const container = xlsxRef.current;
    if (!container) return;

    let cancelled = false;
    (async () => {
      try {
        const XLSX = await import("xlsx");
        const resp = await fetch(data.url!);
        const buf = await resp.arrayBuffer();
        if (cancelled) return;
        const wb = XLSX.read(buf, { type: "array" });
        container.innerHTML = "";
        for (const name of wb.SheetNames) {
          const sheet = wb.Sheets[name];
          const html = XLSX.utils.sheet_to_html(sheet, { editable: false });
          container.insertAdjacentHTML("beforeend", html);
        }
      } catch (e) {
        if (!cancelled) setError("Failed to render spreadsheet");
      }
    })();
    return () => { cancelled = true; };
  }, [data?.url, loading, error]);

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

  /* ---- render ---- */

  const displayName = data?.name || docName;
  const ext = fileExt(displayName);
  const isDocx = ext === "docx" || ext === "doc";
  const isSpreadsheet = ext === "xlsx" || ext === "xls" || ext === "csv";

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
                      w-full h-[95dvh] sm:h-[90vh] sm:max-w-5xl
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
              {data?.url && (
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

          {data && !loading && !error && (
            <>
              {/* PDF — iframe */}
              {data.type === "pdf" && (
                <iframe src={data.url ?? undefined} className="w-full h-full" title={data.name} />
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
                  </audio>
                </div>
              )}

              {/* DOCX — docx-preview */}
              {isDocx && (
                <div
                  ref={docxRef}
                  className="w-full h-full overflow-auto bg-white p-4 sm:p-8"
                />
              )}

              {/* XLSX / CSV — SheetJS table */}
              {isSpreadsheet && (
                <div
                  ref={xlsxRef}
                  className="w-full h-full overflow-auto [&_table]:border-collapse [&_td]:border
                             [&_td]:border-border-light [&_td]:px-2 [&_td]:py-1 [&_td]:text-xs
                             [&_th]:bg-surface-2 [&_th]:border [&_th]:border-border
                             [&_th]:px-2 [&_th]:py-1 [&_th]:text-xs [&_th]:font-semibold
                             [&_tr:nth-child(even)]:bg-surface-1"
                />
              )}

              {/* Text content (email bodies, inline text) */}
              {textContent && !isDocx && !isSpreadsheet && (
                <pre
                  className="w-full h-full overflow-auto p-4 sm:p-6 text-sm leading-relaxed
                             whitespace-pre-wrap font-mono text-text-primary bg-surface-1"
                >
                  {textContent}
                </pre>
              )}

              {/* Unsupported */}
              {!textContent && data.type !== "pdf" && data.type !== "image" && data.type !== "audio" && !isDocx && !isSpreadsheet && (
                <div className="flex flex-col items-center gap-4 text-center p-8">
                  <FileText size={48} className="text-text-disabled" />
                  <p className="text-sm font-medium">{data.name}</p>
                  <p className="text-xs text-text-secondary mt-1">
                    Preview not available for this file type.
                  </p>
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
