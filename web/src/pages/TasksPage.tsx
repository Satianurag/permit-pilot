import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import IntakeModal from "../components/IntakeModal";
import { api, Task } from "../lib/api";

export default function TasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [intakeOpen, setIntakeOpen] = useState(false);

  useEffect(() => {
    api.listTasks()
      .then(setTasks)
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-2xl font-semibold text-pp-navy">My Tasks</h2>
          <p className="text-sm text-slate-600">Assigned permit reviews requiring clerk action.</p>
        </div>
        <button
          type="button"
          onClick={() => setIntakeOpen(true)}
          className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm font-medium"
        >
          New intake
        </button>
      </div>
      {error && <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3">{error}</p>}
      <div className="bg-white border border-pp-border rounded-lg overflow-hidden shadow-sm">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-left text-slate-600">
            <tr>
              <th className="px-4 py-3 font-medium">Task</th>
              <th className="px-4 py-3 font-medium">Type</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Opened</th>
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
                <td className="px-4 py-3 text-slate-600">{task.task_type}</td>
                <td className="px-4 py-3 capitalize">{task.status}</td>
                <td className="px-4 py-3 text-slate-500">{new Date(task.created_at).toLocaleString()}</td>
              </tr>
            ))}
            {tasks.length === 0 && !error && (
              <tr>
                <td colSpan={4} className="px-4 py-8 text-center text-slate-500">
                  No open tasks.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <IntakeModal open={intakeOpen} onClose={() => setIntakeOpen(false)} />
    </div>
  );
}
