import { useEffect, useId, useRef, useState } from "react";
import { AgentCard, api } from "../lib/api";

interface Props {
  open: boolean;
  onClose: () => void;
}

export default function AgentCatalog({ open, onClose }: Props) {
  const titleId = useId();
  const closeRef = useRef<HTMLButtonElement>(null);
  const [agents, setAgents] = useState<AgentCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    api
      .listAgents()
      .then(setAgents)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [open]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-30 bg-black/30 flex justify-end" role="presentation" onClick={onClose}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-md bg-white h-full shadow-xl p-6 overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id={titleId} className="text-lg font-semibold text-pp-navy">
              Agent registry
            </h2>
            <p className="text-sm text-slate-600 mt-1">Signed A2A agents authorized for NYC permit review.</p>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="text-sm text-slate-600 hover:text-pp-navy">
            Close
          </button>
        </div>
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
              <p className="text-xs text-slate-500 mt-2">Fingerprint: {agent.fingerprint}</p>
            </li>
          ))}
        </ul>
      </aside>
    </div>
  );
}
