import { FormEvent, useEffect, useRef, useState } from "react";
import { Navigate, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../lib/api";
import { isAuthenticated, setSession, setToken } from "../lib/auth";
import { errorMessage } from "../lib/errors";

type GoogleSignInState = "loading" | "ready" | "unconfigured" | "loadError";

function loadGisScript(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>('script[src="https://accounts.google.com/gsi/client"]');
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true });
      existing.addEventListener("error", () => reject(new Error("Google Sign-In failed to load")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Google Sign-In failed to load"));
    document.head.appendChild(script);
  });
}

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const [params] = useSearchParams();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showDemo, setShowDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [googleState, setGoogleState] = useState<GoogleSignInState>("loading");
  const googleButtonRef = useRef<HTMLDivElement>(null);
  const expired = params.get("expired") === "1";

  const afterLogin = () => {
    const from = location.state as { from?: { pathname?: string; search?: string; hash?: string } } | null;
    const target =
      from?.from?.pathname && from.from.pathname !== "/login"
        ? `${from.from.pathname}${from.from.search ?? ""}${from.from.hash ?? ""}`
        : api.consumeReturnPath();
    navigate(target || "/work", { replace: true });
  };

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setGoogleState("loading");
      try {
        const { client_id: fromApi } = await api.googleClient();
        const clientId = fromApi || import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
        if (!clientId) {
          if (!cancelled) setGoogleState("unconfigured");
          return;
        }
        await loadGisScript();
        if (cancelled || !window.google?.accounts?.id || !googleButtonRef.current) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: async (response) => {
            setLoading(true);
            setError(null);
            try {
              const token = await api.loginGoogle(response.credential);
              setToken(token.access_token);
              const profile = await api.me();
              setSession(token.access_token, profile);
              afterLogin();
            } catch (err) {
              setError(errorMessage(err));
            } finally {
              setLoading(false);
            }
          },
        });
        googleButtonRef.current.innerHTML = "";
        window.google.accounts.id.renderButton(googleButtonRef.current, {
          theme: "outline",
          size: "large",
          text: "signin_with",
          width: 320,
        });
        if (!cancelled) setGoogleState("ready");
      } catch {
        if (!cancelled) setGoogleState("loadError");
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
  }, []);

  if (isAuthenticated()) {
    const from = location.state as { from?: { pathname?: string; search?: string; hash?: string } } | null;
    const target =
      from?.from?.pathname
        ? `${from.from.pathname}${from.from.search ?? ""}${from.from.hash ?? ""}`
        : api.consumeReturnPath();
    return <Navigate to={target || "/work"} replace />;
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
      afterLogin();
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
            Your review queue, completeness checklist, and numbered objections — above DOB NOW, not instead of it.
          </p>
        </div>
        <p className="text-xs text-blue-200/60">Clerk workspace · sits above DOB NOW</p>
      </aside>

      <div className="pp-login-form-wrap">
        <main className="pp-login-card">
          <div className="lg:hidden mb-6">
            <p className="text-[0.65rem] uppercase tracking-[0.2em] text-pp-muted">NYC Department of Buildings</p>
            <h1 className="pp-display text-2xl font-semibold text-pp-navy mt-1">Permit Pilot</h1>
          </div>

          <h2 className="pp-display text-xl font-semibold text-pp-navy">Sign in</h2>
          <p className="mt-1.5 text-sm text-pp-muted">Open your queue. Any Google account works for this demo.</p>

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

          <div className="mt-6 min-h-12 flex justify-center">
            <div ref={googleButtonRef} aria-label="Sign in with Google" />
          </div>
          {googleState === "loading" && (
            <p className="text-xs text-pp-muted text-center mt-2" role="status">
              Loading Google Sign-In…
            </p>
          )}
          {googleState === "unconfigured" && (
            <p className="text-xs text-pp-muted text-center mt-2">
              Google Sign-In is not configured on this deployment. Use a demo clerk account below.
            </p>
          )}
          {googleState === "loadError" && (
            <p className="text-xs text-pp-muted text-center mt-2" role="alert">
              Google Sign-In could not load. Check your connection or use a demo clerk account below.
            </p>
          )}

          <button
            type="button"
            className="mt-6 text-sm text-pp-accent hover:underline"
            onClick={() => setShowDemo((value) => !value)}
            aria-expanded={showDemo}
          >
            {showDemo ? "Hide demo clerk account" : "Use a demo clerk account"}
          </button>

          {showDemo && (
            <form className="mt-4 space-y-4" onSubmit={submit}>
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
                {loading ? "Signing in…" : "Sign in with demo account"}
              </button>
            </form>
          )}

          <p className="pp-login-notice">
            This demo does not use NYC.ID. Sessions end when you close the tab. The applicant is never emailed from
            this tool.
          </p>
        </main>
      </div>
    </div>
  );
}
