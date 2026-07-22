"use client";

import {
  useState, useEffect, useLayoutEffect, useRef, useCallback,
} from "react";
import { createPortal } from "react-dom";
import {
  Paperclip, Search, X, Loader2, AlertCircle, Upload, Check,
} from "lucide-react";
import { listDocuments, uploadFile, getJob } from "@/lib/api";

/* Dropdown is portaled to document.body (fixed position) so it always
 * escapes ancestor stacking contexts (e.g. overflow-auto table wrappers)
 * instead of rendering behind sticky/z-indexed siblings like the app header. */
const MENU_WIDTH = 288; // w-72
const MENU_MAX_HEIGHT = 256; // max-h-64
const MENU_GAP = 4;

function computeMenuPosition(rect: DOMRect): { top: number; left: number } {
  const spaceAbove = rect.top;
  const spaceBelow = window.innerHeight - rect.bottom;
  const openAbove = spaceAbove >= MENU_MAX_HEIGHT + MENU_GAP || spaceAbove > spaceBelow;
  const top = openAbove
    ? Math.max(8, rect.top - MENU_MAX_HEIGHT - MENU_GAP)
    : rect.bottom + MENU_GAP;
  const left = Math.min(Math.max(rect.left, 8), window.innerWidth - MENU_WIDTH - 8);
  return { top, left };
}

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

interface DocRef {
  id: number;
  name: string;
  page_count: number | null;
  ocr_status?: string;
}

interface UploadState {
  fileName: string;
  jobId: number;
  status: "processing" | "complete" | "failed" | "extracting";
  documentId: number | null;
  error: string | null;
  isZip?: boolean;
  totalFiles?: number;
  childJobIds?: number[];
}

interface DocumentAttachButtonProps {
  caseId: number;
  attachedIds: number[];
  onAttach: (documentId: number, documentName: string) => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function DocumentAttachButton({
  caseId,
  attachedIds,
  onAttach,
}: DocumentAttachButtonProps) {
  const [open, setOpen] = useState(false);
  const [docs, setDocs] = useState<DocRef[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [uploads, setUploads] = useState<UploadState[]>([]);
  const [menuPos, setMenuPos] = useState<{ top: number; left: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  /* Position the portaled menu against the trigger container, and keep it
   * in sync on scroll/resize while open. */
  useLayoutEffect(() => {
    if (!open) return;
    const update = () => {
      if (containerRef.current) {
        setMenuPos(computeMenuPosition(containerRef.current.getBoundingClientRect()));
      }
    };
    update();
    window.addEventListener("scroll", update, true);
    window.addEventListener("resize", update);
    return () => {
      window.removeEventListener("scroll", update, true);
      window.removeEventListener("resize", update);
    };
  }, [open]);

  /* Close on outside click (checks both the trigger and the portaled menu) */
  useEffect(() => {
    if (!open) return;
    const handler = (e: MouseEvent) => {
      const target = e.target as Node;
      if (
        containerRef.current && !containerRef.current.contains(target)
        && menuRef.current && !menuRef.current.contains(target)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  /* Load documents when opened */
  const refreshDocs = useCallback(async () => {
    setLoading(true);
    try {
      const res = (await listDocuments(caseId)) as DocRef[];
      setDocs(res);
    } catch { /* silent */ }
    setLoading(false);
  }, [caseId]);

  useEffect(() => {
    if (!open) return;
    refreshDocs();
  }, [open, refreshDocs]);

  /* Poll a single upload job until complete */
  const pollUpload = useCallback(async (upload: UploadState): Promise<UploadState> => {
    try {
      const job = await getJob(upload.jobId) as any;
      if (job.status === "complete") {
        // ZIP extraction completed — check for child jobs
        if (upload.isZip) {
          const meta = job.metadata || {};
          const childJobIds: number[] = meta.child_job_ids || [];
          const totalFiles: number = meta.total_files || childJobIds.length;
          if (childJobIds.length > 0) {
            // Re-fetch docs now, and again after a delay for child jobs
            setTimeout(() => refreshDocs(), 5000);
            return {
              ...upload,
              status: "complete",
              documentId: null,
              totalFiles,
              childJobIds,
            };
          }
          return { ...upload, status: "complete", documentId: null, totalFiles };
        }
        // Regular file — re-fetch docs to find the new document
        const freshDocs = (await listDocuments(caseId)) as DocRef[];
        const found = freshDocs.find((d) => d.name === upload.fileName);
        if (found) {
          return { ...upload, status: "complete", documentId: found.id };
        }
        // If doc not found by exact name, try the most recently created doc
        if (freshDocs.length > 0) {
          const newest = freshDocs.reduce((a, b) =>
            (a.id > b.id) ? a : b
          );
          return { ...upload, status: "complete", documentId: newest.id };
        }
        return { ...upload, status: "failed", error: "Document not found after ingest" };
      }
      if (job.status === "failed") {
        return { ...upload, status: "failed", error: job.error_message || "Ingestion failed" };
      }
      return upload; // still processing
    } catch {
      return upload;
    }
  }, [caseId, refreshDocs]);

  /* Start polling when uploads are added */
  useEffect(() => {
    const active = uploads.filter((u) => u.status === "processing");
    if (active.length === 0) return;

    let cancelled = false;
    let attempts = 0;
    const maxAttempts = 60; // 2 minutes at 2s intervals

    const poll = async () => {
      while (!cancelled && attempts < maxAttempts) {
        attempts++;
        await new Promise((r) => setTimeout(r, 2000));
        if (cancelled) return;

        const results = await Promise.all(
          active.map(async (u) => {
            const current = (await pollUpload(u));
            return current;
          }),
        );

        setUploads((prev) => {
          const updated = [...prev];
          for (const r of results) {
            const idx = updated.findIndex((u) => u.jobId === r.jobId);
            if (idx >= 0) updated[idx] = r;
          }
          return updated;
        });

        // If all are done, stop
        if (results.every((r) => r.status !== "processing")) return;
      }
    };

    poll();

    return () => { cancelled = true; };
  }, [uploads.length]); // eslint-disable-line react-hooks/exhaustive-deps

  /* When an upload completes, auto-attach and clean up */
  useEffect(() => {
    let changed = false;
    for (const u of uploads) {
      if (u.status === "complete" && u.documentId && !attachedIds.includes(u.documentId)) {
        onAttach(u.documentId, u.fileName);
        changed = true;
      }
    }
    if (changed) {
      // Clean single-file completes after 3s
      const timer = setTimeout(() => {
        setUploads((prev) => prev.filter((u) => u.status === "processing" || u.status === "extracting"));
      }, 3000);
      return () => clearTimeout(timer);
    }
    // Clean ZIP completes after 8s (give child jobs time)
    const zipComplete = uploads.filter((u) => u.status === "complete" && u.isZip);
    if (zipComplete.length > 0) {
      const timer = setTimeout(() => {
        setUploads((prev) => prev.filter((u) => !(u.status === "complete" && u.isZip)));
        refreshDocs();
      }, 8000);
      return () => clearTimeout(timer);
    }
  }, [uploads, attachedIds, onAttach, refreshDocs]);

  /* Handle file upload */
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    try {
      const result: any = await uploadFile(caseId, file);
      const isZip = result.is_zip === true;
      setUploads((prev) => [
        ...prev,
        {
          fileName: file.name,
          jobId: result.job_id,
          status: isZip ? "extracting" : "processing",
          documentId: null,
          error: null,
          isZip,
        },
      ]);
      // Keep dropdown open so user sees progress
    } catch {
      // silent
    }
  };

  /* Filter docs */
  const availableDocs = docs.filter((d) => !attachedIds.includes(d.id));
  const filtered = search.trim()
    ? availableDocs.filter((d) =>
        d.name.toLowerCase().includes(search.toLowerCase()),
      )
    : availableDocs;

  return (
    <div className="relative inline-flex items-center gap-1.5" ref={containerRef}>
      {/* Attach button — opens dropdown */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded
                   border border-border text-text-secondary
                   hover:border-brand hover:text-brand
                   transition-colors"
      >
        <Paperclip size={12} />
        Attach
      </button>

      {/* Direct upload button — always visible */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.docx,.txt,.csv,.xlsx,.jpg,.jpeg,.png,.zip,.md,.markdown"
        className="hidden"
        onChange={handleUpload}
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded
                   border border-border text-text-secondary
                   hover:border-brand hover:text-brand
                   transition-colors"
        title="Upload new document"
      >
        <Upload size={12} />
        Upload
      </button>

      {/* Upload progress chips */}
      {uploads.filter((u) => u.status === "processing" || u.status === "extracting").map((u) => (
        <span
          key={u.jobId}
          className="inline-flex items-center gap-1 text-[10px]
                     bg-surface-2 border border-border rounded px-1.5 py-0.5"
        >
          <Loader2 size={10} className="animate-spin text-text-disabled" />
          <span className="text-text-disabled truncate max-w-[100px]">
            {u.isZip ? `Extracting ${u.fileName}...` : u.fileName}
          </span>
        </span>
      ))}
      {uploads.filter((u) => u.status === "complete" && u.isZip).map((u) => (
        <span
          key={u.jobId}
          className="inline-flex items-center gap-1 text-[10px]
                     bg-success-bg text-success border border-success/20 rounded px-1.5 py-0.5"
        >
          <Check size={10} />
          <span className="truncate max-w-[150px]">
            {u.fileName} · {u.totalFiles || "?"} files
          </span>
        </span>
      ))}
      {uploads.filter((u) => u.status === "complete").map((u) => (
        <span
          key={u.jobId}
          className="inline-flex items-center gap-1 text-[10px]
                     bg-success-bg text-success border border-success/20 rounded px-1.5 py-0.5"
        >
          <Check size={10} />
          <span className="truncate max-w-[100px]">{u.fileName}</span>
        </span>
      ))}
      {uploads.filter((u) => u.status === "failed").map((u) => (
        <span
          key={u.jobId}
          className="inline-flex items-center gap-1 text-[10px]
                     bg-danger-bg text-danger border border-danger/20 rounded px-1.5 py-0.5"
          title={u.error || "Upload failed"}
        >
          <AlertCircle size={10} />
          <span className="truncate max-w-[100px]">{u.fileName}</span>
        </span>
      ))}

      {/* Dropdown — existing docs. Portaled to document.body with fixed
          positioning so it always escapes ancestor stacking contexts
          (e.g. overflow-auto tables) instead of rendering behind sticky
          siblings like the app header. */}
      {open && menuPos && createPortal(
        <div
          ref={menuRef}
          style={{ top: menuPos.top, left: menuPos.left, width: MENU_WIDTH, maxHeight: MENU_MAX_HEIGHT }}
          className="fixed bg-surface-1 border border-border rounded-lg shadow-lg
                     flex flex-col z-50"
        >
          {/* Search */}
          <div className="shrink-0 p-2 border-b border-border">
            <div className="relative">
              <Search
                size={12}
                className="absolute left-2 top-1/2 -translate-y-1/2 text-text-disabled pointer-events-none"
              />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search documents..."
                className="w-full bg-surface-2 border border-border rounded
                           pl-6 pr-6 py-1 text-xs text-text-primary
                           placeholder:text-text-disabled
                           focus:border-brand focus:ring-1 focus:ring-brand-ring focus:outline-none"
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  className="absolute right-1 top-1/2 -translate-y-1/2
                             text-text-disabled hover:text-text-secondary"
                >
                  <X size={10} />
                </button>
              )}
            </div>
          </div>

          {/* Doc list */}
          <div className="flex-1 overflow-y-auto">
            {loading ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 size={14} className="animate-spin text-text-disabled" />
              </div>
            ) : filtered.length === 0 ? (
              <div className="px-3 py-3 text-xs text-text-disabled text-center">
                {search ? "No matching documents" : "No documents available. Upload one first."}
              </div>
            ) : (
              filtered.map((doc) => (
                <button
                  key={doc.id}
                  onClick={() => {
                    onAttach(doc.id, doc.name);
                    setOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-left
                             hover:bg-surface-2 transition-colors text-xs"
                >
                  <Paperclip size={12} className="text-text-disabled shrink-0" />
                  <span className="flex-1 truncate">{doc.name}</span>
                  {doc.page_count != null && (
                    <span className="text-[10px] text-text-disabled shrink-0">
                      {doc.page_count}p
                    </span>
                  )}
                </button>
              ))
            )}
          </div>

          {/* Footer upload option */}
          <div className="shrink-0 border-t border-border p-1.5">
            <button
              onClick={() => fileInputRef.current?.click()}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded
                         text-xs text-text-secondary hover:text-brand
                         hover:bg-brand-bg transition-colors"
            >
              <Upload size={12} />
              Upload new...
            </button>
          </div>
        </div>,
        document.body,
      )}
    </div>
  );
}
