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

    /* eslint-disable react-hooks/set-state-in-effect */
    setLoading(true);
    setError(null);
    setData(null);
    setTextContent(null);
    /* eslint-enable react-hooks/set-state-in-effect */

    getDocumentPreviewUrl(docId)
      .then((d) => {
        setData(d);
        // Inline content (e.g. storage-less documents like inbound email
        // replies) is returned directly — no file to fetch.
        if (d.content !== undefined) {
          setTextContent(d.content);
          return;
        }
        // For text files backed by a file, fetch the content.
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

  /* ---- render ---- */

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-2 sm:p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-surface-1 border border-border rounded-t-xl sm:rounded-xl shadow-md
                      w-full h-[95dvh] sm:h-[90vh] sm:max-w-[90vw] sm:max-w-3xl
                      flex flex-col overflow-hidden
                      animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 sm:px-6 py-3 border-b border-border">
          <div className="min-w-0 mr-2">
            <h2 className="text-sm font-semibold truncate">
              {data?.name || docName}
            </h2>
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
              <p className="text-xs text-text-secondary">
                This document may have been uploaded before the storage fix.
                Try re-uploading it.
              </p>
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

              {/* Text */}
              {(data.type === "text" || (data.type === "unknown" && textContent)) && (
                <pre className="w-full h-full overflow-auto p-4 sm:p-6 text-sm leading-relaxed
                               whitespace-pre-wrap font-mono text-text-primary bg-surface-1">
                  {textContent || "[No content]"}
                </pre>
              )}

              {/* Office / unsupported */}
              {(data.type === "office" || (data.type === "unknown" && !textContent)) && (
                <div className="flex flex-col items-center gap-4 text-center p-8">
                  <FileText size={48} className="text-text-disabled" />
                  <div>
                    <p className="text-sm font-medium">{data.name}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      Preview not available for this file type.
                    </p>
                  </div>
                  <a
                    href={data.url ?? undefined}
                    download={data.name}
                    className="inline-flex items-center gap-2 bg-brand hover:bg-brand-hover
                               text-white px-4 py-2 rounded-lg text-sm font-medium
                               transition-colors"
                  >
                    <Download size={16} />
                    Download File
                  </a>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
