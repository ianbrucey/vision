"use client";

import { useState } from "react";
import {
  FileText, PenLine, Code2, Braces, ChevronDown, ChevronRight,
  Plus, FolderOpen,
} from "lucide-react";
import type { WorkspaceItemSummary, FileType } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface FileExplorerProps {
  items: WorkspaceItemSummary[];
  activeItemId: number | null;
  selectedFolder: string | null;
  onSelectItem: (id: number) => void;
  onSelectFolder: (folder: string | null) => void;
  onNewFile: (folder: string) => void;
}

/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */

const DEFAULT_FOLDERS = [
  { key: "freestyle", label: "Freestyle", icon: Code2 },
  { key: "research", label: "Research", icon: FolderOpen },
  { key: "artifacts", label: "Artifacts", icon: FolderOpen },
] as const;

const FILE_TYPE_ICON: Record<FileType, typeof FileText> = {
  markdown: FileText,
  structured_draft: PenLine,
  html: Code2,
  json_view: Braces,
};

const FILE_TYPE_BADGE: Record<FileType, string> = {
  markdown: "bg-info-bg text-info",
  structured_draft: "bg-brand-bg text-brand",
  html: "bg-warning-bg text-warning",
  json_view: "bg-success-bg text-success",
};

const FILE_TYPE_LABEL: Record<FileType, string> = {
  markdown: "note",
  structured_draft: "draft",
  html: "html",
  json_view: "insight",
};

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function FileExplorer({
  items,
  activeItemId,
  selectedFolder,
  onSelectItem,
  onSelectFolder,
  onNewFile,
}: FileExplorerProps) {
  // All folders expanded by default
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());

  const toggleFolder = (key: string) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const folderItems = (folderKey: string) =>
    items.filter((i) => i.folder === folderKey);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="hidden md:flex items-center justify-between px-4 py-3 border-b border-border">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wider">
          Workspace
        </h3>
      </div>

      {/* Folder tree */}
      <div className="flex-1 overflow-y-auto p-2">
        {DEFAULT_FOLDERS.map(({ key, label, icon: FolderIcon }) => {
          const isCollapsed = collapsed.has(key);
          const folderItemList = folderItems(key);
          return (
            <div key={key} className="mb-1">
              {/* Folder header */}
              <button
                onClick={() => {
                  toggleFolder(key);
                  onSelectFolder(selectedFolder === key ? null : key);
                }}
                className="w-full flex items-center gap-1.5 px-2 py-1.5 rounded-md
                           text-left hover:bg-surface-2 transition-colors group"
              >
                {isCollapsed ? (
                  <ChevronRight size={12} className="text-text-disabled" />
                ) : (
                  <ChevronDown size={12} className="text-text-disabled" />
                )}
                <FolderIcon size={14} className="text-text-secondary" />
                <span className="text-xs font-medium text-text-secondary flex-1">
                  {label}
                </span>
                <span className="text-[10px] text-text-disabled tabular-nums">
                  {folderItemList.length}
                </span>
                <span
                  role="button"
                  tabIndex={0}
                  aria-label={`New file in ${label}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    onNewFile(key);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      e.stopPropagation();
                      onNewFile(key);
                    }
                  }}
                  className="opacity-0 group-hover:opacity-100 text-text-disabled
                             hover:text-brand p-0.5 transition-all cursor-pointer"
                  title={`New file in ${label}`}
                >
                  <Plus size={12} />
                </span>
              </button>

              {/* Folder items */}
              {!isCollapsed && (
                <div className="ml-4">
                  {folderItemList.length === 0 ? (
                    <p className="text-[10px] text-text-disabled px-2 py-1 italic">
                      Empty
                    </p>
                  ) : (
                    folderItemList.map((item) => {
                      const Icon = FILE_TYPE_ICON[item.file_type] || FileText;
                      return (
                        <button
                          key={item.id}
                          onClick={() => onSelectItem(item.id)}
                          className={`w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md
                                      text-left transition-colors mb-0.5
                                      ${item.id === activeItemId
                                        ? "bg-brand-bg border border-brand/30"
                                        : "hover:bg-surface-2 border border-transparent"
                                      }`}
                        >
                          <Icon size={13} className="text-text-secondary shrink-0" />
                          <span className="text-xs truncate flex-1">
                            {item.name}
                          </span>
                          <span
                            className={`text-[9px] px-1 py-0.5 rounded-sm font-medium shrink-0
                                        ${FILE_TYPE_BADGE[item.file_type] || "bg-surface-2 text-text-disabled"}`}
                          >
                            {FILE_TYPE_LABEL[item.file_type] || item.file_type}
                          </span>
                        </button>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
