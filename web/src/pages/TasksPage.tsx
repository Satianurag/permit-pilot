import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import IntakeModal from "../components/IntakeModal";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/Toast";
import { api, Task } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";
import { getStoredUser } from "../lib/auth";
import { clockClass, reviewClock } from "../lib/reviewClock";

const FILTERS = [
  { id: "open", label: "Open" },
  { id: "completed", label: "Completed" },
  { id: "all", label: "All" },
] as const;

const ASSIGN_FILTERS = [
  { id: "all", label: "All open work" },
  { id: "mine", label: "Assigned to me" },
  { id: "unassigned", label: "Unassigned" },
] as const;

export default function TasksPage() {
  const { push } = useToast();
  const [params, setParams] = useSearchParams();
  const rawStatus = params.get("status");
  const filter: (typeof FILTERS)[number]["id"] =
    rawStatus === "completed" || rawStatus === "all" ? rawStatus : "open";
  const rawAssign = params.get("assign");
  const assignFilter: (typeof ASSIGN_FILTERS)[number]["id"] =
    rawAssign === "mine" || rawAssign === "unassigned" ? rawAssign : "all";
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [intakeOpen, setIntakeOpen] = useState(false);
  const [claimingId, setClaimingId] = useState<string | null>(null);
  const currentUser = getStoredUser();

  const setFilter = (id: (typeof FILTERS)[number]["id"]) => {
    const next = new URLSearchParams(params);
    if (id === "open") next.delete("status");
    else next.set("status", id);
    setParams(next, { replace: true });
  };

  const setAssignFilter = (id: (typeof ASSIGN_FILTERS)[number]["id"]) => {
    const next = new URLSearchParams(params);
    if (id === "all") next.delete("assign");
    else next.set("assign", id);
    setParams(next, { replace: true });
  };

  const load = (status: string, assign: (typeof ASSIGN_FILTERS)[number]["id"]) => {
    setLoading(true);
    api
      .listTasks(status, assign === "mine", assign === "unassigned")
      .then(setTasks)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => load(filter, assignFilter), [filter, assignFilter]);

  const claimTask = async (task: Task) => {
    setClaimingId(task.id);
    try {
      await api.claimTask(task.id);
      push("Task assigned to you.", "success");
      load(filter, assignFilter);
    } catch (err) {
      push(errorMessage(err), "error");
    } finally {
      setClaimingId(null);
    }
  };

  const sorted = useMemo(
    () =>
      [...tasks].sort((a, b) => reviewClock(a.created_at).due.getTime() - reviewClock(b.created_at).due.getTime()),
    [tasks],
  );

  const overdueCount = sorted.filter((task) => reviewClock(task.created_at).kind === "overdue" && task.status === "open")
    .length;

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Tasks"
        subtitle="Oldest review clock first. Open a row to land on Distribution — the work, not the cover sheet."
        action={
          <button type="button" onClick={() => setIntakeOpen(true)} className="pp-btn-primary">
            + New intake
          </button>
        }
      />

      <div className="flex flex-wrap items-center gap-3">
        <div className="pp-segment" role="group" aria-label="Task status">
          {FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={filter === item.id}
              onClick={() => setFilter(item.id)}
              className="pp-segment-btn"
            >
              {item.label}
            </button>
          ))}
        </div>
        <div className="pp-segment" role="group" aria-label="Assignee filter">
          {ASSIGN_FILTERS.map((item) => (
            <button
              key={item.id}
              type="button"
              aria-pressed={assignFilter === item.id}
              onClick={() => setAssignFilter(item.id)}
              className="pp-segment-btn pp-segment-btn-secondary"
            >
              {item.label}
            </button>
          ))}
        </div>
        {overdueCount > 0 && (
          <p className="text-sm text-red-800 font-medium">{overdueCount} overdue on a 5-day review clock</p>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3" role="alert">
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
            <button type="button" onClick={() => setIntakeOpen(true)} className="pp-btn-primary">
              Start new intake
            </button>
          }
        />
      ) : (
        <div className="pp-table-wrap">
          <table className="pp-table">
            <caption className="sr-only">Permit review tasks sorted by review clock</caption>
            <thead>
              <tr>
                <th scope="col">Task</th>
                <th scope="col">Type</th>
                <th scope="col">Review clock</th>
                <th scope="col">Assignee</th>
                <th scope="col">Status</th>
                <th scope="col">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((task) => {
                const clock = reviewClock(task.created_at);
                const canClaim =
                  task.status === "open" &&
                  (!task.assignee || task.assignee !== currentUser?.username);
                return (
                  <tr key={task.id} className="relative">
                    <td>
                      <Link
                        className="text-pp-accent font-medium hover:underline after:absolute after:inset-0"
                        to={`/cases/${task.case_id}?tab=distribution&from=tasks`}
                      >
                        {task.title}
                      </Link>
                    </td>
                    <td className="text-pp-muted">{formatStatus(task.task_type)}</td>
                    <td className={task.status === "open" ? clockClass(clock.kind) : "text-pp-muted"}>
                      {task.status === "open" ? clock.label : "—"}
                    </td>
                    <td className="text-pp-muted">{task.assignee ?? "Unassigned"}</td>
                    <td>
                      <StatusBadge status={task.status} />
                    </td>
                    <td className="relative z-10">
                      {canClaim && (
                        <button
                          type="button"
                          disabled={claimingId === task.id}
                          onClick={() => void claimTask(task)}
                          className="text-sm font-medium text-pp-accent hover:underline disabled:opacity-50"
                        >
                          {claimingId === task.id ? "Claiming…" : "Claim"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <IntakeModal open={intakeOpen} onClose={() => setIntakeOpen(false)} onCreated={() => load(filter, assignFilter)} />
    </div>
  );
}
