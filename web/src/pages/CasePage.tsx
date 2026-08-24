import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { StatusBadge } from "../components/StatusBadge";
import TraceReplay from "../components/TraceReplay";
import {
  api,
  AuditEvent,
  Case,
  Claim,
  DepartmentReview,
  TraceSpan,
  WorkflowStep,
} from "../lib/api";

const TABS = ["summary", "distribution", "claims", "audit"] as const;
type Tab = (typeof TABS)[number];

interface Props {
  onOpenAgents?: () => void;
}

export default function CasePage({ onOpenAgents }: Props) {
  const { id } = useParams();
  const [tab, setTab] = useState<Tab>("summary");
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [distribution, setDistribution] = useState<DepartmentReview[]>([]);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [workflow, setWorkflow] = useState<WorkflowStep[]>([]);
  const [trace, setTrace] = useState<TraceSpan[]>([]);
  const [orchestratorSummary, setOrchestratorSummary] = useState<string | null>(null);
  const [observability, setObservability] = useState<{
    cloud_trace_url: string | null;
    langfuse_url: string | null;
    gcp_workflows_url: string | null;
  } | null>(null);
  const [selected, setSelected] = useState<DepartmentReview | null>(null);
  const [claimText, setClaimText] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  const caseId = id!;

  const load = () => {
    Promise.all([
      api.getCase(caseId),
      api.getDistribution(caseId),
      api.getClaims(caseId),
      api.getAudit(caseId),
      api.getWorkflow(caseId),
      api.getTrace(caseId),
      api.getObservability(caseId),
    ])
      .then(([c, d, cl, au, wf, tr, obs]) => {
        setCaseData(c);
        setDistribution(d);
        setClaims(cl);
        setAudit(au);
        setWorkflow(wf);
        setTrace(tr);
        setObservability(obs);
      })
      .catch((e: Error) => setError(e.message));
  };

  useEffect(load, [caseId]);

  const refresh = async () => {
    const d = await api.refreshDistribution(caseId);
    setDistribution(d);
    load();
  };

  const submitClaim = async () => {
    if (!claimText.trim()) return;
    await api.createClaim(caseId, claimText.trim());
    setClaimText("");
    load();
  };

  const resumeWorkflow = async () => {
    await api.resumeWorkflow(caseId);
    load();
  };

  const simulateCrash = async () => {
    await api.simulateCrash(caseId);
    load();
  };

  const runGcpWorkflow = async () => {
    await api.runGcpWorkflow(caseId);
    load();
  };

  const runOrchestrator = async () => {
    try {
      const result = await api.orchestrate(caseId);
      setOrchestratorSummary(result.summary);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Orchestration failed");
    }
  };

  const decide = async (decision: string) => {
    await api.decide(caseId, decision, note || decision);
    load();
  };

  if (!caseData) {
    return <p className="text-slate-600">{error ?? "Loading case…"}</p>;
  }

  return (
    <div className="space-y-4 pb-24">
      <div className="flex items-start justify-between gap-4">
        <div>
          <Link to="/tasks" className="text-sm text-pp-accent hover:underline">
            ← Back to tasks
          </Link>
          <h2 className="text-2xl font-semibold text-pp-navy mt-1">{caseData.address}</h2>
          <p className="text-sm text-slate-600 mt-1">
            BIN {caseData.bin || "—"} · BBL {caseData.bbl} · {caseData.work_type}
          </p>
        </div>
        <StatusBadge status={caseData.status} />
      </div>

      <div className="flex gap-1 border-b border-pp-border">
        {TABS.map((name) => (
          <button
            key={name}
            type="button"
            onClick={() => setTab(name)}
            className={`px-4 py-2 text-sm capitalize border-b-2 -mb-px ${
              tab === name ? "border-pp-accent text-pp-accent font-medium" : "border-transparent text-slate-600"
            }`}
          >
            {name}
          </button>
        ))}
      </div>

      {tab === "summary" && (
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-white border border-pp-border rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-pp-navy mb-3">Property</h3>
            <dl className="text-sm space-y-2">
              <div className="flex justify-between"><dt className="text-slate-500">Owner</dt><dd>{caseData.owner || "—"}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Borough</dt><dd>{caseData.borough || "—"}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Work</dt><dd className="text-right max-w-xs">{caseData.work_type}</dd></div>
            </dl>
          </div>
          <div className="bg-white border border-pp-border rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-pp-navy mb-3">Case timeline</h3>
            <p className="text-sm text-slate-600">Opened {new Date(caseData.created_at).toLocaleString()}</p>
            <p className="text-sm text-slate-600">Updated {new Date(caseData.updated_at).toLocaleString()}</p>
            <button
              type="button"
              onClick={runOrchestrator}
              className="mt-4 text-sm px-3 py-1.5 rounded-md bg-pp-accent text-white"
            >
              Run Vertex orchestrator (Gemini)
            </button>
            {orchestratorSummary && (
              <p className="mt-3 text-sm text-slate-700 border-l-4 border-pp-accent pl-3">{orchestratorSummary}</p>
            )}
          </div>
        </div>
      )}

      {tab === "distribution" && (
        <div className="space-y-3">
          {workflow.length > 0 && (
            <div className="bg-slate-50 border border-pp-border rounded-lg p-3 text-sm flex flex-wrap items-center gap-2">
              <span className="font-medium text-pp-navy">Durable workflow:</span>
              {workflow.map((step) => (
                <span
                  key={step.department ?? step.name}
                  className={`px-2 py-0.5 rounded-full text-xs capitalize ${
                    step.status === "completed"
                      ? "bg-emerald-100 text-emerald-800"
                      : step.status === "interrupted" || step.status === "running"
                        ? "bg-amber-100 text-amber-800"
                        : step.status === "failed"
                          ? "bg-red-100 text-red-800"
                          : "bg-slate-200 text-slate-700"
                  }`}
                >
                  {step.department ?? step.name}: {step.status}
                </span>
              ))}
              <button type="button" onClick={resumeWorkflow} className="ml-auto text-xs px-2 py-1 rounded border border-pp-border bg-white">
                Resume
              </button>
              <button type="button" onClick={simulateCrash} className="text-xs px-2 py-1 rounded border border-pp-border bg-white">
                Simulate worker kill
              </button>
              <button type="button" onClick={runGcpWorkflow} className="text-xs px-2 py-1 rounded border border-pp-border bg-white">
                Run GCP Workflows
              </button>
            </div>
          )}
          <div className="flex justify-end">
            <button type="button" onClick={refresh} className="text-sm px-3 py-1.5 rounded-md bg-pp-accent text-white hover:bg-blue-700">
              Refresh from NYC Open Data
            </button>
          </div>
          <div className="bg-white border border-pp-border rounded-lg overflow-hidden shadow-sm">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 text-slate-600 text-left">
                <tr>
                  <th className="px-4 py-3">Department</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Summary</th>
                </tr>
              </thead>
              <tbody>
                {distribution.map((row) => (
                  <tr
                    key={row.department}
                    className="border-t border-pp-border hover:bg-slate-50 cursor-pointer"
                    onClick={() => setSelected(row)}
                  >
                    <td className="px-4 py-3 capitalize font-medium">{row.department}</td>
                    <td className="px-4 py-3"><StatusBadge status={row.status} /></td>
                    <td className="px-4 py-3 text-slate-600">{row.summary}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "claims" && (
        <div className="space-y-4">
          <div className="flex gap-2">
            <input
              className="flex-1 border border-pp-border rounded-md px-3 py-2 text-sm"
              placeholder="Request missing document from applicant…"
              value={claimText}
              onChange={(e) => setClaimText(e.target.value)}
            />
            <button type="button" onClick={submitClaim} className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm">
              Send claim
            </button>
          </div>
          <ul className="space-y-2">
            {claims.map((c) => (
              <li key={c.id} className="bg-white border border-pp-border rounded-md p-3 text-sm">
                <p>{c.message}</p>
                <p className="text-xs text-slate-500 mt-1">{c.status} · {new Date(c.created_at).toLocaleString()}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      {tab === "audit" && (
        <div className="space-y-6">
          <div className="bg-white border border-pp-border rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-pp-navy mb-3">Trace replay</h3>
            <TraceReplay
              spans={trace}
              cloudTraceUrl={observability?.cloud_trace_url}
              langfuseUrl={observability?.langfuse_url}
              gcpWorkflowsUrl={observability?.gcp_workflows_url}
            />
          </div>
          <div>
            <h3 className="font-medium text-pp-navy mb-3">Audit timeline</h3>
            <ol className="space-y-2">
              {audit.map((e) => (
                <li key={e.id} className="bg-white border border-pp-border rounded-md p-3 text-sm">
                  <p className="font-medium capitalize">{e.action.replaceAll("_", " ")}</p>
                  <p className="text-slate-600">{e.detail}</p>
                  <p className="text-xs text-slate-500 mt-1">{e.actor} · {new Date(e.at).toLocaleString()}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/30 flex justify-end z-20" onClick={() => setSelected(null)}>
          <aside className="w-full max-w-md bg-white h-full shadow-xl p-6 overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-semibold capitalize text-pp-navy">{selected.department}</h3>
            <div className="mt-2"><StatusBadge status={selected.status} /></div>
            <p className="mt-4 text-sm text-slate-700">{selected.summary}</p>
            <h4 className="mt-6 text-sm font-medium">Findings</h4>
            <ul className="mt-2 text-sm list-disc pl-5 space-y-1">{selected.findings.map((f) => <li key={f}>{f}</li>)}</ul>
            <h4 className="mt-6 text-sm font-medium">Evidence (NYC Open Data)</h4>
            <ul className="mt-2 text-sm space-y-2">
              {selected.evidence.map((ev) => (
                <li key={`${ev.dataset_id}-${ev.label}`} className="border border-pp-border rounded p-2">
                  <span className="text-slate-500">{ev.dataset_id}</span> · {ev.label}: <strong>{String(ev.value)}</strong>
                </li>
              ))}
            </ul>
            {selected.citations.length > 0 && (
              <>
                <h4 className="mt-6 text-sm font-medium">Citations</h4>
                {selected.citations.map((c) => (
                  <blockquote key={c.code} className="mt-2 text-sm border-l-4 border-pp-accent pl-3 text-slate-700">
                    <p className="font-medium">{c.code}</p>
                    <p>{c.excerpt}</p>
                  </blockquote>
                ))}
              </>
            )}
          </aside>
        </div>
      )}

      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-pp-border shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-3">
          <input
            className="flex-1 border border-pp-border rounded-md px-3 py-2 text-sm"
            placeholder="Clerk note (required for audit)…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <button type="button" onClick={() => decide("approve")} className="px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium">
            Approve dossier
          </button>
          <button type="button" onClick={() => decide("request_changes")} className="px-4 py-2 rounded-md border border-pp-border text-sm font-medium">
            Request changes
          </button>
        </div>
      </footer>
    </div>
  );
}
