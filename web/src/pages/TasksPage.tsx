import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import IntakeModal from "../components/IntakeModal";
import { StatusBadge } from "../components/StatusBadge";
import { api, Task } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [intakeOpen, setIntakeOpen] = useState(false);

  const load = () => {
    setLoading(true);
    api
      .listTasks()
      .then(setTasks)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-pp-navy">My Tasks</h2>
          <p className="text-sm text-slate-600">Open permit reviews requiring clerk action.</p>
        </div>
        <button
          type="button"
          onClick={() => setIntakeOpen(true)}
          className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm font-medium"
        >
          New intake
        </button>
      </div>
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}
      {loading ? (
        <p className="text-sm text-slate-600">Loading tasks…</p>
      ) : tasks.length === 0 ? (
        <EmptyState
          title="No open tasks"
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
        <div className="overflow-x-auto rounded-lg border border-pp-border bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Task
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Type
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Status
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Opened
                </th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <tr key={task.id} className="border-t border-pp-border hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link className="text-pp-accent font-medium hover:underline" to={`/cases/${task.case_id}`}>
                      {task.title}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{formatStatus(task.task_type)}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={task.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500">{new Date(task.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <IntakeModal open={intakeOpen} onClose={() => setIntakeOpen(false)} onCreated={load} />
    </div>
  );
}
