"use client";

import { useState, useEffect, useCallback } from "react";
import { FileText, PenLine, Code2, Braces, ChevronRight, ChevronDown, FolderOpen, FolderPlus, FilePlus, Maximize2, Trash2, Paperclip } from "lucide-react";
import type { WorkspaceItemSummary, FileType, Folder, DocumentSummary } from "@/lib/api";
import { listFolders, createFolder, deleteFolder, deleteWorkspaceItem } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface FileExplorerProps {
  items: WorkspaceItemSummary[];
  activeItemId: number | null;
  caseId: number;
  workspaceId: number | null;
  workspaceName: string;
  workspaces: { id: number; name: string }[];
  onSelectItem: (id: number) => void;
  onNewFile: (folderId: number | null, fileType: FileType) => void;
  onBrowse: () => void;
  onWorkspaceChange: (id: number) => void;
  onCreateWorkspace: (name: string) => void;
  refreshKey: number;
  // Uploaded documents
  documents: DocumentSummary[];
  activeDocumentId: number | null;
  onSelectDocument: (docId: number) => void;
}

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const FILE_TYPE_ICON: Record<FileType, typeof FileText> = {
  markdown: FileText,
  structured_draft: PenLine,
  html: Code2,
  json_view: Braces,
  pdf: FileText,
};

const FILE_TYPE_LABEL: Record<FileType, string> = {
  markdown: "note",
  structured_draft: "draft",
  html: "html",
  json_view: "insight",
  pdf: "pdf",
};

const FILE_TYPE_BADGE: Record<FileType, string> = {
  markdown: "bg-info-bg text-info",
  structured_draft: "bg-brand-bg text-brand",
  html: "bg-warning-bg text-warning",
  json_view: "bg-success-bg text-success",
  pdf: "bg-info-bg text-info",
};

const FILE_TYPE_ICON_COLOR: Record<FileType, string> = {
  markdown: "text-info",
  structured_draft: "text-brand",
  html: "text-warning",
  json_view: "text-success",
  pdf: "text-info",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function FileExplorer({
  items, activeItemId, caseId, workspaceId, workspaceName, workspaces,
  onSelectItem, onNewFile, onBrowse, onWorkspaceChange, onCreateWorkspace, refreshKey,
  documents, activeDocumentId, onSelectDocument,
}: FileExplorerProps) {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [docsExpanded, setDocsExpanded] = useState(false);  // default collapsed
  const expandedKey = `vision_explorer_expanded_${caseId}_${workspaceId}`;
  const [expanded, setExpanded] = useState<Set<number>>(() => {
    try {
      const saved = localStorage.getItem(expandedKey);
      if (saved) return new Set<number>(JSON.parse(saved));
    } catch { /* silent */ }
    return new Set<number>();
  });
  const [showNewMenu, setShowNewMenu] = useState<number | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [creatingInParent, setCreatingInParent] = useState<number | 'root' | false>(false);
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; type: 'folder' | 'file'; id: number } | null>(null);

  // Close context menu when clicking outside
  useEffect(() => {
    const closeContextMenu = () => setContextMenu(null);
    window.addEventListener("click", closeContextMenu);
    return () => window.removeEventListener("click", closeContextMenu);
  }, []);

  // Persist expanded folders to localStorage whenever they change
  useEffect(() => {
    try {
      localStorage.setItem(expandedKey, JSON.stringify([...expanded]));
    } catch { /* silent */ }
  }, [expanded, expandedKey]);

  const loadFolders = useCallback(async () => {
    try {
      const res = await listFolders(caseId, null, workspaceId);
      setFolders(res.folders);
    } catch { /* silent */ }
  }, [caseId, workspaceId]);

  useEffect(() => { loadFolders(); }, [loadFolders, refreshKey]);

  const toggleExpand = (id: number) => {
    setExpanded(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleCreateFolder = async (parentId: number | null) => {
    if (!newFolderName.trim()) return;
    try {
      await createFolder(caseId, newFolderName.trim(), parentId, workspaceId);
      setNewFolderName("");
      setCreatingInParent(false);
      await loadFolders();
    } catch { /* silent */ }
  };

  const handleDeleteFolder = async (folderId: number) => {
    if (!window.confirm("Are you sure you want to delete this folder? ALL files and subfolders inside it will be permanently deleted.")) return;
    try {
      await deleteFolder(folderId);
      await loadFolders();
      window.dispatchEvent(new Event("vision_workspace_updated"));
    } catch { /* silent */ }
  };

  const handleDeleteFile = async (itemId: number) => {
    if (!window.confirm("Are you sure you want to delete this file?")) return;
    try {
      await deleteWorkspaceItem(itemId);
      window.dispatchEvent(new Event("vision_workspace_updated"));
    } catch { /* silent */ }
  };

  const handleContextMenu = (e: React.MouseEvent, type: 'folder' | 'file', id: number) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, type, id });
  };

  /* ---- tree node rendering ---- */
  function renderTree(parentId: number | null, depth: number) {
    const childFolders = folders.filter(f => f.parent_id === parentId);
    // Items that belong directly to this folder (or root items if parentId is null)
    const levelItems = items.filter(i =>
      parentId === null
        ? !i.folder_id  // null, undefined, or 0 all mean root
        : i.folder_id === parentId
    );

    return (
      <>
        {childFolders.map(folder => {
          const isOpen = expanded.has(folder.id);
          // Items inside this specific folder
          const folderItems = items.filter(i => i.folder_id === folder.id);
          return (
            <div key={`f-${folder.id}`}>
              <div
                className="tree-item flex items-center gap-1 py-1 px-3 cursor-pointer hover:bg-[--surface-2] transition-colors text-xs group"
                style={{ paddingLeft: `${12 + depth * 16}px` }}
                onClick={() => toggleExpand(folder.id)}
                onContextMenu={(e) => handleContextMenu(e, 'folder', folder.id)}
              >
                {isOpen ? <ChevronDown size={10} className="text-text-disabled shrink-0" />
                        : <ChevronRight size={10} className="text-text-disabled shrink-0" />}
                <FolderOpen size={14} className="text-brand shrink-0 opacity-80" />
                <span className="flex-1 truncate text-text-primary font-medium">{folder.name}</span>
                <span className="text-[9px] text-[--text-disabled]">{folderItems.length}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowNewMenu(showNewMenu === folder.id ? null : folder.id); }}
                  className="new-btn opacity-0 group-hover:opacity-100 text-[--text-disabled] hover:text-[--text-secondary] p-0.5 ml-auto"
                  title="Add to folder"
                >
                  <FilePlus size={11} />
                </button>
                <button
                  onClick={(e) => { e.stopPropagation(); handleDeleteFolder(folder.id); }}
                  className="delete-btn opacity-0 group-hover:opacity-100 text-[--text-disabled] hover:text-red-500 p-0.5 ml-1"
                  title="Delete folder"
                >
                  <Trash2 size={11} />
                </button>
              </div>
              {showNewMenu === folder.id && (
                <div style={{ paddingLeft: `${12 + depth * 16 + 20}px` }} className="bg-surface-1 flex flex-col gap-0.5 py-1">
                  <button onClick={() => { onNewFile(folder.id, "markdown"); setShowNewMenu(null); }}
                    className="text-left text-[10px] px-2 py-1 hover:bg-[--surface-2] rounded text-[--text-secondary]">📝 Note</button>
                  <button onClick={() => { onNewFile(folder.id, "structured_draft"); setShowNewMenu(null); }}
                    className="text-left text-[10px] px-2 py-1 hover:bg-[--surface-2] rounded text-[--text-secondary]">📄 Draft</button>
                  <button onClick={() => { onNewFile(folder.id, "json_view"); setShowNewMenu(null); }}
                    className="text-left text-[10px] px-2 py-1 hover:bg-[--surface-2] rounded text-[--text-secondary]">📊 Insight</button>
                  <button onClick={() => { setCreatingInParent(folder.id); setShowNewMenu(null); }}
                    className="text-left text-[10px] px-2 py-1 hover:bg-[--surface-2] rounded text-[--text-secondary]">📁 Subfolder</button>
                </div>
              )}
              {creatingInParent === folder.id && (
                <div style={{ paddingLeft: `${12 + depth * 16 + 20}px` }} className="flex items-center gap-1 px-3 py-1">
                  <input value={newFolderName} onChange={e => setNewFolderName(e.target.value)}
                    onKeyDown={e => { if (e.key === "Enter") handleCreateFolder(folder.id); if (e.key === "Escape") setCreatingInParent(false); }}
                    placeholder="Folder name..." autoFocus
                    className="text-[10px] bg-[--surface-2] border border-[--border] rounded px-2 py-0.5 w-full outline-none" />
                </div>
              )}
              {isOpen && (
                <div className="relative">
                  {/* Vertical tree line */}
                  <div 
                    className="absolute top-0 bottom-0 border-l border-border/60" 
                    style={{ left: `${12 + depth * 16 + 5}px` }} 
                  />
                  {/* Recursive: renders child folders AND items at this level */}
                  {renderTree(folder.id, depth + 1)}
                </div>
              )}
            </div>
          );
        })}

        {/* Items at this level (no parent folder, or root-level items) */}
        {levelItems.map(item => renderFileItem(item, depth))}
      </>
    );
  }

  function renderFileItem(item: WorkspaceItemSummary, depth: number) {
    const Icon = FILE_TYPE_ICON[item.file_type] || FileText;
    const isActive = item.id === activeItemId;
    return (
      <div
        key={`item-${item.id}`}
        className={`tree-item flex items-center gap-1.5 py-1 px-3 cursor-pointer transition-colors text-xs border-l-2 ${isActive ? "bg-brand-bg/50 border-brand text-brand" : "border-transparent text-text-primary hover:bg-surface-2"}`}
        style={{ paddingLeft: `${28 + depth * 16}px` }}
        onClick={() => onSelectItem(item.id)}
        onContextMenu={(e) => handleContextMenu(e, 'file', item.id)}
        title={item.name}
      >
        <Icon size={14} className={`shrink-0 ${FILE_TYPE_ICON_COLOR[item.file_type] || 'text-text-secondary'} ${isActive ? 'opacity-100' : 'opacity-70'}`} />
        <span className="flex-1 truncate">{item.name}</span>
        <span className={`text-[9px] px-1 py-0.5 rounded-sm font-medium shrink-0 ${FILE_TYPE_BADGE[item.file_type] || ""}`}>
          {FILE_TYPE_LABEL[item.file_type] || item.file_type}
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header — workspace selector + actions */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[--border] gap-1">
        <select
          value={workspaceId ?? ""}
          onChange={(e) => {
            const v = e.target.value;
            if (v === "__new__") {
              const name = prompt("Workspace name:");
              if (name?.trim()) onCreateWorkspace(name.trim());
            } else {
              onWorkspaceChange(Number(v));
            }
          }}
          className="text-[10px] font-semibold bg-transparent border-none text-[--text-secondary] uppercase tracking-wider cursor-pointer min-w-0 truncate flex-1"
        >
          {workspaces.map(ws => (
            <option key={ws.id} value={ws.id}>{ws.name}</option>
          ))}
          <option value="__new__">+ New Workspace</option>
        </select>
        <div className="flex items-center gap-0.5 shrink-0">
          <button onClick={() => setCreatingInParent('root')} title="New folder"
            className="text-[--text-disabled] hover:text-[--text-secondary] p-0.5">
            <FolderPlus size={14} />
          </button>
          <button onClick={onBrowse} title="Browse all files"
            className="text-[--text-disabled] hover:text-[--text-secondary] p-0.5">
            <Maximize2 size={14} />
          </button>
        </div>
      </div>

      {/* New root folder input */}
      {creatingInParent === 'root' && (
        <div className="flex items-center gap-1 px-3 py-1 border-b border-[--border]">
          <input value={newFolderName} onChange={e => setNewFolderName(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") handleCreateFolder(null); if (e.key === "Escape") setCreatingInParent(false); }}
            placeholder="New folder name..." autoFocus
            className="text-[10px] bg-[--surface-2] border border-[--border] rounded px-2 py-0.5 w-full outline-none" />
        </div>
      )}

      {/* Uploaded Documents — top, default collapsed */}
      <div className="border-b border-[--border]">
        <button
          onClick={() => setDocsExpanded(!docsExpanded)}
          className="flex items-center gap-1.5 w-full px-3 py-1.5 text-xs text-[--text-secondary] hover:text-[--text-primary] transition-colors"
        >
          {docsExpanded ? <ChevronDown size={10} className="text-text-disabled shrink-0" />
                        : <ChevronRight size={10} className="text-text-disabled shrink-0" />}
          <Paperclip size={12} className="text-text-disabled shrink-0" />
          <span className="flex-1 text-left font-medium">Uploaded Documents</span>
          <span className="text-[9px] text-[--text-disabled]">{documents.length}</span>
        </button>
        {docsExpanded && documents.length > 0 && (
          <div className="pb-1">
            {documents.map(doc => {
              const isActive = doc.id === activeDocumentId;
              const isPdf = doc.document_type === "pdf" || doc.name?.toLowerCase().endsWith(".pdf");
              const isDocx = doc.document_type === "docx" || doc.name?.toLowerCase().endsWith(".docx");
              const icon = isPdf ? "📄" : isDocx ? "📝" : "📎";
              return (
                <div
                  key={`doc-${doc.id}`}
                  onClick={() => onSelectDocument(doc.id)}
                  className={`tree-item flex items-center gap-1.5 py-1 px-3 cursor-pointer transition-colors text-xs border-l-2 ml-2 ${
                    isActive
                      ? "bg-brand-bg/50 border-brand text-brand"
                      : "border-transparent text-text-primary hover:bg-surface-2"
                  }`}
                >
                  <span className="shrink-0 text-[11px]">{icon}</span>
                  <span className="flex-1 truncate">{doc.name}</span>
                  {doc.page_count != null && (
                    <span className="text-[9px] text-[--text-disabled] shrink-0">{doc.page_count}p</span>
                  )}
                </div>
              );
            })}
          </div>
        )}
        {docsExpanded && documents.length === 0 && (
          <div className="pb-2 px-3">
            <p className="text-[10px] text-text-disabled ml-4">No documents uploaded yet.</p>
          </div>
        )}
      </div>

      {/* Tree */}
      <div className="flex-1 overflow-y-auto py-1">
        {/* Root-level new file button */}
        <div className="flex items-center gap-1 px-3 py-1 relative group">
          <button onClick={() => setShowNewMenu(showNewMenu === -1 ? null : -1)}
            className="tree-item flex items-center gap-1 py-1 text-xs text-[--text-disabled] hover:text-[--text-secondary] transition-colors w-full text-left">
            <FilePlus size={12} />
            <span>New file</span>
          </button>
          {showNewMenu === -1 && (
            <div className="absolute left-0 top-full mt-1 bg-surface-1 border border-border rounded-lg shadow-xl z-50 py-1 min-w-[160px]">
              <button onClick={() => { onNewFile(null, "markdown"); setShowNewMenu(null); }}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-[--surface-2] text-[--text-primary]">📝 Note</button>
              <button onClick={() => { onNewFile(null, "structured_draft"); setShowNewMenu(null); }}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-[--surface-2] text-[--text-primary]">📄 Draft</button>
              <button onClick={() => { onNewFile(null, "json_view"); setShowNewMenu(null); }}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-[--surface-2] text-[--text-primary]">📊 Insight</button>
              <button onClick={() => { onNewFile(null, "html"); setShowNewMenu(null); }}
                className="w-full text-left px-3 py-1.5 text-xs hover:bg-[--surface-2] text-[--text-primary]">📄 HTML Letter</button>
            </div>
          )}
        </div>
        {renderTree(null, 0)}
      </div>

      {/* Context Menu */}
      {contextMenu && (
        <div
          className="fixed z-50 bg-surface-1 border border-border rounded-lg shadow-xl flex flex-col py-1 text-[11px] min-w-[150px]"
          style={{ top: contextMenu.y, left: contextMenu.x }}
          onClick={(e) => e.stopPropagation()}
        >
          {contextMenu.type === 'folder' ? (
            <>
              <button 
                onClick={() => { setShowNewMenu(contextMenu.id); setContextMenu(null); }} 
                className="text-left px-3 py-1.5 hover:bg-surface-2 text-text-primary flex items-center gap-2"
              >
                <FilePlus size={12}/> Add to folder
              </button>
              <div className="h-px bg-border my-1" />
              <button 
                onClick={() => { handleDeleteFolder(contextMenu.id); setContextMenu(null); }} 
                className="text-left px-3 py-1.5 hover:bg-surface-2 text-red-500 flex items-center gap-2"
              >
                <Trash2 size={12}/> Delete folder
              </button>
            </>
          ) : (
            <>
              <button 
                onClick={() => { handleDeleteFile(contextMenu.id); setContextMenu(null); }} 
                className="text-left px-3 py-1.5 hover:bg-surface-2 text-red-500 flex items-center gap-2"
              >
                <Trash2 size={12}/> Delete file
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}
