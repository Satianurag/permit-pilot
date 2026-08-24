const prefix = "pp-briefing:";

export function readBriefing(caseId: string): string | null {
  try {
    return sessionStorage.getItem(prefix + caseId);
  } catch {
    return null;
  }
}

export function writeBriefing(caseId: string, summary: string): void {
  try {
    sessionStorage.setItem(prefix + caseId, summary);
  } catch {
    /* quota / private mode */
  }
}

