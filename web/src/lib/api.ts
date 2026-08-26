import { clearSession, getToken } from "./auth";
import { parseApiError } from "./errors";
import { consumeReturnPath, saveReturnPath } from "./returnPath";

export type ReviewStatus = "checking" | "pass" | "fail" | "needs_info";

export interface Task {
  id: string;
  case_id: string;
  title: string;
  task_type: string;
  status: string;
  assignee: string | null;
  created_at: string;
}

export interface Case {
  id: string;
  address: string;
  bbl: string;
  bin: string;
  work_type: string;
  owner: string;
  borough: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface EvidenceItem {
  source: string;
  dataset_id: string;
  label: string;
  value: unknown;
}

export interface DepartmentReview {
  department: string;
  status: ReviewStatus;
  summary: string;
  findings: string[];
  evidence: EvidenceItem[];
  citations: { code: string; excerpt: string; source_url?: string | null }[];
  updated_at: string;
}

export interface Claim {
  id: string;
  case_id: string;
  message: string;
  status: string;
  response_message: string | null;
  notification_channel: string | null;
  notification_reference: string | null;
  notified_at: string | null;
  manual_dob_now_sent: boolean;
  created_at: string;
  responded_at: string | null;
}

export interface RelatedPermit {
  job_number: string | null;
  work_type: string | null;
  status: string | null;
  filing_date: string | null;
}

export interface ParcelContext {
  latitude: number | null;
  longitude: number | null;
  map_url: string | null;
  zoning_district: string | null;
}

export interface ClerkBriefing {
  summary: string;
  model: string;
  generated_at: string;
  generated_by: string;
}

export interface ConditionTemplate {
  id: string;
  label: string;
  code: string;
}

export interface AddressMatch {
  address: string;
  bbl: string;
  bin: string;
  borough: string;
  owner: string;
  zoning_district: string;
}

export interface AgentCard {
  name: string;
  description: string;
  skills: string[];
  tools: string[];
  signed: boolean;
  fingerprint: string;
}

export interface WorkflowStep {
  name: string;
  department: string | null;
  status: "pending" | "running" | "completed" | "failed" | "interrupted";
  detail: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface TraceSpan {
  id: string;
  case_id: string;
  name: string;
  actor: string;
  status: string;
  detail: string;
  parent_id: string | null;
  started_at: string;
  ended_at: string | null;
  duration_ms: number | null;
  attributes: Record<string, string>;
}

export interface IntakePayload {
  address: string;
  bbl: string;
  bin?: string;
  work_type: string;
  owner?: string;
  borough?: string | null;
  packet_text?: string;
  packet_filename?: string | null;
  packet_content_type?: string | null;
  plan_filename?: string | null;
  plan_content_type?: string | null;
  plan_pdf_base64?: string | null;
}

export interface IntakeDocument {
  redacted_text: string;
  pii_findings: string[];
  stored_at: string;
  filename: string | null;
  content_type: string | null;
  has_pdf: boolean;
}

export interface CaseBundle {
  case: Case;
  distribution: DepartmentReview[];
  claims: Claim[];
  audit: AuditEvent[];
  workflow: WorkflowStep[];
  trace: TraceSpan[];
  observability: {
    cloud_trace_url: string | null;
    langfuse_url: string | null;
    gcp_workflows_url: string | null;
  };
  document: IntakeDocument | null;
  related_permits: RelatedPermit[];
  parcel: ParcelContext | null;
  briefing: ClerkBriefing | null;
}

export interface AuditEvent {
  id: string;
  case_id: string;
  actor: string;
  action: string;
  detail: string;
  at: string;
}

export interface ClerkProfile {
  username: string;
  full_name: string;
  role: string;
}

function apiBase(): string {
  return import.meta.env.VITE_API_BASE ?? "/api";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${apiBase()}${path}`, { ...init, headers });
  if (res.status === 401) {
    const returnPath = `${window.location.pathname}${window.location.search}${window.location.hash}`;
    saveReturnPath(returnPath);
    clearSession();
    const login = `/login?expired=1`;
    window.location.href = login;
    throw new Error("Your session expired. Sign in again.");
  }
  if (!res.ok) throw new Error(await parseApiError(res));
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body ? JSON.stringify(body) : undefined,
  });
}

export const api = {
  login: async (username: string, password: string) => {
    const body = new URLSearchParams({ username, password });
    const res = await fetch(`${apiBase()}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) throw new Error(await parseApiError(res));
    return res.json() as Promise<{ access_token: string; token_type: string }>;
  },
  me: () => get<ClerkProfile>("/auth/me"),
  listTasks: (status = "open", mine = false, unassigned = false) => {
    const params = new URLSearchParams({ status });
    if (mine) params.set("mine", "true");
    if (unassigned) params.set("unassigned", "true");
    return get<Task[]>(`/tasks?${params.toString()}`);
  },
  claimTask: (taskId: string) => post<Task>(`/tasks/${taskId}/claim`),
  listCases: (q?: string, status?: string) => {
    const params = new URLSearchParams();
    if (q?.trim()) params.set("q", q.trim());
    if (status?.trim()) params.set("status", status.trim());
    const query = params.toString();
    return get<Case[]>(`/cases${query ? `?${query}` : ""}`);
  },
  resolveAddress: (address: string, borough: string) =>
    get<{ matches: AddressMatch[] }>(
      `/nyc/resolve-address?address=${encodeURIComponent(address)}&borough=${encodeURIComponent(borough)}`,
    ),
  listConditions: () => get<ConditionTemplate[]>("/config/conditions"),
  updateCase: (id: string, patch: Partial<Pick<Case, "address" | "bbl" | "bin" | "work_type" | "owner" | "borough">>) =>
    request<Case>(`/cases/${id}`, { method: "PATCH", body: JSON.stringify(patch) }),
  getCase: (id: string) => get<Case>(`/cases/${id}`),
  getCaseBundle: (id: string) => get<CaseBundle>(`/cases/${id}/bundle`),
  getCaseContext: (id: string) =>
    get<{ related_permits: RelatedPermit[]; parcel: ParcelContext | null }>(`/cases/${id}/context`),
  getPlanPdf: (id: string) =>
    get<{ filename: string; content_type: string; pdf_base64: string }>(`/cases/${id}/documents/pdf`),
  refreshDistribution: (id: string) => post<DepartmentReview[]>(`/cases/${id}/distribution/refresh`),
  refreshBinDepartments: (id: string) =>
    post<DepartmentReview[]>(`/cases/${id}/distribution/refresh-bin-departments`),
  intake: (payload: IntakePayload) => post<Case>("/cases/intake", payload),
  previewRedaction: (packetText: string) =>
    post<{ redacted_text: string; findings: string[] }>("/cases/intake/preview-redaction", {
      packet_text: packetText,
    }),
  createClaim: (id: string, message: string) => post<Claim>(`/cases/${id}/claims`, { message }),
  markClaimDobNowSent: (caseId: string, claimId: string) =>
    post<Claim>(`/cases/${caseId}/claims/${claimId}/mark-dob-now-sent`),
  respondToClaim: (caseId: string, claimId: string, message: string) =>
    post<Claim>(`/cases/${caseId}/claims/${claimId}/respond`, { message }),
  decide: (id: string, decision: string, note: string, override = false) =>
    post<Case>(`/cases/${id}/decision`, { decision, note, override }),
  orchestrate: (id: string) => post<{ summary: string; model: string }>(`/cases/${id}/orchestrate`),
  resumeWorkflow: (id: string) => post<{ step: unknown; steps: WorkflowStep[] }>(`/cases/${id}/workflow/resume`),
  interruptWorkflow: (id: string) => post<{ step: WorkflowStep; steps: WorkflowStep[] }>(`/cases/${id}/workflow/interrupt`),
  startGcpWorkflow: (id: string) => post<{ execution_id: string; case_id: string }>(`/cases/${id}/workflow/gcp-run`),
  listAgents: () => get<AgentCard[]>("/agents"),
  invokeAgent: (name: string, signature: string | null, caseId?: string) =>
    request<{ status: string; message: string }>(`/agents/${name}/invoke`, {
      method: "POST",
      headers: {
        ...(signature ? { "X-Agent-Signature": signature } : {}),
        ...(caseId ? { "X-Case-Id": caseId } : {}),
      },
    }),
  consumeReturnPath,
};
