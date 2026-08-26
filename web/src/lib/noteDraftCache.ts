const prefix = "pp-note:";

export function readNoteDraft(caseId: string): string | null {
  try {
    return sessionStorage.getItem(prefix + caseId);
  } catch {
    return null;
  }
}

export function writeNoteDraft(caseId: string, note: string): void {
  try {
    if (note.trim()) sessionStorage.setItem(prefix + caseId, note);
    else sessionStorage.removeItem(prefix + caseId);
  } catch {
    /* quota / private mode */
  }
}
