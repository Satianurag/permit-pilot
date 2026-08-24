import { formatStatus } from "../lib/formatStatus";

const styles: Record<string, string> = {
  pass: "bg-emerald-100 text-emerald-800 border-emerald-200",
  fail: "bg-red-100 text-red-800 border-red-200",
  checking: "bg-amber-100 text-amber-800 border-amber-200",
  needs_info: "bg-slate-100 text-slate-700 border-slate-200",
  in_review: "bg-blue-100 text-blue-800 border-blue-200",
  awaiting_clerk: "bg-violet-100 text-violet-800 border-violet-200",
  awaiting_applicant: "bg-amber-100 text-amber-800 border-amber-200",
  approved: "bg-emerald-100 text-emerald-800 border-emerald-200",
  changes_requested: "bg-orange-100 text-orange-800 border-orange-200",
  open: "bg-blue-100 text-blue-800 border-blue-200",
  resolved: "bg-emerald-100 text-emerald-800 border-emerald-200",
  completed: "bg-slate-100 text-slate-700 border-slate-200",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex px-2 py-0.5 rounded border text-xs font-medium uppercase ${styles[status] ?? styles.needs_info}`}
      aria-label={`Status: ${formatStatus(status)}`}
    >
      {formatStatus(status)}
    </span>
  );
}
