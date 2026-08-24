import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import IntakeModal from "../components/IntakeModal";
import Skeleton from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { api, Task } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";
import { clockClass, reviewClock } from "../lib/reviewClock";

const FILTERS = [
  { id: "open", label: "Open" },
  { id: "completed", label: "Completed" },
  { id: "all", label: "All" },
] as const;

export default function TasksPage() {
  const [params, setParams] = useSearchParams();
  const rawStatus = params.get("status");
  const filter: (typeof FILTERS)[number]["id"] =
    rawStatus === "completed" || rawStatus === "all" ? rawStatus : "open";
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [intakeOpen, setIntakeOpen] = useState(false);

  const setFilter = (id: (typeof FILTERS)[number]["id"]) => {
    const next = new URLSearchParams(params);
    if (id === "open") next.delete("status");
    else next.set("status", id);
    setParams(next, { replace: true });
  };

  const load = (status: string) => {
    setLoading(true);
    api
      .listTasks(status)
      .then(setTasks)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(filter), [filter]);

  const sorted = useMemo(
    () =>
      [...tasks].sort((a, b) => reviewClock(a.created_at).due.getTime() - reviewClock(b.created_at).due.getTime()),
    [tasks],
  );

  const overdueCount = sorted.filter((task) => reviewClock(task.created_at).kind === "overdue" && task.status === "open")
    .length;

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-pp-navy">My Tasks</h2>
          <p className="text-sm text-slate-600">
            Oldest review clock first. Open a row to land on Distribution — the work, not the cover sheet.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setIntakeOpen(true)}
          className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm font-medium"
        >
          New intake
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex gap-1" role="group" aria-label="Task status">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={filter === item.id}
              onClick={() => setFilter(item.id)}
              className={`px-3 py-1.5 text-sm rounded-md border ${
                filter === item.id
                  ? "bg-pp-navy text-white border-pp-navy"
                  : "bg-white border-pp-border text-slate-700"
              }`}
            >
              {item.label}
            </button>
          ))}
        </div>
        {overdueCount > 0 && (
          <p className="text-sm text-red-800">{overdueCount} overdue on a 5-day review clock</p>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}
      {loading ? (
        <Skeleton rows={6} label="Loading tasks" />
      ) : sorted.length === 0 ? (
        <EmptyState
          title="No tasks in this view"
          description="When distribution reviews or applicant responses need attention, they will appear here."
          action={
            <button
              type="button"
              onClick={() => setIntakeOpen(true)}
              className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm"
            >
              Start new intake
            </button>
          }
        />
      ) : (
        <div className="table-scroll rounded-lg border border-pp-border bg-white" tabIndex={0}>
          <table className="min-w-full text-sm">
            <caption className="sr-only">Permit review tasks sorted by review clock</caption>
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">
                  Task
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Type
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Review clock
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((task) => {
                const clock = reviewClock(task.created_at);
                return (
                  <tr key={task.id} className="relative border-t border-pp-border hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link
                        className="text-pp-accent font-medium hover:underline after:absolute after:inset-0"
                        to={`/cases/${task.case_id}?tab=distribution&from=tasks`}
                      >
                        {task.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-slate-600">{formatStatus(task.task_type)}</td>
                    <td className={`px-4 py-3 ${clockClass(clock.kind)}`}>{clock.label}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={task.status} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <IntakeModal open={intakeOpen} onClose={() => setIntakeOpen(false)} onCreated={() => load(filter)} />
    </div>
  );
}
