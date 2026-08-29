import { Link } from "react-router-dom";
import { DashboardActivity } from "../lib/api";
import { formatAuditDetail } from "../lib/auditFormat";
import { formatStatus } from "../lib/formatStatus";

interface Props {
  items: DashboardActivity[];
  emptyMessage?: string;
}

export default function ActivityFeed({ items, emptyMessage = "No audit events yet." }: Props) {
  if (items.length === 0) {
    return <p className="text-sm text-pp-muted py-8 text-center">{emptyMessage}</p>;
  }

  return (
    <ul className="divide-y divide-[var(--color-pp-border)]">
      {items.map((item) => {
        const { summary, truncated } = formatAuditDetail(item.action, item.detail);
        return (
          <li key={item.id} className="py-4 flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <Link
                  to={`/cases/${item.case_id}?tab=history&from=activity`}
                  className="text-sm font-semibold text-pp-navy hover:text-pp-accent"
                >
                  {item.address}
                </Link>
                <span className="text-xs text-pp-muted">·</span>
                <span className="text-xs font-medium text-pp-muted uppercase tracking-wide">
                  {formatStatus(item.action)}
                </span>
              </div>
              <p className="text-sm text-pp-muted mt-1">{summary}</p>
              {truncated && (
                <Link
                  to={`/cases/${item.case_id}?tab=history&from=activity`}
                  className="text-xs text-pp-accent hover:underline mt-1 inline-block"
                >
                  Read full entry in case audit
                </Link>
              )}
              <p className="text-xs text-pp-muted mt-2">{item.actor}</p>
            </div>
            <time className="text-xs text-pp-muted shrink-0 tabular-nums" dateTime={item.at}>
              {new Date(item.at).toLocaleString()}
            </time>
          </li>
        );
      })}
    </ul>
  );
}
