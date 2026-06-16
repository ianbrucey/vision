"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { FileText, Plus, Loader2, Trash2, Pencil } from "lucide-react";
import {
  listWorkspaceItems,
  getWorkspaceItem,
  createWorkspaceItem,
  updateWorkspaceItem,
  updateWorkspaceBlock,
  deleteWorkspaceItem,
  type WorkspaceItemSummary,
  type WorkspaceItemFull,
  type FileType,
  type Block,
} from "@/lib/api";
import FileExplorer from "@/components/FileExplorer";
import DraftPreview from "@/components/DraftPreview";
import MarkdownRenderer from "@/components/MarkdownRenderer";
import HtmlRenderer from "@/components/HtmlRenderer";
import JsonViewRenderer from "@/components/views/JsonViewRenderer";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface WorkspaceTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

/** Sync workspace state (item, folder) to URL without clobbering other params. */
function useWorkspaceUrl() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();

  const itemParam = searchParams.get("item");
  const folderParam = searchParams.get("folder");

  const setUrlParams = useCallback(
    (updates: { item?: number | null; folder?: string | null }) => {
      const params = new URLSearchParams(searchParams.toString());
      if (updates.item !== undefined) {
        if (updates.item !== null) params.set("item", String(updates.item));
        else params.delete("item");
      }
      if (updates.folder !== undefined) {
        if (updates.folder !== null) params.set("folder", updates.folder);
        else params.delete("folder");
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [searchParams, pathname, router],
  );

  return {
    initialItemId: itemParam ? Number(itemParam) : null,
    initialFolder: folderParam || null,
    setUrlParams,
  };
}

/** Extract markdown string from content (which may be array-wrapped from JSONB). */
function getMarkdownContent(content: unknown): { markdown: string } {
  // Content from API is a JSONB array: [{"markdown": "..."}]
  if (Array.isArray(content) && content.length > 0) {
    const first = content[0] as Record<string, unknown> | null;
    if (first && typeof first === "object" && "markdown" in first) {
      return { markdown: String(first.markdown || "") };
    }
    // Direct block array with markdown-like content
    if (first && typeof first === "object" && "content" in first) {
      return { markdown: String(first.content || "") };
    }
  }
  // Content might be the envelope directly: {"markdown": "..."}
  if (content && typeof content === "object" && !Array.isArray(content) && "markdown" in content) {
    return { markdown: String((content as Record<string, unknown>).markdown || "") };
  }
  return { markdown: "" };
}

/** Extract HTML string from content (for html file_type items). */
function getHtmlContent(content: unknown): string {
  // Content from API is a JSONB array: [{"html": "..."}]
  if (Array.isArray(content) && content.length > 0) {
    const first = content[0] as Record<string, unknown> | null;
    if (first && typeof first === "object" && "html" in first) {
      return String(first.html || "");
    }
  }
  // Content might be the envelope directly: {"html": "..."}
  if (content && typeof content === "object" && !Array.isArray(content) && "html" in content) {
    return String((content as Record<string, unknown>).html || "");
  }
  return "";
}

/** Extract Block array from content (for structured_draft items). */
function getBlocksContent(content: unknown): Block[] {
  if (Array.isArray(content)) {
    // Filter to items that have the Block shape
    return content.filter(
      (item): item is Block =>
        item != null &&
        typeof item === "object" &&
        "id" in item &&
        "type" in item &&
        "content" in item &&
        typeof (item as Block).type === "string",
    );
  }
  return [];
}

const formatDate = (iso: string) =>
  new Date(iso).toLocaleDateString(undefined, {
    month: "short", day: "numeric", hour: "numeric", minute: "2-digit",
  });

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function WorkspaceTab({ caseId }: WorkspaceTabProps) {
  const { initialItemId, initialFolder, setUrlParams } = useWorkspaceUrl();

  const [items, setItems] = useState<WorkspaceItemSummary[]>([]);
  const [activeItem, setActiveItem] = useState<WorkspaceItemFull | null>(null);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<"list" | "preview">("list");
  const [selectedFolder, setSelectedFolder] = useState<string | null>(initialFolder);
  const [showNewFileMenu, setShowNewFileMenu] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  /* ---- fetch ---- */

  const refreshList = useCallback(async () => {
    try {
      // Always fetch ALL items — folder filtering is visual only (in FileExplorer)
      const res = await listWorkspaceItems(caseId);
      setItems(res.items);
      setError(null);
      return res.items;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspace items");
      return [];
    }
  }, [caseId]);

  useEffect(() => {
    let cancelled = false;
    refreshList().then((list) => {
      if (cancelled) return;
      setLoading(false);
      if (list.length > 0 && !activeItem) {
        // Restore the item from URL, or default to the first item
        const targetId =
          initialItemId && list.some((i) => i.id === initialItemId)
            ? initialItemId
            : list[0].id;
        selectItem(targetId);
      }
    });
    return () => { cancelled = true; };
  }, [refreshList]);

  const selectItem = async (id: number) => {
    setContentLoading(true);
    setEditMode(false);
    setSaveStatus("idle");
    setUrlParams({ item: id });
    try {
      const res = await getWorkspaceItem(id);
      setActiveItem(res.item);
      if (window.innerWidth < 768) setMobileView("preview");
    } catch {
      refreshList();
    } finally {
      setContentLoading(false);
    }
  };

  /* ---- actions ---- */

  const handleNewFile = async (folder: string, fileType: FileType = "markdown") => {
    try {
      const content =
        fileType === "markdown"
          ? [{ markdown: "# Untitled\n\nStart writing..." }]
          : fileType === "structured_draft"
            ? [
                { id: "h1", type: "section_heading", content: "New Section" },
                { id: "p1", type: "numbered_paragraph", content: "Start writing here..." },
              ]
            : [];

      const res = await createWorkspaceItem({
        case_id: caseId,
        name: fileType === "markdown" ? "Untitled Note" : "Untitled Draft",
        file_type: fileType,
        folder,
        content,
      });
      await refreshList();
      setActiveItem(res.item);
      setEditMode(true);
      if (window.innerWidth < 768) setMobileView("preview");
      setShowNewFileMenu(null);
    } catch { /* silent */ }
  };

  const handleMarkdownChange = (markdown: string) => {
    if (!activeItem) return;
    setSaveStatus("idle");
    setActiveItem({
      ...activeItem,
      content: [{ markdown }] as unknown as WorkspaceItemFull["content"],
    });
  };

  /** Persist markdown content to the API. Returns true on success. */
  const persistMarkdown = async (item: WorkspaceItemFull): Promise<boolean> => {
    try {
      setSaveStatus("saving");
      await updateWorkspaceItem(item.id, {
        content: item.content,
      });
      setSaveStatus("saved");
      refreshList();
      return true;
    } catch (err) {
      console.error("Workspace save failed:", err);
      setSaveStatus("error");
      return false;
    }
  };

  const handleMarkdownSave = async () => {
    if (!activeItem) return;
    await persistMarkdown(activeItem);
  };

  /** Auto-save when the user leaves the editor (blur/defocus). */
  const handleMarkdownBlur = async () => {
    if (!activeItem || saveStatus !== "idle") return;
    await persistMarkdown(activeItem);
  };

  const handleBlockUpdate = async (blockId: string, content: string) => {
    if (!activeItem) return;
    await updateWorkspaceBlock(activeItem.id, blockId, content);
    setActiveItem((prev) => {
      if (!prev) return prev;
      const blocks = getBlocksContent(prev.content);
      return {
        ...prev,
        content: blocks.map((b) => (b.id === blockId ? { ...b, content } : b)),
      } as WorkspaceItemFull;
    });
    refreshList();
  };

  const handleDelete = async (itemId: number) => {
    await deleteWorkspaceItem(itemId);
    if (activeItem?.id === itemId) {
      setActiveItem(null);
      setUrlParams({ item: null });
    }
    await refreshList();
  };

  const handleStatusChange = async (status: string) => {
    if (!activeItem) return;
    await updateWorkspaceItem(activeItem.id, { status });
    setActiveItem((prev) => prev ? { ...prev, status } : prev);
    refreshList();
  };

  const handleNameChange = async (name: string) => {
    if (!activeItem) return;
    await updateWorkspaceItem(activeItem.id, { name });
    setActiveItem((prev) => prev ? { ...prev, name } : prev);
    refreshList();
  };

  /* ---- renderer dispatch ---- */

  const renderContent = () => {
    if (!activeItem) return null;

    switch (activeItem.file_type) {
      case "markdown":
        return (
          <MarkdownRenderer
            content={getMarkdownContent(activeItem.content)}
            editMode={editMode}
            onChange={handleMarkdownChange}
            onSave={handleMarkdownSave}
            onBlur={handleMarkdownBlur}
            saveStatus={saveStatus}
          />
        );
      case "structured_draft":
        return (
          <DraftPreview
            blocks={getBlocksContent(activeItem.content)}
            editMode={editMode}
            onBlockUpdate={handleBlockUpdate}
          />
        );
      case "html":
        return <HtmlRenderer html={getHtmlContent(activeItem.content)} />;
      case "json_view":
        return (
          <JsonViewRenderer
            content={activeItem.content}
            itemId={activeItem.id}
            editMode={editMode}
          />
        );
      default:
        return null;
    }
  };

  /* ---- loading ---- */
  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  /* ---- error ---- */
  if (error && items.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="text-center px-4">
          <p className="text-sm text-danger">{error}</p>
          <button onClick={refreshList} className="text-xs text-info mt-2">Retry</button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Mobile toolbar */}
      <div className="md:hidden shrink-0 bg-surface-1 border-b border-border px-4 py-2 flex items-center gap-2">
        {mobileView === "preview" ? (
          <button onClick={() => setMobileView("list")} className="text-sm text-text-secondary">
            ← Workspace
          </button>
        ) : (
          <span className="text-sm font-medium">Workspace</span>
        )}
        <div className="flex-1" />
        {mobileView === "preview" && activeItem && (
          <>
            {activeItem.file_type !== "html" && (
              <button
                onClick={() => setEditMode(!editMode)}
                className={`text-xs px-3 py-1 rounded-md font-medium ${
                  editMode ? "bg-brand text-white" : "bg-surface-2 text-text-secondary"
                }`}
              >
                {editMode ? "Done" : "Edit"}
              </button>
            )}
          </>
        )}
        <div className="relative">
          <button
            onClick={() => setShowNewFileMenu(showNewFileMenu ? null : "mobile")}
            className="text-brand p-1"
          >
            <Plus size={18} />
          </button>
          {showNewFileMenu === "mobile" && (
            <div className="absolute right-0 top-full mt-1 w-44 bg-surface-2 border border-border
                            rounded-lg shadow-lg z-40 py-1">
              <button
                onClick={() => handleNewFile("freestyle", "markdown")}
                className="w-full text-left px-3 py-2 text-xs hover:bg-surface-3"
              >
                📝 New Markdown Note
              </button>
              <button
                onClick={() => handleNewFile("artifacts", "structured_draft")}
                className="w-full text-left px-3 py-2 text-xs hover:bg-surface-3"
              >
                📄 New Structured Draft
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="flex-1 flex min-h-0">
        {/* File explorer sidebar */}
        <aside
          className={`w-[260px] flex-shrink-0 bg-surface-1 border-r border-border flex flex-col
                      overflow-hidden ${mobileView === "preview" ? "max-md:hidden" : "max-md:w-full max-md:border-r-0"}`}
        >
          {/* Desktop "New File" button */}
          <div className="hidden md:flex items-center justify-between px-4 py-3 border-b border-border">
            <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
              Workspace
            </h3>
            <div className="relative">
              <button
                onClick={() => setShowNewFileMenu(showNewFileMenu === "desktop" ? null : "desktop")}
                className="text-brand hover:text-brand-hover p-1"
                title="New file"
              >
                <Plus size={16} />
              </button>
              {showNewFileMenu === "desktop" && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-surface-2 border border-border
                                rounded-lg shadow-lg z-40 py-1">
                  <p className="text-[10px] text-text-disabled px-3 py-1.5 uppercase tracking-wider">
                    New File
                  </p>
                  <button
                    onClick={() => handleNewFile("freestyle", "markdown")}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-surface-3 flex items-center gap-2"
                  >
                    <FileText size={12} />
                    Markdown Note
                  </button>
                  <button
                    onClick={() => handleNewFile("artifacts", "structured_draft")}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-surface-3 flex items-center gap-2"
                  >
                    <Pencil size={12} />
                    Structured Draft
                  </button>
                </div>
              )}
            </div>
          </div>

          <FileExplorer
            items={items}
            activeItemId={activeItem?.id ?? null}
            selectedFolder={selectedFolder}
            onSelectItem={selectItem}
            onSelectFolder={(folder) => {
              setSelectedFolder(folder);
              setUrlParams({ folder });
            }}
            onNewFile={(folder) => handleNewFile(folder, "markdown")}
          />
        </aside>

        {/* Main viewport */}
        <main
          className={`flex-1 flex flex-col min-w-0 overflow-hidden ${mobileView === "list" ? "max-md:hidden" : ""}`}
        >
          {activeItem ? (
            <>
              {/* Desktop toolbar */}
              <div className="hidden md:flex shrink-0 items-center justify-between px-4 py-2
                              bg-surface-1 border-b border-border">
                <div className="min-w-0 mr-2">
                  <input
                    type="text"
                    value={activeItem.name}
                    onChange={(e) => {
                      setActiveItem({ ...activeItem, name: e.target.value });
                    }}
                    onBlur={(e) => handleNameChange(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") (e.target as HTMLInputElement).blur();
                    }}
                    className="text-sm font-semibold bg-transparent border-none outline-none
                               text-text-primary w-full min-w-0"
                  />
                  <p className="text-[10px] text-text-disabled">
                    {activeItem.file_type} · {activeItem.folder} · {activeItem.status} · updated {formatDate(activeItem.updated_at)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={activeItem.status}
                    onChange={(e) => handleStatusChange(e.target.value)}
                    className="text-[10px] bg-surface-2 border border-border rounded px-2 py-1
                               text-text-secondary cursor-pointer"
                  >
                    <option value="draft">Draft</option>
                    <option value="review">Review</option>
                    <option value="final">Final</option>
                  </select>
                  {activeItem.file_type !== "html" && (
                    <button
                      onClick={() => setEditMode(!editMode)}
                      className={`text-xs px-3 py-1 rounded font-medium transition-colors ${
                        editMode
                          ? "bg-brand text-white"
                          : "bg-surface-2 text-text-secondary hover:text-text-primary"
                      }`}
                    >
                      {editMode ? "Done" : "Edit"}
                    </button>
                  )}
                  <button
                    onClick={() => {
                      if (confirm("Delete this item?")) handleDelete(activeItem.id);
                    }}
                    className="text-text-disabled hover:text-danger p-1 transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Content area */}
              {contentLoading ? (
                <div className="flex-1 flex items-center justify-center">
                  <Loader2 className="animate-spin text-text-disabled" size={20} />
                </div>
              ) : (
                renderContent()
              )}
            </>
          ) : (
            /* Empty state */
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center px-4">
                <FileText size={32} className="text-text-disabled mx-auto mb-3 opacity-50" />
                <p className="text-sm text-text-secondary">No file selected</p>
                <p className="text-xs text-text-disabled mt-1">
                  {items.length === 0
                    ? "Create a file with the + button, or ask the agent in chat."
                    : "Select a file from the explorer."}
                </p>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
