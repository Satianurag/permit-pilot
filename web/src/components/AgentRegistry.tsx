import { useQuery } from "@tanstack/react-query";
import { api, AgentCard } from "../lib/api";
import { errorMessage } from "../lib/errors";

export default function AgentRegistry() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["agents"],
    queryFn: api.listAgents,
  });

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
        </li>
      ))}
    </ul>
  );
}
