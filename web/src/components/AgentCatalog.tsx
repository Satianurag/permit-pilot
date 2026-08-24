import { useEffect, useState } from "react";
import ModalDialog from "./ModalDialog";
import { AgentCard, api } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function AgentCatalog({ open, onClose }: Props) {
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api
      .listAgents()
      .then(setAgents)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [open]);

  return (
    <ModalDialog open={open} title="Agent registry" onClose={onClose} variant="drawer">
      <p className="text-sm text-slate-600 -mt-2">Signed A2A agents authorized for NYC permit review.</p>
      {loading && <p className="mt-4 text-sm text-slate-600">Loading agents…</p>}
      {error && (
        <p className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2" role="alert">
          {error}
        </p>
      )}
      {!loading && !error && agents.length === 0 && (
        <p className="mt-4 text-sm text-slate-500">No registered agents.</p>
      )}
      <ul className="mt-4 space-y-3">
        {agents.map((agent) => (
          <li key={agent.name} className="border border-pp-border rounded-lg p-3 text-sm">
            <div className="flex items-center justify-between gap-2">
              <p className="font-medium">{agent.name}</p>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${
                  agent.signed ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"
                }`}
              >
                {agent.signed ? "Signed" : "Unsigned"}
              </span>
            </div>
            <p className="text-slate-600 mt-1">{agent.description}</p>
            {agent.skills.length > 0 && (
              <p className="text-xs text-slate-500 mt-2">Skills: {agent.skills.join(", ")}</p>
            )}
            {agent.tools.length > 0 && (
              <p className="text-xs text-slate-500">Tools: {agent.tools.join(", ")}</p>
            )}
            <p className="text-xs text-slate-500 mt-2 font-mono">Fingerprint: {agent.fingerprint}</p>
          </li>
        ))}
      </ul>
    </ModalDialog>
  );
}
