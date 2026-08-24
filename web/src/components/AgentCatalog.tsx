import { useEffect, useState } from "react";
import { AgentCard, api } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
  caseId?: string;
  onAudit?: () => void;
}

export default function AgentCatalog({ open, onClose, caseId, onAudit }: Props) {
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    api.listAgents().then(setAgents).catch(() => setAgents([]));
  }, [open]);

  if (!open) return null;

  const testAgent = async (agent: AgentCard, signed: boolean) => {
    setMessage(null);
    const sig = signed ? agent.fingerprint : "unsigned-rogue-agent";
    try {
      await api.invokeAgent(agent.name, sig, caseId);
      setMessage(`${agent.name}: authorized`);
    } catch (err) {
      setMessage(`${agent.name}: blocked — ${err instanceof Error ? err.message : "rejected"}`);
      if (caseId && onAudit) onAudit();
    }
  };

  return (
    <div className="fixed inset-0 z-30 bg-black/30 flex justify-end" onClick={onClose}>
      <aside className="w-full max-w-md bg-white h-full shadow-xl p-6 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <h2 className="text-lg font-semibold text-pp-navy">Agent Catalog</h2>
        <p className="text-sm text-slate-600 mt-1">A2A agent cards registered for NYC permit review.</p>
        {message && <p className="mt-3 text-sm bg-slate-50 border border-pp-border rounded p-2">{message}</p>}
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
              <p className="text-xs text-slate-500 mt-2">fp: {agent.fingerprint}</p>
              <div className="flex gap-2 mt-3">
                <button
                  type="button"
                  onClick={() => testAgent(agent, true)}
                  className="text-xs px-2 py-1 rounded bg-pp-accent text-white"
                >
                  Verify signed
                </button>
                <button
                  type="button"
                  onClick={() => testAgent(agent, false)}
                  className="text-xs px-2 py-1 rounded border border-pp-border"
                >
                  Test rogue
                </button>
              </div>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
