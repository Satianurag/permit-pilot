import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";

export default function NotFoundPage() {
  return (
    <div className="min-h-screen bg-pp-surface flex items-center justify-center px-4">
      <EmptyState
        title="Page not found"
        description="That route does not exist in Permit Pilot. Return to your task queue or search for a dossier."
        action={
          <div className="flex flex-wrap justify-center gap-2">
            <Link to="/tasks" className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm">
              My Tasks
            </Link>
            <Link to="/permits" className="px-4 py-2 rounded-md border border-pp-border text-sm">
              Permit search
            </Link>
          </div>
        }
      />
    </div>
  );
}
