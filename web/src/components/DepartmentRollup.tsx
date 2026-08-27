import { DashboardDepartmentRollup } from "../lib/api";
import { formatStatus } from "../lib/formatStatus";

interface Props {
  rollup: DashboardDepartmentRollup[];
}

function total(row: DashboardDepartmentRollup) {
  return row.pass_count + row.fail_count + row.checking_count + row.needs_info_count;
}

export default function DepartmentRollup({ rollup }: Props) {
  if (rollup.length === 0) {
    return (
      <p className="text-sm text-pp-muted py-4 text-center">
        Department counts appear once open cases have distribution reviews.
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {rollup.map((row) => {
        const sum = total(row) || 1;
        return (
          <div key={row.department}>
            <div className="flex items-center justify-between gap-2 mb-1.5">
              <span className="text-sm font-medium text-pp-navy capitalize">{formatStatus(row.department)}</span>
              <span className="text-xs text-pp-muted">{sum} review{sum === 1 ? "" : "s"} on active cases</span>
            </div>
            <div className="pp-dept-bar" role="img" aria-label={`${row.department} distribution breakdown`}>
              {row.pass_count > 0 && (
                <span
                  className="pp-dept-bar-seg-pass"
                  style={{ width: `${(row.pass_count / sum) * 100}%` }}
                  title={`${row.pass_count} pass`}
                />
              )}
              {row.fail_count > 0 && (
                <span
                  className="pp-dept-bar-seg-fail"
                  style={{ width: `${(row.fail_count / sum) * 100}%` }}
                  title={`${row.fail_count} fail`}
                />
              )}
              {row.checking_count > 0 && (
                <span
                  className="pp-dept-bar-seg-checking"
                  style={{ width: `${(row.checking_count / sum) * 100}%` }}
                  title={`${row.checking_count} checking`}
                />
              )}
              {row.needs_info_count > 0 && (
                <span
                  className="pp-dept-bar-seg-needs"
                  style={{ width: `${(row.needs_info_count / sum) * 100}%` }}
                  title={`${row.needs_info_count} needs info`}
                />
              )}
            </div>
            <div className="flex flex-wrap gap-3 mt-2 text-xs text-pp-muted">
              {row.pass_count > 0 && <span className="text-emerald-700">{row.pass_count} pass</span>}
              {row.fail_count > 0 && <span className="text-red-700">{row.fail_count} fail</span>}
              {row.checking_count > 0 && <span className="text-amber-700">{row.checking_count} checking</span>}
              {row.needs_info_count > 0 && <span>{row.needs_info_count} needs info</span>}
            </div>
          </div>
        );
      })}
      <div className="flex flex-wrap gap-4 pt-2 text-xs text-pp-muted border-t border-pp-border">
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-emerald-700" /> Pass</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-red-600" /> Fail</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-amber-600" /> Checking</span>
        <span className="inline-flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-slate-500" /> Needs info</span>
      </div>
    </div>
  );
}
