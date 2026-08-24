import { clearSession, getToken } from "./auth";
import { parseApiError } from "./errors";

export type ReviewStatus = "checking" | "pass" | "fail" | "needs_info";

export interface Task {
  id: string;
  case_id: string;
  title: string;
  task_type: string;
  status: string;
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
  created_at: string;
  responded_at: string | null;
}

export interface AuditEvent {
  id: string;
  case_id: string;
  actor: string;
  action: string;
  detail: string;
  at: string;
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
}

export interface IntakeDocument {
  redacted_text: string;
  pii_findings: string[];
  stored_at: string;
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
    clearSession();
    window.location.href = "/login";
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
  listTasks: () => get<Task[]>("/tasks"),
  listCases: (q?: string) => get<Case[]>(`/cases${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  getCaseBundle: (id: string) => get<CaseBundle>(`/cases/${id}/bundle`),
  refreshDistribution: (id: string) => post<DepartmentReview[]>(`/cases/${id}/distribution/refresh`),
  intake: (payload: IntakePayload) => post<Case>("/cases/intake", payload),
  createClaim: (id: string, message: string) => post<Claim>(`/cases/${id}/claims`, { message }),
  respondToClaim: (caseId: string, claimId: string, message: string) =>
    post<Claim>(`/cases/${caseId}/claims/${claimId}/respond`, { message }),
  decide: (id: string, decision: string, note: string) =>
    post<Case>(`/cases/${id}/decision`, { decision, note }),
  orchestrate: (id: string) => post<{ summary: string; model: string }>(`/cases/${id}/orchestrate`),
  listAgents: () => get<AgentCard[]>("/agents"),
};
