import { Link, Outlet, useLocation, useNavigate } from "react-router-dom";
import { clearSession, getStoredUser } from "../lib/auth";

const NAV = [
  { to: "/dashboard", label: "Home", short: "Home" },
  { to: "/tasks", label: "My Tasks", short: "Tasks" },
  { to: "/activity", label: "Activity", short: "Activity" },
  { to: "/permits", label: "Permit search", short: "Search" },
  { to: "/agents", label: "Agent registry", short: "Agents" },
] as const;

const TOPBAR_COPY: Record<string, { kicker: string; title: string }> = {
  "/dashboard": { kicker: "Clerk workspace", title: "Home · overview and alerts" },
  "/tasks": { kicker: "Clerk workspace", title: "My tasks · review queue" },
  "/activity": { kicker: "Clerk workspace", title: "Activity · audit feed" },
  "/permits": { kicker: "Clerk workspace", title: "Permit search · dossier lookup" },
  "/agents": { kicker: "Clerk workspace", title: "Agent registry · signed allowlist" },
};

function topbarCopy(pathname: string) {
  if (pathname.startsWith("/cases/")) {
    return { kicker: "Case file", title: "Review · distribution · audit trail" };
  }
  const match = NAV.find((item) =>
    item.to === "/dashboard" ? pathname === "/dashboard" || pathname === "/" : pathname.startsWith(item.to),
  );
  return match ? TOPBAR_COPY[match.to] : TOPBAR_COPY["/dashboard"];
}

export default function AppShell() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const user = getStoredUser();
  const copy = topbarCopy(pathname);

  const signOut = () => {
    clearSession();
    navigate("/login");
  };

  const isActive = (path: string) =>
    path === "/dashboard" ? pathname === "/dashboard" || pathname === "/" : pathname.startsWith(path);

  return (
    <div className="pp-app-shell">
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      <aside className="pp-sidebar" aria-label="Clerk navigation">
        <div className="pp-sidebar-brand">
          <p className="text-[0.65rem] uppercase tracking-[0.2em] text-blue-200/80">NYC Department of Buildings</p>
          <p className="pp-display text-xl font-semibold mt-1">Permit Pilot</p>
        </div>
        <nav className="pp-sidebar-nav">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              aria-current={isActive(item.to) ? "page" : undefined}
              className="pp-sidebar-link"
            >
              <NavIcon path={item.to} />
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="pp-sidebar-footer">
          {user && (
            <div className="mb-3 px-1">
              <p className="text-sm font-medium truncate">{user.full_name}</p>
              <p className="text-xs text-blue-200/70 capitalize">{user.role.replace(/_/g, " ")}</p>
            </div>
          )}
          <button type="button" onClick={signOut} className="pp-sidebar-link w-full text-left">
            Sign out
          </button>
        </div>
      </aside>

      <div className="pp-main-column">
        <header className="pp-topbar">
          <div className="lg:hidden w-full min-w-0">
            <p className="pp-display text-lg font-semibold text-pp-navy">Permit Pilot</p>
            <nav className="pp-mobile-nav mt-2" aria-label="Primary">
              {NAV.map((item) => (
                <Link key={item.to} to={item.to} aria-current={isActive(item.to) ? "page" : undefined}>
                  {item.short}
                </Link>
              ))}
            </nav>
          </div>
          <div className="hidden lg:block min-w-0">
            <p className="text-xs uppercase tracking-widest text-pp-muted">{copy.kicker}</p>
            <p className="text-sm font-medium text-pp-navy truncate">{copy.title}</p>
          </div>
          <div className="flex items-center gap-2 ml-auto shrink-0">
            {user && <span className="hidden sm:inline text-sm text-pp-muted truncate max-w-[12rem]">{user.full_name}</span>}
            <Link to="/tasks" className="pp-btn-primary text-sm py-2">
              Open queue
            </Link>
          </div>
        </header>

        <main id="main-content" tabIndex={-1} className="pp-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavIcon({ path }: { path: string }) {
  const common = "inline-flex h-8 w-8 items-center justify-center rounded-lg bg-white/10 text-xs font-bold";
  if (path === "/dashboard") return <span className={common}>⌂</span>;
  if (path === "/tasks") return <span className={common}>☰</span>;
  if (path === "/activity") return <span className={common}>↺</span>;
  if (path === "/agents") return <span className={common}>AI</span>;
  return <span className={common}>⌕</span>;
}
