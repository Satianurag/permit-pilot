import { KeyboardEvent, useCallback, useEffect, useId, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import ModalDialog from "../components/ModalDialog";
import Skeleton from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import TraceReplay from "../components/TraceReplay";
import { useToast } from "../components/Toast";
import { api, Case, CaseBundle, Claim, ConditionTemplate, DepartmentReview, Task } from "../lib/api";
import { getStoredUser, isAdmin } from "../lib/auth";
import { readBriefing, writeBriefing } from "../lib/briefingCache";
import { errorMessage } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";

const TABS = ["summary", "distribution", "documents", "claims", "audit"] as const;
type Tab = (typeof TABS)[number];
const TERMINAL = new Set(["approved", "changes_requested"]);

function isTab(value: string | null): value is Tab {
  return TABS.includes(value as Tab);
}

export default function CasePage() {
  const { id } = useParams();
  const caseId = id!;
  const tabsId = useId();
  const navigate = useNavigate();
  const { push } = useToast();
  const [params, setParams] = useSearchParams();
  const tab: Tab = isTab(params.get("tab")) ? (params.get("tab") as Tab) : "summary";
  const from = params.get("from") === "search" ? "search" : "tasks";
  const [bundle, setBundle] = useState<CaseBundle | null>(null);
  const [selected, setSelected] = useState<DepartmentReview | null>(null);
  const [claimText, setClaimText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [respondingClaimId, setRespondingClaimId] = useState<string | null>(null);
  const [note, setNote] = useState("");
  const [briefing, setBriefing] = useState<string | null>(() => readBriefing(caseId));
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [approveOpen, setApproveOpen] = useState(false);
  const [changesOpen, setChangesOpen] = useState(false);
  const [conditions, setConditions] = useState<ConditionTemplate[]>([]);
  const [planUrl, setPlanUrl] = useState<string | null>(null);
  const [nextTask, setNextTask] = useState<Task | null>(null);
  const admin = isAdmin(getStoredUser());

  const setTab = (name: Tab) => {
    const next = new URLSearchParams(params);
    next.set("tab", name);
    setParams(next, { replace: true });
  };

  const onTabKey = (event: KeyboardEvent<HTMLDivElement>) => {
    if (!["ArrowRight", "ArrowLeft", "Home", "End"].includes(event.key)) return;
    event.preventDefault();
    const i = TABS.indexOf(tab);
    let next = i;
    if (event.key === "ArrowRight") next = (i + 1) % TABS.length;
    if (event.key === "ArrowLeft") next = (i - 1 + TABS.length) % TABS.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = TABS.length - 1;
    setTab(TABS[next]);
    document.getElementById(`${tabsId}-${TABS[next]}`)?.focus();
  };

  const requireNote = () => {
    if (note.trim()) return true;
    setError("Clerk note is required for the audit trail");
    document.getElementById("clerk-note")?.focus();
    return false;
  };

  const load = useCallback(
    (silent = false) => {
      if (!silent) setLoading(true);
      setError(null);
      api
        .getCaseBundle(caseId)
        .then(setBundle)
        .catch((err: Error) => setError(err.message))
        .finally(() => setLoading(false));
    },
    [caseId],
  );

  useEffect(() => load(), [load]);

  useEffect(() => {
    api.listConditions().then(setConditions).catch(() => setConditions([]));
  }, []);

  useEffect(() => {
    setBriefing(readBriefing(caseId));
    setNextTask(null);
    setPlanUrl(null);
  }, [caseId]);

  useEffect(() => {
    if (bundle?.briefing?.summary) {
      setBriefing(bundle.briefing.summary);
      writeBriefing(caseId, bundle.briefing.summary);
    }
  }, [bundle?.briefing, caseId]);

  useEffect(() => {
    if (!bundle?.document?.has_pdf) {
      setPlanUrl(null);
      return;
    }
    let active = true;
    let objectUrl: string | null = null;
    api
      .getPlanPdf(caseId)
      .then((pdf) => {
        if (!active) return;
        const bytes = Uint8Array.from(atob(pdf.pdf_base64), (ch) => ch.charCodeAt(0));
        const blob = new Blob([bytes], { type: pdf.content_type });
        objectUrl = URL.createObjectURL(blob);
        setPlanUrl(objectUrl);
      })
      .catch(() => {
        if (active) setPlanUrl(null);
      });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [bundle?.document?.has_pdf, caseId]);

  const caseData: Case | null = bundle?.case ?? null;
  const canDecide = Boolean(caseData && !TERMINAL.has(caseData.status));
  const failed = bundle?.distribution.filter((row) => row.status === "fail" && row.department !== "critic") ?? [];
  const needsInfo =
    bundle?.distribution.filter((row) => row.status === "needs_info" && row.department !== "critic") ?? [];
  const checking = bundle?.distribution.some((row) => row.status === "checking") ?? false;
  const stalled = bundle?.workflow.some((step) => step.status === "failed" || step.status === "interrupted") ?? false;

  useEffect(() => {
    if (!checking) return;
    const timer = window.setInterval(() => load(true), 4000);
    return () => window.clearInterval(timer);
  }, [checking, load]);

  const runAction = async (key: string, action: () => Promise<void>, successMessage?: string) => {
    setBusy(key);
    setError(null);
    try {
      await action();
      load(true);
      if (successMessage) push(successMessage, "success");
    } catch (err) {
      const message = errorMessage(err);
      setError(message);
      push(message, "error");
    } finally {
      setBusy(null);
    }
  };

  const appendCondition = (template: ConditionTemplate) => {
    const line = `${template.code}: ${template.label}`;
    setNote((current) => (current.trim() ? `${current.trim()}\n${line}` : line));
    document.getElementById("clerk-note")?.focus();
  };

  const decide = (decision: string, override = false) =>
    runAction(
      "decide",
      async () => {
        if (!note.trim()) throw new Error("Clerk note is required for the audit trail");
        await api.decide(caseId, decision, note.trim(), override);
        setApproveOpen(false);
        setChangesOpen(false);
        const queue = await api.listTasks("open");
        setNextTask(queue.find((task) => task.case_id !== caseId) ?? null);
      },
      decision === "approve" ? "Dossier approved." : "Changes requested.",
    );

  if (loading && !bundle) {
    return <Skeleton rows={8} label="Loading case" />;
  }

  if (!caseData) {
    return <p className="text-red-700">{error ?? "Case not found"}</p>;
  }

  return (
    <div className={`space-y-4 ${canDecide ? "pb-36" : ""}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            to={from === "search" ? "/permits" : "/tasks"}
            className="text-sm text-pp-accent hover:underline"
          >
            ← Back to {from === "search" ? "search" : "tasks"}
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

      {nextTask && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950" role="status">
          Decision saved.{" "}
          <button
            type="button"
            className="font-medium underline"
            onClick={() => navigate(`/cases/${nextTask.case_id}?tab=distribution&from=tasks`)}
          >
            Open next task: {nextTask.title}
          </button>
        </div>
      )}

      {failed.length > 0 && canDecide && (
        <p className="text-sm text-red-900 bg-red-50 border border-red-200 rounded-md p-3" role="status">
          {failed.length} department review{failed.length === 1 ? "" : "s"} failed. Request changes, or approve only with
          a recorded override.
        </p>
      )}
      {needsInfo.length > 0 && canDecide && (
        <p className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-md p-3" role="status">
          {needsInfo.length} department review{needsInfo.length === 1 ? "" : "s"} need more information (
          {needsInfo.map((row) => row.department).join(", ")}). Request changes or approve with override.
        </p>
      )}
      {checking && canDecide && (
        <p className="text-sm text-blue-900 bg-blue-50 border border-blue-200 rounded-md p-3" role="status">
          Distribution is still running. Approval is blocked until department reviews finish.
        </p>
      )}

      <div
        role="tablist"
        aria-label="Case sections"
        className="flex flex-wrap gap-1 border-b border-pp-border"
        onKeyDown={onTabKey}
      >
        {TABS.map((name) => (
          <button
            key={name}
            id={`${tabsId}-${name}`}
            role="tab"
            type="button"
            tabIndex={tab === name ? 0 : -1}
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
          <div className="bg-white border border-pp-border rounded-lg p-4">
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
              {bundle?.parcel?.zoning_district && (
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Zoning</dt>
                  <dd>{bundle.parcel.zoning_district}</dd>
                </div>
              )}
              {bundle?.parcel?.map_url && (
                <div className="pt-2">
                  <a
                    href={bundle.parcel.map_url}
                    target="_blank"
                    rel="noreferrer"
                    className="text-sm text-pp-accent hover:underline"
                  >
                    Open parcel map (NYC Open Data)
                  </a>
                </div>
              )}
            </dl>
          </div>
          <div className="bg-white border border-pp-border rounded-lg p-4 space-y-4">
            <div>
              <h3 className="font-medium text-pp-navy mb-3">Case timeline</h3>
              <p className="text-sm text-slate-600">Opened {new Date(caseData.created_at).toLocaleString()}</p>
              <p className="text-sm text-slate-600">Updated {new Date(caseData.updated_at).toLocaleString()}</p>
              <button
                type="button"
                disabled={busy === "briefing"}
                onClick={() =>
                  runAction("briefing", async () => {
                    const result = await api.orchestrate(caseId);
                    setBriefing(result.summary);
                    writeBriefing(caseId, result.summary);
                  }, "Clerk briefing generated.")
                }
                className="mt-4 text-sm px-3 py-1.5 rounded-md bg-pp-accent text-white disabled:opacity-50"
              >
                {busy === "briefing" ? "Generating…" : "Generate clerk briefing"}
              </button>
              {briefing && (
                <p className="mt-3 text-sm text-slate-700 border-l-4 border-pp-accent pl-3 whitespace-pre-wrap">{briefing}</p>
              )}
            </div>
            {bundle && bundle.related_permits.length > 0 && (
              <div>
                <h3 className="font-medium text-pp-navy mb-2">Related permits (NYC Open Data)</h3>
                <ul className="text-sm space-y-2">
                  {bundle.related_permits.map((permit) => (
                    <li key={`${permit.job_number ?? permit.work_type}-${permit.filing_date}`} className="border border-pp-border rounded p-2">
                      <p className="font-medium">{permit.job_number || "Permit"}</p>
                      <p className="text-slate-600">{permit.work_type || "—"}</p>
                      <p className="text-slate-500 text-xs">
                        {permit.status || "Unknown status"}
                        {permit.filing_date ? ` · filed ${permit.filing_date}` : ""}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "distribution" && bundle && (
        <div role="tabpanel" id={`${tabsId}-panel-distribution`} aria-labelledby={`${tabsId}-distribution`} className="space-y-3">
          {bundle.workflow.length > 0 && (
            <div className="bg-slate-50 border border-pp-border rounded-lg p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <p className="font-medium text-pp-navy">Department workflow</p>
                {stalled && (
                  <button
                    type="button"
                    disabled={busy === "resume"}
                    onClick={() => runAction("resume", async () => { await api.resumeWorkflow(caseId); })}
                    className="text-sm px-3 py-1 rounded-md bg-pp-navy text-white disabled:opacity-50"
                  >
                    {busy === "resume" ? "Resuming…" : "Resume workflow"}
                  </button>
                )}
              </div>
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
              onClick={() => runAction("refresh", async () => { await api.refreshDistribution(caseId); })}
              className="text-sm px-3 py-1.5 rounded-md bg-pp-accent text-white disabled:opacity-50"
            >
              {busy === "refresh" ? "Refreshing…" : "Refresh from NYC Open Data"}
            </button>
          </div>
          {bundle.distribution.length === 0 ? (
            <EmptyState
              title="No department reviews yet"
              description="Distribution results appear after intake or after you refresh from NYC Open Data."
            />
          ) : (
            <div className="table-scroll rounded-lg border border-pp-border bg-white" tabIndex={0}>
              <table className="min-w-full text-sm">
                <caption className="sr-only">Department distribution reviews. Activate a row for findings.</caption>
                <thead className="bg-slate-50 text-slate-600 text-left">
                  <tr>
                    <th scope="col" className="px-4 py-2">
                      Department
                    </th>
                    <th scope="col" className="px-4 py-2">
                      Status
                    </th>
                    <th scope="col" className="px-4 py-2">
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
                      onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                          event.preventDefault();
                          setSelected(row);
                        }
                      }}
                      tabIndex={0}
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
        <div role="tabpanel" id={`${tabsId}-panel-documents`} aria-labelledby={`${tabsId}-documents`} className="space-y-4">
          {!bundle?.document ? (
            <EmptyState
              title="No intake document on file"
              description="Upload a plan PDF or applicant packet during intake. Packet text is stored redacted after PII removal."
            />
          ) : (
            <div className="bg-white border border-pp-border rounded-lg p-4 space-y-4">
              <div>
                <h3 className="font-medium text-pp-navy">Intake packet (redacted)</h3>
                <p className="text-xs text-slate-500 mt-1">
                  {bundle.document.filename ? `${bundle.document.filename} · ` : ""}
                  {bundle.document.redacted_text.length.toLocaleString()} characters · stored{" "}
                  {new Date(bundle.document.stored_at).toLocaleString()}
                </p>
              </div>
              {bundle.document.pii_findings.length > 0 && (
                <div className="rounded-md bg-amber-50 border border-amber-200 p-3 text-sm">
                  <p className="font-medium text-amber-900">PII redacted</p>
                  <p className="text-amber-800 mt-1">{bundle.document.pii_findings.join(", ")}</p>
                </div>
              )}
              {bundle.document.redacted_text ? (
                <pre className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 border border-pp-border rounded-md p-4">
                  {bundle.document.redacted_text}
                </pre>
              ) : (
                <p className="text-sm text-slate-600">No packet text — plan PDF only.</p>
              )}
              {bundle.document.has_pdf && (
                <div>
                  <h3 className="font-medium text-pp-navy mb-2">Plan PDF</h3>
                  {planUrl ? (
                    <iframe title="Plan PDF" src={planUrl} className="w-full min-h-[28rem] border border-pp-border rounded-md" />
                  ) : (
                    <Skeleton rows={4} label="Loading plan PDF" />
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {tab === "claims" && bundle && (
        <div role="tabpanel" id={`${tabsId}-panel-claims`} aria-labelledby={`${tabsId}-claims`} className="space-y-4">
          <p className="text-sm text-slate-600">
            Claims are recorded on the case and handed off to DOB NOW with a reference ID for the audit trail.
          </p>
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
                onClick={() =>
                  runAction("claim", async () => {
                    if (!claimText.trim()) throw new Error("Enter a document request for the applicant");
                    await api.createClaim(caseId, claimText.trim());
                    setClaimText("");
                  }, "Claim recorded and DOB NOW handoff reference saved.")
                }
                className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm disabled:opacity-50"
              >
                {busy === "claim" ? "Saving…" : "Record claim"}
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
                  {claim.notification_reference && (
                    <p className="text-xs text-slate-500">
                      DOB NOW handoff · {claim.notification_reference}
                      {claim.notified_at ? ` · ${new Date(claim.notified_at).toLocaleString()}` : ""}
                    </p>
                  )}
                  {claim.response_message && (
                    <div className="rounded-md bg-slate-50 border border-pp-border p-3">
                      <p className="text-xs font-medium text-slate-500">Applicant response (recorded by clerk)</p>
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
                              onClick={() =>
                                runAction(`respond-${claim.id}`, async () => {
                                  if (!responseText.trim()) throw new Error("Enter the applicant response received");
                                  await api.respondToClaim(caseId, claim.id, responseText.trim());
                                  setResponseText("");
                                  setRespondingClaimId(null);
                                })
                              }
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
          <div className="bg-white border border-pp-border rounded-lg p-4">
            <h3 className="font-medium text-pp-navy mb-3">Trace replay</h3>
            <TraceReplay
              spans={bundle.trace}
              cloudTraceUrl={admin ? bundle.observability.cloud_trace_url : null}
              langfuseUrl={admin ? bundle.observability.langfuse_url : null}
              gcpWorkflowsUrl={admin ? bundle.observability.gcp_workflows_url : null}
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

      <ModalDialog
        open={Boolean(selected)}
        title={selected ? `${selected.department} review` : "Review"}
        onClose={() => setSelected(null)}
        variant="drawer"
      >
        {selected && (
          <div className="space-y-4">
            <StatusBadge status={selected.status} />
            <p className="text-sm text-slate-700">{selected.summary}</p>
            <div>
              <h4 className="text-sm font-medium">Findings</h4>
              <ul className="mt-2 text-sm list-disc pl-5 space-y-1">
                {selected.findings.map((finding) => (
                  <li key={finding}>{finding}</li>
                ))}
              </ul>
            </div>
            <div>
              <h4 className="text-sm font-medium">Evidence (NYC Open Data)</h4>
              <ul className="mt-2 text-sm space-y-2">
                {selected.evidence.map((ev) => (
                  <li key={`${ev.dataset_id}-${ev.label}`} className="border border-pp-border rounded p-2">
                    <span className="text-slate-500">{ev.dataset_id}</span> · {ev.label}:{" "}
                    <strong>{String(ev.value)}</strong>
                  </li>
                ))}
              </ul>
            </div>
            {selected.citations.length > 0 && (
              <div>
                <h4 className="text-sm font-medium">Citations</h4>
                {selected.citations.map((citation) => (
                  <blockquote key={citation.code} className="mt-2 text-sm border-l-4 border-pp-accent pl-3 text-slate-700">
                    <p className="font-medium">{citation.code}</p>
                    <p>{citation.excerpt}</p>
                  </blockquote>
                ))}
              </div>
            )}
          </div>
        )}
      </ModalDialog>

      {canDecide && (
        <footer className="fixed bottom-0 left-0 right-0 z-10 bg-white border-t border-pp-border">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col gap-3">
            {failed.length > 0 && (
              <p className="text-xs text-red-800">Failed reviews: {failed.map((row) => row.department).join(", ")}</p>
            )}
            {needsInfo.length > 0 && (
              <p className="text-xs text-amber-800">
                Needs info: {needsInfo.map((row) => row.department).join(", ")}
              </p>
            )}
            {conditions.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {conditions.map((template) => (
                  <button
                    key={template.id}
                    type="button"
                    onClick={() => appendCondition(template)}
                    className="px-2 py-1 text-xs rounded-md border border-pp-border bg-slate-50 hover:bg-white"
                  >
                    {template.code}
                  </button>
                ))}
              </div>
            )}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="flex flex-col gap-2 sm:flex-1">
              <label htmlFor="clerk-note" className="text-sm font-medium text-slate-700">
                Clerk note (required)
              </label>
              <input
                id="clerk-note"
                className="w-full border border-pp-border rounded-md px-3 py-2 text-sm"
                placeholder="Clerk note — required for the audit trail"
                value={note}
                onChange={(e) => setNote(e.target.value)}
              />
            </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy === "decide" || checking}
                  onClick={() => requireNote() && setApproveOpen(true)}
                  className="flex-1 sm:flex-none px-4 py-2 rounded-md bg-emerald-700 text-white text-sm font-medium disabled:opacity-50"
                >
                  Approve dossier
                </button>
                <button
                  type="button"
                  disabled={busy === "decide"}
                  onClick={() => requireNote() && setChangesOpen(true)}
                  className="flex-1 sm:flex-none px-4 py-2 rounded-md border border-pp-border text-sm font-medium disabled:opacity-50"
                >
                  Request changes
                </button>
              </div>
            </div>
          </div>
        </footer>
      )}

      <ConfirmDialog
        open={approveOpen}
        title={
          failed.length
            ? "Approve with failed reviews?"
            : needsInfo.length
              ? "Approve with open information requests?"
              : checking
                ? "Distribution still running"
                : "Approve this dossier?"
        }
        description={
          checking
            ? "Department reviews are still running. Wait for distribution to finish or request changes."
            : failed.length
              ? `Reviews failed for ${failed.map((row) => row.department).join(", ")}. Approving records an override. This closes open tasks.`
              : needsInfo.length
                ? `Reviews need more information from ${needsInfo.map((row) => row.department).join(", ")}. Approving records an override.`
                : `You are approving ${caseData.address}. This closes open tasks and writes the audit log.`
        }
        confirmLabel={failed.length || needsInfo.length ? "Approve with override" : "Approve dossier"}
        busy={busy === "decide"}
        danger={failed.length > 0 || needsInfo.length > 0}
        onCancel={() => setApproveOpen(false)}
        onConfirm={() => {
          if (checking) {
            setApproveOpen(false);
            return;
          }
          decide("approve", failed.length > 0 || needsInfo.length > 0);
        }}
      />
      <ConfirmDialog
        open={changesOpen}
        title="Request changes?"
        description="This records a changes-requested decision, closes open tasks, and writes your note to the audit log. It does not notify the applicant automatically."
        confirmLabel="Request changes"
        busy={busy === "decide"}
        danger
        onCancel={() => setChangesOpen(false)}
        onConfirm={() => decide("request_changes")}
      />
    </div>
  );
}
