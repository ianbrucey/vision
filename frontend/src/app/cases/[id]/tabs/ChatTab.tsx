"use client";

import {
  useState, useEffect, useRef, useCallback, type FormEvent,
} from "react";
import {
  AlertCircle, Send, Loader2, PanelLeft, Mic, MicOff,
} from "lucide-react";
import type { TabId } from "../TabNav";
import {
  listChatSessions, createChatSession, archiveChatSession, updateChatSession,
  getChatMessages, streamChatMessage,
  type ChatSession, type ChatMessage,
} from "@/lib/api";
import SessionSidebar, { useSessionSidebarMobile } from "./SessionSidebar";
import ChatMessages, { type UIMessage } from "./ChatMessages";

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
  /* ---- sessions ---- */
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  /* ---- messages ---- */
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  /* ---- input ---- */
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [recording, setRecording] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const streamCtrlRef = useRef<AbortController | null>(null);
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

  /* ================================================================ */
  /* Session management                                               */
  /* ================================================================ */

  const loadSessions = useCallback(async () => {
    try {
      const s = await listChatSessions(caseId);
      setSessions(s);
      if (s.length > 0 && !activeSessionId) {
        setActiveSessionId(s[0].id);
      }
    } catch {
      // sessions not yet available
    } finally {
      setSessionsLoading(false);
    }
  }, [caseId, activeSessionId]);

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  const handleNewSession = async () => {
    try {
      const { session_id } = await createChatSession(caseId);
      setMessages([]);
      setActiveSessionId(session_id);
      await loadSessions();
      inputRef.current?.focus();
    } catch (err) {
      console.error("Failed to create session", err);
    }
  };

  const handleArchiveSession = async (sid: number) => {
    await archiveChatSession(sid);
    if (activeSessionId === sid) {
      setActiveSessionId(null);
      setMessages([]);
    }
    await loadSessions();
  };

  const handleRenameSession = async (sid: number, title: string) => {
    try {
      await updateChatSession(sid, { title });
      setSessions((prev) =>
        prev.map((s) => (s.id === sid ? { ...s, title } : s)),
      );
    } catch (err) {
      console.error("Failed to rename session", err);
    }
  };

  /* ================================================================ */
  /* Message loading                                                   */
  /* ================================================================ */

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;
    setMessagesLoading(true);
    getChatMessages(activeSessionId)
      .then((msgs: ChatMessage[]) => {
        if (cancelled) return;
        const loaded: UIMessage[] = msgs.map((m) => ({
          role: m.role,
          content: m.content,
          sequence: m.sequence ?? null,
          toolName: m.tool_name || undefined,
          toolInputs: m.tool_inputs || undefined,
          toolResult: m.tool_result || undefined,
          timestamp: new Date(m.created_at),
        }));
        loaded.sort((a, b) => {
          const sa = a.sequence ?? Number.MAX_SAFE_INTEGER;
          const sb = b.sequence ?? Number.MAX_SAFE_INTEGER;
          return sa - sb;
        });
        setMessages(loaded);
      })
      .catch(() => {
        if (!cancelled) setMessages([]);
      })
      .finally(() => {
        if (!cancelled) setMessagesLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeSessionId]);

  /* ================================================================ */
  /* Send message                                                     */
  /* ================================================================ */

  const handleSend = async (e?: FormEvent) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    let sid = activeSessionId;
    if (!sid) {
      try {
        const { session_id } = await createChatSession(caseId);
        sid = session_id;
        setActiveSessionId(sid);
        await loadSessions();
      } catch {
        return;
      }
    }

    setInput("");
    const userMsg: UIMessage = {
      role: "user", content: text, sequence: null, timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setStreaming(true);

    const assistantMsg: UIMessage = {
      role: "assistant", content: "", sequence: null, timestamp: new Date(),
    };
    setMessages((prev) => [...prev, assistantMsg]);

    streamCtrlRef.current = streamChatMessage(
      sid,
      text,
      (event) => {
        setMessages((prev) => {
          const copy = [...prev];

          switch (event.type) {
            case "user_echo":
              for (let i = copy.length - 1; i >= 0; i--) {
                if (copy[i].role === "user" && copy[i].sequence === null) {
                  copy[i] = { ...copy[i], sequence: event.sequence ?? null };
                  break;
                }
              }
              break;

            case "assistant": {
              for (let i = copy.length - 1; i >= 0; i--) {
                if (copy[i].role === "assistant" && copy[i].sequence === null) {
                  copy[i] = {
                    ...copy[i],
                    content: copy[i].content + (event.content || ""),
                  };
                  break;
                }
              }
              break;
            }

            case "assistant_final":
              for (let i = copy.length - 1; i >= 0; i--) {
                if (copy[i].role === "assistant" && copy[i].sequence === null) {
                  copy[i] = { ...copy[i], sequence: event.sequence ?? null };
                  break;
                }
              }
              break;

            case "tool_call":
            case "tool_result":
              copy.push({
                role: event.type as "tool_call" | "tool_result",
                content: "",
                sequence: event.sequence ?? null,
                toolName: event.type === "tool_call" ? (event.name || "") : undefined,
                toolInputs: event.type === "tool_call" ? event.inputs : undefined,
                toolResult: event.type === "tool_result" ? event.content : undefined,
                toolExpanded: false,
                timestamp: new Date(),
              });
              break;

            case "status":
            case "init":
              break;

            case "done":
              break;

            case "error":
              copy.push({
                role: "error",
                content: event.message || "Unknown error",
                sequence: null,
                timestamp: new Date(),
              });
              break;
          }

          copy.sort((a, b) => {
            const sa = a.sequence ?? Number.MAX_SAFE_INTEGER;
            const sb = b.sequence ?? Number.MAX_SAFE_INTEGER;
            return sa - sb;
          });

          return copy;
        });
      },
      () => {
        setStreaming(false);
        loadSessions();
      },
      (err) => {
        setStreaming(false);
        setMessages((prev) => [
          ...prev,
          { role: "error", content: err, sequence: null, timestamp: new Date() },
        ]);
      },
    );
  };

  const handleCancel = () => {
    streamCtrlRef.current?.abort();
    setStreaming(false);
  };

  /* ---- voice recording ---- */

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
        setInput((prev) => prev + " ");

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
          setInput((prev) =>
            prev.endsWith(" ") ? prev + data.text : prev + " " + data.text,
          );
        } catch {
          // silently fail — user can still type
        }
      };

      recorder.start();
      setRecording(true);
    } catch {
      // mic permission denied or unavailable
    }
  };

  const stopRecording = () => {
    mediaRecorderRef.current?.stop();
  };

  /* ================================================================ */
  /* Toggle tool expansion                                             */
  /* ================================================================ */

  const toggleTool = (idx: number) => {
    setMessages((prev) => {
      const copy = [...prev];
      const msg = copy[idx];
      if (msg?.role === "tool_call") {
        copy[idx] = { ...msg, toolExpanded: !msg.toolExpanded };
      }
      return copy;
    });
  };

  /* ================================================================ */
  /* Derived                                                           */
  /* ================================================================ */

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  /* ================================================================ */
  /* Render                                                            */
  /* ================================================================ */

  return (
    <div className="flex-1 flex min-h-0">
      {/* Session sidebar */}
      <SessionSidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        loading={sessionsLoading}
        collapsed={collapsed}
        mobileOpen={mobileOpen}
        onSelect={(id) => {
          setActiveSessionId(id);
          setMessages([]);
        }}
        onNew={handleNewSession}
        onArchive={handleArchiveSession}
        onRename={handleRenameSession}
        onToggleCollapse={() => setCollapsed((prev) => !prev)}
        onCloseMobile={closeMobile}
      />

      {/* Main chat area */}
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

        {/* Desktop collapsed bar — only when sidebar is hidden */}
        {collapsed && (
          <div className="hidden md:flex shrink-0 border-b border-border px-3 py-1.5 items-center gap-2 bg-surface-1">
            <button
              onClick={() => setCollapsed(false)}
              className="p-1 rounded text-text-disabled hover:text-text-secondary
                         hover:bg-surface-2 transition-colors"
              title="Show sessions"
              aria-label="Show sessions"
            >
              <PanelLeft size={16} />
            </button>
            {activeSession && (
              <span className="text-xs text-text-secondary truncate flex-1 min-w-0">
                {activeSession.title || `Chat ${activeSession.id}`}
              </span>
            )}
            <button
              onClick={handleNewSession}
              className="text-xs px-2 py-1 rounded-full bg-surface-2 text-text-secondary
                         hover:bg-brand hover:text-white transition-colors shrink-0"
            >
              + New
            </button>
          </div>
        )}

        {/* Mobile session bar — always visible (sidebar is never inline on mobile) */}
        <div className="md:hidden shrink-0 border-b border-border px-3 py-1.5 flex items-center gap-2 bg-surface-1">
          <button
            onClick={openMobile}
            className="flex items-center gap-1.5 text-xs text-text-secondary
                       hover:text-text-primary transition-colors px-2 py-1 rounded
                       hover:bg-surface-2"
          >
            <PanelLeft size={14} />
            Sessions
          </button>
          {activeSession && (
            <span className="text-xs text-text-secondary truncate flex-1 min-w-0">
              {activeSession.title || `Chat ${activeSession.id}`}
            </span>
          )}
          <button
            onClick={handleNewSession}
            className="text-xs px-2 py-1 rounded-full bg-surface-2 text-text-secondary
                       hover:bg-brand hover:text-white transition-colors shrink-0"
          >
            + New
          </button>
        </div>

        {/* Messages */}
        <ChatMessages
          messages={messages}
          loading={messagesLoading}
          streaming={streaming}
          activeSession={activeSession}
          grounded={grounded}
          onToggleTool={toggleTool}
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
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={streaming}
              className="flex-1 min-w-0 bg-surface-1 border border-border rounded-lg px-3 md:px-4 py-2.5
                         text-sm md:text-base placeholder:text-text-disabled
                         focus:border-brand focus:ring-2 focus:ring-brand-ring focus:outline-hidden
                         disabled:opacity-50"
              placeholder={
                activeSession
                  ? "Ask the agent..."
                  : grounded
                    ? "Create a session, then ask the agent..."
                    : "Provide a case narrative first..."
              }
            />
            {streaming ? (
              <button
                type="button"
                onClick={handleCancel}
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
                  disabled={!input.trim()}
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
