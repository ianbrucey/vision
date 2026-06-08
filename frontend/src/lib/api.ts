const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8400";

function getAuthHeaders(): Record<string, string> {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem("vision_token");
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

async function fetchAPI(path: string, options?: RequestInit) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...getAuthHeaders(), ...options?.headers },
    ...options,
  });
  if (res.status === 401) {
    localStorage.removeItem("vision_token");
    localStorage.removeItem("vision_user");
    if (typeof window !== "undefined") window.location.href = "/login";
    throw new Error("Session expired");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

// Cases
export const listCases = (params?: { status?: string; case_type?: string }) => {
  const qs = new URLSearchParams(params as Record<string, string>).toString();
  return fetchAPI(`/api/cases${qs ? `?${qs}` : ""}`);
};

export const getCase = (id: number) => fetchAPI(`/api/cases/${id}`);

export const createCase = (data: { name: string; case_type: string; narrative?: string; description?: string }) =>
  fetchAPI("/api/cases", { method: "POST", body: JSON.stringify(data) });

export const updateCase = (id: number, data: { name?: string; case_type?: string; narrative?: string; description?: string; status?: string }) =>
  fetchAPI(`/api/cases/${id}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteCase = (id: number) =>
  fetchAPI(`/api/cases/${id}`, { method: "DELETE" });

// Parties
export const addParty = (caseId: number, data: { name: string; party_kind: string; roles: string[] }) =>
  fetchAPI(`/api/cases/${caseId}/parties`, { method: "POST", body: JSON.stringify(data) });

export const listParties = (caseId: number) => fetchAPI(`/api/cases/${caseId}/parties`);

// Allegations
export const addAllegation = (caseId: number, data: { allegation_id: string; text: string; category?: string }) =>
  fetchAPI(`/api/cases/${caseId}/allegations`, { method: "POST", body: JSON.stringify(data) });

// Documents / Ingestion
export const uploadFile = async (caseId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/cases/${caseId}/ingest`, {
    method: "POST",
    body: form,
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) throw new Error(`Upload failed: ${res.statusText}`);
  return res.json();
};

export const listDocuments = (caseId: number) =>
  fetchAPI(`/api/cases/${caseId}/documents`);

export const getDocumentPreviewUrl = (docId: number): Promise<{ url: string; name: string; type: string }> =>
  fetchAPI(`/api/documents/${docId}/preview`);

export const deleteDocument = (docId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/documents/${docId}`, { method: "DELETE" });

// Jobs
export const getJob = (id: number) => fetchAPI(`/api/jobs/${id}`);
export const listJobs = (params?: { case_id?: number; status?: string }) => {
  const qs = new URLSearchParams(
    Object.fromEntries(Object.entries(params || {}).map(([k, v]) => [k, String(v)]))
  ).toString();
  return fetchAPI(`/api/jobs${qs ? `?${qs}` : ""}`);
};

// Health
export const healthCheck = () => fetchAPI("/api/health");

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export interface ChatSession {
  id: number;
  case_id: number;
  sdk_session_id: string | null;
  title: string | null;
  status: string;
  context_summary: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: number;
  role: "user" | "assistant" | "tool_call" | "tool_result" | "system";
  content: string;
  tool_name: string | null;
  tool_inputs: Record<string, unknown> | null;
  tool_result: Record<string, unknown> | null;
  citations: Array<{ block_id: number; page: number; quote: string }> | null;
  sequence: number;
  created_at: string;
}

export const createChatSession = (caseId: number): Promise<{ session_id: number; case_id: number; project_key: string; system_prompt: string }> =>
  fetchAPI("/api/chat/sessions", { method: "POST", body: JSON.stringify({ case_id: caseId }) });

export const listChatSessions = (caseId: number): Promise<ChatSession[]> =>
  fetchAPI(`/api/chat/sessions?case_id=${caseId}`);

export const archiveChatSession = (sessionId: number): Promise<{ archived: boolean }> =>
  fetchAPI(`/api/chat/sessions/${sessionId}`, { method: "DELETE" });

export const getChatMessages = (sessionId: number): Promise<ChatMessage[]> =>
  fetchAPI(`/api/chat/sessions/${sessionId}/messages`);

/**
 * Stream an agent response via SSE.
 * Returns an AbortController so the caller can cancel mid-stream.
 */
export function streamChatMessage(
  sessionId: number,
  message: string,
  onEvent: (event: { type: string; content?: string; name?: string; inputs?: unknown; tool_use_id?: string; subtype?: string; session_id?: string; cost?: number; message?: string; sequence?: number | null }) => void,
  onDone: () => void,
  onError: (err: string) => void,
): AbortController {
  const controller = new AbortController();

  fetch(`${API_BASE}/api/chat/sessions/${sessionId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...getAuthHeaders() },
    body: JSON.stringify({ message }),
    signal: controller.signal,
  })
    .then(async (res) => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }
      const reader = res.body?.getReader();
      if (!reader) throw new Error("No response stream");

      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        // SSE messages are delimited by \n\n
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const line = part.trim();
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              onEvent(data);
            } catch { /* skip malformed */ }
          }
        }
      }
      onDone();
    })
    .catch((err) => {
      if (err.name === "AbortError") return;
      onError(err instanceof Error ? err.message : "Stream failed");
    });

  return controller;
}
