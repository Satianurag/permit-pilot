import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api, AgentCard } from "../lib/api";
import { errorMessage } from "../lib/errors";

export default function AgentRegistry() {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["agents"],
    queryFn: api.listAgents,
  });
  const [busy, setBusy] = useState<string | null>(null);
  const [results, setResults] = useState<Record<string, string>>({});

  if (isLoading) {
    return <p className="text-sm text-pp-muted">Loading Agent Registry…</p>;
  }
  if (error) {
    return (
      <p className="pp-login-alert pp-login-alert--error" role="alert">
        {errorMessage(error)}
      </p>
    );
  }

  const agents: AgentCard[] = data?.agents ?? [];

  const invoke = async (agent: AgentCard, tampered: boolean) => {
    const key = `${agent.name}:${tampered ? "tamper" : "ok"}`;
    setBusy(key);
    setResults((current) => ({ ...current, [key]: "" }));
    try {
      const fingerprint = tampered ? `${agent.fingerprint || "unsigned"}x` : (agent.fingerprint || "");
      const result = await api.invokeAgent(agent.name, {
        fingerprint,
        message: tampered ? "tampered gateway probe" : "Signed clerk ping via Agent Gateway fingerprint allowlist.",
      });
      setResults((current) => ({
        ...current,
        [key]: `Pass — Agent Runtime ${result.engine_id || agent.name}. ${(result.text || "ok").slice(0, 240)}`,
      }));
    } catch (err) {
      const message = errorMessage(err);
      setResults((current) => ({
        ...current,
        [key]: tampered
          ? `Blocked (403 allowlist) — ${message}`
          : `Failed — ${message}`,
      }));
    } finally {
      setBusy(null);
      void refetch();
    }
  };

  return (
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
              {agent.signed ? "Runtime identity" : "Pending deploy"}
            </span>
          </div>
          {agent.skills.length > 0 && (
            <p className="text-xs text-pp-muted mt-3">
              <span className="font-semibold text-pp-ink">Department:</span> {agent.skills.join(", ")}
            </p>
          )}
          <p className="text-xs text-pp-muted mt-2 font-mono break-all">
            <span className="font-semibold text-pp-ink font-sans">Tools:</span> {agent.tools.join(", ")}
          </p>
          {agent.engine_id && (
            <p className="text-xs text-pp-muted mt-2 font-mono break-all">Engine {agent.engine_id}</p>
          )}
          {agent.spiffe && (
            <p className="text-xs text-pp-muted mt-2 font-mono break-all">
              <span className="font-semibold text-pp-ink font-sans">SPIFFE:</span> {agent.spiffe}
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              className="pp-btn-primary text-xs py-1.5"
              disabled={busy !== null || !agent.signed}
              onClick={() => invoke(agent, false)}
            >
              {busy === `${agent.name}:ok` ? "Invoking…" : "Test gateway"}
            </button>
            <button
              type="button"
              className="pp-btn-secondary text-xs py-1.5"
              disabled={busy !== null}
              onClick={() => invoke(agent, true)}
            >
              {busy === `${agent.name}:tamper` ? "Sending…" : "Send tampered request"}
            </button>
          </div>
          {(results[`${agent.name}:ok`] || results[`${agent.name}:tamper`]) && (
            <div className="mt-3 space-y-1 text-xs">
              {results[`${agent.name}:ok`] && <p className="text-emerald-800">{results[`${agent.name}:ok`]}</p>}
              {results[`${agent.name}:tamper`] && <p className="text-rose-800">{results[`${agent.name}:tamper`]}</p>}
            </div>
          )}
        </li>
      ))}
    </ul>
  );
}
