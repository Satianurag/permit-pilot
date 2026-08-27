import { Link } from "react-router-dom";
import { formatStatus } from "../lib/formatStatus";

interface Props {
  casesByStatus: Record<string, number>;
}

const STATUS_ORDER = [
  "in_review",
  "awaiting_clerk",
  "awaiting_applicant",
  "approved",
  "changes_requested",
] as const;

export default function CaseStatusChart({ casesByStatus }: Props) {
  const entries = STATUS_ORDER.filter((status) => (casesByStatus[status] ?? 0) > 0).map((status) => ({
    status,
    count: casesByStatus[status] ?? 0,
  }));

  const otherEntries = Object.entries(casesByStatus)
    .filter(([status]) => !STATUS_ORDER.includes(status as (typeof STATUS_ORDER)[number]))
    .map(([status, count]) => ({ status, count }));

  const all = [...entries, ...otherEntries];
  const max = Math.max(...all.map((row) => row.count), 1);

  if (all.length === 0) {
    return <p className="text-sm text-pp-muted py-4 text-center">No cases in the store yet.</p>;
  }

  return (
    <div className="space-y-3" role="list" aria-label="Cases by status">
      {all.map(({ status, count }) => (
        <div key={status} role="listitem">
          <div className="flex items-center justify-between gap-2 mb-1">
            <Link
              to={`/permits?status=${encodeURIComponent(status)}`}
              className="text-sm font-medium text-pp-navy hover:text-pp-accent"
            >
              {formatStatus(status)}
            </Link>
            <span className="text-sm font-semibold text-pp-navy tabular-nums">{count}</span>
          </div>
          <div className="pp-status-bar" aria-hidden>
            <span className="pp-status-bar-fill" style={{ width: `${(count / max) * 100}%` }} />
          </div>
        </div>
      ))}
    </div>
  );
}
