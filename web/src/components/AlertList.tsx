import { Link } from "react-router-dom";
import { DashboardAlert } from "../lib/api";
import { formatStatus } from "../lib/formatStatus";

const kindTone: Record<string, string> = {
  overdue_task: "bg-red-500",
  department_fail: "bg-red-500",
  workflow_failed: "bg-red-500",
  workflow_interrupted: "bg-amber-500",
  needs_info: "bg-slate-500",
  stale_distribution: "bg-amber-500",
  applicant_response: "bg-emerald-500",
};

interface Props {
  alerts: DashboardAlert[];
}

export default function AlertList({ alerts }: Props) {
  if (alerts.length === 0) {
    return (
      <p className="text-sm text-pp-muted py-6 text-center border border-dashed rounded-xl border-pp-border">
        No urgent items — queue is clear on review clock and distribution checks.
      </p>
    );
  }

  return (
    <ul className="space-y-2">
      {alerts.map((alert) => (
        <li key={alert.id}>
          <Link to={alert.href} className="pp-alert block no-underline text-inherit">
            <span
              className={`pp-alert-dot ${kindTone[alert.kind] ?? "bg-pp-blue"}`}
              aria-hidden
            />
            <span className="min-w-0 flex-1">
              <span className="block text-sm font-semibold text-pp-navy">{alert.title}</span>
              <span className="block text-sm text-pp-muted mt-0.5 line-clamp-2">{alert.detail}</span>
              <span className="block text-xs text-pp-muted mt-1 capitalize">{formatStatus(alert.kind.replace(/_/g, " "))}</span>
            </span>
            <span className="text-pp-accent text-sm font-medium shrink-0">Open →</span>
          </Link>
        </li>
      ))}
    </ul>
  );
}
