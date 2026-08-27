import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import AlertList from "../components/AlertList";
import CaseStatusChart from "../components/CaseStatusChart";
import DepartmentRollup from "../components/DepartmentRollup";
import IntakeModal from "../components/IntakeModal";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import QuickActions from "../components/QuickActions";
import Skeleton from "../components/Skeleton";
import StatCard from "../components/StatCard";
import { api, DashboardSummary } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { getStoredUser } from "../lib/auth";

function greeting(name: string) {
  const hour = new Date().getHours();
  const salutation = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  const first = name.split(" ")[0] ?? name;
  return `${salutation}, ${first}`;
}

export default function DashboardPage() {
  const user = getStoredUser();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [intakeOpen, setIntakeOpen] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .dashboardSummary()
      .then((nextSummary) => {
        setSummary(nextSummary);
        setError(null);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  if (loading && !summary) {
    return (
      <div className="space-y-6">
        <Skeleton rows={2} label="Loading dashboard" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} rows={2} label="Loading metric" />
          ))}
        </div>
        <Skeleton rows={8} label="Loading panels" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={new Date().toLocaleDateString(undefined, {
          weekday: "long",
          month: "long",
          day: "numeric",
        })}
        title={user ? greeting(user.full_name) : "Clerk dashboard"}
        subtitle="At-a-glance metrics and alerts. Open My Tasks for the full queue, Activity for the audit feed, and Permit search for dossier lookup."
        action={
          <div className="flex flex-wrap gap-2">
            <button type="button" className="pp-btn-secondary" onClick={load} disabled={loading}>
              Refresh
            </button>
            <button type="button" className="pp-btn-primary" onClick={() => setIntakeOpen(true)}>
              + New intake
            </button>
          </div>
        }
      />

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}

      {summary && (
        <>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Open reviews"
              value={summary.open_tasks}
              meta={`${summary.my_tasks} assigned to you`}
              href="/tasks"
            />
            <StatCard
              label="Overdue on review clock"
              value={summary.overdue_tasks}
              meta="5-day internal target"
              href="/tasks"
              tone={summary.overdue_tasks > 0 ? "danger" : "default"}
            />
            <StatCard
              label="Awaiting applicant"
              value={summary.awaiting_applicant}
              meta={`${summary.awaiting_clerk} back with clerk`}
              href="/permits?status=awaiting_applicant"
              tone={summary.awaiting_applicant > 0 ? "warn" : "default"}
            />
            <StatCard
              label="Unassigned work"
              value={summary.unassigned_tasks}
              meta={`${summary.in_review} in active review`}
              href="/tasks?assign=unassigned"
              tone={summary.unassigned_tasks > 0 ? "warn" : "default"}
            />
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Panel title="Quick actions" subtitle="Jump into daily clerk work.">
              <QuickActions onNewIntake={() => setIntakeOpen(true)} />
            </Panel>

            <Panel
              title="Needs attention"
              subtitle="Failed departments, overdue clocks, interrupted workflows, and applicant responses."
              className="xl:col-span-2"
              action={
                summary.alerts.length > 0 ? (
                  <Link to="/tasks" className="text-sm font-medium text-pp-accent hover:underline">
                    Open task queue
                  </Link>
                ) : undefined
              }
            >
              <AlertList alerts={summary.alerts} />
            </Panel>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Panel title="Case pipeline" subtitle="Dossiers by status — click a bar to filter search.">
              <CaseStatusChart casesByStatus={summary.cases_by_status} />
              <Link to="/permits" className="pp-btn-secondary w-full mt-4 text-center">
                Search all permits
              </Link>
            </Panel>

            <Panel
              title="Department rollup"
              subtitle="Pass / fail / checking across open cases."
              className="xl:col-span-2"
            >
              <DepartmentRollup rollup={summary.department_rollup} />
            </Panel>
          </div>

          <Panel title="Operational signals" subtitle="Live counts from the case store.">
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 text-sm">
              <li className="pp-card p-4 flex flex-col gap-1">
                <span className="text-pp-muted">Stale distribution (&gt;24h)</span>
                <span className="pp-display text-2xl font-semibold text-pp-navy">{summary.stale_distribution}</span>
              </li>
              <li className="pp-card p-4 flex flex-col gap-1">
                <span className="text-pp-muted">Failed dept reviews</span>
                <span className="pp-display text-2xl font-semibold text-pp-navy">{summary.failed_department_reviews}</span>
              </li>
              <li className="pp-card p-4 flex flex-col gap-1">
                <span className="text-pp-muted">Interrupted workflows</span>
                <span className="pp-display text-2xl font-semibold text-pp-navy">{summary.interrupted_workflows}</span>
              </li>
              <li className="pp-card p-4 flex flex-col gap-1">
                <span className="text-pp-muted">Last refreshed</span>
                <span className="font-medium text-pp-navy">{new Date(summary.generated_at).toLocaleString()}</span>
              </li>
            </ul>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link to="/activity" className="pp-btn-secondary">
                View audit activity feed
              </Link>
              <Link to="/tasks" className="pp-btn-secondary">
                Open full task queue
              </Link>
            </div>
          </Panel>
        </>
      )}

      <IntakeModal open={intakeOpen} onClose={() => setIntakeOpen(false)} onCreated={load} />
    </div>
  );
}
