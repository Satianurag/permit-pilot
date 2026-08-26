import { KeyboardEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import ModalDialog from "../components/ModalDialog";
import Skeleton from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import TraceReplay from "../components/TraceReplay";
import { useToast } from "../components/Toast";
import { api, Case, CaseBundle, Claim, ConditionTemplate, DepartmentReview, ParcelContext, RelatedPermit, Task } from "../lib/api";
import { groupAuditEvents, sortDepartmentReviews } from "../lib/auditFormat";
import { readBriefing, writeBriefing } from "../lib/briefingCache";
import { errorMessage, isNotFoundError } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";
import { readNoteDraft, writeNoteDraft } from "../lib/noteDraftCache";
import { reviewClock } from "../lib/reviewClock";

const TABS = ["summary", "distribution", "documents", "claims", "audit"] as const;
type Tab = (typeof TABS)[number];
const TERMINAL = new Set(["approved", "changes_requested"]);
const DISTRIBUTION_STALE_MS = 24 * 60 * 60 * 1000;

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
  const [context, setContext] = useState<{ related_permits: RelatedPermit[]; parcel: ParcelContext | null } | null>(null);
  const [contextLoading, setContextLoading] = useState(false);
  const [selected, setSelected] = useState<DepartmentReview | null>(null);
  const [claimText, setClaimText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [respondingClaimId, setRespondingClaimId] = useState<string | null>(null);
  const [note, setNote] = useState(() => readNoteDraft(caseId) ?? "");
  const [briefing, setBriefing] = useState<string | null>(() => readBriefing(caseId));
  const [error, setError] = useState<string | null>(null);
  const [bundleError, setBundleError] = useState<string | null>(null);
  const [caseStub, setCaseStub] = useState<Case | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [approveOpen, setApproveOpen] = useState(false);
  const [changesOpen, setChangesOpen] = useState(false);
  const [conditions, setConditions] = useState<ConditionTemplate[]>([]);
  const [planUrl, setPlanUrl] = useState<string | null>(null);
  const [nextTask, setNextTask] = useState<Task | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({ address: "", bbl: "", bin: "", work_type: "", owner: "", borough: "" });
  const [decisionSheetOpen, setDecisionSheetOpen] = useState(false);
  const [expandedAudit, setExpandedAudit] = useState<Record<string, boolean>>({});
  const [showAllPermits, setShowAllPermits] = useState(false);
  const footerRef = useRef<HTMLElement>(null);
  const mobileFooterRef = useRef<HTMLDivElement>(null);

  const setTab = (name: Tab) => {
    const next = new URLSearchParams(params);
    next.set("tab", name);
    setParams(next);
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

  const requireNote = (override = false) => {
    if (!note.trim()) {
      setError("Clerk note is required for the audit trail");
      document.getElementById("clerk-note")?.focus();
      return false;
    }
    if (override && note.trim().length < 20) {
      setError("Override decisions require a clerk note of at least 20 characters explaining why.");
      document.getElementById("clerk-note")?.focus();
      return false;
    }
    return true;
  };

  const onNoteChange = (value: string) => {
    setNote(value);
    writeNoteDraft(caseId, value);
  };

  const load = useCallback(
    (silent = false) => {
      if (!silent) setLoading(true);
      setBundleError(null);
      api
        .getCaseBundle(caseId)
        .then(setBundle)
        .catch((err: Error) => setBundleError(err.message))
        .finally(() => setLoading(false));
    },
    [caseId],
  );

  useEffect(() => load(), [load]);

  useEffect(() => {
    if (bundle || !bundleError || isNotFoundError(bundleError)) {
      setCaseStub(null);
      return;
    }
    api
      .getCase(caseId)
      .then(setCaseStub)
      .catch(() => setCaseStub(null));
  }, [bundle, bundleError, caseId]);

  useEffect(() => {
    api.listConditions().then(setConditions).catch(() => setConditions([]));
  }, []);

  useEffect(() => {
    setBriefing(readBriefing(caseId));
    setNote(readNoteDraft(caseId) ?? "");
    setNextTask(null);
    setPlanUrl(null);
    setContext(null);
    setDecisionSheetOpen(false);
  }, [caseId]);

  useEffect(() => {
    if (tab !== "summary" || context || contextLoading) return;
    setContextLoading(true);
    api
      .getCaseContext(caseId)
      .then(setContext)
      .catch(() => setContext({ related_permits: [], parcel: null }))
      .finally(() => setContextLoading(false));
  }, [tab, caseId, context, contextLoading]);

  useEffect(() => {
    if (bundle?.briefing?.summary) {
      setBriefing(bundle.briefing.summary);
      writeBriefing(caseId, bundle.briefing.summary);
    }
  }, [bundle?.briefing, caseId]);

  const storedBriefing = bundle?.briefing;
  const hasStoredBriefing = Boolean(storedBriefing?.summary || briefing);

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
  const mutating = busy !== null;
  const showDecisionFooter = canDecide && (tab === "distribution" || tab === "summary");
  const failed = bundle?.distribution.filter((row) => row.status === "fail" && row.department !== "critic") ?? [];
  const needsInfo =
    bundle?.distribution.filter((row) => row.status === "needs_info" && row.department !== "critic") ?? [];
  const checking = bundle?.distribution.some((row) => row.status === "checking") ?? false;
  const overrideNeeded = failed.length > 0 || needsInfo.length > 0;
  const departmentRows = sortDepartmentReviews(
    bundle?.distribution.filter((row) => row.department !== "critic") ?? [],
  );
  const criticReview = bundle?.distribution.find((row) => row.department === "critic");
  const workflowRunning =
    bundle?.workflow.some((step) => step.status === "running" || step.status === "pending") ?? false;
  const stalled = bundle?.workflow.some((step) => step.status === "failed" || step.status === "interrupted") ?? false;
  const distributionUpdatedAt = bundle?.distribution.reduce<string | null>((latest, row) => {
    if (!row.updated_at) return latest;
    if (!latest || row.updated_at > latest) return row.updated_at;
    return latest;
  }, null);
  const distributionStale =
    distributionUpdatedAt != null &&
    Date.now() - new Date(distributionUpdatedAt).getTime() > DISTRIBUTION_STALE_MS;

  useEffect(() => {
    if (!checking && !workflowRunning) return;
    const timer = window.setInterval(() => load(true), 4000);
    return () => window.clearInterval(timer);
  }, [checking, workflowRunning, load]);

  useEffect(() => {
    if (!showDecisionFooter) {
      document.documentElement.style.removeProperty("--pp-footer-height");
      return;
    }
    const sync = () => {
      const desktop = footerRef.current;
      const mobile = mobileFooterRef.current;
      const height =
        desktop && desktop.offsetHeight > 0
          ? desktop.offsetHeight
          : mobile?.offsetHeight ?? 0;
      if (height > 0) {
        document.documentElement.style.setProperty("--pp-footer-height", `${height}px`);
      }
    };
    sync();
    const ro = new ResizeObserver(sync);
    if (footerRef.current) ro.observe(footerRef.current);
    if (mobileFooterRef.current) ro.observe(mobileFooterRef.current);
    return () => {
      ro.disconnect();
      document.documentElement.style.removeProperty("--pp-footer-height");
    };
  }, [showDecisionFooter, decisionSheetOpen, failed.length, needsInfo.length, conditions.length, note]);

  const lookupBinForCase = () =>
    runAction(
      "lookup-bin",
      async () => {
        if (!caseData) return;
        const borough = caseData.borough || "Queens";
        const result = await api.resolveAddress(caseData.address, borough);
        const match = result.matches.find((row) => row.bin) ?? result.matches[0];
        if (!match?.bin) throw new Error("No BIN found for this address. Edit the address or enter BIN manually.");
        await api.updateCase(caseId, {
          bin: match.bin,
          bbl: match.bbl || caseData.bbl,
        });
        await api.refreshBinDepartments(caseId);
        setSelected(null);
      },
      "BIN resolved — fire, housing, and building reviews refreshed.",
    );

  const openEditCase = () => {
    if (!caseData) return;
    setEditForm({
      address: caseData.address,
      bbl: caseData.bbl,
      bin: caseData.bin,
      work_type: caseData.work_type,
      owner: caseData.owner,
      borough: caseData.borough ?? "",
    });
    setEditOpen(true);
  };

  const saveEditCase = () =>
    runAction(
      "edit-case",
      async () => {
        await api.updateCase(caseId, {
          address: editForm.address.trim(),
          bbl: editForm.bbl.trim(),
          bin: editForm.bin.trim(),
          work_type: editForm.work_type.trim(),
          owner: editForm.owner.trim(),
          borough: editForm.borough.trim() || undefined,
        });
        setEditOpen(false);
      },
      "Case details updated.",
    );

  const runAction = async (
    key: string,
    action: () => Promise<void>,
    successMessage?: string,
    reload = true,
    stickySuccess = false,
  ) => {
    setBusy(key);
    setError(null);
    try {
      await action();
      if (reload) load(true);
      if (successMessage) push(successMessage, "success", { sticky: stickySuccess });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

  const appendCondition = (template: ConditionTemplate) => {
    const line = `${template.code}: ${template.label}`;
    onNoteChange(note.trim() ? `${note.trim()}\n${line}` : line);
    document.getElementById("clerk-note")?.focus();
  };

  const decisionBlocked = mutating || checking;
  const decisionDisabledTitle = mutating
    ? "Wait for the current action to finish before recording a decision"
    : checking
      ? "Department reviews are still running"
      : undefined;

  const decide = (decision: string, override = false) =>
    runAction(
      "decide",
      async () => {
        if (!note.trim()) throw new Error("Clerk note is required for the audit trail");
        if (override && note.trim().length < 20) {
          throw new Error("Override decisions require a clerk note of at least 20 characters explaining why.");
        }
        await api.decide(caseId, decision, note.trim(), override);
        setApproveOpen(false);
        setChangesOpen(false);
        setDecisionSheetOpen(false);
        writeNoteDraft(caseId, "");
        setNote("");
        const queue = await api.listTasks("open");
        const sorted = [...queue]
          .filter((task) => task.case_id !== caseId)
          .sort(
            (a, b) => reviewClock(a.created_at).due.getTime() - reviewClock(b.created_at).due.getTime(),
          );
        setNextTask(sorted[0] ?? null);
      },
      decision === "approve" ? "Dossier approved." : "Changes requested.",
      true,
      true,
    );

  if (loading && !bundle) {
    return <Skeleton rows={8} label="Loading case" />;
  }

  if (!bundle && bundleError && isNotFoundError(bundleError)) {
    return (
      <div className="space-y-4">
        <EmptyState
          title="Case not found"
          description="This dossier ID does not exist or you no longer have access."
          action={
            <div className="flex flex-wrap justify-center gap-2">
              <Link to="/tasks" className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm">
                My Tasks
              </Link>
              <Link to="/permits" className="px-4 py-2 rounded-md border border-pp-border text-sm">
                Permit search
              </Link>
            </div>
          }
        />
      </div>
    );
  }

  if (!bundle && bundleError) {
    return (
      <div className="space-y-4">
        <Link to={from === "search" ? "/permits" : "/tasks"} className="text-sm text-pp-accent hover:underline">
          ← Back to {from === "search" ? "search" : "tasks"}
        </Link>
        {caseStub && (
          <div>
            <h1 className="text-2xl font-semibold text-pp-navy">{caseStub.address}</h1>
            <p className="text-sm text-slate-600 mt-1">
              BIN {caseStub.bin || "—"} · BBL {caseStub.bbl}
            </p>
          </div>
        )}
        <EmptyState
          title={isNotFoundError(bundleError) ? "Case not found" : "Couldn't load this case"}
          description={errorMessage(bundleError)}
          action={
            !isNotFoundError(bundleError) ? (
              <button type="button" onClick={() => load()} className="px-4 py-2 rounded-md bg-pp-accent text-white text-sm">
                Try again
              </button>
            ) : (
              <Link to="/tasks" className="px-4 py-2 rounded-md border border-pp-border text-sm">
                Back to tasks
              </Link>
            )
          }
        />
      </div>
    );
  }

  if (!caseData) {
    return <Skeleton rows={4} label="Loading case" />;
  }

  return (
    <div
      className="space-y-4"
      style={showDecisionFooter ? { paddingBottom: "var(--pp-footer-height, 9rem)" } : undefined}
    >
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link
            to={from === "search" ? "/permits" : "/tasks"}
            className="text-sm text-pp-accent hover:underline"
          >
            ← Back to {from === "search" ? "search" : "tasks"}
          </Link>
          <h1 className="text-2xl font-semibold text-pp-navy mt-1">{caseData.address}</h1>
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

      {canDecide && (failed.length > 0 || needsInfo.length > 0 || checking) && (
        <p className="text-sm text-slate-800 bg-slate-50 border border-pp-border rounded-md p-3" role="status">
          {checking && "Distribution is still running — approval is blocked until reviews finish. "}
          {!checking && failed.length > 0 && needsInfo.length > 0 && (
            <>
              {failed.length + needsInfo.length} department{failed.length + needsInfo.length === 1 ? "" : "s"} need
              attention ({failed.map((row) => row.department).join(", ")} failed;{" "}
              {needsInfo.map((row) => row.department).join(", ")} need info). See Distribution tab.
            </>
          )}
          {!checking && failed.length > 0 && needsInfo.length === 0 && (
            <>
              {failed.length} department review{failed.length === 1 ? "" : "s"} failed — see Distribution tab. Request
              changes or approve with override.
            </>
          )}
          {!checking && needsInfo.length > 0 && failed.length === 0 && (
            <>
              {needsInfo.length} department review{needsInfo.length === 1 ? "" : "s"} need more information (
              {needsInfo.map((row) => row.department).join(", ")}). Add missing identifiers on Summary or approve with
              override.
            </>
          )}
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
            <div className="flex items-center justify-between gap-2 mb-3">
              <h3 className="font-medium text-pp-navy">Property</h3>
              {canDecide && (
                <button
                  type="button"
                  onClick={openEditCase}
                  className="text-sm text-pp-accent hover:underline"
                >
                  Edit case details
                </button>
              )}
            </div>
            <dl className="text-sm space-y-2">
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Owner</dt>
                <dd className="text-right">
                  {caseData.owner || "—"}
                  <p className="text-xs text-slate-500 mt-1 text-left sm:text-right">
                    Owner from NYC PLUTO (public record). Names in intake packets are redacted before storage.
                  </p>
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Borough</dt>
                <dd>{caseData.borough || "—"}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate-500">Work</dt>
                <dd className="text-right max-w-xs">{caseData.work_type}</dd>
              </div>
              {context?.parcel?.zoning_district && (
                <div className="flex justify-between gap-4">
                  <dt className="text-slate-500">Zoning</dt>
                  <dd>{context.parcel.zoning_district}</dd>
                </div>
              )}
            </dl>
            {context?.parcel?.map_url && (
              <div className="pt-2 mt-2 border-t border-pp-border">
                <a
                  href={context.parcel.map_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sm text-pp-accent hover:underline"
                >
                  Open parcel map (NYC Open Data)
                </a>
              </div>
            )}
          </div>
          <div className="bg-white border border-pp-border rounded-lg p-4 space-y-4">
            <div>
              <h3 className="font-medium text-pp-navy mb-3">Case timeline</h3>
              <p className="text-sm text-slate-600">Opened {new Date(caseData.created_at).toLocaleString()}</p>
              <p className="text-sm text-slate-600">Updated {new Date(caseData.updated_at).toLocaleString()}</p>
              <button
                type="button"
                disabled={!canDecide || busy === "briefing"}
                onClick={() =>
                  runAction("briefing", async () => {
                    const result = await api.orchestrate(caseId);
                    setBriefing(result.summary);
                    writeBriefing(caseId, result.summary);
                  }, hasStoredBriefing ? "Clerk briefing regenerated." : "Clerk briefing generated.")
                }
                className="mt-4 text-sm px-3 py-1.5 rounded-md bg-pp-accent text-white disabled:opacity-50"
              >
                {busy === "briefing"
                  ? "Generating…"
                  : hasStoredBriefing
                    ? "Regenerate briefing"
                    : "Generate clerk briefing"}
              </button>
              {(briefing || storedBriefing?.summary) && (
                <div className="mt-3">
                  {storedBriefing?.generated_at && (
                    <p className="text-xs text-slate-500 mb-1">
                      Generated {new Date(storedBriefing.generated_at).toLocaleString()}
                      {storedBriefing.generated_by ? ` · ${storedBriefing.generated_by}` : ""}
                    </p>
                  )}
                  <p className="text-sm text-slate-700 border-l-4 border-pp-accent pl-3 whitespace-pre-wrap">
                    {briefing || storedBriefing?.summary}
                  </p>
                </div>
              )}
            </div>
            {contextLoading && (
              <p className="text-sm text-slate-500">Loading NYC Open Data context…</p>
            )}
            {context && !contextLoading && (
              <div>
                <h3 className="font-medium text-pp-navy mb-2">Related permits (NYC Open Data)</h3>
                {context.related_permits.length === 0 ? (
                  <p className="text-sm text-slate-600">No related permit filings found for this BBL or BIN.</p>
                ) : (
                  <>
                    <ul className="text-sm space-y-2">
                      {(showAllPermits
                        ? context.related_permits
                        : context.related_permits.slice(0, 5)).map((permit, index) => (
                        <li
                          key={`${permit.job_number ?? "job"}-${permit.filing_date ?? index}-${permit.work_type ?? ""}`}
                          className="border border-pp-border rounded p-2"
                        >
                          <p className="font-medium">{permit.job_number || "Filing (no job number)"}</p>
                          <p className="text-slate-600">{permit.work_type || "—"}</p>
                          <p className="text-slate-500 text-xs">
                            {permit.status || "Unknown status"}
                            {permit.filing_date ? ` · ${permit.filing_date}` : ""}
                          </p>
                        </li>
                      ))}
                    </ul>
                    {context.related_permits.length > 5 && (
                      <button
                        type="button"
                        className="mt-2 text-sm text-pp-accent hover:underline"
                        onClick={() => setShowAllPermits((open) => !open)}
                      >
                        {showAllPermits
                          ? "Show fewer"
                          : `Show all ${context.related_permits.length} permits`}
                      </button>
                    )}
                  </>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {tab === "distribution" && bundle && (
        <div role="tabpanel" id={`${tabsId}-panel-distribution`} aria-labelledby={`${tabsId}-distribution`} className="space-y-3">
          {stalled && (
            <p className="text-sm text-amber-900 bg-amber-50 border border-amber-200 rounded-md p-3" role="status">
              Department workflow stalled — resume to continue from the last checkpoint. Completed departments are not
              re-run.
            </p>
          )}
          {bundle.workflow.length > 0 && (
            <div className="bg-slate-50 border border-pp-border rounded-lg p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <p className="font-medium text-pp-navy">Department workflow</p>
                <div className="flex flex-wrap gap-2">
                  {workflowRunning && (
                    <button
                      type="button"
                      disabled={busy === "interrupt"}
                      onClick={() =>
                        runAction("interrupt", async () => {
                          await api.interruptWorkflow(caseId);
                        }, "Worker crash simulated — resume to continue.")
                      }
                      className="text-sm px-3 py-1 rounded-md border border-red-300 text-red-800 bg-white disabled:opacity-50"
                    >
                      {busy === "interrupt" ? "Interrupting…" : "Simulate worker crash"}
                    </button>
                  )}
                  {stalled && (
                    <button
                      type="button"
                      disabled={busy === "resume"}
                      onClick={() =>
                        runAction("resume", async () => {
                          await api.resumeWorkflow(caseId);
                        }, "Workflow resumed from checkpoint.")
                      }
                      className="text-sm px-3 py-1 rounded-md bg-pp-navy text-white disabled:opacity-50"
                    >
                      {busy === "resume" ? "Resuming…" : "Resume workflow"}
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={busy === "gcp"}
                    onClick={() =>
                      runAction("gcp", async () => {
                        await api.startGcpWorkflow(caseId);
                      }, "Cloud Workflows execution started.")
                    }
                    className="text-sm px-3 py-1 rounded-md border border-pp-border bg-white disabled:opacity-50"
                  >
                    {busy === "gcp" ? "Starting…" : "Run on Cloud Workflows"}
                  </button>
                </div>
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
          <div className="flex flex-wrap items-center justify-between gap-2">
            {distributionUpdatedAt && (
              <div className="text-sm text-slate-600">
                <p>Data as of {new Date(distributionUpdatedAt).toLocaleString()}</p>
                {distributionStale && (
                  <p className="text-amber-800 bg-amber-50 border border-amber-200 rounded px-2 py-1 mt-1 text-xs">
                    Distribution data is over 24 hours old — refresh from NYC Open Data before deciding.
                  </p>
                )}
              </div>
            )}
            <button
              type="button"
              disabled={!canDecide || busy === "refresh"}
              onClick={() =>
                runAction(
                  "refresh",
                  async () => {
                    const distribution = await api.refreshDistribution(caseId);
                    setBundle((prev) => (prev ? { ...prev, distribution } : prev));
                  },
                  "Distribution refreshed from NYC Open Data.",
                  false,
                )
              }
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
            <>
            <div className="table-scroll rounded-lg border border-pp-border bg-white">
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
                    <th scope="col" className="px-4 py-2">
                      Updated
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {departmentRows.map((row) => (
                    <tr key={row.department} className="border-t border-pp-border hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <button
                          type="button"
                          onClick={() => setSelected(row)}
                          className="flex items-center gap-2 text-left capitalize font-medium text-pp-navy hover:text-pp-accent w-full"
                        >
                          <span>{row.department}</span>
                          <span className="text-slate-400 text-xs" aria-hidden="true">›</span>
                          <span className="sr-only">Open {row.department} review details</span>
                        </button>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={row.status} />
                      </td>
                      <td className="px-4 py-3 text-slate-600">{row.summary}</td>
                      <td className="px-4 py-3 text-slate-500 text-xs">
                        {new Date(row.updated_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {criticReview && (
              <div className="bg-white border border-pp-border rounded-lg p-4">
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <h3 className="font-medium text-pp-navy">Policy check</h3>
                  <StatusBadge status={criticReview.status} />
                </div>
                <p className="text-sm text-slate-600">{criticReview.summary}</p>
                <button
                  type="button"
                  className="mt-3 text-sm text-pp-accent hover:underline"
                  onClick={() => setSelected(criticReview)}
                >
                  View policy check details
                </button>
              </div>
            )}
            </>
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
            Claims are recorded on the case file with a reference ID for manual DOB NOW entry. The applicant is not
            notified automatically.
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
                  }, "Claim recorded with manual DOB NOW reference.")
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
                    <div className="text-xs text-slate-600 space-y-2 border border-pp-border rounded-md p-3 bg-slate-50">
                      <p>
                        Reference for manual DOB NOW entry:{" "}
                        <span className="font-mono">{claim.notification_reference}</span>
                      </p>
                      <p className="text-slate-500">The applicant is not notified automatically.</p>
                      <div className="flex flex-wrap items-center gap-3">
                        <button
                          type="button"
                          className="text-xs px-2 py-1 rounded-md border border-pp-border bg-white"
                          onClick={() => navigator.clipboard.writeText(claim.notification_reference ?? "")}
                        >
                          Copy reference
                        </button>
                        {!claim.manual_dob_now_sent && (
                          <button
                            type="button"
                            className="text-xs px-2 py-1 rounded-md border border-pp-border bg-white"
                            disabled={busy === `dob-${claim.id}`}
                            onClick={() =>
                              runAction(`dob-${claim.id}`, async () => {
                                await api.markClaimDobNowSent(caseId, claim.id);
                              }, "Marked as sent to DOB NOW.")
                            }
                          >
                            {busy === `dob-${claim.id}` ? "Saving…" : "Mark as sent to DOB NOW"}
                          </button>
                        )}
                        {claim.manual_dob_now_sent && (
                          <span className="text-emerald-800">
                            Sent to DOB NOW manually
                            {claim.notified_at ? ` · ${new Date(claim.notified_at).toLocaleString()}` : ""}
                          </span>
                        )}
                      </div>
                    </div>
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
            <h3 className="font-medium text-pp-navy mb-3">Activity log</h3>
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
                {groupAuditEvents(bundle.audit).map((item, index) => {
                  if (item.kind === "workflow_group") {
                    return (
                      <li
                        key={`workflow-group-${index}`}
                        className="bg-slate-50 border border-pp-border rounded-md p-3 text-sm"
                      >
                        <p className="font-medium text-slate-700">
                          {item.count} department workflow step{item.count === 1 ? "" : "s"} completed
                        </p>
                        <p className="text-xs text-slate-500 mt-1">
                          {item.actor} · {new Date(item.at).toLocaleString()}
                        </p>
                      </li>
                    );
                  }
                  const { event, summary, truncated } = item;
                  const expanded = expandedAudit[event.id];
                  return (
                    <li key={event.id} className="bg-white border border-pp-border rounded-md p-3 text-sm">
                      <p className="font-medium capitalize">{formatStatus(event.action)}</p>
                      <p className="text-slate-600 whitespace-pre-wrap">
                        {truncated && expanded ? event.detail : summary}
                      </p>
                      {truncated && (
                        <button
                          type="button"
                          className="text-xs text-pp-accent hover:underline mt-1"
                          onClick={() =>
                            setExpandedAudit((prev) => ({ ...prev, [event.id]: !prev[event.id] }))
                          }
                        >
                          {expanded ? "Show less" : "Show more"}
                        </button>
                      )}
                      <p className="text-xs text-slate-500 mt-1">
                        {event.actor} · {new Date(event.at).toLocaleString()}
                      </p>
                    </li>
                  );
                })}
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
              <h3 className="text-sm font-medium">Findings</h3>
              <ul className="mt-2 text-sm list-disc pl-5 space-y-1">
                {selected.findings.map((finding) => (
                  <li key={finding}>{finding}</li>
                ))}
              </ul>
            </div>
            <div>
              <h3 className="text-sm font-medium">
                {selected.department === "critic" || selected.evidence.some((ev) => ev.source === "Policy check")
                  ? "Policy check"
                  : "Evidence (NYC Open Data)"}
              </h3>
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
                <h3 className="text-sm font-medium">Citations</h3>
                {selected.citations.map((citation) => (
                  <blockquote key={citation.code} className="mt-2 text-sm border-l-4 border-pp-accent pl-3 text-slate-700">
                    <p className="font-medium">{citation.code}</p>
                    <p>{citation.excerpt}</p>
                  </blockquote>
                ))}
              </div>
            )}
            {selected.status === "needs_info" &&
              (selected.summary.toLowerCase().includes("bin") || !caseData.bin) && (
                <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm space-y-2">
                  <p className="text-amber-900">This review needs a BIN to query NYC Open Data.</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy === "lookup-bin"}
                      onClick={() => lookupBinForCase()}
                      className="px-3 py-1.5 rounded-md bg-pp-accent text-white text-sm disabled:opacity-50"
                    >
                      {busy === "lookup-bin" ? "Looking up…" : "Look up BIN from address"}
                    </button>
                    {canDecide && (
                      <button
                        type="button"
                        onClick={() => {
                          setSelected(null);
                          openEditCase();
                        }}
                        className="px-3 py-1.5 rounded-md border border-pp-border text-sm"
                      >
                        Enter BIN manually
                      </button>
                    )}
                  </div>
                </div>
              )}
          </div>
        )}
      </ModalDialog>

      <ModalDialog open={editOpen} title="Edit case details" onClose={() => setEditOpen(false)}>
        <div className="space-y-3 text-sm">
          <label className="block">
            <span className="font-medium text-slate-700">Address</span>
            <input
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2"
              value={editForm.address}
              onChange={(e) => setEditForm((f) => ({ ...f, address: e.target.value }))}
            />
          </label>
          <label className="block">
            <span className="font-medium text-slate-700">BBL</span>
            <input
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2"
              value={editForm.bbl}
              onChange={(e) => setEditForm((f) => ({ ...f, bbl: e.target.value }))}
            />
          </label>
          <label className="block">
            <span className="font-medium text-slate-700">BIN</span>
            <input
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2"
              value={editForm.bin}
              onChange={(e) => setEditForm((f) => ({ ...f, bin: e.target.value }))}
            />
          </label>
          <label className="block">
            <span className="font-medium text-slate-700">Work type</span>
            <input
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2"
              value={editForm.work_type}
              onChange={(e) => setEditForm((f) => ({ ...f, work_type: e.target.value }))}
            />
          </label>
          <label className="block">
            <span className="font-medium text-slate-700">Owner</span>
            <input
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2"
              value={editForm.owner}
              onChange={(e) => setEditForm((f) => ({ ...f, owner: e.target.value }))}
            />
          </label>
          <label className="block">
            <span className="font-medium text-slate-700">Borough</span>
            <input
              className="mt-1 w-full border border-pp-border rounded-md px-3 py-2"
              value={editForm.borough}
              onChange={(e) => setEditForm((f) => ({ ...f, borough: e.target.value }))}
            />
          </label>
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              disabled={busy === "edit-case"}
              onClick={() => saveEditCase()}
              className="px-4 py-2 rounded-md bg-pp-accent text-white disabled:opacity-50"
            >
              {busy === "edit-case" ? "Saving…" : "Save changes"}
            </button>
            <button type="button" onClick={() => setEditOpen(false)} className="px-4 py-2 rounded-md border border-pp-border">
              Cancel
            </button>
          </div>
        </div>
      </ModalDialog>

      {showDecisionFooter && (
        <>
          <div
            ref={mobileFooterRef}
            className="sm:hidden fixed bottom-0 left-0 right-0 z-10 bg-white border-t border-pp-border p-3"
          >
            <button
              type="button"
              onClick={() => setDecisionSheetOpen(true)}
              className="w-full px-4 py-3 rounded-md bg-pp-navy text-white text-sm font-medium"
            >
              Record decision
            </button>
          </div>

          <dialog
            className="pp-dialog sm:hidden fixed inset-x-0 bottom-0 z-20 m-0 max-h-[85vh] w-full rounded-t-xl border border-pp-border bg-white p-4 shadow-xl open:flex open:flex-col"
            open={decisionSheetOpen}
            onClose={() => setDecisionSheetOpen(false)}
          >
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-medium text-pp-navy">Record decision</h2>
              <button type="button" onClick={() => setDecisionSheetOpen(false)} className="text-sm text-slate-600">
                Close
              </button>
            </div>
            <div className="flex-1 overflow-y-auto space-y-3 pb-4">
              {conditions.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-600 mb-2">Insert standard condition:</p>
                  <div className="flex flex-wrap gap-2">
                    {conditions.map((template) => (
                      <button
                        key={template.id}
                        type="button"
                        onClick={() => appendCondition(template)}
                        className="px-2 py-1 text-xs rounded-md border border-pp-border bg-slate-50"
                      >
                        {template.code}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <label htmlFor="clerk-note-mobile" className="text-sm font-medium text-slate-700">
                  Clerk note (required)
                </label>
                <textarea
                  id="clerk-note-mobile"
                  className="mt-1 w-full border border-pp-border rounded-md px-3 py-2 text-sm min-h-24"
                  placeholder="Clerk note — required for the audit trail"
                  value={note}
                  onChange={(e) => onNoteChange(e.target.value)}
                />
                {overrideNeeded && (
                  <p className="text-xs text-slate-500 mt-1">Override decisions require at least 20 characters.</p>
                )}
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={busy === "decide" || decisionBlocked}
                  title={decisionDisabledTitle}
                  onClick={() => requireNote(overrideNeeded) && setApproveOpen(true)}
                  className="flex-1 px-4 py-2 rounded-md bg-emerald-700 text-white text-sm font-medium disabled:opacity-50"
                >
                  Approve dossier
                </button>
                <button
                  type="button"
                  disabled={busy === "decide" || mutating}
                  onClick={() => requireNote() && setChangesOpen(true)}
                  className="flex-1 px-4 py-2 rounded-md border border-pp-border text-sm font-medium disabled:opacity-50"
                >
                  Request changes
                </button>
              </div>
            </div>
          </dialog>

          <footer
            ref={footerRef}
            className="hidden sm:block fixed bottom-0 left-0 right-0 z-10 bg-white border-t border-pp-border"
          >
            <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex flex-col gap-3">
              {conditions.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-slate-600 mb-2">Insert standard condition:</p>
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
                </div>
              )}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
                <div className="flex flex-col gap-2 sm:flex-1">
                  <label htmlFor="clerk-note" className="text-sm font-medium text-slate-700">
                    Clerk note (required)
                  </label>
                  <textarea
                    id="clerk-note"
                    className="w-full border border-pp-border rounded-md px-3 py-2 text-sm min-h-20"
                    placeholder="Clerk note — required for the audit trail"
                    value={note}
                    onChange={(e) => onNoteChange(e.target.value)}
                  />
                  {overrideNeeded && (
                    <p className="text-xs text-slate-500">Override decisions require at least 20 characters.</p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    disabled={busy === "decide" || decisionBlocked}
                    title={decisionDisabledTitle}
                    onClick={() => requireNote(overrideNeeded) && setApproveOpen(true)}
                    className="flex-1 sm:flex-none px-4 py-2 rounded-md bg-emerald-700 text-white text-sm font-medium disabled:opacity-50"
                  >
                    Approve dossier
                  </button>
                  <button
                    type="button"
                    disabled={busy === "decide" || mutating}
                    onClick={() => requireNote() && setChangesOpen(true)}
                    className="flex-1 sm:flex-none px-4 py-2 rounded-md border border-pp-border text-sm font-medium disabled:opacity-50"
                  >
                    Request changes
                  </button>
                </div>
              </div>
            </div>
          </footer>
        </>
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
