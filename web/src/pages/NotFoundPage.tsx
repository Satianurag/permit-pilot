import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <EmptyState
        title="Page not found"
        description="That route does not exist in Permit Pilot. Return to your task queue or search for a dossier."
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <Link to="/dashboard" className="pp-btn-primary text-sm">
              Dashboard
            </Link>
            <Link to="/tasks" className="pp-btn-secondary text-sm">
              My Tasks
            </Link>
            <Link to="/activity" className="pp-btn-secondary text-sm">
              Activity
            </Link>
            <Link to="/permits" className="pp-btn-secondary text-sm">
              Permit search
            </Link>
          </div>
        }
      />
    </div>
  );
}
