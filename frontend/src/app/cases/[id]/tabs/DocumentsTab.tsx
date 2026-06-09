"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import {
  Upload,
  FileText,
  Check,
  Loader2,
  Clock,
  AlertCircle,
  X,
  ExternalLink,
  Trash2,
} from "lucide-react";
import { uploadFile, listDocuments, listJobs, deleteDocument } from "@/lib/api";
import DocumentPreviewModal from "@/components/DocumentPreviewModal";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Document {
  id: number;
  name: string;
  page_count: number | null;
  ocr_status: string;
  created_at: string;
}

interface Job {
  id: number;
  case_id: number;
  job_type: string;
  status: string;
  progress_pct: number;
  storage_ref: { original_name?: string } | null;
  error_message: string | null;
  completed_at: string | null;
  created_at: string;
}

interface UploadEntry {
  id: string; // local UUID for "uploading" phase, job ID string for server-tracked
  fileName: string;
  fileSize: number;
  status: "uploading" | "queued" | "processing" | "complete" | "failed";
  progress: number;
  jobId: number | null;
  error: string | null;
  /** True if this entry was recovered from server on mount (survived a refresh). */
  fromServer: boolean;
}

const DOCS_PER_PAGE = 5;
const POLL_INTERVAL = 3000;

/* ------------------------------------------------------------------ */
/*  Helpers                                                             */
/* ------------------------------------------------------------------ */

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

function jobToEntry(j: Job): UploadEntry {
  const ref = j.storage_ref;
  return {
    id: `job-${j.id}`,
    fileName: ref?.original_name || `Job #${j.id}`,
    fileSize: 0,
    status:
      j.status === "complete"
        ? "complete"
        : j.status === "failed"
          ? "failed"
          : j.status === "processing"
            ? "processing"
            : "queued",
    progress: j.progress_pct,
    jobId: j.id,
    error: j.error_message,
    fromServer: true,
  };
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface DocumentsTabProps {
  caseId: number;
}

export default function DocumentsTab({ caseId }: DocumentsTabProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [docPage, setDocPage] = useState(0);
  const [uploads, setUploads] = useState<UploadEntry[]>([]);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [previewDoc, setPreviewDoc] = useState<{
    id: number;
    name: string;
  } | null>(null);
  const [deleting, setDeleting] = useState<number | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  /* ---- fetch server state on mount ---- */

  const refreshServerState = useCallback(async () => {
    // Fetch documents
    try {
      const docs = (await listDocuments(caseId)) as Document[];
      setDocuments(docs);
    } catch { /* silent */ }

    // Fetch jobs — these survive refresh
    try {
      const jobs = (await listJobs({ case_id: caseId })) as Job[];
      const active = jobs.filter(
        (j) =>
          j.job_type === "ingest" &&
          (j.status === "queued" || j.status === "processing"),
      );
      const recentComplete = jobs.filter(
        (j) =>
          j.job_type === "ingest" &&
          j.status === "complete" &&
          j.completed_at &&
          new Date(j.completed_at).getTime() > Date.now() - 60_000, // last 60s
      );

      if (active.length > 0 || recentComplete.length > 0) {
        setUploads((prev) => {
          const existingIds = new Set(prev.map((u) => u.jobId).filter(Boolean));
          const merged = prev.filter((u) => u.status === "uploading"); // keep in-flight uploads
          for (const j of [...active, ...recentComplete]) {
            if (!existingIds.has(j.id)) {
              merged.push(jobToEntry(j));
            }
          }
          return merged;
        });
      }
    } catch { /* silent */ }
  }, [caseId]);

  useEffect(() => {
    refreshServerState();
  }, [refreshServerState]);

  /* ---- poll while active jobs exist ---- */

  const hasActive =
    uploads.filter(
      (u) =>
        u.status === "uploading" ||
        u.status === "queued" ||
        u.status === "processing",
    ).length > 0;

  useEffect(() => {
    if (!hasActive) {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
      return;
    }

    if (!pollRef.current) {
      pollRef.current = setInterval(async () => {
        try {
          const jobs = (await listJobs({ case_id: caseId })) as Job[];
          const jobMap = new Map(jobs.map((j) => [j.id, j]));

          setUploads((prev) => {
            const updated = prev.map((u) => {
              if (!u.jobId || !jobMap.has(u.jobId)) return u;
              const job = jobMap.get(u.jobId)!;
              let status: UploadEntry["status"] = u.status;
              if (job.status === "complete") status = "complete";
              else if (job.status === "failed") status = "failed";
              else if (job.status === "processing") status = "processing";
              else if (job.status === "queued") status = "queued";
              return {
                ...u,
                status,
                progress: job.progress_pct,
                error: job.error_message,
              };
            });

            // If everything just finished, refresh the documents list
            const justFinished =
              prev.some(
                (u) =>
                  u.status !== "complete" && u.status !== "failed",
              ) &&
              updated.every(
                (u) => u.status === "complete" || u.status === "failed",
              );
            if (justFinished) refreshServerState();

            return updated;
          });
        } catch { /* polling error — will retry */ }
      }, POLL_INTERVAL);
    }

    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, [hasActive, caseId, refreshServerState]);

  /* ---- upload handler ---- */

  const handleFiles = async (files: FileList | File[]) => {
    setUploadError(null);
    const fileArr = Array.from(files);
    if (fileArr.length === 0) return;

    // Create local "uploading" entries
    const localEntries: UploadEntry[] = fileArr.map((f) => ({
      id: crypto.randomUUID(),
      fileName: f.name,
      fileSize: f.size,
      status: "uploading" as const,
      progress: 0,
      jobId: null,
      error: null,
      fromServer: false,
    }));
    setUploads((prev) => [...prev, ...localEntries]);

    for (let i = 0; i < fileArr.length; i++) {
      const entry = localEntries[i];
      try {
        setUploads((prev) =>
          prev.map((u) =>
            u.id === entry.id
              ? { ...u, status: "uploading" as const, progress: 0 }
              : u,
          ),
        );
        const result = await uploadFile(caseId, fileArr[i]);
        setUploads((prev) =>
          prev.map((u) =>
            u.id === entry.id
              ? {
                  ...u,
                  status: "queued" as const,
                  jobId: result.job_id,
                  progress: 5,
                }
              : u,
          ),
        );
      } catch (err: unknown) {
        setUploads((prev) =>
          prev.map((u) =>
            u.id === entry.id
              ? {
                  ...u,
                  status: "failed" as const,
                  error:
                    err instanceof Error ? err.message : "Upload failed",
                }
              : u,
          ),
        );
      }
    }
  };

  /* ---- actions ---- */

  const removeUpload = (id: string) => {
    setUploads((prev) => prev.filter((u) => u.id !== id));
  };

  const handlePreview = (docId: number, docName: string) => {
    setPreviewDoc({ id: docId, name: docName });
  };

  const handleDelete = async (docId: number) => {
    setDeleting(docId);
    try {
      await deleteDocument(docId);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch { /* silent */ } finally {
      setDeleting(null);
    }
  };

  /* ---- pagination ---- */

  const totalPages = Math.ceil(documents.length / DOCS_PER_PAGE);
  const pageDocs = documents.slice(
    docPage * DOCS_PER_PAGE,
    (docPage + 1) * DOCS_PER_PAGE,
  );

  /* ---- render ---- */

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="px-4 py-4 md:py-6 md:max-w-3xl md:mx-auto space-y-4 md:space-y-6">

        {/* Upload zone */}
        <div>
          <h2 className="text-base font-semibold mb-3">Upload Documents</h2>
          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.csv,.xlsx,.jpg,.jpeg,.png,.m4a,.mp3,.wav,.ogg,.flac,.webm,.mp4"
            className="hidden"
            onChange={(e) => {
              if (e.target.files) handleFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full border-2 border-dashed border-border rounded-lg p-6 md:p-8 text-center
                       hover:border-brand active:border-brand
                       transition-colors cursor-pointer bg-transparent"
          >
            <Upload
              className="mx-auto mb-2 md:mb-3 text-text-disabled"
              size={32}
              strokeWidth={1.5}
            />
            <p className="text-sm">
              <span className="text-brand font-medium">Tap to upload</span>{" "}
              <span className="hidden sm:inline">or drag and drop</span>
            </p>
            <p className="text-xs text-text-disabled mt-1">
              PDF, DOCX, TXT, CSV, XLSX, images, audio — up to 50MB each
            </p>
          </button>
          {uploadError && (
            <p className="text-xs text-danger mt-2 flex items-center gap-1">
              <AlertCircle size={12} />
              {uploadError}
            </p>
          )}
        </div>

        {/* Upload queue */}
        {uploads.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-text-secondary mb-2">
              {hasActive
                ? `Processing — ${uploads.filter((u) => u.status !== "complete" && u.status !== "failed").length} of ${uploads.length} files`
                : `Complete — ${uploads.length} file${uploads.length > 1 ? "s" : ""}`}
            </h3>
            <div className="space-y-2">
              {uploads.map((u) => (
                <div
                  key={u.id}
                  className={`bg-surface-1 border rounded-lg p-3 ${
                    u.status === "failed"
                      ? "border-danger/30"
                      : u.status === "processing"
                        ? "border-warning/30"
                        : u.status === "complete"
                          ? "border-success/30"
                          : "border-border"
                  }`}
                >
                  <div className="flex items-center gap-3">
                    {u.status === "complete" && (
                      <Check size={16} className="text-success shrink-0" strokeWidth={2.5} />
                    )}
                    {u.status === "failed" && (
                      <AlertCircle size={16} className="text-danger shrink-0" />
                    )}
                    {u.status === "processing" && (
                      <Loader2 size={16} className="text-warning animate-spin shrink-0" />
                    )}
                    {(u.status === "uploading" || u.status === "queued") && (
                      <Clock size={16} className="text-text-disabled shrink-0" />
                    )}

                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{u.fileName}</p>
                      <p className="text-xs text-text-disabled">
                        {u.fileSize > 0 ? formatSize(u.fileSize) : ""}
                        {u.fromServer && (
                          <span className="ml-1 text-text-disabled/60">
                            · recovered
                          </span>
                        )}
                        {u.status === "failed" && u.error && (
                          <span className="text-danger ml-2">{u.error}</span>
                        )}
                      </p>
                    </div>

                    <span
                      className={`text-xs px-2 py-0.5 rounded-sm shrink-0 font-medium ${
                        u.status === "complete"
                          ? "bg-success-bg text-success"
                          : u.status === "failed"
                            ? "bg-danger-bg text-danger"
                            : u.status === "processing"
                              ? "bg-warning-bg text-warning"
                              : "bg-surface-2 text-text-disabled"
                      }`}
                    >
                      {u.status === "uploading"
                        ? "Uploading..."
                        : u.status === "queued"
                          ? "Queued"
                          : u.status === "processing"
                            ? `${u.progress}%`
                            : u.status === "failed"
                              ? "Failed"
                              : "Complete"}
                    </span>

                    {(u.status === "complete" || u.status === "failed") && (
                      <button
                        onClick={() => removeUpload(u.id)}
                        className="text-text-disabled hover:text-text-secondary transition-colors shrink-0"
                        aria-label="Dismiss"
                      >
                        <X size={14} />
                      </button>
                    )}
                  </div>

                  {u.status === "processing" && (
                    <div className="mt-2 w-full bg-surface-3 rounded-full h-1.5">
                      <div
                        className="bg-warning h-1.5 rounded-full transition-all duration-500"
                        style={{ width: `${u.progress}%` }}
                      />
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Ingested documents */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-sm font-medium text-text-secondary">
              Ingested{" "}
              <span className="text-text-disabled font-normal">
                · {documents.length}
              </span>
            </h3>
            {totalPages > 1 && (
              <span className="text-xs text-text-disabled">
                {docPage * DOCS_PER_PAGE + 1}–
                {Math.min((docPage + 1) * DOCS_PER_PAGE, documents.length)} of{" "}
                {documents.length}
              </span>
            )}
          </div>

          {documents.length === 0 ? (
            <div className="bg-surface-1 border border-border rounded-lg p-8 text-center">
              <FileText size={24} className="text-text-disabled mx-auto mb-2" />
              <p className="text-sm text-text-secondary">No documents yet</p>
              <p className="text-xs text-text-disabled mt-1">
                Upload files above to begin ingestion.
              </p>
            </div>
          ) : (
            <div className="bg-surface-1 border border-border rounded-lg divide-y divide-border">
              {pageDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="p-3 flex items-center gap-3 hover:bg-surface-2 transition-colors cursor-pointer"
                >
                  <FileText size={18} className="text-text-disabled shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{doc.name}</p>
                    <p className="text-xs text-text-disabled">
                      {doc.page_count != null
                        ? `${doc.page_count} pages`
                        : "—"}
                      {" · "}
                      {doc.ocr_status === "complete"
                        ? "Indexed"
                        : doc.ocr_status}
                      {" · "}
                      {formatDate(doc.created_at)}
                    </p>
                  </div>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-sm shrink-0 ${
                      doc.ocr_status === "complete"
                        ? "bg-success-bg text-success"
                        : "bg-warning-bg text-warning"
                    }`}
                  >
                    {doc.ocr_status === "complete" ? "Ready" : doc.ocr_status}
                  </span>
                  <div className="flex items-center gap-1 shrink-0">
                    {doc.ocr_status === "complete" && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handlePreview(doc.id, doc.name);
                        }}
                        className="text-xs px-2 py-1 rounded-sm border border-border text-info
                                   hover:bg-info-bg hover:border-info/30 active:bg-info-bg/50
                                   transition-colors inline-flex items-center gap-1 min-h-[28px]"
                      >
                        <ExternalLink size={12} />
                        Preview
                      </button>
                    )}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(doc.id);
                      }}
                      disabled={deleting === doc.id}
                      className="text-xs px-2 py-1 rounded-sm border border-danger/20 text-danger
                                 hover:bg-danger-bg active:bg-danger-bg/50
                                 disabled:opacity-50 transition-colors
                                 inline-flex items-center gap-1 min-h-[28px]"
                      aria-label="Delete document"
                    >
                      {deleting === doc.id ? (
                        <Loader2 size={12} className="animate-spin" />
                      ) : (
                        <Trash2 size={12} />
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-3">
              <span className="text-xs text-text-disabled">
                Page {docPage + 1} of {totalPages}
              </span>
              <div className="flex gap-1">
                <button
                  onClick={() => setDocPage((p) => Math.max(0, p - 1))}
                  disabled={docPage === 0}
                  className="text-xs px-3 py-1.5 rounded-sm border border-border
                             bg-surface-1 transition-colors min-h-[36px]
                             disabled:cursor-not-allowed disabled:text-text-disabled
                             text-text-secondary hover:bg-surface-2 active:bg-surface-3"
                >
                  Previous
                </button>
                <button
                  onClick={() =>
                    setDocPage((p) => Math.min(totalPages - 1, p + 1))
                  }
                  disabled={docPage >= totalPages - 1}
                  className="text-xs px-3 py-1.5 rounded-sm border border-border
                             bg-surface-1 transition-colors min-h-[36px]
                             disabled:cursor-not-allowed disabled:text-text-disabled
                             text-text-secondary hover:bg-surface-2 active:bg-surface-3"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Preview modal */}
      {previewDoc && (
        <DocumentPreviewModal
          docId={previewDoc.id}
          docName={previewDoc.name}
          open={!!previewDoc}
          onClose={() => setPreviewDoc(null)}
        />
      )}
    </div>
  );
}
