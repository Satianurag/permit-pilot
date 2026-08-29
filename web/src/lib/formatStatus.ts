const GLOSSARY: Record<string, string> = {
  in_review: "In review",
  awaiting_clerk: "Awaiting clerk",
  awaiting_applicant: "Awaiting applicant",
  changes_requested: "Changes requested",
  needs_info: "Needs information",
  distribution_review: "Review this case",
  claim_response: "Applicant replied",
  checking: "Checking city records",
  pass: "Clear",
  fail: "Objections",
  skipped: "Not needed",
  interrupted: "Interrupted",
  running: "Running",
  pending: "Pending",
  open: "Open",
  completed: "Completed",
  resolved: "Resolved",
  approved: "Approved",
  intake: "Intake",
  pii_redacted: "PII redacted",
  briefing_generated: "Briefing generated",
  claim_opened: "Claim opened",
  claim_responded: "Claim responded",
  workflow_resumed: "Workflow resumed",
  workflow_interrupted: "Workflow interrupted",
  plan_uploaded: "Plan uploaded",
  request_changes: "Request changes",
  approve: "Approve",
};

export function formatStatus(status: string): string {
  if (GLOSSARY[status]) return GLOSSARY[status];
  return status.replaceAll("_", " ");
}
