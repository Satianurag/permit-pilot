import { FormEvent, useState } from "react";
import { Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { isAuthenticated, setSession, setToken } from "../lib/auth";
import { errorMessage } from "../lib/errors";

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const expired = params.get("expired") === "1";

  if (isAuthenticated()) {
    const from = location.state as { from?: { pathname?: string; search?: string; hash?: string } } | null;
    const target =
      from?.from?.pathname
        ? `${from.from.pathname}${from.from.search ?? ""}${from.from.hash ?? ""}`
        : api.consumeReturnPath();
    return <Navigate to={target} replace />;
  }

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const token = await api.login(username.trim(), password);
      setToken(token.access_token);
      const profile = await api.me();
      setSession(token.access_token, profile);
      const from = location.state as { from?: { pathname?: string; search?: string; hash?: string } } | null;
      const target =
        from?.from?.pathname
          ? `${from.from.pathname}${from.from.search ?? ""}${from.from.hash ?? ""}`
          : api.consumeReturnPath();
      navigate(target, { replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pp-login-shell">
      <aside className="pp-login-brand" aria-hidden="true">
        <div>
          <div className="pp-login-brand-mark">PP</div>
          <p className="text-[0.65rem] uppercase tracking-[0.2em] text-blue-200/80 mt-6">NYC Department of Buildings</p>
          <h1 className="pp-display text-4xl font-semibold mt-3">Permit Pilot</h1>
          <p className="pp-login-brand-quote mt-4">
            Clerk workspace for NYC permit review — tasks, case files, department distribution, and signed agent
            gateway controls in one place.
          </p>
        </div>
        <p className="text-xs text-blue-200/60">Fortified Enterprise Fleet · All Things Agentic</p>
      </aside>

      <div className="pp-login-form-wrap">
        <main className="pp-login-card">
          <div className="lg:hidden mb-6">
            <p className="text-[0.65rem] uppercase tracking-[0.2em] text-pp-muted">NYC Department of Buildings</p>
            <h1 className="pp-display text-2xl font-semibold text-pp-navy mt-1">Permit Pilot</h1>
          </div>

          <h2 className="pp-display text-xl font-semibold text-pp-navy">Sign in</h2>
          <p className="mt-1.5 text-sm text-pp-muted">Access your review queue, dashboard, and case files.</p>

          {expired && (
            <p className="pp-login-alert pp-login-alert--warn" role="status">
              Your session expired. Sign in again to return to your case.
            </p>
          )}

          {error && (
            <p className="pp-login-alert pp-login-alert--error" role="alert">
              {error}
            </p>
          )}

          <form className="mt-6 space-y-4" onSubmit={submit}>
            <div>
              <label htmlFor="username" className="pp-login-field-label">
                Username
              </label>
              <input
                id="username"
                required
                autoComplete="username"
                className="pp-input mt-1.5"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div>
              <label htmlFor="password" className="pp-login-field-label">
                Password
              </label>
              <div className="pp-login-password-wrap">
                <input
                  id="password"
                  required
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  className="pp-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="pp-login-password-toggle"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-pressed={showPassword}
                  aria-controls="password"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="pp-btn-primary w-full mt-2">
              {loading ? "Signing in…" : "Sign in"}
            </button>
          </form>

          <p className="pp-login-notice">
            Production NYC.ID SSO is planned. This demo uses clerk accounts in Firestore. Sessions end when you close
            the browser tab. Failed sign-in attempts are logged server-side.
          </p>
        </main>
      </div>
    </div>
  );
}
