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

function apiBase(): string {
  return import.meta.env.VITE_API_BASE ?? "/api";
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body?: unknown, headers?: Record<string, string>): Promise<T> {
  const res = await fetch(`${apiBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...headers },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<T>;
}

export const api = {
  listTasks: () => get<Task[]>("/tasks"),
  getCase: (id: string) => get<Case>(`/cases/${id}`),
  getDistribution: (id: string) => get<DepartmentReview[]>(`/cases/${id}/distribution`),
  getClaims: (id: string) => get<Claim[]>(`/cases/${id}/claims`),
  getAudit: (id: string) => get<AuditEvent[]>(`/cases/${id}/audit`),
  getWorkflow: (id: string) => get<WorkflowStep[]>(`/cases/${id}/workflow`),
  getTrace: (id: string) => get<TraceSpan[]>(`/cases/${id}/trace`),
  listAgents: () => get<AgentCard[]>("/agents"),
  orchestrate: (id: string) => post<{ summary: string; model: string }>(`/cases/${id}/orchestrate`),
  runGcpWorkflow: (id: string) => post<{ execution_id: string }>(`/cases/${id}/workflow/gcp-run`),
  getObservability: (caseId?: string) =>
    get<{ cloud_trace_url: string | null; langfuse_url: string | null; gcp_workflows_url: string | null }>(
      `/config/observability${caseId ? `?case_id=${caseId}` : ""}`
    ),
  refreshDistribution: (id: string) => post<DepartmentReview[]>(`/cases/${id}/distribution/refresh`),
  intake: (payload: IntakePayload) => post<Case>("/cases/intake", payload),
  resumeWorkflow: (id: string) => post<{ step: WorkflowStep | null; steps: WorkflowStep[] }>(`/cases/${id}/workflow/resume`),
  simulateCrash: (id: string) => post<WorkflowStep>(`/cases/${id}/workflow/simulate-crash`),
  invokeAgent: (name: string, signature: string, caseId?: string) =>
    post<{ status: string }>(`/agents/${name}/invoke`, undefined, {
      "X-Agent-Signature": signature,
      ...(caseId ? { "X-Case-Id": caseId } : {}),
    }),
  createClaim: (id: string, message: string) => post<Claim>(`/cases/${id}/claims`, { message }),
  decide: (id: string, decision: string, note: string) =>
    post<Case>(`/cases/${id}/decision`, { decision, note }),
};
