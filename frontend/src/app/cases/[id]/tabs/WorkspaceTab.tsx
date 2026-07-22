"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { FileText, FilePlus, Plus, Check, X, Loader2, Trash2, Pencil } from "lucide-react";
import {
  listWorkspaces,
  createWorkspace,
  listWorkspaceItems,
  getWorkspaceItem,
  createWorkspaceItem,
  updateWorkspaceItem,
  updateWorkspaceBlock,
  deleteWorkspaceItem,
  type Workspace,
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
import PdfRenderer from "@/components/PdfRenderer";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface WorkspaceTabProps {
  caseId: number;
}

/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */

/** Sync workspace state (item, folder, workspace) to URL without clobbering other params. */
function useWorkspaceUrl() {
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const router = useRouter();

  const itemParam = searchParams.get("item");
  const folderParam = searchParams.get("folder");
  const wsParam = searchParams.get("ws");

  const setUrlParams = useCallback(
    (updates: { item?: number | null; folder?: string | null; ws?: number | null }) => {
      const params = new URLSearchParams(searchParams.toString());
      if (updates.item !== undefined) {
        if (updates.item !== null) params.set("item", String(updates.item));
        else params.delete("item");
      }
      if (updates.folder !== undefined) {
        if (updates.folder !== null) params.set("folder", updates.folder);
        else params.delete("folder");
      }
      if (updates.ws !== undefined) {
        if (updates.ws !== null) params.set("ws", String(updates.ws));
        else params.delete("ws");
      }
      const qs = params.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [searchParams, pathname, router],
  );

  return {
    initialItemId: itemParam ? Number(itemParam) : null,
    initialFolder: folderParam || null,
    initialWsId: wsParam ? Number(wsParam) : null,
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
  const { initialItemId, initialFolder, initialWsId, setUrlParams } = useWorkspaceUrl();

  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<number | null>(initialWsId);
  const [items, setItems] = useState<WorkspaceItemSummary[]>([]);
  const [activeTabId, setActiveTabId] = useState<number | null>(initialItemId);
  const [openTabIds, setOpenTabIds] = useState<number[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem(`vision_workspace_tabs_${caseId}`);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed) && parsed.length > 0) {
            if (initialItemId && !parsed.includes(initialItemId)) {
              return [...parsed, initialItemId];
            }
            return parsed;
          }
        }
      } catch (e) {}
    }
    return initialItemId ? [initialItemId] : [];
  });
  const [openItemsData, setOpenItemsData] = useState<Record<number, WorkspaceItemFull>>({});

  useEffect(() => {
    localStorage.setItem(`vision_workspace_tabs_${caseId}`, JSON.stringify(openTabIds));
  }, [openTabIds, caseId]);
  const [loading, setLoading] = useState(true);
  const [contentLoading, setContentLoading] = useState(false);
  const [editMode, setEditMode] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mobileView, setMobileView] = useState<"list" | "preview">("list");
  const [selectedFolder, setSelectedFolder] = useState<string | null>(initialFolder);
  const [showNewFileMenu, setShowNewFileMenu] = useState<string | null>(null);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [explorerRefreshKey, setExplorerRefreshKey] = useState(0);

  /* ---- fetch ---- */

  const refreshList = useCallback(async () => {
    try {
      const [wsRes, itemRes] = await Promise.all([
        listWorkspaces(caseId),
        listWorkspaceItems(caseId),
      ]);
      setWorkspaces(wsRes.workspaces);
      // Restore from URL or default to first workspace
      if (!activeWorkspaceId && wsRes.workspaces.length > 0) {
        const restored = initialWsId && wsRes.workspaces.some(w => w.id === initialWsId)
          ? initialWsId
          : wsRes.workspaces[0].id;
        setActiveWorkspaceId(restored);
        setUrlParams({ ws: restored });
      }
      setItems(itemRes.items);
      setError(null);
      return itemRes.items;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load workspace items");
      return [];
    }
  }, [caseId, activeWorkspaceId]);

  // Shim to keep existing code working smoothly
  const activeItem = activeTabId ? openItemsData[activeTabId] : null;

  const setActiveItem = (itemOrUpdater: WorkspaceItemFull | null | ((prev: WorkspaceItemFull | null) => WorkspaceItemFull | null)) => {
    if (!activeTabId) return;
    setOpenItemsData(prev => {
        const prevItem = prev[activeTabId] || null;
        const newItem = typeof itemOrUpdater === 'function' ? itemOrUpdater(prevItem) : itemOrUpdater;
        if (!newItem) {
            const next = { ...prev };
            delete next[activeTabId];
            return next;
        }
        return { ...prev, [activeTabId]: newItem };
    });
  };

  useEffect(() => {
    let cancelled = false;
    refreshList().then((list) => {
      if (cancelled) return;
      setLoading(false);
      if (list.length > 0) {
        if (activeTabId && !openItemsData[activeTabId]) {
          // We know the ID but haven't fetched its full content yet
          selectItem(activeTabId);
        } else if (!activeTabId) {
          // No active tab set, default to the last opened tab, or the first item
          let targetId = list[0].id;
          if (openTabIds.length > 0 && list.some(i => i.id === openTabIds[openTabIds.length - 1])) {
            targetId = openTabIds[openTabIds.length - 1];
          }
          selectItem(targetId);
        }
      }
    });
    return () => { cancelled = true; };
  }, [refreshList]);

  // Listen for agent background updates
  useEffect(() => {
    const handleWorkspaceUpdated = async () => {
      // Re-fetch the file list and tree
      setExplorerRefreshKey(k => k + 1);
      await refreshList();
      // Silently re-fetch the active file's full content so the preview updates
      if (activeTabId) {
        try {
          const res = await getWorkspaceItem(activeTabId);
          setOpenItemsData(prev => ({...prev, [activeTabId]: res.item}));
        } catch { /* silent */ }
      }
    };

    window.addEventListener("vision_workspace_updated", handleWorkspaceUpdated);
    return () => {
      window.removeEventListener("vision_workspace_updated", handleWorkspaceUpdated);
    };
  }, [refreshList, activeTabId]);

  const selectItem = async (id: number) => {
    setEditMode(false);
    setSaveStatus("idle");
    setUrlParams({ item: id });
    
    setOpenTabIds(prev => prev.includes(id) ? prev : [...prev, id]);
    setActiveTabId(id);

    if (!openItemsData[id]) {
      setContentLoading(true);
      try {
        const res = await getWorkspaceItem(id);
        setOpenItemsData(prev => ({...prev, [id]: res.item}));
      } catch {
        refreshList();
      } finally {
        setContentLoading(false);
      }
    } else {
      if (window.innerWidth < 768) setMobileView("preview");
    }
  };

  const closeTab = (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setOpenTabIds(prev => {
      const next = prev.filter(tid => tid !== id);
      if (activeTabId === id) {
        const newActive = next.length > 0 ? next[next.length - 1] : null;
        setActiveTabId(newActive);
        setUrlParams({ item: newActive });
      }
      return next;
    });
  };

  /* ---- actions ---- */

  const handleNewFile = async (folderId: number | null, fileType: FileType = "markdown") => {
    try {
      const content =
        fileType === "markdown"
          ? [{ markdown: "# Untitled\n\nStart writing..." }]
          : fileType === "structured_draft"
            ? [
                { id: "h1", type: "section_heading", content: "New Section" },
                { id: "p1", type: "numbered_paragraph", content: "Start writing here..." },
              ]
            : fileType === "json_view"
              ? [{ documentMetadata: { title: "Untitled" }, views: [] }]
              : fileType === "html"
                ? [{ html: "<!DOCTYPE html><html><body></body></html>" }]
                : [];

      const res = await createWorkspaceItem({
        case_id: caseId,
        name: fileType === "markdown" ? "Untitled Note"
            : fileType === "structured_draft" ? "Untitled Draft"
            : fileType === "json_view" ? "Untitled Insight"
            : "Untitled Letter",
        file_type: fileType,
        folder: "artifacts",  // deprecated but still required by API
        folder_id: folderId,
        content,
        workspace_id: activeWorkspaceId,
      });
      const newId = res.item.id;
      setOpenTabIds(prev => prev.includes(newId) ? prev : [...prev, newId]);
      setOpenItemsData(prev => ({...prev, [newId]: res.item}));
      setActiveTabId(newId);
      setEditMode(true);
      if (window.innerWidth < 768) setMobileView("preview");
      setShowNewFileMenu(null);
      // Refresh explorer list AFTER state is settled to avoid duplicate rendering
      setExplorerRefreshKey(k => k + 1);
      refreshList();
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
    
    setOpenTabIds(prev => {
      const next = prev.filter(tid => tid !== itemId);
      if (activeTabId === itemId) {
        const newActive = next.length > 0 ? next[next.length - 1] : null;
        setActiveTabId(newActive);
        setUrlParams({ item: newActive });
      }
      return next;
    });
    
    setOpenItemsData(prev => {
      const next = {...prev};
      delete next[itemId];
      return next;
    });
    
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
            key={`md-${activeItem.id}`}
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
            key={`draft-${activeItem.id}`}
            blocks={getBlocksContent(activeItem.content)}
            editMode={editMode}
            onBlockUpdate={handleBlockUpdate}
            onBlocksChange={async (newBlocks) => {
              if (!activeItem) return;
              await updateWorkspaceItem(activeItem.id, { content: newBlocks });
              setActiveItem({ ...activeItem, content: newBlocks });
            }}
            onMetadataChange={async (newMeta) => {
              if (!activeItem) return;
              await updateWorkspaceItem(activeItem.id, { metadata: newMeta });
              setActiveItem({ ...activeItem, metadata: newMeta });
            }}
            documentType={activeItem.document_type}
            metadata={activeItem.metadata}
          />
        );
      case "html":
        return <HtmlRenderer key={`html-${activeItem.id}`} html={getHtmlContent(activeItem.content)} />;
      case "pdf":
        return <PdfRenderer key={`pdf-${activeItem.id}`} content={activeItem.content} />;
      case "json_view":
        return (
          <JsonViewRenderer
            key={`json-${activeItem.id}`}
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
            <FilePlus size={18} />
          </button>
          {showNewFileMenu === "mobile" && (
            <div className="absolute right-0 top-full mt-1 w-44 bg-surface-2 border border-border
                            rounded-lg shadow-lg z-40 py-1">
              <button
                onClick={() => handleNewFile(null, "markdown")}
                className="w-full text-left px-3 py-2 text-xs hover:bg-surface-3"
              >
                📝 New Markdown Note
              </button>
              <button
                onClick={() => handleNewFile(null, "structured_draft")}
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
          <FileExplorer
            items={Array.from(
              new Map(
                items
                  .filter(i => i.workspace_id === activeWorkspaceId || i.workspace_id === null)
                  .map(i => [i.id, i])
              ).values()
            )}
            activeItemId={activeItem?.id ?? null}
            caseId={caseId}
            workspaceId={activeWorkspaceId}
            workspaceName={workspaces.find(w => w.id === activeWorkspaceId)?.name || "Main"}
            workspaces={workspaces}
            onSelectItem={selectItem}
            onNewFile={(folderId, fileType) => handleNewFile(folderId, fileType)}
            onBrowse={() => {/* TODO: FolderBrowserModal */}}
            onWorkspaceChange={(id) => { setActiveWorkspaceId(id); setUrlParams({ ws: id }); }}
            onCreateWorkspace={async (name) => {
              try {
                const result = await createWorkspace(caseId, name);
                setActiveWorkspaceId(result.id);
                setUrlParams({ ws: result.id });
                await refreshList();
              } catch { /* silent */ }
            }}
            refreshKey={explorerRefreshKey}
          />
        </aside>

        {/* Main viewport */}
        <main
          className={`flex-1 flex flex-col min-w-0 overflow-hidden ${mobileView === "list" ? "max-md:hidden" : ""}`}
        >
          {openTabIds.length > 0 && (
            <div className="flex flex-row overflow-x-auto bg-surface-1 border-b border-border shrink-0 hide-scrollbar">
              {openTabIds.map(id => {
                const summary = items.find(i => i.id === id) || openItemsData[id];
                const isActive = activeTabId === id;
                return (
                  <div
                    key={id}
                    onClick={() => selectItem(id)}
                    className={`flex items-center gap-2 px-3 py-2 cursor-pointer border-r border-border min-w-[120px] max-w-[200px] group transition-colors ${
                      isActive 
                        ? 'bg-surface-2 border-t-2 border-t-brand text-text-primary' 
                        : 'bg-surface-1 text-text-secondary hover:bg-surface-2 border-t-2 border-t-transparent'
                    }`}
                  >
                    <FileText size={12} className={isActive ? "text-brand" : "text-text-disabled"} />
                    <span className="text-xs truncate flex-1 font-medium">{summary?.name || "Loading..."}</span>
                    <button
                      onClick={(e) => closeTab(id, e)}
                      className={`p-0.5 rounded hover:bg-surface-3 transition-colors ${isActive ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}
                    >
                      <X size={12} className="text-text-secondary hover:text-text-primary" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}

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
