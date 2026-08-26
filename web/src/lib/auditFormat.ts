import { AuditEvent } from "./api";

const DETAIL_LIMIT = 200;

export function formatAuditDetail(action: string, detail: string): { summary: string; truncated: boolean } {
  const normalized = action.toLowerCase();
  if (normalized.includes("workflow_step_completed")) {
    return { summary: "Department workflow step completed", truncated: false };
  }
  if (detail.startsWith("Intake packet redacted:")) {
    return { summary: "Intake packet redacted — applicant PII removed before storage", truncated: false };
  }
  if (detail.length > DETAIL_LIMIT) {
    return { summary: `${detail.slice(0, DETAIL_LIMIT)}…`, truncated: true };
  }
  return { summary: detail, truncated: false };
}

export type GroupedAuditEvent =
  | { kind: "single"; event: AuditEvent; summary: string; truncated: boolean }
  | { kind: "workflow_group"; count: number; at: string; actor: string };

export function groupAuditEvents(events: AuditEvent[]): GroupedAuditEvent[] {
  const grouped: GroupedAuditEvent[] = [];
  let workflowRun = 0;
  let workflowActor = "";
  let workflowAt = "";

  const flushWorkflow = () => {
    if (workflowRun === 0) return;
    grouped.push({
      kind: "workflow_group",
      count: workflowRun,
      actor: workflowActor,
      at: workflowAt,
    });
    workflowRun = 0;
  };

  for (const event of events) {
    if (event.action.toLowerCase().includes("workflow_step_completed")) {
      workflowRun += 1;
      workflowActor = event.actor;
      workflowAt = event.at;
      continue;
    }
    flushWorkflow();
    const { summary, truncated } = formatAuditDetail(event.action, event.detail);
    grouped.push({ kind: "single", event, summary, truncated });
  }
  flushWorkflow();
  return grouped;
}

const DEPT_ORDER = ["zoning", "building", "fire", "utilities", "landmarks", "housing"];

export function sortDepartmentReviews<T extends { department: string }>(rows: T[]): T[] {
  return [...rows].sort((a, b) => {
    const ia = DEPT_ORDER.indexOf(a.department);
    const ib = DEPT_ORDER.indexOf(b.department);
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib);
  });
}
