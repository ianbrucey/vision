"use client";

import {
  useState, useEffect, useRef, useCallback, type FormEvent,
} from "react";
import {
  listChatSessions, createChatSession, archiveChatSession, updateChatSession,
  getChatMessages, streamChatMessage,
  type ChatSession, type ChatMessage,
} from "@/lib/api";

/* ------------------------------------------------------------------ */
/* Types                                                              */
/* ------------------------------------------------------------------ */

export interface UIMessage {
  role: "user" | "assistant" | "system" | "error";
  content: string;
  sequence: number | null;
  timestamp: Date;
}

/* ------------------------------------------------------------------ */
/* Hook                                                               */
/* ------------------------------------------------------------------ */

const SESSION_KEY = (caseId: number) => `vision_chat_active_session_${caseId}`;

export function useChatSession(caseId: number) {
  /* ---- sessions ---- */
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionIdRaw] = useState<number | null>(() => {
    if (typeof window === "undefined") return null;
    const raw = localStorage.getItem(SESSION_KEY(caseId));
    return raw ? Number(raw) : null;
  });
  const [sessionsLoading, setSessionsLoading] = useState(true);

  /* ---- messages ---- */
  const [messages, setMessages] = useState<UIMessage[]>([]);
  const [messagesLoading, setMessagesLoading] = useState(false);

  /* ---- input ---- */
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [working, setWorking] = useState(false);
  const streamCtrlRef = useRef<AbortController | null>(null);
  const sendingRef = useRef(false);

  /* ---- persist active session ---- */
  const setActiveSessionId = useCallback((id: number | null) => {
    setActiveSessionIdRaw(id);
    if (id !== null) {
      localStorage.setItem(SESSION_KEY(caseId), String(id));
    } else {
      localStorage.removeItem(SESSION_KEY(caseId));
    }
  }, [caseId]);

  /* ---- load sessions ---- */
  const loadSessions = useCallback(async () => {
    try {
      const s = await listChatSessions(caseId);
      setSessions(s);
      if (s.length > 0) {
        const persisted = localStorage.getItem(SESSION_KEY(caseId));
        const persistedId = persisted ? Number(persisted) : null;
        const stillExists = persistedId && s.some((x) => x.id === persistedId);
        if (stillExists) {
          setActiveSessionIdRaw(persistedId);
        } else if (!activeSessionId) {
          setActiveSessionIdRaw(s[0].id);
        }
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

  /* ---- session actions ---- */
  const handleNewSession = async () => {
    try {
      const { session_id } = await createChatSession(caseId);
      setMessages([]);
      setActiveSessionId(session_id);
      await loadSessions();
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

  /* ---- load messages ---- */
  useEffect(() => {
    if (!activeSessionId) return;
    if (sendingRef.current) return; // don't clobber during active send
    let cancelled = false;
    setMessagesLoading(true);
    getChatMessages(activeSessionId)
      .then((msgs: ChatMessage[]) => {
        if (cancelled) return;
        const loaded: UIMessage[] = msgs
          .filter((m) => m.role !== "tool_call" && m.role !== "tool_result")
          .map((m) => ({
            role: m.role as UIMessage["role"],
            content: m.content,
            sequence: m.sequence ?? null,
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

  /* ---- send message ---- */
  const handleSend = async (text: string) => {
    if (!text.trim() || streaming) return;

    sendingRef.current = true;

    let sid = activeSessionId;
    if (!sid) {
      try {
        const { session_id } = await createChatSession(caseId);
        sid = session_id;
        setActiveSessionId(sid);
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
            case "assistant":
              setWorking(false);
              for (let i = copy.length - 1; i >= 0; i--) {
                if (copy[i].role === "assistant" && copy[i].sequence === null) {
                  const chunk = event.content || "";
                  const existing = copy[i].content;
                  // Add spacing between distinct streaming chunks.
                  // First chunk: no prefix. Subsequent chunks: newline separator.
                  const sep = existing ? "\n\n" : "";
                  copy[i] = {
                    ...copy[i],
                    content: existing + sep + chunk,
                  };
                  break;
                }
              }
              break;
            case "assistant_final":
              for (let i = copy.length - 1; i >= 0; i--) {
                if (copy[i].role === "assistant" && copy[i].sequence === null) {
                  copy[i] = { ...copy[i], sequence: event.sequence ?? null };
                  break;
                }
              }
              break;
            case "tool_call":
              setWorking(true);
              break;
            case "tool_result":
              // Silently skip — users don't need to see raw tool output.
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
        sendingRef.current = false;
        setStreaming(false);
        setWorking(false);
        loadSessions();
      },
      (err) => {
        sendingRef.current = false;
        setStreaming(false);
        setWorking(false);
        setMessages((prev) => [
          ...prev,
          { role: "error", content: err, sequence: null, timestamp: new Date() },
        ]);
      },
    );
  };

  const handleCancel = () => {
    streamCtrlRef.current?.abort();
    sendingRef.current = false;
    setStreaming(false);
    setWorking(false);
  };

  /* ---- derived ---- */
  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return {
    // sessions
    sessions,
    activeSessionId,
    activeSession,
    sessionsLoading,
    setActiveSessionId,
    loadSessions,
    handleNewSession,
    handleArchiveSession,
    handleRenameSession,
    // messages
    messages,
    messagesLoading,
    setMessages,
    // streaming
    input,
    setInput,
    streaming,
    working,
    handleSend,
    handleCancel,
  };
}
