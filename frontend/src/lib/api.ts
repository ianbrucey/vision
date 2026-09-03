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

// ---------------------------------------------------------------------------
// Solicitations
// ---------------------------------------------------------------------------

export interface SolicitationDocument {
  id: number;
  name: string;
  page_count: number | null;
  document_type: string | null;
  ocr_status: "pending" | "processing" | "complete" | "failed";
  source: "user_upload" | "discovery" | "data_lab" | "email" | "portal" | "api" | "sam_gov" | "other";
  storage_path: string | null;
  created_at: string;
}

export interface Solicitation {
  id: number;
  external_id: string;
  case_id: number;
  source_type: "federal" | "state" | "local";
  title: string;
  url: string;
  notice_id: string | null;
  ingestion_status: "pending" | "fetching" | "complete" | "failed";
  has_missing_docs: boolean;
  error_message: string | null;
  agency: string | null;
  naics_code: string | null;
  naics_label?: string | null;
  psc_code: string | null;
  set_aside_type: string | null;
  set_aside_description: string | null;
  point_of_contact: Record<string, unknown> | unknown[] | null;
  place_of_performance: Record<string, unknown> | null;
  response_deadline: string | null;
  posted_date: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  triage_status: "pending" | "running" | "complete" | "failed";
  triage_error: string | null;
  has_partial_artifacts: boolean;
  notice_type: "rfi" | "sources_sought" | "rfp" | "rfq" | "other" | null;
  quick_kill: boolean | null;
  quick_kill_reason: string | null;
  artifact_scope_of_work: string | null;
  artifact_technical_requirements: string | null;
  artifact_deliverables_timeline: string | null;
  artifact_evaluation_criteria: string | null;
  artifact_submission_checklist: string | null;
  matching_status: "pending" | "running" | "complete" | "failed";
  matching_error: string | null;
  outreach_email_subject: string | null;
  outreach_email_body: string | null;
  assignee_id: string | null;
  assigned_at: string | null;
  assignee_username: string | null;
  quotes_total?: number;
  quotes_draft?: number;
  quotes_submitted?: number;
  unread_replies?: number;
  has_outreach?: boolean;
}

export interface SolicitationWithDocuments extends Solicitation {
  documents: SolicitationDocument[];
}

// Vendor Matching

export type OutreachStatus = "not_contacted" | "requested" | "received" | "declined";

export interface VendorMatch {
  id: number;
  external_id: string;
  solicitation_id: number;
  vendor_id: number;
  rank: number;
  match_score: number;
  match_rationale: string;
  naics_match_type: "exact" | "family" | "capability_only" | "manual";
  vendor_name: string;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  website: string | null;
  state: string | null;
  city: string | null;
  naics_code_primary: string | null;
  is_small_business: boolean;
  is_sdvosb: boolean;
  is_hubzone: boolean;
  is_8a: boolean;
  is_woman_owned: boolean;
  is_veteran_owned: boolean;
  outreach_status: OutreachStatus;
  outreach_requested_at: string | null;
  outreach_received_at: string | null;
  outreach_doc_id: number | null;
  outreach_doc_name: string | null;
  created_at: string;
}

export interface VendorMatchesResponse {
  matching_status: "pending" | "running" | "complete" | "failed";
  matching_error: string | null;
  outreach_email_subject: string | null;
  outreach_email_body: string | null;
  matches: VendorMatch[];
}

export const getVendorMatches = (
  solicitationId: number,
): Promise<VendorMatchesResponse> =>
  fetchAPI(`/api/solicitations/${solicitationId}/vendor-matches`);

export const triggerVendorMatching = (
  solicitationId: number,
): Promise<{ job_id: number; matching_status: string }> =>
  fetchAPI(`/api/solicitations/${solicitationId}/vendor-matching`, { method: "POST" });

export const updateVendorMatchOutreach = (
  matchId: number,
  updates: {
    outreach_status?: OutreachStatus;
    outreach_doc_id?: number;
    clear_outreach_doc?: boolean;
  },
): Promise<VendorMatch> =>
  fetchAPI(`/api/vendor-matches/${matchId}/outreach`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });

// T10c — Per-vendor message thread

export interface VendorOutreachMessage {
  id: number;
  vendor_match_id: number;
  direction: "outbound" | "inbound";
  status: "draft" | "sent" | "failed" | "received";
  subject: string;
  body: string;
  mailgun_message_id: string | null;
  document_id: number | null;
  sent_at: string | null;
  received_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export const getVendorMatchMessages = (
  matchId: number,
): Promise<{ match: VendorMatch; messages: VendorOutreachMessage[] }> =>
  fetchAPI(`/api/vendor-matches/${matchId}/messages`);

export const createDraftMessage = (
  matchId: number,
): Promise<VendorOutreachMessage> =>
  fetchAPI(`/api/vendor-matches/${matchId}/messages/draft`, { method: "POST" });

export const updateDraftMessage = (
  messageId: number,
  updates: { subject?: string; body?: string },
): Promise<VendorOutreachMessage> =>
  fetchAPI(`/api/vendor-match-messages/${messageId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });

export const sendMessage = (
  messageId: number,
): Promise<VendorOutreachMessage> =>
  fetchAPI(`/api/vendor-match-messages/${messageId}/send`, { method: "POST" });

export const markMessagesRead = (
  matchId: number,
): Promise<{ read: boolean }> =>
  fetchAPI(`/api/vendor-matches/${matchId}/messages/read`, { method: "POST" });

// Vendor creation (T7 — inline vendor creation)

export interface VendorCreateInput {
  vendor_name: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  website?: string;
  city?: string;
  state?: string;
  naics_code_primary?: string;
  capabilities?: string;
  is_small_business?: boolean;
  is_woman_owned?: boolean;
  is_veteran_owned?: boolean;
  is_sdvosb?: boolean;
  is_hubzone?: boolean;
  is_8a?: boolean;
}

export interface CreatedVendor extends VendorCreateInput {
  id: number;
  source: string;
  created_at: string;
}

export const createVendor = (
  data: VendorCreateInput,
): Promise<CreatedVendor> =>
  fetchAPI("/api/vendors", { method: "POST", body: JSON.stringify(data) });

export const attachVendorMatch = (
  solicitationId: number,
  vendorId: number,
): Promise<VendorMatch> =>
  fetchAPI(`/api/solicitations/${solicitationId}/vendor-matches`, {
    method: "POST",
    body: JSON.stringify({ vendor_id: vendorId }),
  });

export const listNaicsCodes = (): Promise<{ code: string; title: string }[]> =>
  fetchAPI("/api/naics-codes");

export const listSolicitations = (
  params?: { source_type?: string; ingestion_status?: string; naics_code?: string; state?: string; limit?: number; offset?: number },
): Promise<{ total: number; limit: number; offset: number; count: number; solicitations: Solicitation[] }> => {
  const qs = new URLSearchParams();
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== "") qs.set(k, String(v));
    }
  }
  return fetchAPI(`/api/solicitations${qs.size ? `?${qs}` : ""}`);
};

export const createSolicitation = (
  data: { source_type: string; url?: string; title?: string; description?: string },
): Promise<{ solicitation: Solicitation; job_id: number | null }> =>
  fetchAPI("/api/solicitations", { method: "POST", body: JSON.stringify(data) });

export interface SamMetadataPreview {
  notice_id: string;
  title: string | null;
  department: string | null;
  sub_tier: string | null;
  office: string | null;
  posted_date: string | null;
  response_deadline: string | null;
  naics_code: string | null;
  set_aside: string | null;
  description: string | null;
}

export const previewSamMetadata = (urlOrNoticeId: string): Promise<SamMetadataPreview> => {
  const qs = new URLSearchParams();
  if (urlOrNoticeId.includes("/") || urlOrNoticeId.includes("?")) {
    qs.set("url", urlOrNoticeId);
  } else {
    qs.set("notice_id", urlOrNoticeId);
  }
  return fetchAPI(`/api/solicitations/preview-sam?${qs}`);
};

export const ingestSolicitationPackage = async (
  formData: FormData
): Promise<{ solicitation: Solicitation; document_count: number; job_id: number }> => {
  const res = await fetch(`${API_BASE}/api/solicitations/ingest-package`, {
    method: "POST",
    body: formData,
    headers: { ...getAuthHeaders() },
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Package upload failed: ${res.statusText}`);
  }
  return res.json();
};

export const getSolicitation = (id: number): Promise<SolicitationWithDocuments> =>
  fetchAPI(`/api/solicitations/${id}`);

export const rerunSolicitation = (id: number): Promise<{ solicitation_id: number; job_id: number; status: string }> =>
  fetchAPI(`/api/solicitations/${id}/rerun`, { method: "POST" });

export const deleteSolicitation = (id: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/solicitations/${id}`, { method: "DELETE" });

export const triggerTriage = (
  id: number,
): Promise<{ job_id: number; triage_status: string }> =>
  fetchAPI(`/api/solicitations/${id}/triage`, { method: "POST" });

export const claimSolicitation = (id: number): Promise<Solicitation> =>
  fetchAPI(`/api/solicitations/${id}/claim`, { method: "POST" });

export const releaseSolicitation = (id: number): Promise<Solicitation> =>
  fetchAPI(`/api/solicitations/${id}/release`, { method: "POST" });

export const assignSolicitation = (id: number, userId: string): Promise<Solicitation> =>
  fetchAPI(`/api/solicitations/${id}/assign`, { method: "POST", body: JSON.stringify({ user_id: userId }) });

export const getMySolicitations = (): Promise<{
  solicitations: Solicitation[];
  summary: { total_assigned: number; needs_triage: number; needs_quote: number; quotes_in_progress: number };
}> => fetchAPI("/api/solicitations/mine");

export const getSolicitationByCase = (
  caseId: number,
): Promise<SolicitationWithDocuments> =>
  fetchAPI(`/api/cases/${caseId}/solicitation`);

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

export interface DocumentSummary {
  id: number;
  name: string;
  document_type: string;
  page_count: number | null;
  source: string;
  created_at: string;
}

export const listDocumentsSummary = (caseId: number): Promise<{ documents: DocumentSummary[] }> =>
  fetchAPI(`/api/cases/${caseId}/documents-summary`);

export const getDocumentPreviewUrl = (docId: number): Promise<{ url: string | null; name: string; type: string; content?: string }> =>
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

// Synthesis
export const synthesizeCase = (caseId: number): Promise<{ job_id: number; status: string }> =>
  fetchAPI(`/api/cases/${caseId}/synthesize`, { method: "POST" });

// Drafts
export interface Block {
  id: string;
  type: "section_heading" | "numbered_paragraph" | "unnumbered_paragraph"
      | "block_quote" | "list_item" | "signature_row"
      | "section_divider" | "raw_html";
  content: string;
  /** For list_item: "letter" | "roman" | "bullet" — defaults to "letter" */
  list_style?: "letter" | "roman" | "bullet";
  /** For signature_row: printed name below the line */
  printed_name?: string;
}

export interface DraftSummary {
  id: number;
  case_id: number;
  name: string;
  document_type: string;
  status: string;
  created_by: string;
  block_count: number;
  created_at: string;
  updated_at: string;
}

export interface Draft extends DraftSummary {
  content: Block[];
  metadata: Record<string, unknown> | null;
}

export const listDrafts = (caseId: number): Promise<{ drafts: DraftSummary[] }> =>
  fetchAPI(`/api/cases/${caseId}/drafts`);

export const getDraft = (draftId: number): Promise<{ draft: Draft }> =>
  fetchAPI(`/api/drafts/${draftId}`);

export const createDraft = (data: {
  case_id: number;
  name: string;
  document_type?: string;
  content?: Block[];
}): Promise<{ draft: Draft }> =>
  fetchAPI("/api/drafts", { method: "POST", body: JSON.stringify(data) });

export const updateDraft = (
  draftId: number,
  data: { name?: string; document_type?: string; status?: string; content?: Block[] },
): Promise<{ draft: Draft }> =>
  fetchAPI(`/api/drafts/${draftId}`, { method: "PATCH", body: JSON.stringify(data) });

export const updateBlock = (
  draftId: number,
  blockId: string,
  content: string,
): Promise<{ draft: Draft }> =>
  fetchAPI(`/api/drafts/${draftId}/blocks/${blockId}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });

export const deleteDraft = (draftId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/drafts/${draftId}`, { method: "DELETE" });

// Workspace
export type FileType = "markdown" | "structured_draft" | "html" | "json_view" | "pdf";

export interface Workspace {
  id: number;
  case_id: number;
  name: string;
  phase: string | null;
  description: string | null;
  parent_id: number | null;
  status: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceItemSummary {
  id: number;
  case_id: number;
  name: string;
  file_type: FileType;
  document_type: string;
  folder: string;
  folder_id: number | null;
  status: string;
  created_by: string;
  workspace_id: number | null;
  block_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkspaceItemFull extends WorkspaceItemSummary {
  content: unknown;
  metadata: Record<string, unknown> | null;
}

export const listWorkspaces = (caseId: number): Promise<{ workspaces: Workspace[] }> =>
  fetchAPI(`/api/cases/${caseId}/workspaces`);

export const createWorkspace = (caseId: number, name: string, description?: string): Promise<{ id: number; name: string }> =>
  fetchAPI("/api/workspaces", { method: "POST", body: JSON.stringify({ case_id: caseId, name, description }) });

// Folders
export interface Folder {
  id: number;
  case_id: number;
  workspace_id: number | null;
  name: string;
  parent_id: number | null;
  sort_order: number;
  created_at: string;
  updated_at: string;
}

export const listFolders = (caseId: number, parentId?: number | null, workspaceId?: number | null): Promise<{ folders: Folder[] }> => {
  const params = new URLSearchParams();
  if (parentId != null) params.set("parent_id", String(parentId));
  if (workspaceId != null) params.set("workspace_id", String(workspaceId));
  const q = params.toString();
  return fetchAPI(`/api/cases/${caseId}/folders${q ? `?${q}` : ""}`);
};

export const createFolder = (caseId: number, name: string, parentId?: number | null, workspaceId?: number | null): Promise<{ id: number; name: string }> =>
  fetchAPI("/api/folders", { method: "POST", body: JSON.stringify({ case_id: caseId, name, parent_id: parentId ?? null, workspace_id: workspaceId ?? null }) });

export const deleteFolder = (folderId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/folders/${folderId}`, { method: "DELETE" });

export const listWorkspaceItems = (
  caseId: number,
  params?: { folder?: string; file_type?: string },
): Promise<{ items: WorkspaceItemSummary[] }> => {
  const qs = new URLSearchParams();
  if (params?.folder) qs.set("folder", params.folder);
  if (params?.file_type) qs.set("file_type", params.file_type);
  const q = qs.toString();
  return fetchAPI(`/api/cases/${caseId}/workspace${q ? `?${q}` : ""}`);
};

export const getWorkspaceItem = (itemId: number): Promise<{ item: WorkspaceItemFull }> =>
  fetchAPI(`/api/workspace/${itemId}`);

export const createWorkspaceItem = (data: {
  case_id: number;
  name: string;
  file_type?: string;
  document_type?: string;
  folder?: string;
  folder_id?: number | null;
  content?: unknown;
  workspace_id?: number | null;
}): Promise<{ item: WorkspaceItemFull }> =>
  fetchAPI("/api/workspace", { method: "POST", body: JSON.stringify(data) });

export const updateWorkspaceItem = (
  itemId: number,
  data: { name?: string; content?: unknown; folder?: string; status?: string; file_type?: string; document_type?: string; metadata?: Record<string, unknown> | null },
): Promise<{ item: WorkspaceItemFull }> =>
  fetchAPI(`/api/workspace/${itemId}`, { method: "PATCH", body: JSON.stringify(data) });

export const updateWorkspaceBlock = (
  itemId: number,
  blockId: string,
  content: string,
): Promise<{ item: WorkspaceItemFull }> =>
  fetchAPI(`/api/workspace/${itemId}/blocks/${blockId}`, {
    method: "PATCH",
    body: JSON.stringify({ content }),
  });

export const deleteWorkspaceItem = (itemId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/workspace/${itemId}`, { method: "DELETE" });

// Business Vault
export interface VaultDocument {
  id: number;
  name: string;
  page_count: number | null;
  document_type: string | null;
}

export interface VaultItem {
  id: number;
  case_id: number | null;
  kind: string;
  name: string;
  status: string;
  notes: string | null;
  data: Record<string, unknown>;
  documents?: VaultDocument[];
  document_count: number;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export const listVaultItems = (
  params?: { case_id?: number; kind?: string },
): Promise<{ items: VaultItem[] }> => {
  const qs = new URLSearchParams();
  if (params?.case_id) qs.set("case_id", String(params.case_id));
  if (params?.kind) qs.set("kind", params.kind);
  const s = qs.toString();
  return fetchAPI(`/api/vault${s ? `?${s}` : ""}`);
};

export const getVaultItem = (itemId: number): Promise<{ item: VaultItem }> =>
  fetchAPI(`/api/vault/${itemId}`);

export const createVaultItem = (data: {
  case_id?: number | null;
  kind: string;
  name: string;
  status?: string;
  notes?: string | null;
  data?: Record<string, unknown>;
  created_by?: string;
}): Promise<{ item: VaultItem }> =>
  fetchAPI("/api/vault", { method: "POST", body: JSON.stringify(data) });

export const updateVaultItem = (
  itemId: number,
  data: { kind?: string; name?: string; status?: string; notes?: string | null; data?: Record<string, unknown>; case_id?: number | null },
): Promise<{ item: VaultItem }> =>
  fetchAPI(`/api/vault/${itemId}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteVaultItem = (itemId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/vault/${itemId}`, { method: "DELETE" });

export const attachVaultDocuments = (
  itemId: number,
  document_ids: number[],
): Promise<{ attached: number }> =>
  fetchAPI(`/api/vault/${itemId}/documents`, {
    method: "POST",
    body: JSON.stringify({ document_ids }),
  });

export const detachVaultDocument = (
  itemId: number,
  documentId: number,
): Promise<{ detached: boolean }> =>
  fetchAPI(`/api/vault/${itemId}/documents/${documentId}`, { method: "DELETE" });

// Tasks
export interface TaskDocument {
  id: number;
  name: string;
  page_count: number | null;
  document_type: string | null;
}

export interface Task {
  id: number;
  case_id: number;
  title: string;
  notes: string | null;
  status: "open" | "in_progress" | "blocked" | "complete";
  priority: "low" | "medium" | "high" | "urgent";
  assignee_id: string | null;
  deadline: string | null;
  completed_at: string | null;
  created_by: string | null;
  document_count: number;
  documents?: TaskDocument[];
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export const listTasks = (
  caseId: number,
  params?: { status?: string; assignee_id?: string; limit?: number },
): Promise<{ tasks: Task[] }> => {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.assignee_id) qs.set("assignee_id", params.assignee_id);
  if (params?.limit) qs.set("limit", String(params.limit));
  const s = qs.toString();
  return fetchAPI(`/api/cases/${caseId}/tasks${s ? `?${s}` : ""}`);
};

export const getTask = (taskId: number): Promise<{ task: Task }> =>
  fetchAPI(`/api/tasks/${taskId}`);

export const createTask = (
  caseId: number,
  data: { title: string; notes?: string; assignee_id?: string; deadline?: string; priority?: string; document_ids?: number[] },
): Promise<{ task: Task }> =>
  fetchAPI(`/api/cases/${caseId}/tasks`, { method: "POST", body: JSON.stringify(data) });

export const updateTask = (
  taskId: number,
  data: { title?: string; notes?: string; status?: string; priority?: string; assignee_id?: string; deadline?: string },
): Promise<{ task: Task }> =>
  fetchAPI(`/api/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(data) });

export const attachTaskDocuments = (
  taskId: number,
  document_ids: number[],
): Promise<{ task: Task; attached: number }> =>
  fetchAPI(`/api/tasks/${taskId}/documents`, { method: "POST", body: JSON.stringify({ document_ids }) });

export const detachTaskDocument = (
  taskId: number,
  documentId: number,
): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/tasks/${taskId}/documents/${documentId}`, { method: "DELETE" });

export const deleteTask = (taskId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/tasks/${taskId}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Calendar Events & Reminders
// ---------------------------------------------------------------------------

export interface CalendarEvent {
  id: number;
  case_id: number;
  workspace_id: number | null;
  title: string;
  description: string | null;
  start_time: string;
  end_time: string | null;
  all_day: boolean;
  category: "hearing" | "deposition" | "deadline" | "meeting" | "other";
  location: string | null;
  created_by: "user" | "agent";
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Reminder {
  id: number;
  case_id: number;
  event_id: number | null;
  title: string;
  description: string | null;
  remind_at: string;
  category: "hearing" | "deposition" | "deadline" | "meeting" | "other";
  status: "pending" | "fired" | "dismissed";
  created_by: "user" | "agent";
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

// Calendar Events
export const listCalendarEvents = (
  caseId: number,
  params?: { start_date?: string; end_date?: string; category?: string; limit?: number },
): Promise<{ count: number; events: CalendarEvent[] }> => {
  const qs = new URLSearchParams();
  if (params?.start_date) qs.set("start_date", params.start_date);
  if (params?.end_date) qs.set("end_date", params.end_date);
  if (params?.category) qs.set("category", params.category);
  if (params?.limit) qs.set("limit", String(params.limit));
  const s = qs.toString();
  return fetchAPI(`/api/cases/${caseId}/calendar/events${s ? `?${s}` : ""}`);
};

export const getCalendarEvent = (eventId: number): Promise<{ event: CalendarEvent & { reminders?: Reminder[] } }> =>
  fetchAPI(`/api/calendar/events/${eventId}`);

export const createCalendarEvent = (
  caseId: number,
  data: { title: string; start_time: string; end_time?: string; all_day?: boolean; category?: string; description?: string; location?: string },
): Promise<{ event: CalendarEvent }> =>
  fetchAPI(`/api/cases/${caseId}/calendar/events`, { method: "POST", body: JSON.stringify(data) });

export const updateCalendarEvent = (
  eventId: number,
  data: { title?: string; description?: string; start_time?: string; end_time?: string; all_day?: boolean; category?: string; location?: string },
): Promise<{ event: CalendarEvent }> =>
  fetchAPI(`/api/calendar/events/${eventId}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteCalendarEvent = (eventId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/calendar/events/${eventId}`, { method: "DELETE" });

// Reminders
export const listReminders = (
  caseId: number,
  params?: { status?: string; category?: string; event_id?: number; limit?: number },
): Promise<{ count: number; reminders: Reminder[] }> => {
  const qs = new URLSearchParams();
  if (params?.status) qs.set("status", params.status);
  if (params?.category) qs.set("category", params.category);
  if (params?.event_id != null) qs.set("event_id", String(params.event_id));
  if (params?.limit) qs.set("limit", String(params.limit));
  const s = qs.toString();
  return fetchAPI(`/api/cases/${caseId}/calendar/reminders${s ? `?${s}` : ""}`);
};

export const getReminder = (reminderId: number): Promise<{ reminder: Reminder }> =>
  fetchAPI(`/api/calendar/reminders/${reminderId}`);

export const createReminder = (
  caseId: number,
  data: { title: string; remind_at: string; event_id?: number; category?: string; description?: string },
): Promise<{ reminder: Reminder }> =>
  fetchAPI(`/api/cases/${caseId}/calendar/reminders`, { method: "POST", body: JSON.stringify(data) });

export const updateReminder = (
  reminderId: number,
  data: { title?: string; description?: string; remind_at?: string; category?: string; status?: string },
): Promise<{ reminder: Reminder }> =>
  fetchAPI(`/api/calendar/reminders/${reminderId}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteReminder = (reminderId: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/calendar/reminders/${reminderId}`, { method: "DELETE" });

// Health
export const healthCheck = () => fetchAPI("/api/health");

// ---------------------------------------------------------------------------
// Company Profiles
// ---------------------------------------------------------------------------

export interface CompanyProfile {
  id: number;
  name: string;
  content: Record<string, unknown>;
  source_docs: Array<{ document_id: number; document_name: string }>;
  status: "draft" | "complete";
  statement_draft_id?: number | null;
  created_at: string;
  updated_at: string;
}

export const listCompanyProfiles = (): Promise<{ profiles: CompanyProfile[] }> =>
  fetchAPI("/api/profiles");

export const getCompanyProfile = (id: number): Promise<{ profile: CompanyProfile }> =>
  fetchAPI(`/api/profiles/${id}`);

export const createCompanyProfile = (name: string): Promise<{ profile: CompanyProfile }> =>
  fetchAPI("/api/profiles", { method: "POST", body: JSON.stringify({ name }) });

export const updateCompanyProfile = (
  id: number,
  data: { name?: string; content?: Record<string, unknown>; status?: string; source_docs?: Array<{ document_id: number; document_name: string }> },
): Promise<{ profile: CompanyProfile }> =>
  fetchAPI(`/api/profiles/${id}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteCompanyProfile = (id: number): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/profiles/${id}`, { method: "DELETE" });

export const synthesizeProfile = (profileId: number): Promise<{ job_id: number; status: string }> =>
  fetchAPI(`/api/profiles/${profileId}/synthesize`, { method: "POST" });

export const generateCapabilityStatement = (profileId: number): Promise<{ job_id: number; status: string }> =>
  fetchAPI(`/api/profiles/${profileId}/generate-statement`, { method: "POST" });

// ---------------------------------------------------------------------------
// Correspondence
// ---------------------------------------------------------------------------

export interface CorrespondenceThread {
  id: number;
  case_id: number;
  title: string;
  status: "active" | "archived";
  item_count: number;
  last_activity: string | null;
  created_at: string;
  updated_at: string;
}

export interface CorrespondenceAttachment {
  id: number;
  document_id: number;
  document_name: string;
}

export interface CorrespondenceItem {
  id: number;
  thread_id: number;
  sender_party_id: number | null;
  sender_name: string | null;
  receiver_party_id: number | null;
  receiver_name: string | null;
  direction: "sent" | "received";
  notes: string | null;
  date_sent: string | null;
  date_received: string | null;
  attachments: CorrespondenceAttachment[];
  created_at: string;
  updated_at: string;
}

export const listCorrespondenceThreads = (
  caseId: number,
  status?: string,
): Promise<{ threads: CorrespondenceThread[] }> => {
  const qs = status ? `?status=${status}` : "";
  return fetchAPI(`/api/cases/${caseId}/correspondence/threads${qs}`);
};

export const createCorrespondenceThread = (
  caseId: number,
  data: { title: string },
): Promise<{ thread: CorrespondenceThread }> =>
  fetchAPI(`/api/cases/${caseId}/correspondence/threads`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateCorrespondenceThread = (
  threadId: number,
  data: { title?: string; status?: string },
): Promise<{ thread: CorrespondenceThread }> =>
  fetchAPI(`/api/correspondence/threads/${threadId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteCorrespondenceThread = (
  threadId: number,
): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/correspondence/threads/${threadId}`, { method: "DELETE" });

export const listCorrespondenceItems = (
  threadId: number,
): Promise<{ items: CorrespondenceItem[] }> =>
  fetchAPI(`/api/correspondence/threads/${threadId}/items`);

export const createCorrespondenceItem = (
  threadId: number,
  data: {
    sender_party_id?: number | null;
    receiver_party_id?: number | null;
    direction: string;
    notes?: string | null;
    date_sent?: string | null;
    date_received?: string | null;
    document_ids?: number[];
  },
): Promise<{ item: CorrespondenceItem }> =>
  fetchAPI(`/api/correspondence/threads/${threadId}/items`, {
    method: "POST",
    body: JSON.stringify(data),
  });

export const updateCorrespondenceItem = (
  itemId: number,
  data: {
    sender_party_id?: number | null;
    receiver_party_id?: number | null;
    direction?: string;
    notes?: string | null;
    date_sent?: string | null;
    date_received?: string | null;
  },
): Promise<{ item: CorrespondenceItem }> =>
  fetchAPI(`/api/correspondence/items/${itemId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });

export const deleteCorrespondenceItem = (
  itemId: number,
): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/correspondence/items/${itemId}`, { method: "DELETE" });

export const attachCorrespondenceDocument = (
  itemId: number,
  documentId: number,
): Promise<{ attachment: CorrespondenceAttachment }> =>
  fetchAPI(`/api/correspondence/items/${itemId}/attachments`, {
    method: "POST",
    body: JSON.stringify({ document_id: documentId }),
  });

export const detachCorrespondenceDocument = (
  itemId: number,
  documentId: number,
): Promise<{ deleted: boolean }> =>
  fetchAPI(`/api/correspondence/items/${itemId}/attachments/${documentId}`, {
    method: "DELETE",
  });

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
  message_count: number;
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

export const updateChatSession = (sessionId: number, data: { title?: string }): Promise<ChatSession> =>
  fetchAPI(`/api/chat/sessions/${sessionId}`, { method: "PATCH", body: JSON.stringify(data) });

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

// ---------------------------------------------------------------------------
// SAM.gov Databank Notices
// ---------------------------------------------------------------------------

export interface SamNotice {
  id: number;
  notice_id: string | null;
  opportunity_title: string;
  contract_opportunity_type: string | null;
  naics_code: string | null;
  naics_description: string | null;
  psc_code: string | null;
  current_set_aside: string | null;
  current_set_aside_code: string | null;
  sub_tier_name: string | null;
  contracting_office: string | null;
  pop_city: string | null;
  pop_state: string | null;
  pop_country: string | null;
  current_response_date: string | null;
  last_published_date: string | null;
  status: string | null;
  poc_name: string | null;
  poc_email: string | null;
  awardee_name: string | null;
  awardee_uei: string | null;
  attachment_count: number | null;
  ivl_enabled: boolean | null;
  description: string | null;
  upload_batch_id: string | null;
  source_csv: string | null;
  created_at: string;
}

export interface SamNoticesQuery {
  q?: string;
  naics_code?: string;
  naics_description?: string;
  psc_code?: string;
  contract_opportunity_type?: string;
  current_set_aside?: string;
  current_set_aside_code?: string;
  sub_tier_name?: string;
  pop_state?: string;
  pop_city?: string;
  status?: string;
  awardee_name?: string;
  awardee_uei?: string;
  notice_id?: string;
  contracting_office?: string;
  initiative?: string;
  response_date_from?: string;
  response_date_to?: string;
  published_date_from?: string;
  published_date_to?: string;
  has_attachments?: boolean;
  ivl_enabled?: boolean;
  limit?: number;
  offset?: number;
  order_by?: string;
  order_dir?: string;
}

export interface SamNoticesResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  results: SamNotice[];
}

export const querySamNotices = (body: SamNoticesQuery): Promise<SamNoticesResponse> =>
  fetchAPI("/api/sam-notices/query", { method: "POST", body: JSON.stringify(body) });

export const uploadSamNoticesCsv = (file: File): Promise<{
  batch_id: string;
  rows_in_csv: number;
  rows_inserted: number;
  duplicates_skipped: number;
  source: string;
}> => {
  const formData = new FormData();
  formData.append("file", file);
  const token = localStorage.getItem("vision_token");
  return fetch(`${API_BASE}/api/sam-notices/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  }).then((res) => {
    if (res.status === 401) {
      localStorage.removeItem("vision_token");
      localStorage.removeItem("vision_user");
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new Error("Session expired");
    }
    if (!res.ok) return res.json().then((err) => { throw new Error(err.detail || `HTTP ${res.status}`); });
    return res.json();
  });
};

export interface SamNoticeBatch {
  batch_id: string;
  source: string;
  rows: number;
  uploaded_at: string;
}

export const listSamNoticeBatches = (): Promise<{ batches: SamNoticeBatch[] }> =>
  fetchAPI("/api/sam-notices/batches");

export const deleteSamNoticeBatch = (batchId: string): Promise<{ deleted: number; batch_id: string }> =>
  fetchAPI(`/api/sam-notices/batches/${batchId}`, { method: "DELETE" });

export interface SolicitationLookup {
  solicitation_number: string;
  title: string;
  notice_id: string;
  ui_link: string;
  response_deadline: string | null;
  posted_date: string | null;
}

export const lookupSolicitationUrl = (sol: string): Promise<SolicitationLookup> =>
  fetchAPI(`/api/sam-notices/lookup?sol=${encodeURIComponent(sol)}`);

export const deleteSamNotice = (id: number): Promise<{ deleted: number }> =>
  fetchAPI(`/api/sam-notices/${id}`, { method: "DELETE" });

export const deleteAllSamNotices = (): Promise<{ deleted: number }> =>
  fetchAPI("/api/sam-notices/all", { method: "DELETE" });

// ---------------------------------------------------------------------------
// Subcontracting Leads (USASpending.gov)
// ---------------------------------------------------------------------------

export interface SubcontractingLead {
  id: number;
  external_id: string;
  award_id_piid: string;
  solicitation_identifier: string | null;
  idv_type: string | null;
  multiple_or_single_award: string | null;
  recipient_uei: string;
  recipient_name: string;
  recipient_parent_name: string | null;
  recipient_city: string | null;
  recipient_state: string | null;
  naics_code: string | null;
  naics_description: string | null;
  psc_code: string | null;
  psc_description: string | null;
  potential_value: number | null;
  current_value: number | null;
  base_action_date: string | null;
  ordering_period_end: string | null;
  pop_current_end: string | null;
  pop_potential_end: string | null;
  subcontracting_plan_code: string | null;
  subcontracting_plan: string | null;
  awarding_agency: string | null;
  awarding_sub_agency: string | null;
  set_aside_type: string | null;
  pool_id: string | null;
  pool_awardee_count: number | null;
  is_woman_owned: boolean | null;
  is_sdvosb: boolean | null;
  is_hubzone: boolean | null;
  is_8a: boolean | null;
  is_small_disadvantaged: boolean | null;
  is_minority_owned: boolean | null;
  pipeline_status: string;
  pipeline_category: string | null;
  pipeline_priority: string | null;
  pipeline_priority_score: number | null;
  pipeline_notes: string | null;
  outreach_status: string;
  outreach_last_contact: string | null;
  usaspending_permalink: string | null;
  upload_batch_id: string | null;
  source_csv: string | null;
  created_at: string;
  updated_at: string;
}

export interface SubLeadsQuery {
  pipeline_status?: string;
  pipeline_category?: string;
  pipeline_priority?: string;
  naics_code?: string;
  subcontracting_plan_code?: string;
  recipient_uei?: string;
  recipient_name?: string;
  q?: string;
  limit?: number;
  offset?: number;
  order_by?: string;
  order_dir?: string;
}

export interface SubLeadsResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  results: SubcontractingLead[];
}

export const querySubcontractingLeads = (body: SubLeadsQuery): Promise<SubLeadsResponse> =>
  fetchAPI("/api/subcontracting-leads/query", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const uploadSubLeadsCsv = (file: File): Promise<{
  batch_id: string;
  source: string;
  total_rows: number;
  inserted: number;
  updated: number;
  skipped: number;
  skipped_breakdown: Record<string, number>;
  errors: Array<{ row: number; piid?: string; error: string }>;
}> => {
  const formData = new FormData();
  formData.append("file", file);
  const token = localStorage.getItem("vision_token");
  return fetch(`${API_BASE}/api/subcontracting-leads/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  }).then((res) => {
    if (res.status === 401) {
      localStorage.removeItem("vision_token");
      localStorage.removeItem("vision_user");
      window.location.href = "/login";
      throw new Error("Session expired");
    }
    if (!res.ok) {
      return res.json().then((err) => { throw new Error(err.detail || `HTTP ${res.status}`); });
    }
    return res.json();
  });
};

export const processSubLeadsPools = (): Promise<{ pools_updated: number }> =>
  fetchAPI("/api/subcontracting-leads/process-pools", { method: "POST" });

export const getSubcontractingLead = (id: number): Promise<SubcontractingLead> =>
  fetchAPI(`/api/subcontracting-leads/${id}`);

export interface UpdateTriageBody {
  pipeline_priority?: string;
  pipeline_priority_score?: number;
  pipeline_notes?: string;
  pipeline_status?: string;
}

export const updateLeadTriage = (id: number, body: UpdateTriageBody): Promise<{ id: number; updated: boolean }> =>
  fetchAPI(`/api/subcontracting-leads/${id}/triage`, {
    method: "POST",
    body: JSON.stringify(body),
  });

export interface SubLeadsBatch {
  batch_id: string;
  source: string;
  rows: number;
  uploaded_at: string;
}

export const listSubLeadsBatches = (): Promise<{ batches: SubLeadsBatch[] }> =>
  fetchAPI("/api/subcontracting-leads/batches");

// ---------------------------------------------------------------------------
// Pipeline Processing
// ---------------------------------------------------------------------------

export interface ProcessBatchResult {
  batch_id: string;
  dry_run: boolean;
  total_rows: number;
  queued: number;
  skipped: number;
  duplicate: number;
  skipped_breakdown: Record<string, number>;
  errors: Array<{ sam_notice_id: number; notice_id: string; error: string }>;
}

export const processBatch = (
  batchId: string,
  dryRun: boolean = false,
): Promise<ProcessBatchResult> =>
  fetchAPI("/api/pipeline/process-batch", {
    method: "POST",
    body: JSON.stringify({ batch_id: batchId, dry_run: dryRun }),
  });

export const getBatchStatus = (
  batchId: string,
): Promise<{
  batch_id: string;
  pending: number;
  queued: number;
  skipped: number;
  duplicate: number;
  errors: number;
  total: number;
}> => fetchAPI(`/api/pipeline/batch-status/${batchId}`);

// ---------------------------------------------------------------------------
// Acquisition Gateway Forecasts
// ---------------------------------------------------------------------------

export interface ForecastOpportunity {
  id: number;
  title: string;
  description: string | null;
  source_url: string | null;
  agency: string | null;
  office: string | null;
  naics_code: string | null;
  naics_description: string | null;
  set_aside: string | null;
  place_of_performance: string | null;
  period_of_performance: string | null;
  fiscal_year: string | null;
  estimated_value_text: string | null;
  estimated_value_low: number | null;
  estimated_value_high: number | null;
  created_date: string | null;
  last_updated_date: string | null;
  upload_batch_id: string | null;
  created_at: string;
}

export interface ForecastQuery {
  q?: string;
  agency?: string;
  naics_code?: string;
  set_aside?: string;
  fiscal_year?: string;
  estimated_value_text?: string;
  value_under?: number;
  value_over?: number;
  office?: string;
  place_of_performance?: string;
  limit?: number;
  offset?: number;
  order_by?: string;
  order_dir?: string;
}

export interface ForecastResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  results: ForecastOpportunity[];
}

export const queryForecasts = (body: ForecastQuery): Promise<ForecastResponse> =>
  fetchAPI("/api/forecasts/query", { method: "POST", body: JSON.stringify(body) });

export const uploadForecastHtml = (file: File): Promise<{ batch_id: string; rows_inserted: number; source: string }> => {
  const formData = new FormData();
  formData.append("file", file);
  const token = localStorage.getItem("vision_token");
  return fetch(`${API_BASE}/api/forecasts/upload`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  }).then((res) => {
    if (res.status === 401) {
      localStorage.removeItem("vision_token");
      localStorage.removeItem("vision_user");
      if (typeof window !== "undefined") window.location.href = "/login";
      throw new Error("Session expired");
    }
    if (!res.ok) return res.json().then((err) => { throw new Error(err.detail || `HTTP ${res.status}`); });
    return res.json();
  });
};

export const deleteAllForecasts = (): Promise<{ deleted: number }> =>
  fetchAPI("/api/forecasts/all", { method: "DELETE" });

export const deleteForecast = (id: number): Promise<{ deleted: number }> =>
  fetchAPI(`/api/forecasts/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// DLA Batch Search
// ---------------------------------------------------------------------------

export interface DlaBatchRow {
  id: number;
  nsn: string;
  fsc: string | null;
  niin: string | null;
  nomenclature: string | null;
  amc: string | null;
  amsc: string | null;
  aac: string | null;
  competable: string | null;
  competability_notes: string | null;
  unit_price: number | null;
  ui: string | null;
  slc: string | null;
  ciic: string | null;
  dmil: string | null;
  hmic: string | null;
  crit_cd: string | null;
  approved_cage: string | null;
  approved_part: string | null;
  cage_company: string | null;
  cage_city: string | null;
  cage_state: string | null;
  vendor_name: string | null;
  contact_name: string | null;
  contact_email: string | null;
  contact_phone: string | null;
  website: string | null;
  is_small_business: string | null;
  qty: string | null;
  solicitation: string | null;
  purchase_request: string | null;
  source_file: string | null;
  created_at: string;
}

export interface DlaBatchResponse {
  total: number;
  limit: number;
  offset: number;
  count: number;
  results: DlaBatchRow[];
}

export interface DlaBatchStats {
  total: number;
  competable: number;
  with_vendor: number;
  with_email: number;
  priced: number;
  unique_nsns: number;
  unique_sols: number;
}

export const queryDlaBatch = (params: Record<string, string | number | undefined>): Promise<DlaBatchResponse> => {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== "") qs.set(k, String(v));
  });
  return fetchAPI(`/api/dla-batch/query?${qs.toString()}`);
};

export const getDlaBatchStats = (): Promise<DlaBatchStats> =>
  fetchAPI("/api/dla-batch/stats");

// ---------------------------------------------------------------------------
// Saved Reports
// ---------------------------------------------------------------------------

export interface SavedReport {
  id: number;
  case_id: number | null;
  name: string;
  data_source: "forecasts" | "sam_notices";
  query_filters: Record<string, unknown>;
  sort_by: string | null;
  sort_dir: "ASC" | "DESC";
  created_by: "agent" | "user";
  created_at: string;
  updated_at: string;
}

export interface CreateReportInput {
  name: string;
  data_source: "forecasts" | "sam_notices";
  query_filters: Record<string, unknown>;
  case_id?: number | null;
  sort_by?: string;
  sort_dir?: "ASC" | "DESC";
}

export const listReports = (caseId: number | null, dataSource?: string): Promise<{ reports: SavedReport[] }> => {
  const params = new URLSearchParams();
  if (caseId != null) params.set("case_id", String(caseId));
  if (dataSource) params.set("data_source", dataSource);
  return fetchAPI(`/api/reports?${params.toString()}`);
};

export const createReport = (data: CreateReportInput): Promise<{ report: SavedReport }> =>
  fetchAPI("/api/reports", { method: "POST", body: JSON.stringify(data) });

export const getReport = (id: number): Promise<{ report: SavedReport }> =>
  fetchAPI(`/api/reports/${id}`);

export const deleteReport = (id: number): Promise<{ deleted: number }> =>
  fetchAPI(`/api/reports/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// GA DOAS Opportunities
// ---------------------------------------------------------------------------

export interface GaDoasOpportunity {
  id: number; event_id: string; event_url: string | null;
  title: string; government_entity: string | null;
  start_date: string | null; end_date: string | null;
  ends_in: string | null; status: string | null;
  source_file: string | null; upload_batch_id: string | null; created_at: string;
}

export interface GaDoasQuery {
  q?: string; government_entity?: string; event_id?: string; status?: string;
  limit?: number; offset?: number; order_by?: string; order_dir?: string;
}

export interface GaDoasResponse {
  total: number; limit: number; offset: number; count: number; results: GaDoasOpportunity[];
}

export const queryGaDoas = (body: GaDoasQuery): Promise<GaDoasResponse> =>
  fetchAPI("/api/ga-doas/query", { method: "POST", body: JSON.stringify(body) });

export const uploadGaDoasHtml = (file: File): Promise<{ batch_id: string; rows_imported: number; rows_inserted: number; source: string }> => {
  const fd = new FormData(); fd.append("file", file);
  const token = localStorage.getItem("vision_token");
  return fetch(`${API_BASE}/api/ga-doas/upload`, { method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {}, body: fd })
    .then(r => { if (r.status === 401) { localStorage.clear(); window.location.href = "/login"; throw new Error("Session expired"); }
      if (!r.ok) return r.json().then(e => { throw new Error(e.detail || `HTTP ${r.status}`); }); return r.json(); });
};

export const deleteAllGaDoas = (): Promise<{ deleted: number }> =>
  fetchAPI("/api/ga-doas/all", { method: "DELETE" });

// ---------------------------------------------------------------------------
// DIBBS RFQs
// ---------------------------------------------------------------------------

export interface DibbsRfq {
  id: number; row_num: number | null; nsn: string | null; mil_spec: string | null;
  nomenclature: string; tech_docs: string | null; solicitation: string;
  status: string | null; purchase_request: string | null; qty: number | null;
  issued: string | null; return_by: string | null; fsc_code: string | null;
  unit_price: number | null; estimated_total: number | null; ui: string | null; moe: string | null;
  upload_batch_id: string | null; source_file: string | null; created_at: string;
}

export interface DibbsQuery {
  q?: string; nsn?: string; fsc_code?: string; solicitation?: string; status?: string;
  limit?: number; offset?: number; order_by?: string; order_dir?: string;
}

export interface DibbsResponse { total: number; limit: number; offset: number; count: number; results: DibbsRfq[]; }

export const queryDibbs = (body: DibbsQuery): Promise<DibbsResponse> =>
  fetchAPI("/api/dibbs/query", { method: "POST", body: JSON.stringify(body) });

export const uploadDibbsCsv = (file: File): Promise<{ batch_id: string; rows_imported: number; rows_inserted: number; source: string }> => {
  const fd = new FormData(); fd.append("file", file);
  const t = localStorage.getItem("vision_token");
  return fetch(`${API_BASE}/api/dibbs/upload`, { method: "POST", headers: t ? { Authorization: `Bearer ${t}` } : {}, body: fd })
    .then(r => { if (r.status === 401) { localStorage.clear(); window.location.href = "/login"; throw new Error("Session expired"); }
      if (!r.ok) return r.json().then(e => { throw new Error(e.detail || `HTTP ${r.status}`); }); return r.json(); });
};

export const deleteAllDibbs = (): Promise<{ deleted: number }> =>
  fetchAPI("/api/dibbs/all", { method: "DELETE" });

// ---------------------------------------------------------------------------
// Admin — User Management
// ---------------------------------------------------------------------------

export interface AdminUser {
  id: string;
  username: string;
  email: string | null;
  role: string;
  is_active: boolean;
  last_login: string | null;
  created_at: string;
  updated_at: string;
}

export const listUsers = (): Promise<{ users: AdminUser[] }> =>
  fetchAPI("/api/admin/users");

export const createUser = (data: {
  username: string;
  password: string;
  email?: string;
  role?: string;
}): Promise<AdminUser> =>
  fetchAPI("/api/admin/users", { method: "POST", body: JSON.stringify(data) });

export const updateUser = (
  userId: string,
  data: { email?: string; role?: string; is_active?: boolean }
): Promise<AdminUser> =>
  fetchAPI(`/api/admin/users/${userId}`, { method: "PATCH", body: JSON.stringify(data) });

// ---------------------------------------------------------------------------
// Quotes
// ---------------------------------------------------------------------------

export interface Quote {
  id: number;
  external_id: string;
  solicitation_id: number;
  created_by: string;
  created_by_username?: string;
  notes: string | null;
  amount: number | null;
  poc_name: string | null;
  poc_email: string | null;
  poc_phone: string | null;
  status: "draft" | "pending_site_visit" | "submitted" | "awarded" | "lost";
  document_id: number | null;
  created_at: string;
  updated_at: string;
}

export const createQuote = (
  solicitationId: number,
  data: { notes?: string; amount?: number; poc_name?: string; poc_email?: string; poc_phone?: string }
): Promise<Quote> =>
  fetchAPI(`/api/solicitations/${solicitationId}/quotes`, { method: "POST", body: JSON.stringify(data) });

export const listQuotes = (solicitationId: number): Promise<{ quotes: Quote[] }> =>
  fetchAPI(`/api/solicitations/${solicitationId}/quotes`);

export const updateQuote = (
  solicitationId: number,
  quoteId: number,
  data: { notes?: string; amount?: number; poc_name?: string; poc_email?: string; poc_phone?: string; status?: string }
): Promise<Quote> =>
  fetchAPI(`/api/solicitations/${solicitationId}/quotes/${quoteId}`, { method: "PATCH", body: JSON.stringify(data) });

export const deleteQuote = (solicitationId: number, quoteId: number): Promise<{ deleted: number }> =>
  fetchAPI(`/api/solicitations/${solicitationId}/quotes/${quoteId}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Vendors — Registration
// ---------------------------------------------------------------------------

export interface VendorProfile {
  id: number;
  external_id: string;
  user_id: string;
  business_name: string;
  vendor_type: "individual" | "service" | "manufacturer";
  uei: string | null;
  cage_code: string | null;
  capabilities: string | null;
  website: string | null;
  phone: string | null;
  city: string | null;
  state: string | null;
  bonding_capacity: number | null;
  status: string;
  created_at: string;
}

export const registerVendor = (data: {
  username: string;
  password: string;
  email?: string;
  business_name: string;
  vendor_type: string;
  phone?: string;
  website?: string;
  uei?: string;
  capabilities?: string;
}): Promise<{ user: { id: string; username: string; role: string }; profile: Record<string, unknown> }> => {
  const token = typeof window !== "undefined" ? localStorage.getItem("vision_token") : null;
  return fetch(`${API_BASE}/api/vendors/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(data),
  }).then((res) => {
    if (!res.ok) return res.json().then((err) => { throw new Error(err.detail || `HTTP ${res.status}`); });
    return res.json();
  });
};

export const getMyVendorProfile = (): Promise<VendorProfile> =>
  fetchAPI("/api/vendors/profile");

export const updateMyVendorProfile = (data: Record<string, unknown>): Promise<VendorProfile> =>
  fetchAPI("/api/vendors/profile", { method: "PATCH", body: JSON.stringify(data) });

// ---------------------------------------------------------------------------
// Vendors — Master Teaming Agreement (MTA)
// ---------------------------------------------------------------------------

export interface MtaAgreement {
  id: number;
  agreement_type: string;
  vendor_user_id: string;
  solicitation_id: number | null;
  document_id: number | null;
  status: string;
  executed_at: string | null;
  expires_at: string | null;
  signed_name: string | null;
  signed_title: string | null;
  signed_ip: string | null;
  signed_user_agent: string | null;
  content_hash: string | null;
  template_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface MtaStatusResponse {
  signed: boolean;
  agreement?: MtaAgreement | null;
  document_id?: number | null;
  preview_url?: string | null;
  preview_name?: string | null;
}

export const getMyMtaStatus = (): Promise<MtaStatusResponse> =>
  fetchAPI("/api/vendors/mta");

export const signMyMta = (data: {
  signed_name: string;
  signed_title: string;
  consent: boolean;
}): Promise<{ agreement: MtaAgreement; already_signed: boolean }> =>
  fetchAPI("/api/vendors/mta/sign", { method: "POST", body: JSON.stringify(data) });
