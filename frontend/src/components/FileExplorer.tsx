"use client";

import { useState, useEffect, useCallback } from "react";
import { FileText, PenLine, Code2, Braces, ChevronRight, ChevronDown, FolderOpen, FolderPlus, FilePlus, Maximize2 } from "lucide-react";
import type { WorkspaceItemSummary, FileType, Folder } from "@/lib/api";
import { listFolders, createFolder } from "@/lib/api";

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
}

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const FILE_TYPE_ICON: Record<FileType, typeof FileText> = {
  markdown: FileText,
  structured_draft: PenLine,
  html: Code2,
  json_view: Braces,
};

const FILE_TYPE_LABEL: Record<FileType, string> = {
  markdown: "note",
  structured_draft: "draft",
  html: "html",
  json_view: "insight",
};

const FILE_TYPE_BADGE: Record<FileType, string> = {
  markdown: "bg-info-bg text-info",
  structured_draft: "bg-brand-bg text-brand",
  html: "bg-warning-bg text-warning",
  json_view: "bg-success-bg text-success",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function FileExplorer({
  items, activeItemId, caseId, workspaceId, workspaceName, workspaces,
  onSelectItem, onNewFile, onBrowse, onWorkspaceChange, onCreateWorkspace, refreshKey,
}: FileExplorerProps) {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [showNewMenu, setShowNewMenu] = useState<number | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [creatingInParent, setCreatingInParent] = useState<number | null>(null);

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
      setCreatingInParent(null);
      await loadFolders();
    } catch { /* silent */ }
  };

  /* ---- tree node rendering ---- */
  function renderTree(parentId: number | null, depth: number) {
    const childFolders = folders.filter(f => f.parent_id === parentId);
    // Items that belong directly to this folder (or root items if parentId is null)
    const levelItems = items.filter(i =>
      parentId === null
        ? (i.folder_id === null || i.folder_id === undefined)
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
              >
                {isOpen ? <ChevronDown size={10} className="text-[--text-disabled] shrink-0" />
                        : <ChevronRight size={10} className="text-[--text-disabled] shrink-0" />}
                <FolderOpen size={14} className="text-[--text-secondary] shrink-0" />
                <span className="flex-1 truncate text-[--text-primary] font-medium">{folder.name}</span>
                <span className="text-[9px] text-[--text-disabled]">{folderItems.length}</span>
                <button
                  onClick={(e) => { e.stopPropagation(); setShowNewMenu(showNewMenu === folder.id ? null : folder.id); }}
                  className="new-btn opacity-0 group-hover:opacity-100 text-[--text-disabled] hover:text-[--text-secondary] p-0.5"
                  title="Add to folder"
                >
                  <FilePlus size={11} />
                </button>
              </div>
              {showNewMenu === folder.id && (
                <div style={{ paddingLeft: `${12 + depth * 16 + 20}px` }} className="flex flex-col gap-0.5 py-1">
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
                    onKeyDown={e => { if (e.key === "Enter") handleCreateFolder(folder.id); if (e.key === "Escape") setCreatingInParent(null); }}
                    placeholder="Folder name..." autoFocus
                    className="text-[10px] bg-[--surface-2] border border-[--border] rounded px-2 py-0.5 w-full outline-none" />
                </div>
              )}
              {isOpen && (
                <>
                  {/* Items in this folder */}
                  {folderItems.map(item => renderFileItem(item, depth + 1))}
                  {/* Child folders (recursive) */}
                  {renderTree(folder.id, depth + 1)}
                </>
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
        className={`tree-item flex items-center gap-1 py-1 px-3 cursor-pointer hover:bg-[--surface-2] transition-colors text-xs ${isActive ? "bg-[--brand-bg] text-[--brand]" : "text-[--text-primary]"}`}
        style={{ paddingLeft: `${28 + depth * 16}px` }}
        onClick={() => onSelectItem(item.id)}
        title={item.name}
      >
        <Icon size={14} className="shrink-0" />
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
          <button onClick={() => setCreatingInParent(null)} title="New folder"
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
      {creatingInParent === null && (
        <div className="flex items-center gap-1 px-3 py-1 border-b border-[--border]">
          <input value={newFolderName} onChange={e => setNewFolderName(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter") handleCreateFolder(null); if (e.key === "Escape") setCreatingInParent(null); }}
            placeholder="New folder name..." autoFocus
            className="text-[10px] bg-[--surface-2] border border-[--border] rounded px-2 py-0.5 w-full outline-none" />
        </div>
      )}

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
            <div className="absolute left-12 top-full mt-0 bg-[--surface-4] border border-[--border] rounded-lg shadow-lg z-20 py-1 min-w-[140px]">
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
    </div>
  );
}
