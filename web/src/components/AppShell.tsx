import { Link, Outlet, useLocation } from "react-router-dom";

interface Props {
  onOpenAgents?: () => void;
}

export default function AppShell({ onOpenAgents }: Props) {
  const { pathname } = useLocation();
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-pp-navy text-white border-b border-pp-slate">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-200">NYC Department of Buildings</p>
            <h1 className="text-xl font-semibold">Permit Pilot</h1>
          </div>
          <nav className="flex gap-2 text-sm items-center">
            <Link
              to="/tasks"
              className={`px-3 py-1.5 rounded-md ${pathname.startsWith("/tasks") ? "bg-white/15" : "hover:bg-white/10"}`}
            >
              My Tasks
            </Link>
            {onOpenAgents && (
              <button
                type="button"
                onClick={onOpenAgents}
                className="px-3 py-1.5 rounded-md hover:bg-white/10"
              >
                Agent Catalog
              </button>
            )}
          </nav>
        </div>
      </header>
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-6">
        <Outlet />
      </main>
    </div>
  );
}
