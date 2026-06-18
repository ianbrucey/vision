"use client";

import { useRef, useCallback, useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import { MessageCircle, Loader2, ChevronDown } from "lucide-react";
import type { ChatSession } from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

export interface UIMessage {
  role: "user" | "assistant" | "system" | "error";
  content: string;
  sequence: number | null;
  timestamp: Date;
}

interface ChatMessagesProps {
  messages: UIMessage[];
  loading: boolean;
  streaming: boolean;
  working: boolean;
  activeSession: ChatSession | undefined;
  grounded: boolean;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function ChatMessages({
  messages,
  loading,
  streaming,
  working,
  activeSession,
  grounded,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  /* Auto-scroll to bottom when messages change */
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  /* Show scroll-to-bottom button when scrolled up */
  const handleScroll = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(fromBottom > 150);
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  /* ---- loading state ---- */

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="animate-spin text-text-disabled" size={24} />
      </div>
    );
  }

  /* ---- empty state ---- */

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center">
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
    );
  }

  /* ---- message list ---- */

  return (
    <div className="flex-1 relative min-h-0">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="absolute inset-0 overflow-y-auto px-3 md:px-4 py-3 space-y-3"
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`rounded-lg px-3 py-2 text-sm ${
                msg.role === "user"
                  ? "bg-brand text-white"
                  : msg.role === "error"
                    ? "bg-danger-bg text-danger border border-danger/20"
                    : "bg-surface-1 border border-border text-text-primary"
              }`}
            >
              {/* Assistant / user / error content */}
              {msg.role === "assistant" && (
                <div className="wrap-break-word prose prose-sm max-w-none prose-table:text-sm prose-td:border prose-td:border-border prose-td:px-2 prose-td:py-1 prose-th:bg-surface-2 prose-th:px-2 prose-th:py-1 prose-th:font-semibold">
                  {msg.content ? (
                    <ReactMarkdown remarkPlugins={[remarkBreaks]}>{msg.content}</ReactMarkdown>
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
        ))}
        {/* Working indicator — shown during tool execution before text arrives */}
        {working && (
          <div className="flex justify-start">
            <div className="rounded-lg px-3 py-2 text-sm bg-surface-1 border border-border text-text-secondary">
              <span className="inline-flex items-center gap-2">
                <Loader2 size={14} className="animate-spin" />
                Working...
              </span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Scroll-to-bottom — outside scrollable so it isn't clipped */}
      {showScrollBtn && (
        <div className="absolute bottom-2 right-4 pointer-events-none z-10">
          <button
            onClick={scrollToBottom}
            className="pointer-events-auto
                       bg-surface-1 border border-border rounded-full
                       size-9 flex items-center justify-center
                       shadow-md hover:bg-surface-2 active:bg-surface-3
                       transition-colors"
            aria-label="Scroll to bottom"
          >
            <ChevronDown size={18} className="text-text-secondary" />
          </button>
        </div>
      )}
    </div>
  );
}
