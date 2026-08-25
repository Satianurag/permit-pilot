import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { clearSession, getStoredUser } from "../lib/auth";

interface Props {
  onOpenAgents?: () => void;
}

export default function AppShell({ onOpenAgents }: Props) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const user = getStoredUser();

  const signOut = () => {
    clearSession();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>
      <header className="bg-pp-navy text-white border-b border-pp-slate">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-widest text-blue-200">NYC Department of Buildings</p>
            <p className="text-lg font-semibold leading-tight">Permit Pilot</p>
          </div>
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <nav className="flex flex-wrap gap-1" aria-label="Primary">
              <Link
                to="/tasks"
                aria-current={pathname.startsWith("/tasks") ? "page" : undefined}
                className={`px-3 py-1.5 rounded-md ${pathname.startsWith("/tasks") ? "bg-white/15" : "hover:bg-white/10"}`}
              >
                My Tasks
              </Link>
              <Link
                to="/permits"
                aria-current={pathname.startsWith("/permits") ? "page" : undefined}
                className={`px-3 py-1.5 rounded-md ${pathname.startsWith("/permits") ? "bg-white/15" : "hover:bg-white/10"}`}
              >
                Permit search
              </Link>
              {onOpenAgents && (
                <button type="button" onClick={onOpenAgents} className="px-3 py-1.5 rounded-md hover:bg-white/10">
                  Agent registry
                </button>
              )}
            </nav>
            {user && (
              <div className="flex items-center gap-2 border-l border-white/20 pl-2 ml-1">
                <span className="text-blue-100">{user.full_name}</span>
                <button type="button" onClick={signOut} className="px-3 py-1.5 rounded-md hover:bg-white/10">
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </header>
      <main id="main-content" tabIndex={-1} className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-6 pb-28">
        <Outlet />
      </main>
    </div>
  );
}
