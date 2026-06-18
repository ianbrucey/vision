"use client";

import { useState, useEffect, useCallback, Suspense } from "react";
import { useParams, useRouter, useSearchParams, usePathname } from "next/navigation";
import { ArrowLeft } from "lucide-react";
import { getCase, updateCase } from "@/lib/api";
import { useAuth } from "@/components/AuthProvider";
import TabNav, { type TabId } from "./TabNav";
import OverviewTab from "./tabs/OverviewTab";
import ChatTab from "./tabs/ChatTab";
import DocumentsTab from "./tabs/DocumentsTab";
import DraftsTab from "./tabs/DraftsTab";
import WorkspaceTab from "./tabs/WorkspaceTab";
import CorrespondenceTab from "./tabs/CorrespondenceTab";
import TasksTab from "./tabs/TasksTab";
import CalendarTab from "./tabs/CalendarTab";
import FloatingChat, { FloatingChatButton } from "@/components/FloatingChat";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface Case {
  id: number;
  name: string;
  case_type: string;
  status: string;
  description: string | null;
  narrative: string | null;
  updated_at: string;
  created_at: string;
}

/* ------------------------------------------------------------------ */
/*  Inner component (after Suspense)                                    */
/* ------------------------------------------------------------------ */

function CaseDashboardInner() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const pathname = usePathname();
  const { user, logout } = useAuth();

  // Tab state lives in the URL — survives refresh
  const tabParam = searchParams.get("tab");
  const activeTab: TabId =
    tabParam === "chat" || tabParam === "documents" || tabParam === "drafts" || tabParam === "workspace" || tabParam === "correspondence" || tabParam === "tasks" || tabParam === "calendar"
      ? tabParam
      : "overview";

  const setActiveTab = (tab: TabId) => {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === "overview") {
      params.delete("tab");
    } else {
      params.set("tab", tab);
    }
    const qs = params.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  };

  const [case_, setCase] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);

  /* ---- data ---- */

  const loadCase = useCallback(async () => {
    const c = await getCase(Number(id));
    setCase(c as Case);
    setError(null);
    return c as Case;
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    /* eslint-disable react-hooks/set-state-in-effect */
    loadCase()
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Failed to load case");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    /* eslint-enable react-hooks/set-state-in-effect */
    return () => {
      cancelled = true;
    };
  }, [loadCase]);

  /* ---- actions ---- */

  const handleSaveNarrative = async (narrative: string): Promise<string> => {
    const updated = await updateCase(Number(id), { narrative });
    setCase((prev) =>
      prev ? { ...prev, narrative, updated_at: updated.updated_at } : prev,
    );
    return updated.updated_at as string;
  };

  /* ---- derived ---- */

  const caseTypeLabel = (t: string) => t.replace(/_/g, " ");
  const savedNarrative = case_?.narrative || "";
  const lastSavedAt = savedNarrative ? case_?.updated_at || null : null;

  /* ---- loading skeleton ---- */

  if (loading) {
    return (
      <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
        <header className="shrink-0 bg-surface-1 border-b border-border">
          <div className="flex items-center h-14 px-4 max-w-5xl mx-auto">
            <div className="h-5 bg-surface-3 rounded w-32 animate-pulse" />
          </div>
        </header>
        <div className="flex-1 p-4 md:p-6 max-w-3xl mx-auto space-y-4">
          <div className="h-16 bg-surface-3 rounded-lg animate-pulse" />
          <div className="h-40 bg-surface-3 rounded-lg animate-pulse" />
          <div className="grid grid-cols-2 gap-2">
            <div className="h-16 bg-surface-3 rounded-lg animate-pulse" />
            <div className="h-16 bg-surface-3 rounded-lg animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  /* ---- error ---- */

  if (error || !case_) {
    return (
      <div className="min-h-dvh bg-surface-0 text-text-primary flex items-center justify-center p-4">
        <div className="text-center max-w-sm">
          <div className="size-12 rounded-full bg-danger-bg flex items-center justify-center mx-auto mb-4">
            <span className="text-danger text-xl">!</span>
          </div>
          <p className="text-sm font-medium text-danger">
            {error || "Case not found"}
          </p>
          <button
            onClick={() => router.push("/")}
            className="mt-4 inline-flex items-center gap-2 text-sm text-info hover:text-brand transition-colors"
          >
            <ArrowLeft size={16} />
            Back to cases
          </button>
        </div>
      </div>
    );
  }

  /* ---- render ---- */

  return (
    <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
      {/* Header — sticky on mobile so it stays visible when scrolling */}
      <header className="sticky top-0 shrink-0 bg-surface-1 border-b border-border z-30">
        <div className="flex items-center h-14 px-4 gap-3 max-w-5xl mx-auto">
          <button
            onClick={() => router.push("/")}
            className="text-text-secondary hover:text-text-primary transition-colors shrink-0
                       min-h-[44px] min-w-[44px] flex items-center justify-center -ml-2"
            aria-label="Back to cases"
          >
            <ArrowLeft size={20} />
          </button>
          <div className="min-w-0">
            <h1 className="text-sm md:text-base font-semibold truncate">
              {case_.name}
            </h1>
            <p className="text-xs text-text-disabled hidden md:block">
              {caseTypeLabel(case_.case_type)}
            </p>
          </div>

          <div className="flex items-center gap-2 ml-auto shrink-0">
            <span className="text-xs px-2 py-0.5 rounded-sm bg-info-bg text-info hidden sm:inline">
              {case_.status}
            </span>
            {user && (
              <button
                onClick={logout}
                className="text-xs text-text-disabled hover:text-text-secondary transition-colors"
              >
                Sign out
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Tab Content — pb-14 on mobile clears the fixed bottom nav */}
      <div className="flex-1 flex flex-col overflow-hidden pb-14 md:pb-0 md:ml-[220px]">
        {activeTab === "overview" && (
          <OverviewTab
            key={`${case_.id}-${case_.updated_at}`}
            caseId={Number(id)}
            savedNarrative={savedNarrative}
            lastSavedAt={lastSavedAt}
            hasDocuments={(case_ as any).documents?.length > 0}
            existingParties={(case_ as any).parties || []}
            existingAllegations={(case_ as any).allegations || []}
            onSave={handleSaveNarrative}
            onNavigate={setActiveTab}
          />
        )}
        {activeTab === "chat" && (
          <ChatTab caseId={Number(id)} grounded={!!lastSavedAt} onNavigate={setActiveTab} />
        )}
        {activeTab === "documents" && <DocumentsTab caseId={Number(id)} />}
        {activeTab === "drafts" && <DraftsTab caseId={Number(id)} />}
        {activeTab === "workspace" && <WorkspaceTab caseId={Number(id)} />}
        {activeTab === "correspondence" && <CorrespondenceTab caseId={Number(id)} />}
        {activeTab === "tasks" && <TasksTab caseId={Number(id)} />}
        {activeTab === "calendar" && <CalendarTab caseId={Number(id)} />}
      </div>

      {/* Tab Navigation */}
      <TabNav activeTab={activeTab} onTabChange={setActiveTab} />

      {/* Floating chat — accessible from any tab except Chat */}
      {activeTab !== "chat" && (
        <FloatingChatButton onClick={() => setChatOpen(true)} />
      )}
      <FloatingChat
        caseId={Number(id)}
        open={chatOpen}
        onClose={() => setChatOpen(false)}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Page export (wraps inner in Suspense for useSearchParams)          */
/* ------------------------------------------------------------------ */

export default function CaseDashboardPage() {
  return (
    <Suspense
      fallback={
        <div className="h-dvh bg-surface-0 text-text-primary flex flex-col">
          <header className="shrink-0 bg-surface-1 border-b border-border">
            <div className="flex items-center h-14 px-4 max-w-5xl mx-auto">
              <div className="h-5 bg-surface-3 rounded w-32 animate-pulse" />
            </div>
          </header>
          <div className="flex-1 p-4 md:p-6 max-w-3xl mx-auto space-y-4">
            <div className="h-16 bg-surface-3 rounded-lg animate-pulse" />
            <div className="h-40 bg-surface-3 rounded-lg animate-pulse" />
          </div>
        </div>
      }
    >
      <CaseDashboardInner />
    </Suspense>
  );
}
