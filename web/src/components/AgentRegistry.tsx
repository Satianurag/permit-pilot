import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useToast } from "./Toast";
import { AgentCard, api } from "../lib/api";
import { errorMessage } from "../lib/errors";

export default function AgentRegistry() {
  const location = useLocation();
  const { push } = useToast();
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, string>>({});

  const caseId = (() => {
    const match = location.pathname.match(/\/cases\/([^/]+)/);
    return match?.[1];
  })();

  useEffect(() => {
    setLoading(true);
    setResults({});
    api
      .listAgents()
      .then(setAgents)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const testAgent = async (agent: AgentCard, tampered: boolean) => {
    const key = `${agent.name}-${tampered ? "rogue" : "valid"}`;
    setBusy(key);
    try {
      const signature = tampered ? "rogue-fingerprint-0000" : agent.fingerprint;
      const result = await api.invokeAgent(agent.name, signature, caseId);
      setResults((prev) => ({
        ...prev,
        [agent.name]: `${result.status}: ${result.message}`,
      }));
      push(tampered ? "Tampered request blocked by gateway." : "Signed agent admitted by gateway.", "success");
    } catch (err) {
      const message = errorMessage(err);
      setResults((prev) => ({ ...prev, [agent.name]: message }));
      push(message, "error");
    } finally {
      setBusy(null);
    }
  };

  if (loading) {
    return <p className="text-sm text-pp-muted">Loading registered agents…</p>;
  }

  if (error) {
    return (
      <p className="pp-login-alert pp-login-alert--error" role="alert">
        {errorMessage(error)}
      </p>
    );
  }

  return (
    <div className="space-y-4">
      {!caseId && (
        <div className="pp-panel border-amber-200 bg-amber-50/80 text-amber-950 text-sm">
          Gateway test results are written to a case audit trail when you open a{" "}
          <Link to="/tasks" className="font-semibold text-pp-accent hover:underline">
            case file
          </Link>{" "}
          first.
        </div>
      )}

      {agents.length === 0 ? (
        <p className="text-sm text-pp-muted">No registered agents.</p>
      ) : (
        <ul className="grid gap-4 lg:grid-cols-2">
          {agents.map((agent) => (
            <li key={agent.name} className="pp-card p-4 sm:p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="font-semibold text-pp-navy">{agent.name}</p>
                  <p className="text-sm text-pp-muted mt-1">{agent.description}</p>
                </div>
                <span
                  className={`shrink-0 text-xs px-2.5 py-1 rounded-full font-semibold ${
                    agent.signed ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-900"
                  }`}
                >
                  {agent.signed ? "On allowlist" : "Not listed"}
                </span>
              </div>

              {agent.skills.length > 0 && (
                <p className="text-xs text-pp-muted mt-3">
                  <span className="font-semibold text-pp-ink">Skills:</span> {agent.skills.join(", ")}
                </p>
              )}

              <p className="text-xs text-pp-muted mt-2 font-mono break-all">
                <span className="font-semibold text-pp-ink font-sans">Fingerprint:</span> {agent.fingerprint}
              </p>

              <div className="mt-4 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => testAgent(agent, false)}
                  className="pp-btn-primary text-xs py-2 px-3 disabled:opacity-50"
                >
                  {busy === `${agent.name}-valid` ? "Testing…" : "Test gateway"}
                </button>
                <button
                  type="button"
                  disabled={busy !== null}
                  onClick={() => testAgent(agent, true)}
                  className="pp-btn-secondary text-xs py-2 px-3 disabled:opacity-50"
                >
                  {busy === `${agent.name}-rogue` ? "Testing…" : "Send tampered request"}
                </button>
              </div>

              {results[agent.name] && (
                <p className="mt-3 text-xs text-pp-ink bg-pp-paper border border-pp-border rounded-lg p-2.5">
                  {results[agent.name]}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
