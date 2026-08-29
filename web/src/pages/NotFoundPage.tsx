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
            <Link to="/work" className="pp-btn-primary text-sm">
              My work
            </Link>
            <Link to="/find" className="pp-btn-secondary text-sm">
              Find a case
            </Link>
          </div>
        }
      />
    </div>
  );
}
