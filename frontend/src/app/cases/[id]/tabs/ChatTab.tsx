"use client";

import {
  useState, useEffect, useRef, type FormEvent,
} from "react";
import {
  AlertCircle, Send, PanelLeft, Mic, MicOff,
} from "lucide-react";
import type { TabId } from "../TabNav";
import SessionSidebar, { useSessionSidebarMobile } from "./SessionSidebar";
import ChatMessages from "./ChatMessages";
import { useChatSession } from "@/hooks/useChatSession";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface ChatTabProps {
  caseId: number;
  grounded: boolean;
  onNavigate: (tab: TabId) => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

const COLLAPSED_KEY = "vision_chat_sidebar_collapsed";

export default function ChatTab({ caseId, grounded, onNavigate }: ChatTabProps) {
  /* ---- chat state (shared hook) ---- */
  const chat = useChatSession(caseId);

  /* ---- voice recording (ChatTab-specific) ---- */
  const [recording, setRecording] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  /* ---- sidebar state ---- */
  const [collapsed, setCollapsed] = useState(() => {
    if (typeof window === "undefined") return false;
    return localStorage.getItem(COLLAPSED_KEY) === "true";
  });
  const { mobileOpen, openMobile, closeMobile } = useSessionSidebarMobile();

  /* Persist collapsed state */
  useEffect(() => {
    localStorage.setItem(COLLAPSED_KEY, String(collapsed));
  }, [collapsed]);

  /* ---- voice recording handlers ---- */

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        if (blob.size < 100) return;
        setRecording(false);
        chat.setInput((prev: string) => prev + " ");

        try {
          const form = new FormData();
          form.append("file", blob, "recording.webm");
          const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8400";
          const token = localStorage.getItem("vision_token");
          const res = await fetch(`${API_BASE}/api/chat/transcribe`, {
            method: "POST",
            body: form,
            headers: token ? { Authorization: `Bearer ${token}` } : {},
          });
          if (!res.ok) throw new Error("Transcription failed");
          const data = await res.json();
          chat.setInput((prev: string) =>
            prev.endsWith(" ") ? prev + data.text : prev + " " + data.text,
          );
        } catch { /* silent */ }
      };

      recorder.start();
      setRecording(true);
    } catch { /* mic denied */ }
  };

  const stopRecording = () => mediaRecorderRef.current?.stop();

  /* ---- send handler (wraps hook's handleSend for form event) ---- */
  const handleSend = (e?: FormEvent) => {
    e?.preventDefault();
    chat.handleSend(chat.input);
  };

  /* ================================================================ */
  /* Render                                                            */
  /* ================================================================ */

  return (
    <div className="flex-1 flex min-h-0">
      <SessionSidebar
        sessions={chat.sessions}
        activeSessionId={chat.activeSessionId}
        loading={chat.sessionsLoading}
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onSelect={(id) => {
          chat.setActiveSessionId(id);
          chat.setMessages([]);
        }}
        onNew={chat.handleNewSession}
        onArchive={chat.handleArchiveSession}
        onRename={chat.handleRenameSession}
        onToggleCollapse={() => setCollapsed((prev: boolean) => !prev)}
        onCloseMobile={closeMobile}
      />

      <div className="flex-1 flex flex-col min-h-0">
        {/* Grounding warning */}
        {!grounded && (
          <div className="shrink-0 bg-warning-bg border-b border-warning/20 px-4 py-2 flex items-center gap-2 text-xs text-warning">
            <AlertCircle size={14} />
            <span className="hidden sm:inline">Case not grounded — agent responses will be limited.</span>
            <span className="sm:hidden">Not grounded.</span>
            <button
              onClick={() => onNavigate("overview")}
              className="underline hover:text-warning/80 transition-colors shrink-0 ml-auto sm:ml-1"
            >
              Go to Overview
            </button>
          </div>
        )}

        {/* Desktop collapsed bar */}
        {collapsed && (
          <div className="hidden md:flex shrink-0 border-b border-border px-3 py-1.5 items-center gap-2 bg-surface-1">
            <button
              onClick={() => setCollapsed(false)}
              className="p-1 rounded text-text-disabled hover:text-text-secondary hover:bg-surface-2 transition-colors"
              title="Show sessions"
            >
              <PanelLeft size={16} />
            </button>
            {chat.activeSession && (
              <span className="text-xs text-text-secondary truncate flex-1 min-w-0">
                {chat.activeSession.title || `Chat ${chat.activeSession.id}`}
              </span>
            )}
            <button
              onClick={chat.handleNewSession}
              className="text-xs px-2 py-1 rounded-full bg-surface-2 text-text-secondary hover:bg-brand hover:text-white transition-colors shrink-0"
            >
              + New
            </button>
          </div>
        )}

        {/* Mobile session bar */}
        <div className="md:hidden shrink-0 border-b border-border px-3 py-1.5 flex items-center gap-2 bg-surface-1">
          <button
            onClick={openMobile}
            className="flex items-center gap-1.5 text-xs text-text-secondary hover:text-text-primary transition-colors px-2 py-1 rounded hover:bg-surface-2"
          >
            <PanelLeft size={14} />
            Sessions
          </button>
          {chat.activeSession && (
            <span className="text-xs text-text-secondary truncate flex-1 min-w-0">
              {chat.activeSession.title || `Chat ${chat.activeSession.id}`}
            </span>
          )}
          <button
            onClick={chat.handleNewSession}
            className="text-xs px-2 py-1 rounded-full bg-surface-2 text-text-secondary hover:bg-brand hover:text-white transition-colors shrink-0"
          >
            + New
          </button>
        </div>

        {/* Messages */}
        <ChatMessages
          messages={chat.messages}
          loading={chat.messagesLoading}
          streaming={chat.streaming}
          activeSession={chat.activeSession}
          grounded={grounded}
          onToggleTool={chat.toggleTool}
        />

        {/* Input */}
        <form
          onSubmit={handleSend}
          className="sticky bottom-0 shrink-0 border-t border-border p-3 md:p-4 bg-surface-0"
        >
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={chat.input}
              onChange={(e) => chat.setInput(e.target.value)}
              disabled={chat.streaming}
              className="flex-1 min-w-0 bg-surface-1 border border-border rounded-lg px-3 md:px-4 py-2.5
                         text-sm md:text-base placeholder:text-text-disabled
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         disabled:opacity-50"
              placeholder={
                chat.activeSession
                  ? "Ask the agent..."
                  : grounded ? "Create a session, then ask the agent..." : "Provide a case narrative first..."
              }
            />
            {chat.streaming ? (
              <button
                type="button"
                onClick={chat.handleCancel}
                className="bg-danger hover:bg-danger/80 text-white px-4 py-2.5 rounded-lg text-sm font-medium shrink-0 transition-colors"
              >
                Stop
              </button>
            ) : (
              <>
                <button
                  type="button"
                  onClick={recording ? stopRecording : startRecording}
                  className={`shrink-0 size-11 flex items-center justify-center rounded-lg transition-colors ${
                    recording
                      ? "bg-danger text-white animate-pulse"
                      : "bg-surface-2 text-text-secondary hover:bg-surface-3 hover:text-text-primary"
                  }`}
                  aria-label={recording ? "Stop recording" : "Start recording"}
                >
                  {recording ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
                <button
                  type="submit"
                  disabled={!chat.input.trim()}
                  className="bg-brand hover:bg-brand-hover active:bg-brand-active text-white
                             px-4 py-2.5 rounded-lg text-sm font-medium shrink-0
                             transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                             min-h-[44px] flex items-center gap-1.5"
                >
                  <Send size={16} />
                  <span className="hidden sm:inline">Send</span>
                </button>
              </>
            )}
          </div>
        </form>
      </div>
    </div>
  );
}
