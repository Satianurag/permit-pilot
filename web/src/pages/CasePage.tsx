import { useCallback, useEffect, useId, useState } from "react";
import { Link, useParams } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import TraceReplay from "../components/TraceReplay";
import { api, Case, CaseBundle, Claim, DepartmentReview } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";

const TABS = ["summary", "distribution", "documents", "claims", "audit"] as const;
type Tab = (typeof TABS)[number];
const TERMINAL_STATUSES = new Set(["approved", "changes_requested"]);

export default function CasePage() {
  const { id } = useParams();
  const caseId = id!;
  const tabsId = useId();
  const [tab, setTab] = useState<Tab>("summary");
  const [bundle, setBundle] = useState<CaseBundle | null>(null);
  const [selected, setSelected] = useState<DepartmentReview | null>(null);
  const [claimText, setClaimText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [respondingClaimId, setRespondingClaimId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [briefing, setBriefing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [approveOpen, setApproveOpen] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    api
      .getCaseBundle(caseId)
      .then((data) => {
        setBundle(data);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [caseId]);

  useEffect(load, [load]);

  const caseData: Case | null = bundle?.case ?? null;
  const canDecide = caseData && !TERMINAL_STATUSES.has(caseData.status);

  const runAction = async (key: string, action: () => Promise<void>) => {
    setBusy(key);
    setError(null);
    try {
      await action();
      load();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const refreshDistribution = () =>
    runAction("refresh", async () => {
      await api.refreshDistribution(caseId);
    });

  const submitClaim = () =>
    runAction("claim", async () => {
      if (!claimText.trim()) throw new Error("Enter a document request for the applicant");
      await api.createClaim(caseId, claimText.trim());
      setClaimText("");
    });

  const submitResponse = (claimId: string) =>
    runAction(`respond-${claimId}`, async () => {
      if (!responseText.trim()) throw new Error("Enter the applicant response received");
      await api.respondToClaim(caseId, claimId, responseText.trim());
      setResponseText("");
      setRespondingClaimId(null);
    });

  const generateBriefing = () =>
    runAction("briefing", async () => {
      const result = await api.orchestrate(caseId);
      setBriefing(result.summary);
    });

  const decide = (decision: string) =>
    runAction("decide", async () => {
      if (!note.trim()) throw new Error("Clerk note is required for audit");
      await api.decide(caseId, decision, note.trim());
      setApproveOpen(false);
    });

  if (loading && !bundle) {
    return <p className="text-slate-600">Loading case…</p>;
  }

  if (!caseData) {
    return <p className="text-red-700">{error ?? "Case not found"}</p>;
  }

  return (
    <div className="space-y-4 pb-28">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
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

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}

      <div role="tablist" aria-label="Case sections" className="flex flex-wrap gap-1 border-b border-pp-border">
        {TABS.map((name) => (
          <button
            key={name}
            id={`${tabsId}-${name}`}
            role="tab"
            type="button"
            aria-selected={tab === name}
            aria-controls={`${tabsId}-panel-${name}`}
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
        <div
          role="tabpanel"
          id={`${tabsId}-panel-summary`}
          aria-labelledby={`${tabsId}-summary`}
          className="grid md:grid-cols-2 gap-4"
        >
          <div className="bg-white border border-pp-border rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-pp-navy mb-3">Property</h3>
            <dl className="text-sm space-y-2">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Owner</dt>
                <dd>{caseData.owner || "—"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Borough</dt>
                <dd>{caseData.borough || "—"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Work</dt>
                <dd className="text-right max-w-xs">{caseData.work_type}</dd>
              </div>
            </dl>
          </div>
          <div className="bg-white border border-pp-border rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-pp-navy mb-3">Case timeline</h3>
            <p className="text-sm text-slate-600">Opened {new Date(caseData.created_at).toLocaleString()}</p>
            <p className="text-sm text-slate-600">Updated {new Date(caseData.updated_at).toLocaleString()}</p>
            <button
              type="button"
              disabled={busy === "briefing"}
              onClick={generateBriefing}
              className="mt-4 text-sm px-3 py-1.5 rounded-md bg-pp-accent text-white disabled:opacity-50"
            >
              {busy === "briefing" ? "Generating…" : "Generate clerk briefing"}
            </button>
            {briefing && (
              <p className="mt-3 text-sm text-slate-700 border-l-4 border-pp-accent pl-3">{briefing}</p>
            )}
          </div>
        </div>
      )}

      {tab === "distribution" && bundle && (
        <div role="tabpanel" id={`${tabsId}-panel-distribution`} aria-labelledby={`${tabsId}-distribution`} className="space-y-3">
          {bundle.workflow.length > 0 && (
            <div className="bg-slate-50 border border-pp-border rounded-lg p-3 text-sm">
              <p className="font-medium text-pp-navy mb-2">Department workflow</p>
              <div className="flex flex-wrap gap-2">
                {bundle.workflow.map((step) => (
                  <span
                    key={step.department ?? step.name}
                    className="px-2 py-0.5 rounded-full text-xs capitalize bg-white border border-pp-border"
                  >
                    {step.department ?? step.name}: {formatStatus(step.status)}
                  </span>
                ))}
              </div>
            </div>
          )}
          <div className="flex justify-end">
            <button
              type="button"
              disabled={busy === "refresh"}
              onClick={refreshDistribution}
              className="text-sm px-3 py-1.5 rounded-md bg-pp-accent text-white disabled:opacity-50"
            >
              {busy === "refresh" ? "Refreshing…" : "Refresh from NYC Open Data"}
            </button>
          </div>
          {bundle.distribution.length === 0 ? (
            <EmptyState
              title="No department reviews yet"
              description="Distribution results will appear after intake completes or after you refresh from NYC Open Data."
            />
          ) : (
            <div className="overflow-x-auto rounded-lg border border-pp-border bg-white shadow-sm">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-50 text-slate-600 text-left">
                  <tr>
                    <th scope="col" className="px-4 py-3">
                      Department
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Status
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Summary
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {bundle.distribution.map((row) => (
                    <tr
                      key={row.department}
                      className="border-t border-pp-border hover:bg-slate-50 cursor-pointer"
                      onClick={() => setSelected(row)}
                    >
                      <td className="px-4 py-3 capitalize font-medium">
                        {row.department}
                        <span className="sr-only"> — open details</span>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="px-4 py-3 text-slate-600">{row.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {tab === "documents" && (
        <div role="tabpanel" id={`${tabsId}-panel-documents`} aria-labelledby={`${tabsId}-documents`}>
          {!bundle?.document ? (
            <EmptyState
              title="No intake document on file"
              description="Documents from new intake are stored after PII redaction."
            />
          ) : (
            <div className="bg-white border border-pp-border rounded-lg p-4 shadow-sm space-y-4">
              <div>
                <h3 className="font-medium text-pp-navy">Redacted applicant packet</h3>
                <p className="text-xs text-slate-500 mt-1">
                  Stored {new Date(bundle.document.stored_at).toLocaleString()}
                </p>
              </div>
              {bundle.document.pii_findings.length > 0 && (
                <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm">
                  <p className="font-medium text-amber-900">PII redacted</p>
                  <p className="text-amber-800 mt-1">{bundle.document.pii_findings.join(", ")}</p>
                </div>
              )}
              <pre className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 border border-pp-border rounded-md p-4">
                {bundle.document.redacted_text || "Empty packet"}
              </pre>
            </div>
          )}
        </div>
      )}

      {tab === "claims" && bundle && (
        <div role="tabpanel" id={`${tabsId}-panel-claims`} aria-labelledby={`${tabsId}-claims`} className="space-y-4">
          {canDecide && (
            <div className="flex flex-col sm:flex-row gap-2">
              <label htmlFor="claim-message" className="sr-only">
                Request missing document
              </label>
              <input
                id="claim-message"
                className="flex-1 border border-pp-border rounded-md px-3 py-2 text-sm"
                placeholder="Request missing document from applicant…"
                value={claimText}
                onChange={(e) => setClaimText(e.target.value)}
              />
              <button
                type="button"
                disabled={busy === "claim"}
                onClick={submitClaim}
                className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm disabled:opacity-50"
              >
                {busy === "claim" ? "Sending…" : "Send claim"}
              </button>
            </div>
          )}
          {bundle.claims.length === 0 ? (
            <EmptyState title="No claims on this case" description="Use a claim when the applicant must supply missing documents." />
          ) : (
            <ul className="space-y-3">
              {bundle.claims.map((claim: Claim) => (
                <li key={claim.id} className="bg-white border border-pp-border rounded-md p-4 text-sm space-y-3">
                  <div className="flex items-center justify-between gap-2">
                    <StatusBadge status={claim.status} />
                    <span className="text-xs text-slate-500">{new Date(claim.created_at).toLocaleString()}</span>
                  </div>
                  <p>{claim.message}</p>
                  {claim.response_message && (
                    <div className="rounded-md bg-slate-50 border border-pp-border p-3">
                      <p className="text-xs font-medium text-slate-500">Applicant response</p>
                      <p className="mt-1">{claim.response_message}</p>
                      {claim.responded_at && (
                        <p className="text-xs text-slate-500 mt-2">{new Date(claim.responded_at).toLocaleString()}</p>
                      )}
                    </div>
                  )}
                  {claim.status === "open" && canDecide && (
                    <div className="space-y-2">
                      {respondingClaimId === claim.id ? (
                        <>
                          <label htmlFor={`response-${claim.id}`} className="block text-sm font-medium text-slate-700">
                            Record applicant response
                          </label>
                          <textarea
                            id={`response-${claim.id}`}
                            className="w-full border border-pp-border rounded-md px-3 py-2 text-sm min-h-20"
                            value={responseText}
                            onChange={(e) => setResponseText(e.target.value)}
                          />
                          <div className="flex gap-2">
                            <button
                              type="button"
                              disabled={busy === `respond-${claim.id}`}
                              onClick={() => submitResponse(claim.id)}
                              className="px-3 py-1.5 rounded-md bg-pp-accent text-white text-sm disabled:opacity-50"
                            >
                              {busy === `respond-${claim.id}` ? "Saving…" : "Save response"}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setRespondingClaimId(null);
                                setResponseText("");
                              }}
                              className="px-3 py-1.5 rounded-md border border-pp-border text-sm"
                            >
                              Cancel
                            </button>
                          </div>
                        </>
                      ) : (
                        <button
                          type="button"
                          onClick={() => setRespondingClaimId(claim.id)}
                          className="text-sm text-pp-accent hover:underline"
                        >
                          Record applicant response
                        </button>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {tab === "audit" && bundle && (
        <div role="tabpanel" id={`${tabsId}-panel-audit`} aria-labelledby={`${tabsId}-audit`} className="space-y-6">
          <div className="bg-white border border-pp-border rounded-lg p-4 shadow-sm">
            <h3 className="font-medium text-pp-navy mb-3">Trace replay</h3>
            <TraceReplay
              spans={bundle.trace}
              cloudTraceUrl={bundle.observability.cloud_trace_url}
              langfuseUrl={bundle.observability.langfuse_url}
              gcpWorkflowsUrl={bundle.observability.gcp_workflows_url}
            />
          </div>
          <div>
            <h3 className="font-medium text-pp-navy mb-3">Audit timeline</h3>
            {bundle.audit.length === 0 ? (
              <EmptyState title="No audit events yet" description="Clerk actions and system events will appear here." />
            ) : (
              <ol className="space-y-2">
                {bundle.audit.map((event) => (
                  <li key={event.id} className="bg-white border border-pp-border rounded-md p-3 text-sm">
                    <p className="font-medium capitalize">{formatStatus(event.action)}</p>
                    <p className="text-slate-600">{event.detail}</p>
                    <p className="text-xs text-slate-500 mt-1">
                      {event.actor} · {new Date(event.at).toLocaleString()}
                    </p>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}

      {selected && (
        <div className="fixed inset-0 bg-black/30 flex justify-end z-20" role="presentation" onClick={() => setSelected(null)}>
          <aside
            role="dialog"
            aria-modal="true"
            aria-label={`${selected.department} review details`}
            className="w-full max-w-md bg-white h-full shadow-xl p-6 overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <button type="button" onClick={() => setSelected(null)} className="text-sm text-pp-accent mb-4">
              Close
            </button>
            <h3 className="text-lg font-semibold capitalize text-pp-navy">{selected.department}</h3>
            <div className="mt-2">
              <StatusBadge status={selected.status} />
            </div>
            <p className="mt-4 text-sm text-slate-700">{selected.summary}</p>
            <h4 className="mt-6 text-sm font-medium">Findings</h4>
            <ul className="mt-2 text-sm list-disc pl-5 space-y-1">
              {selected.findings.map((finding) => (
                <li key={finding}>{finding}</li>
              ))}
            </ul>
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
                {selected.citations.map((citation) => (
                  <blockquote
                    key={citation.code}
                    className="mt-2 text-sm border-l-4 border-pp-accent pl-3 text-slate-700"
                  >
                    <p className="font-medium">{citation.code}</p>
                    <p>{citation.excerpt}</p>
                  </blockquote>
                ))}
              </>
            )}
          </aside>
        </div>
      )}

      {canDecide && (
        <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-pp-border shadow-lg">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <label htmlFor="clerk-note" className="sr-only">
              Clerk note
            </label>
            <input
              id="clerk-note"
              className="flex-1 border border-pp-border rounded-md px-3 py-2 text-sm"
              placeholder="Clerk note (required for audit)…"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                type="button"
                disabled={busy === "decide"}
                onClick={() => setApproveOpen(true)}
                className="flex-1 sm:flex-none px-4 py-2 rounded-md bg-emerald-600 text-white text-sm font-medium disabled:opacity-50"
              >
                Approve dossier
              </button>
              <button
                type="button"
                disabled={busy === "decide"}
                onClick={() => decide("request_changes")}
                className="flex-1 sm:flex-none px-4 py-2 rounded-md border border-pp-border text-sm font-medium disabled:opacity-50"
              >
                {busy === "decide" ? "Saving…" : "Request changes"}
              </button>
            </div>
          </div>
        </footer>
      )}

      <ConfirmDialog
        open={approveOpen}
        title="Approve this dossier?"
        description={`You are approving ${caseData.address}. This closes open tasks and records your decision in the audit log.`}
        confirmLabel="Approve dossier"
        busy={busy === "decide"}
        onCancel={() => setApproveOpen(false)}
        onConfirm={() => decide("approve")}
      />
    </div>
  );
}
