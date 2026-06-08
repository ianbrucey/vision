"use client";

import {
  useState, useEffect, useRef, useCallback, type FormEvent,
} from "react";
import ReactMarkdown from "react-markdown";
import { AlertCircle, MessageCircle, Plus, Send, Loader2, Wrench, ChevronDown, ChevronRight, Trash2 } from "lucide-react";
import type { TabId } from "../TabNav";
import {
  listChatSessions, createChatSession, archiveChatSession,
  getChatMessages, streamChatMessage,
  type ChatSession, type ChatMessage,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Props                                                              */
/* ------------------------------------------------------------------ */

interface ChatTabProps {
  caseId: number;
  grounded: boolean;
  onNavigate: (tab: TabId) => void;
}

/* ------------------------------------------------------------------ */
/* Types for local UI state                                           */
/* ------------------------------------------------------------------ */

interface UIMessage {
  role: "user" | "assistant" | "tool_call" | "tool_result" | "system" | "error";
  content: string;
  sequence: number | null;  // DB sequence — null until saved; sort key
  toolName?: string;
  toolInputs?: unknown;
  toolResult?: unknown;
  toolExpanded?: boolean;
  timestamp: Date;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function ChatTab({ caseId, grounded, onNavigate }: ChatTabProps) {
  /* sessions */
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [sessionsLoading, setSessionsLoading] = useState(true);

  /* messages */
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  /* input */
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const streamCtrlRef = useRef<AbortController | null>(null);

  /* ---------------------------------------------------------------- */
  /* Session management                                               */
  /* ---------------------------------------------------------------- */

  const loadSessions = useCallback(async () => {
    try {
      const s = await listChatSessions(caseId);
      setSessions(s);
      // Auto-select first session, or show empty state
      if (s.length > 0 && !activeSessionId) {
        setActiveSessionId(s[0].id);
      }
    } catch {
      // sessions not yet available (backend down / table missing)
    } finally {
      setSessionsLoading(false);
    }
  }, [caseId, activeSessionId]);

  useEffect(() => { /* eslint-disable react-hooks/set-state-in-effect */ loadSessions(); /* eslint-enable react-hooks/set-state-in-effect */ }, [loadSessions]);

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

  /* ---------------------------------------------------------------- */
  /* Message loading                                                   */
  /* ---------------------------------------------------------------- */

  useEffect(() => {
    if (!activeSessionId) return;
    let cancelled = false;
    /* eslint-disable react-hooks/set-state-in-effect */
    setMessagesLoading(true);
    /* eslint-enable react-hooks/set-state-in-effect */
    getChatMessages(activeSessionId)
      .then((msgs: ChatMessage[]) => {
        if (cancelled) return;
        const loaded = msgs.map(m => ({
          role: m.role,
          content: m.content,
          sequence: m.sequence ?? null,
          toolName: m.tool_name || undefined,
          toolInputs: m.tool_inputs || undefined,
          toolResult: m.tool_result || undefined,
          timestamp: new Date(m.created_at),
        }));
        // Sort by sequence; missing sequences go last
        loaded.sort((a, b) => {
          const sa = a.sequence ?? Number.MAX_SAFE_INTEGER;
          const sb = b.sequence ?? Number.MAX_SAFE_INTEGER;
          return sa - sb;
        });
        setMessages(loaded);
      })
      .catch(() => { if (!cancelled) setMessages([]); })
      .finally(() => { if (!cancelled) setMessagesLoading(false); });
    return () => { cancelled = true; };
  }, [activeSessionId]);

  /* auto-scroll */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* ---------------------------------------------------------------- */
  /* Send message                                                     */
  /* ---------------------------------------------------------------- */

  const handleSend = async (e?: FormEvent) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    let sid = activeSessionId;
    // Auto-create session if needed
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
    const userMsg: UIMessage = { role: "user", content: text, sequence: null, timestamp: new Date() };
    setMessages(prev => [...prev, userMsg]);
    setStreaming(true);

    // Placeholder for streaming assistant message
    const assistantMsg: UIMessage = { role: "assistant", content: "", sequence: null, timestamp: new Date() };
    setMessages(prev => [...prev, assistantMsg]);

    streamCtrlRef.current = streamChatMessage(
      sid,
      text,
      (event) => {
        setMessages(prev => {
          const copy = [...prev];

          switch (event.type) {
            case "user_echo":
              // Stamp the user message with its DB sequence
              for (let i = copy.length - 1; i >= 0; i--) {
                if (copy[i].role === "user" && copy[i].sequence === null) {
                  copy[i] = { ...copy[i], sequence: event.sequence ?? null };
                  break;
                }
              }
              break;

            case "assistant": {
              // Streaming delta — append to the assistant placeholder
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
              // Stamp the assistant placeholder with its DB sequence
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
                role: "error", content: event.message || "Unknown error",
                sequence: null, timestamp: new Date(),
              });
              break;
          }

          // Sort by sequence — unsequenced messages (deltas mid-stream) float to end
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
        // Reload sessions to pick up auto-title
        loadSessions();
      },
      (err) => {
        setStreaming(false);
        setMessages(prev => [...prev, { role: "error", content: err, sequence: null, timestamp: new Date() }]);
      },
    );
  };

  const handleCancel = () => {
    streamCtrlRef.current?.abort();
    setStreaming(false);
  };

  /* ---------------------------------------------------------------- */
  /* Toggle tool expansion                                             */
  /* ---------------------------------------------------------------- */

  const toggleTool = (idx: number) => {
    setMessages(prev => {
      const copy = [...prev];
      const msg = copy[idx];
      if (msg?.role === "tool_call") {
        copy[idx] = { ...msg, toolExpanded: !msg.toolExpanded };
      }
      return copy;
    });
  };

  /* ---------------------------------------------------------------- */
  /* Render: session list                                              */
  /* ---------------------------------------------------------------- */

  const activeSession = sessions.find(s => s.id === activeSessionId);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
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

      {/* Session bar */}
      <div className="shrink-0 border-b border-border px-3 py-1.5 flex items-center gap-2 overflow-x-auto bg-surface-1">
        {sessionsLoading ? (
          <span className="text-xs text-text-disabled">Loading sessions...</span>
        ) : sessions.length === 0 ? (
          <span className="text-xs text-text-disabled">No sessions yet.</span>
        ) : (
          sessions.map(s => (
            <div key={s.id} className="group flex items-center shrink-0">
              <button
                onClick={() => { setActiveSessionId(s.id); setMessages([]); }}
                className={`text-xs px-2.5 py-1 rounded-full transition-colors whitespace-nowrap max-w-[160px] truncate ${
                  s.id === activeSessionId
                    ? "bg-brand text-white"
                    : "bg-surface-2 text-text-secondary hover:bg-surface-3"
                }`}
                title={s.title || `Session ${s.id}`}
              >
                {s.title || `Chat ${s.id}`}
              </button>
              <button
                onClick={() => handleArchiveSession(s.id)}
                className="ml-0.5 opacity-0 group-hover:opacity-100 text-text-disabled hover:text-danger transition-all p-0.5"
                title="Archive"
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))
        )}
        <button
          onClick={handleNewSession}
          className="text-xs px-2 py-1 rounded-full bg-surface-2 text-text-secondary hover:bg-brand hover:text-white transition-colors flex items-center gap-1 shrink-0"
          title="New session"
        >
          <Plus size={12} />
          <span className="hidden sm:inline">New</span>
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 md:px-4 py-3 space-y-3">
        {messagesLoading ? (
          <div className="flex items-center justify-center h-full">
            <Loader2 className="animate-spin text-text-disabled" size={24} />
          </div>
        ) : messages.length === 0 ? (
          /* Empty state */
          <div className="flex items-center justify-center h-full">
            <div className="text-center px-4">
              <div className="size-12 rounded-full bg-surface-3 flex items-center justify-center mx-auto mb-3">
                <MessageCircle className="text-text-disabled" size={24} strokeWidth={1.5} />
              </div>
              <p className="text-sm text-text-secondary font-medium">
                {activeSession ? "Start the conversation" : "Create a session to begin"}
              </p>
              <p className="text-xs text-text-disabled mt-1">
                {grounded
                  ? "Ask the agent about your case evidence, strategy, or documents."
                  : "Provide a case narrative in Overview to get started."}
              </p>
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] md:max-w-[75%] rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-brand text-white"
                  : msg.role === "error"
                    ? "bg-danger-bg text-danger border border-danger/20"
                    : msg.role === "tool_call" || msg.role === "tool_result"
                      ? "bg-surface-2 border border-border text-text-secondary"
                      : "bg-surface-1 border border-border text-text-primary"
              }`}>
                {/* Tool call */}
                {msg.role === "tool_call" && (
                  <button
                    onClick={() => toggleTool(i)}
                    className="flex items-center gap-1.5 w-full text-left"
                  >
                    {msg.toolExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                    <Wrench size={12} />
                    <span className="font-mono text-xs">{msg.toolName}</span>
                  </button>
                )}
                {msg.role === "tool_call" && msg.toolExpanded && (
                  <pre className="mt-1.5 text-xs bg-surface-3 rounded p-1.5 overflow-x-auto max-h-32">
                    {JSON.stringify(msg.toolInputs, null, 2)}
                  </pre>
                )}

                {/* Tool result */}
                {msg.role === "tool_result" && (
                  <details className="text-xs">
                    <summary className="cursor-pointer text-text-disabled hover:text-text-secondary">
                      Tool result
                    </summary>
                    <pre className="mt-1 bg-surface-3 rounded p-1.5 overflow-x-auto max-h-40 text-xs">
                      {typeof msg.toolResult === "string"
                        ? msg.toolResult.slice(0, 2000)
                        : JSON.stringify(msg.toolResult, null, 2).slice(0, 2000)}
                    </pre>
                  </details>
                )}

                {/* Assistant / user / error content */}
                {msg.role === "assistant" && (
                  <div className="wrap-break-word prose prose-sm max-w-none prose-table:text-sm prose-td:border prose-td:border-border prose-td:px-2 prose-td:py-1 prose-th:bg-surface-2 prose-th:px-2 prose-th:py-1 prose-th:font-semibold">
                    {msg.content ? (
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    ) : streaming ? (
                      <span className="inline-flex items-center gap-1 text-text-disabled">
                        <Loader2 size={12} className="animate-spin" />
                        Thinking...
                      </span>
                    ) : null}
                  </div>
                )}
                {(msg.role === "user" || msg.role === "error") && (
                  <div className="whitespace-pre-wrap wrap-break-word">
                    {msg.content}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form
        onSubmit={handleSend}
        className="shrink-0 border-t border-border p-3 md:p-4 bg-surface-0"
      >
        <div className="max-w-2xl mx-auto flex gap-2">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
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
          )}
        </div>
      </form>
    </div>
  );
}
