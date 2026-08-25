/** Internal review target — not a statutory NYC DOB SLA. */
export const REVIEW_WINDOW_DAYS = 5;

export type ClockKind = "overdue" | "due_soon" | "on_track";

export interface ReviewClock {
  due: Date;
  kind: ClockKind;
  label: string;
}

export function reviewDueAt(createdAt: string): Date {
  const due = new Date(createdAt);
  due.setUTCDate(due.getUTCDate() + REVIEW_WINDOW_DAYS);
  return due;
}

export function reviewClock(createdAt: string, now = new Date()): ReviewClock {
  const due = reviewDueAt(createdAt);
  const ms = due.getTime() - now.getTime();
  const kind: ClockKind = ms < 0 ? "overdue" : ms < 24 * 60 * 60 * 1000 ? "due_soon" : "on_track";
  const when = due.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  const label =
    kind === "overdue"
      ? `Overdue · internal target ${when}`
      : kind === "due_soon"
        ? `Due soon · internal target ${when}`
        : `Internal target ${when}`;
  return { due, kind, label };
}

export function clockClass(kind: ClockKind): string {
  if (kind === "overdue") return "text-red-800 font-medium";
  if (kind === "due_soon") return "text-amber-800 font-medium";
  return "text-slate-600";
}
