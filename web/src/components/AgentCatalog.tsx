import { useEffect, useState } from "react";
import { useLocation } from "react-router-dom";
import ModalDialog from "./ModalDialog";
import { useToast } from "./Toast";
import { AgentCard, api } from "../lib/api";
import { errorMessage } from "../lib/errors";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function AgentCatalog({ open, onClose }: Props) {
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
    if (!open) return;
    setLoading(true);
    setResults({});
    api
      .listAgents()
      .then(setAgents)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [open]);

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

  return (
    <ModalDialog open={open} title="Agent registry" onClose={onClose} variant="drawer">
      <p className="text-sm text-slate-600 -mt-2">
        Fingerprint allowlist gateway — trusted agents are admitted; tampered fingerprints are blocked and logged on the
        open case file.
      </p>
      {loading && <p className="mt-4 text-sm text-slate-600">Loading agents…</p>}
      {error && (
        <p className="mt-4 text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2" role="alert">
          {errorMessage(error)}
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
                {agent.signed ? "On allowlist" : "Not listed"}
              </span>
            </div>
            <p className="text-slate-600 mt-1">{agent.description}</p>
            {agent.skills.length > 0 && (
              <p className="text-xs text-slate-500 mt-2">Skills: {agent.skills.join(", ")}</p>
            )}
            <p className="text-xs text-slate-500 mt-2 font-mono">Fingerprint: {agent.fingerprint}</p>
            <div className="mt-3 flex flex-wrap gap-2">
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => testAgent(agent, false)}
                className="text-xs px-2 py-1 rounded-md bg-pp-accent text-white disabled:opacity-50"
              >
                {busy === `${agent.name}-valid` ? "Testing…" : "Test gateway"}
              </button>
              <button
                type="button"
                disabled={busy !== null}
                onClick={() => testAgent(agent, true)}
                className="text-xs px-2 py-1 rounded-md border border-pp-border disabled:opacity-50"
              >
                {busy === `${agent.name}-rogue` ? "Testing…" : "Send tampered request"}
              </button>
            </div>
            {results[agent.name] && (
              <p className="mt-2 text-xs text-slate-700 bg-slate-50 border border-pp-border rounded p-2">
                {results[agent.name]}
              </p>
            )}
            {!caseId && (
              <p className="mt-2 text-xs text-amber-800">Open a case file to log gateway results on the audit trail.</p>
            )}
          </li>
        ))}
      </ul>
    </ModalDialog>
  );
}
