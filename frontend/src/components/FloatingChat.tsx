"use client";

import { useState, useRef, useEffect, useCallback, type FormEvent } from "react";
import {
  MessageCircle, X, Send, Loader2, ChevronDown,
  Maximize2, Minimize2, Mic, MicOff,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { useChatSession } from "@/hooks/useChatSession";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

type ChatMode = "panel" | "fullscreen";

interface FloatingChatProps {
  caseId: number;
  context?: string;
  open: boolean;
  onClose: () => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                          */
/* ------------------------------------------------------------------ */

export default function FloatingChat({ caseId, context, open, onClose }: FloatingChatProps) {
  const chat = useChatSession(caseId);
  const [mode, setMode] = useState<ChatMode>("panel");
  const [showScrollBtn, setShowScrollBtn] = useState(false);
  const [recording, setRecording] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);

  /* Auto-scroll to bottom when new messages arrive (if near bottom) */
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (fromBottom < 150) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    }
  }, [chat.messages]);

  /* Show scroll-to-bottom button when scrolled up */
  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const fromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowScrollBtn(fromBottom > 150);
  }, []);

  const scrollToBottom = () => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
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

  /* Send */
  const handleSend = (e?: FormEvent) => {
    e?.preventDefault();
    chat.handleSend(chat.input);
  };

  /* ---- render ---- */
  if (!open) return null;

  const isFull = mode === "fullscreen";

  return (
    <>
      {/* Backdrop */}
      {!isFull && (
        <div
          className="md:hidden fixed inset-0 bg-black/40 z-40"
          onClick={onClose}
        />
      )}

      {/* Panel */}
      <div
        className={`fixed bg-surface-1 border-l border-border flex flex-col z-50 shadow-xl
                    ${isFull
                      ? "inset-0"
                      : "top-0 right-0 bottom-0 w-full md:w-[420px] max-md:rounded-t-2xl max-md:top-auto max-md:max-h-[80dvh] animate-in slide-in-from-right duration-200"
                    }`}
      >
        {/* Header */}
        <div className="shrink-0 flex items-center justify-between px-4 py-2.5 border-b border-border">
          <div className="flex items-center gap-2 min-w-0">
            <MessageCircle size={16} className="text-brand shrink-0" />
            <span className="text-sm font-medium shrink-0">Agent</span>
            {chat.activeSession && (
              <span className="text-[10px] text-text-disabled truncate">
                · {chat.activeSession.title || `Chat ${chat.activeSession.id}`}
              </span>
            )}
            {context && (
              <span className="hidden sm:inline text-[10px] text-text-disabled">
                · {context}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            {/* Quick session switcher */}
            {chat.sessions.length > 1 && (
              <select
                value={chat.activeSessionId ?? ""}
                onChange={(e) => {
                  const id = e.target.value ? Number(e.target.value) : null;
                  chat.setActiveSessionId(id);
                  chat.setMessages([]);
                }}
                className="text-[10px] bg-surface-2 border border-border rounded px-1.5 py-0.5
                           text-text-secondary max-w-[100px] truncate"
              >
                {chat.sessions.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title || `Chat ${s.id}`}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={chat.handleNewSession}
              className="text-[10px] px-1.5 py-0.5 rounded text-text-secondary
                         hover:text-brand hover:bg-brand-bg transition-colors"
              title="New session"
            >
              + New
            </button>
            <button
              onClick={() => setMode(isFull ? "panel" : "fullscreen")}
              className="p-1 rounded text-text-disabled hover:text-text-secondary transition-colors"
              title={isFull ? "Exit fullscreen" : "Fullscreen"}
            >
              {isFull ? <Minimize2 size={14} /> : <Maximize2 size={14} />}
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded text-text-disabled hover:text-text-primary transition-colors"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Messages */}
        <div
          ref={scrollRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto px-3 py-3 space-y-3 relative"
        >
          {chat.messagesLoading && (
            <div className="flex items-center justify-center h-full">
              <Loader2 className="animate-spin text-text-disabled" size={20} />
            </div>
          )}
          {!chat.messagesLoading && chat.messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center px-4">
                <MessageCircle size={24} className="text-text-disabled mx-auto mb-2" />
                <p className="text-xs text-text-secondary">
                  {chat.activeSession
                    ? "Start the conversation."
                    : "Create a session to begin."}
                </p>
              </div>
            </div>
          )}
          {chat.messages.map((m, i) => (
            <div
              key={i}
              className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[90%] rounded-lg px-3 py-2 text-xs ${
                  m.role === "user"
                    ? "bg-brand text-white"
                    : m.role === "error"
                      ? "bg-danger-bg text-danger border border-danger/20"
                      : "bg-surface-2 text-text-primary border border-border"
                }`}
              >
                {m.role === "assistant" && (
                  <div className="prose prose-xs max-w-none">
                    {m.content ? (
                      <ReactMarkdown>{m.content}</ReactMarkdown>
                    ) : chat.streaming ? (
                      <Loader2 size={10} className="animate-spin inline" />
                    ) : null}
                  </div>
                )}
                {(m.role === "user" || m.role === "error") && (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                )}
              </div>
            </div>
          ))}

          {/* Working indicator */}
          {chat.working && (
            <div className="flex justify-start">
              <div className="max-w-[90%] rounded-lg px-3 py-2 text-xs bg-surface-2 text-text-secondary">
                <span className="inline-flex items-center gap-2">
                  <Loader2 size={12} className="animate-spin" />
                  Working...
                </span>
              </div>
            </div>
          )}

          {/* Scroll-to-bottom button */}
          {showScrollBtn && (
            <div className="sticky bottom-2 flex justify-end pointer-events-none">
              <button
                onClick={scrollToBottom}
                className="pointer-events-auto bg-surface-1 border border-border
                           rounded-full size-8 flex items-center justify-center
                           shadow-md hover:bg-surface-2 transition-colors"
                aria-label="Scroll to bottom"
              >
                <ChevronDown size={14} className="text-text-secondary" />
              </button>
            </div>
          )}
        </div>

        {/* Input */}
        <form onSubmit={handleSend} className="shrink-0 border-t border-border p-3 flex gap-2">
          <input
            type="text"
            value={chat.input}
            onChange={(e) => chat.setInput(e.target.value)}
            disabled={chat.streaming}
            placeholder="Ask the agent..."
            className="flex-1 min-w-0 bg-surface-2 border border-border rounded-lg px-3 py-2
                       text-xs placeholder:text-text-disabled outline-none
                       focus:border-brand disabled:opacity-50"
          />
          {chat.streaming ? (
            <button
              type="button"
              onClick={chat.handleCancel}
              className="bg-danger text-white px-3 py-2 rounded-lg text-xs font-medium shrink-0"
            >
              Stop
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={recording ? stopRecording : startRecording}
                className={`shrink-0 size-8 flex items-center justify-center rounded-lg transition-colors ${
                  recording
                    ? "bg-danger text-white animate-pulse"
                    : "bg-surface-3 text-text-secondary hover:bg-surface-2 hover:text-text-primary"
                }`}
                aria-label={recording ? "Stop recording" : "Start recording"}
              >
                {recording ? <MicOff size={14} /> : <Mic size={14} />}
              </button>
              <button
                type="submit"
                disabled={!chat.input.trim()}
                className="bg-brand hover:bg-brand-hover text-white px-3 py-2 rounded-lg
                           text-xs font-medium shrink-0 disabled:opacity-50 transition-colors"
              >
                <Send size={14} />
              </button>
            </>
          )}
        </form>
      </div>
    </>
  );
}

/* ------------------------------------------------------------------ */
/* Floating button                                                    */
/* ------------------------------------------------------------------ */

interface FloatingChatButtonProps {
  onClick: () => void;
  unread?: number;
}

export function FloatingChatButton({ onClick, unread }: FloatingChatButtonProps) {
  return (
    <button
      onClick={onClick}
      className="fixed bottom-[4.5rem] md:bottom-5 right-5 z-30 size-12 rounded-full bg-brand text-white
                 shadow-lg hover:bg-brand-hover active:scale-95
                 transition-all flex items-center justify-center"
      aria-label="Open chat"
    >
      <MessageCircle size={20} />
      {unread && unread > 0 ? (
        <span
          className="absolute -top-1 -right-1 size-4 rounded-full bg-danger text-white
                     text-[9px] font-semibold flex items-center justify-center"
        >
          {unread}
        </span>
      ) : null}
    </button>
  );
}
