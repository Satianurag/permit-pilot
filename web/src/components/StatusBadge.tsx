import { formatStatus } from "../lib/formatStatus";

const styles: Record<string, string> = {
  pass: "bg-emerald-50 text-emerald-900 border-emerald-200",
  fail: "bg-red-50 text-red-900 border-red-200",
  checking: "bg-amber-50 text-amber-900 border-amber-200",
  needs_info: "bg-slate-100 text-slate-800 border-slate-200",
  skipped: "bg-slate-50 text-slate-700 border-slate-200",
  interrupted: "bg-amber-50 text-amber-900 border-amber-200",
  in_review: "bg-blue-50 text-blue-900 border-blue-200",
  awaiting_clerk: "bg-violet-50 text-violet-900 border-violet-200",
  awaiting_applicant: "bg-amber-50 text-amber-900 border-amber-200",
  approved: "text-slate-800",
  changes_requested: "bg-orange-50 text-orange-900 border-orange-200",
  open: "bg-blue-50 text-blue-900 border-blue-200",
  resolved: "text-slate-800",
  completed: "text-slate-700",
  overdue: "bg-red-50 text-red-900 border-red-200",
  due_soon: "bg-amber-50 text-amber-900 border-amber-200",
  on_track: "bg-slate-100 text-slate-800 border-slate-200",
};

const PLAIN = new Set(["approved", "resolved", "completed"]);

export function StatusBadge({ status }: { status: string }) {
  const label = formatStatus(status);
  if (PLAIN.has(status)) {
    return <span className="text-sm text-slate-700">{label}</span>;
  }
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded border text-xs font-medium capitalize ${styles[status] ?? styles.needs_info}`}
      aria-label={`Status: ${label}`}
    >
      {label}
    </span>
  );
}
