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
    <div className="min-h-screen bg-pp-surface flex items-center justify-center px-4">
      <div className="w-full max-w-md rounded-xl border border-pp-border bg-white p-8">
        <p className="text-xs uppercase tracking-widest text-slate-500">NYC Department of Buildings</p>
        <h1 className="mt-1 text-2xl font-semibold text-pp-navy">Permit Pilot</h1>
        <p className="mt-2 text-sm text-slate-600">Clerk sign-in for the review queue and case files.</p>
        {expired && (
          <p className="mt-4 text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-md p-3" role="status">
            Your session expired. Sign in again to return to your case.
          </p>
        )}
        <p className="mt-3 text-xs text-slate-500">
          Production NYC.ID SSO is planned; this demo uses clerk accounts stored in Firestore. Sessions end when you
          close the browser tab.
        </p>
        {error && (
          <p className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3" role="alert">
            {error}
          </p>
        )}
        <form className="mt-6 space-y-4" onSubmit={submit}>
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-slate-700">
              Username
            </label>
            <input
              id="username"
              required
              autoComplete="username"
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-slate-700">
              Password
            </label>
            <div className="mt-1 flex gap-2">
              <input
                id="password"
                required
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                className="flex-1 border border-pp-border rounded-md px-3 py-2 text-sm"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="px-3 py-2 text-sm rounded-md border border-pp-border"
                onClick={() => setShowPassword((value) => !value)}
                aria-pressed={showPassword}
                aria-controls="password"
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            <p className="mt-1 text-xs text-slate-500">Repeated failed sign-in attempts are logged server-side.</p>
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full px-4 py-2 rounded-md bg-pp-accent text-white text-sm font-medium disabled:opacity-50"
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  );
}
