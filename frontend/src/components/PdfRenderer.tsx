"use client";

import { useEffect, useState } from "react";
import { Loader2, AlertCircle, ExternalLink } from "lucide-react";
import { getDocumentPreviewUrl } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface PdfRendererProps {
  /** Content from workspace item — expected shape: [{document_id: number}] */
  content: unknown;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

function extractDocId(content: unknown): number | null {
  if (Array.isArray(content) && content.length > 0) {
    const first = content[0] as Record<string, unknown> | null;
    if (first && typeof first.document_id === "number") {
      return first.document_id;
    }
  }
  if (content && typeof content === "object" && !Array.isArray(content)) {
    const obj = content as Record<string, unknown>;
    if (typeof obj.document_id === "number") {
      return obj.document_id;
    }
  }
  return null;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function PdfRenderer({ content }: PdfRendererProps) {
  const docId = extractDocId(content);
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!docId) {
      setLoading(false);
      setError("No document_id in content — expected [{document_id: number}]");
      return;
    }

    let cancelled = false;
    getDocumentPreviewUrl(docId)
      .then((data) => {
        if (cancelled) return;
        if (data.url) {
          setUrl(data.url);
        } else {
          setError("No preview URL available for this document");
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load document");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [docId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  if (error || !url) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2 text-text-disabled">
        <AlertCircle size={24} />
        <p className="text-sm">{error || "Unable to preview this document"}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Toolbar */}
      <div className="shrink-0 flex items-center justify-between px-3 py-1.5 border-b border-border bg-surface-2">
        <span className="text-[11px] text-text-disabled">PDF Preview</span>
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-[11px] text-text-secondary hover:text-brand transition-colors"
        >
          <ExternalLink size={12} />
          Open in new tab
        </a>
      </div>
      {/* PDF iframe */}
      <iframe
        src={url}
        className="flex-1 w-full border-0"
        title="PDF Preview"
      />
    </div>
  );
}
