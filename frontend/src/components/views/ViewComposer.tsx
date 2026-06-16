"use client";

import type { ViewEnvelope } from "./types";
import DynamicTable from "./DynamicTable";
import DynamicList from "./DynamicList";
import DynamicCards from "./DynamicCards";
import DynamicChart from "./DynamicChart";
import ViewSwitcher from "./ViewSwitcher";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface ViewComposerProps {
  envelope: ViewEnvelope;
  itemId: number;
  editMode: boolean;
  onContentChange: (updated: ViewEnvelope) => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

/**
 * Renders an array of views as scrollable sections.
 * Each section has a header (title + description + ViewSwitcher)
 * and the appropriate view renderer for its viewType.
 */
export default function ViewComposer({
  envelope,
  itemId,
  editMode,
  onContentChange,
}: ViewComposerProps) {
  const { views } = envelope;

  if (!views || views.length === 0) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-sm text-[--text-disabled]">No views</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      {views.map((view, i) => (
        <section
          key={`view-${i}`}
          className="rounded-lg border border-[--border] bg-[--surface-1] overflow-hidden"
        >
          {/* Section header */}
          <header className="px-4 py-3 border-b border-[--border] bg-[--surface-2] flex items-center justify-between gap-2">
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-[--text-primary] truncate">
                {view.title}
              </h2>
              {view.description && (
                <p className="text-sm text-[--text-secondary] truncate">
                  {view.description}
                </p>
              )}
            </div>
            <ViewSwitcher
              view={view}
              viewIndex={i}
              itemId={itemId}
              envelope={envelope}
              onSwitch={onContentChange}
            />
          </header>

          {/* View content */}
          <div className="p-4">
            <ViewRenderer
              view={view}
              viewIndex={i}
              itemId={itemId}
              editMode={editMode}
              envelope={envelope}
              onContentChange={onContentChange}
            />
          </div>
        </section>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Internal: single-view dispatcher                                   */
/* ------------------------------------------------------------------ */

interface ViewRendererProps {
  view: ViewEnvelope["views"][number];
  viewIndex: number;
  itemId: number;
  editMode: boolean;
  envelope: ViewEnvelope;
  onContentChange: (updated: ViewEnvelope) => void;
}

function ViewRenderer({
  view,
  viewIndex,
  itemId,
  editMode,
  envelope,
  onContentChange,
}: ViewRendererProps) {
  switch (view.viewType) {
    case "table":
      return (
        <DynamicTable
          view={view}
          viewIndex={viewIndex}
          itemId={itemId}
          editMode={editMode}
          envelope={envelope}
          onContentChange={onContentChange}
        />
      );
    case "list":
      return (
        <DynamicList
          view={view}
          viewIndex={viewIndex}
          itemId={itemId}
          editMode={editMode}
          envelope={envelope}
          onContentChange={onContentChange}
        />
      );
    case "cards":
      return (
        <DynamicCards
          view={view}
          viewIndex={viewIndex}
          itemId={itemId}
          editMode={editMode}
          envelope={envelope}
          onContentChange={onContentChange}
        />
      );
    case "chart":
      return <DynamicChart view={view} />;
    default:
      return (
        <p className="text-sm text-[--text-disabled]">
          Unknown view type: {(view as { viewType: string }).viewType}
        </p>
      );
  }
}
