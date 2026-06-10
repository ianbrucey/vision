"use client";

import { useState, useRef, useEffect, useCallback, type FormEvent } from "react";
import { MessageCircle, X, Send, Loader2, ChevronDown, Wrench, ChevronRight } from "lucide-react";
import { createChatSession, streamChatMessage, getChatMessages, type ChatMessage } from "@/lib/api";
import ReactMarkdown from "react-markdown";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

interface UIMessage {
  role: "user" | "assistant" | "tool_call" | "tool_result" | "error";
  content: string;
  toolName?: string;
  toolInputs?: unknown;
  toolResult?: unknown;
  toolExpanded?: boolean;
}

interface FloatingChatProps {
  caseId: number;
  context: string;
  open: boolean;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function FloatingChat({ caseId, context, open, onClose }: FloatingChatProps) {
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const streamCtrlRef = useRef<AbortController | null>(null);

  /* Init session on first open */
  useEffect(() => {
    if (!open || sessionId) return;
    (async () => {
      setLoading(true);
      try {
        const { session_id } = await createChatSession(caseId);
        setSessionId(session_id);
      } catch { /* silent */ }
      setLoading(false);
    })();
  }, [open, caseId, sessionId]);

  /* Auto-scroll */
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  /* Send */
  const handleSend = async (e?: FormEvent) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || streaming || !sessionId) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setStreaming(true);

    const assistantMsg: UIMessage = { role: "assistant", content: "" };
    setMessages((prev) => [...prev, assistantMsg]);

    streamCtrlRef.current = streamChatMessage(
      sessionId,
      text,
      (event) => {
        setMessages((prev) => {
          const copy = [...prev];
          switch (event.type) {
            case "assistant":
              for (let i = copy.length - 1; i >= 0; i--) {
                if (copy[i].role === "assistant" && copy[i].content !== null) {
                  copy[i] = { ...copy[i], content: copy[i].content + (event.content || "") };
                  break;
                }
              }
              break;
            case "tool_call":
              copy.push({ role: "tool_call", content: "", toolName: event.name, toolInputs: event.inputs, toolExpanded: false });
              break;
            case "tool_result":
              copy.push({ role: "tool_result", content: "", toolResult: event.content });
              break;
            case "error":
              copy.push({ role: "error", content: event.message || "Error" });
              break;
          }
          return copy;
        });
      },
      () => setStreaming(false),
      (err) => {
        setStreaming(false);
        setMessages((prev) => [...prev, { role: "error", content: err }]);
      },
    );
  };

  const toggleTool = (idx: number) => {
    setMessages((prev) => {
      const copy = [...prev];
      const m = copy[idx];
      if (m?.role === "tool_call") copy[idx] = { ...m, toolExpanded: !m.toolExpanded };
      return copy;
    });
  };

  /* ---- render ---- */
  if (!open) return null;

  return (
    <>
      {/* Backdrop — mobile only */}
      <div className="md:hidden fixed inset-0 bg-black/40 z-40" onClick={onClose} />

      {/* Panel */}
      <div className="fixed top-0 right-0 bottom-0 w-full md:w-[380px] bg-surface-1 border-l border-border
                      flex flex-col z-50 shadow-xl
                      max-md:rounded-t-2xl max-md:top-auto max-md:max-h-[80dvh]
                      animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-border">
          <div className="flex items-center gap-2">
            <MessageCircle size={16} className="text-brand" />
            <span className="text-sm font-medium">Agent</span>
            <span className="hidden sm:inline text-[10px] text-text-disabled">· scoped to this view</span>
          </div>
          <button onClick={onClose} className="text-text-disabled hover:text-text-primary p-1">
            <X size={18} />
          </button>
        </div>

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
          {loading && (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="animate-spin text-text-disabled" size={20} />
            </div>
          )}
          {!loading && messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center px-4">
                <MessageCircle size={24} className="text-text-disabled mx-auto mb-2" />
                <p className="text-xs text-text-secondary">Ask the agent about this view.</p>
              </div>
            </div>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[90%] rounded-lg px-3 py-2 text-xs ${
                m.role === "user"
                  ? "bg-brand text-white"
                  : m.role === "error"
                    ? "bg-danger-bg text-danger border border-danger/20"
                    : m.role === "tool_call" || m.role === "tool_result"
                      ? "bg-surface-2 border border-border text-text-secondary"
                      : "bg-surface-2 text-text-primary border border-border"
              }`}>
                {m.role === "tool_call" && (
                  <button onClick={() => toggleTool(i)} className="flex items-center gap-1.5 w-full text-left">
                    {m.toolExpanded ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    <Wrench size={10} />
                    <span className="font-mono text-[10px]">{m.toolName}</span>
                  </button>
                )}
                {m.role === "tool_call" && m.toolExpanded && (
                  <pre className="mt-1 text-[10px] bg-surface-3 rounded p-1.5 overflow-x-auto max-h-24">
                    {JSON.stringify(m.toolInputs, null, 2)}
                  </pre>
                )}
                {m.role === "tool_result" && (
                  <details className="text-[10px]">
                    <summary className="cursor-pointer text-text-disabled">Result</summary>
                    <pre className="mt-1 bg-surface-3 rounded p-1.5 overflow-x-auto max-h-24">
                      {typeof m.toolResult === "string" ? m.toolResult.slice(0, 1000) : JSON.stringify(m.toolResult).slice(0, 1000)}
                    </pre>
                  </details>
                )}
                {m.role === "assistant" && (
                  <div className="prose prose-xs max-w-none">
                    {m.content ? <ReactMarkdown>{m.content}</ReactMarkdown>
                      : streaming ? <Loader2 size={10} className="animate-spin inline" /> : null}
                  </div>
                )}
                {(m.role === "user" || m.role === "error") && (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="shrink-0 border-t border-border p-3 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={streaming}
            placeholder="Ask about this view..."
            className="flex-1 min-w-0 bg-surface-2 border border-border rounded-lg px-3 py-2
                       text-xs placeholder:text-text-disabled outline-none
                       focus:border-brand disabled:opacity-50"
          />
          {streaming ? (
            <button type="button" onClick={() => streamCtrlRef.current?.abort()}
                    className="bg-danger text-white px-3 py-2 rounded-lg text-xs font-medium shrink-0">
              Stop
            </button>
          ) : (
            <button type="submit" disabled={!input.trim()}
                    className="bg-brand hover:bg-brand-hover text-white px-3 py-2 rounded-lg
                               text-xs font-medium shrink-0 disabled:opacity-50 transition-colors">
              <Send size={14} />
            </button>
          )}
        </form>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Floating button (separate export for convenience)                   */
/* ------------------------------------------------------------------ */

interface FloatingChatButtonProps {
  onClick: () => void;
  unread?: number;
}

export function FloatingChatButton({ onClick, unread }: FloatingChatButtonProps) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-5 right-5 z-30 size-12 rounded-full bg-brand text-white
                 shadow-lg hover:bg-brand-hover active:scale-95
                 transition-all flex items-center justify-center"
      aria-label="Open chat"
    >
      <MessageCircle size={20} />
      {unread && unread > 0 ? (
        <span className="absolute -top-1 -right-1 size-4 rounded-full bg-danger text-white
                         text-[9px] font-semibold flex items-center justify-center">
          {unread}
        </span>
      ) : null}
    </button>
  );
}
