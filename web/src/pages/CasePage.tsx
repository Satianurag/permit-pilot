import { KeyboardEvent, useCallback, useEffect, useId, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import ConfirmDialog from "../components/ConfirmDialog";
import EmptyState from "../components/EmptyState";
import ModalDialog from "../components/ModalDialog";
import Skeleton from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { useToast } from "../components/Toast";
import { Sheet } from "../components/ui/sheet";
import { api, Case, Claim, ConditionTemplate, DepartmentReview, Task } from "../lib/api";
import { caseBackTarget } from "../lib/caseBack";
import { sortDepartmentReviews } from "../lib/auditFormat";
import { readBriefing, writeBriefing } from "../lib/briefingCache";
import { departmentLabel, generatedByHint } from "../lib/clerkLanguage";
import { errorMessage, isNotFoundError } from "../lib/errors";
import { readNoteDraft, writeNoteDraft } from "../lib/noteDraftCache";
import { reviewClock } from "../lib/reviewClock";
import { caseKeys, useCaseBundle, useCaseContext, useInvalidateCase } from "../lib/useCaseBundle";
import {
  AuditTab,
  ClaimsTab,
  DecisionFields,
  DocumentsTab,
  SummaryTab,
} from "./case/CaseTabs";
import { ReviewTab, TechnicalHistoryControls } from "./case/ReviewTab";

const TABS = ["overview", "review", "packet", "applicant", "history"] as const;
type Tab = (typeof TABS)[number];
const TAB_LABELS: Record<Tab, string> = {
  overview: "Overview",
  review: "Review",
  packet: "Packet",
  applicant: "Applicant",
  history: "History",
};
const LEGACY_TABS: Record<string, Tab> = {
  summary: "overview",
  distribution: "review",
  documents: "packet",
  claims: "applicant",
  audit: "history",
};
const TERMINAL = new Set(["approved", "changes_requested"]);
const DISTRIBUTION_STALE_MS = 24 * 60 * 60 * 1000;

function resolveTab(value: string | null): Tab {
  if (value && TABS.includes(value as Tab)) return value as Tab;
  if (value && LEGACY_TABS[value]) return LEGACY_TABS[value];
  return "review";
}

export default function CasePage() {
  const { id } = useParams();
  const caseId = id!;
  const tabsId = useId();
  const navigate = useNavigate();
  const { push } = useToast();
  const [params, setParams] = useSearchParams();
  const tab: Tab = resolveTab(params.get("tab"));
  const from = params.get("from") ?? "work";
  const back = caseBackTarget(from);
  const bundleQuery = useCaseBundle(caseId);
  const bundle = bundleQuery.data ?? null;
  const bundleError = bundleQuery.error ? errorMessage(bundleQuery.error) : null;
  const invalidate = useInvalidateCase();
  const contextQuery = useCaseContext(caseId, tab === "overview");
  const context = contextQuery.data ?? null;
  const contextLoading = contextQuery.isLoading || contextQuery.isFetching;
  const { data: conditions = [] } = useQuery({
    queryKey: ["conditions"],
    queryFn: api.listConditions,
  });
  const stubQuery = useQuery({
    queryKey: caseKeys.case(caseId),
    queryFn: () => api.getCase(caseId),
    enabled: Boolean(bundleError && !isNotFoundError(bundleError)),
  });
  const [selected, setSelected] = useState<DepartmentReview | null>(null);
  const [claimText, setClaimText] = useState("");
  const [responseText, setResponseText] = useState("");
  const [respondingClaimId, setRespondingClaimId] = useState<string | null>(null);
  const [note, setNote] = useState(() => readNoteDraft(caseId) ?? "");
  const [briefing, setBriefing] = useState<string | null>(() => readBriefing(caseId));
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [approveOpen, setApproveOpen] = useState(false);
  const [changesOpen, setChangesOpen] = useState(false);
  const [planUrl, setPlanUrl] = useState<string | null>(null);
  const [nextTask, setNextTask] = useState<Task | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editForm, setEditForm] = useState({ address: "", bbl: "", bin: "", work_type: "", owner: "", borough: "" });
  const [decisionSheetOpen, setDecisionSheetOpen] = useState(false);
  const [expandedAudit, setExpandedAudit] = useState<Record<string, boolean>>({});
  const [showAllPermits, setShowAllPermits] = useState(false);
  const footerRef = useRef<HTMLElement>(null);
  const mobileFooterRef = useRef<HTMLDivElement>(null);
  const [footerPad, setFooterPad] = useState(0);

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

  const focusNote = () => {
    const mobile = window.matchMedia("(max-width: 639px)").matches || decisionSheetOpen;
    document.getElementById(mobile ? "clerk-note-mobile" : "clerk-note")?.focus();
  };

  const requireNote = (override = false) => {
    if (!note.trim()) {
      setError("Clerk note is required for the audit trail");
      focusNote();
      return false;
    }
    if (override && note.trim().length < 20) {
      setError("Override decisions require a clerk note of at least 20 characters explaining why.");
      focusNote();
      return false;
    }
    return true;
  };

  const onNoteChange = (value: string) => {
    setNote(value);
    writeNoteDraft(caseId, value);
  };

  useEffect(() => {
    setBriefing(readBriefing(caseId));
    setNote(readNoteDraft(caseId) ?? "");
    setNextTask(null);
    setPlanUrl(null);
    setDecisionSheetOpen(false);
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
  const mutating = busy !== null;
  const showDecisionFooter = canDecide && (tab === "review" || tab === "overview");
  const skippedDepts = new Set(Object.keys(bundle?.routing_plan?.skipped || {}));
  const technicalReviews =
    bundle?.distribution.filter((row) => row.department !== "critic" && !skippedDepts.has(row.department)) ?? [];
  const failed = technicalReviews.filter((row) => row.status === "fail");
  const needsInfo = technicalReviews.filter((row) => row.status === "needs_info");
  const checking = technicalReviews.some((row) => row.status === "checking");
  const overrideNeeded = failed.length > 0 || needsInfo.length > 0;
  const departmentRows = sortDepartmentReviews(technicalReviews);
  const criticReview = bundle?.distribution.find((row) => row.department === "critic");
  const distributionUpdatedAt = bundle?.distribution.reduce<string | null>((latest, row) => {
    if (!row.updated_at) return latest;
    if (!latest || row.updated_at > latest) return row.updated_at;
    return latest;
  }, null);
  const distributionStale =
    distributionUpdatedAt != null && Date.now() - new Date(distributionUpdatedAt).getTime() > DISTRIBUTION_STALE_MS;
  const storedBriefing = bundle?.briefing;
  const hasStoredBriefing = Boolean(storedBriefing?.summary || briefing);

  useEffect(() => {
    if (!showDecisionFooter) {
      setFooterPad(0);
      return;
    }
    const sync = () => {
      const desktop = footerRef.current;
      const mobile = mobileFooterRef.current;
      const height =
        desktop && desktop.offsetHeight > 0 ? desktop.offsetHeight : (mobile?.offsetHeight ?? 0);
      setFooterPad(height > 0 ? height + 16 : 0);
    };
    sync();
    const ro = new ResizeObserver(sync);
    if (footerRef.current) ro.observe(footerRef.current);
    if (mobileFooterRef.current) ro.observe(mobileFooterRef.current);
    return () => ro.disconnect();
  }, [showDecisionFooter, decisionSheetOpen, failed.length, needsInfo.length, conditions.length, note]);

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
      if (reload) await invalidate(caseId);
      if (successMessage) push(successMessage, "success", { sticky: stickySuccess });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(null);
    }
  };

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
      "BIN resolved — fire, housing, and building reviews queued.",
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

  const appendCondition = (template: ConditionTemplate) => {
    const line = `${template.code}: ${template.label}`;
    onNoteChange(note.trim() ? `${note.trim()}\n${line}` : line);
    focusNote();
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
          .sort((a, b) => reviewClock(a.created_at).due.getTime() - reviewClock(b.created_at).due.getTime());
        setNextTask(sorted[0] ?? null);
      },
      decision === "approve" ? "Dossier approved." : "Changes requested.",
      true,
      true,
    );

  const copyText = useCallback((value: string) => {
    void navigator.clipboard.writeText(value);
    push("Copied to clipboard.", "info");
  }, [push]);

  if (bundleQuery.isLoading && !bundle) {
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
              <Link to="/work" className="pp-btn-primary text-sm">
                My work
              </Link>
              <Link to="/find" className="pp-btn-secondary text-sm">
                Find a case
              </Link>
            </div>
          }
        />
      </div>
    );
  }

  if (!bundle && bundleError) {
    const caseStub = stubQuery.data;
    return (
      <div className="space-y-4">
        <Link to={back.to} className="text-sm text-pp-accent hover:underline">
          ← Back to {back.label}
        </Link>
        {caseStub && (
          <div>
            <h1 className="pp-page-title">{caseStub.address}</h1>
            <p className="text-sm text-slate-600 mt-1">
              BIN {caseStub.bin || "—"} · BBL {caseStub.bbl}
            </p>
          </div>
        )}
        <EmptyState
          title="Couldn't load this case"
          description={errorMessage(bundleError)}
          action={
            <button type="button" onClick={() => void bundleQuery.refetch()} className="pp-btn-primary text-sm">
              Try again
            </button>
          }
        />
      </div>
    );
  }

  if (!caseData || !bundle) {
    return <Skeleton rows={4} label="Loading case" />;
  }

  const decisionProps = {
    note,
    conditions,
    overrideNeeded,
    busy,
    decisionBlocked,
    decisionDisabledTitle,
    mutating,
    onNote: onNoteChange,
    onAppend: appendCondition,
    onApprove: () => requireNote(overrideNeeded) && setApproveOpen(true),
    onChanges: () => requireNote() && setChangesOpen(true),
  };

  return (
    <div className="space-y-4" style={footerPad > 0 ? { paddingBottom: `${footerPad}px` } : undefined}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <Link to={back.to} className="text-sm text-pp-accent hover:underline">
            ← Back to {back.label}
          </Link>
          <h1 className="pp-page-title mt-1">{caseData.address}</h1>
          <p className="text-sm text-slate-600 mt-1">
            BIN {caseData.bin || "—"} · BBL {caseData.bbl} · {caseData.work_type}
          </p>
        </div>
        <StatusBadge status={caseData.status} />
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}

      {nextTask && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-950" role="status">
          Decision saved.{" "}
          <button
            type="button"
            className="font-medium underline"
            onClick={() => navigate(`/cases/${nextTask.case_id}?tab=review&from=work`)}
          >
            Open next task: {nextTask.title}
          </button>
        </div>
      )}

      {canDecide && (failed.length > 0 || needsInfo.length > 0 || checking) && (
        <p className="text-sm text-slate-800 bg-slate-50 border border-pp-border rounded-xl p-3" role="status">
          {checking && "Distribution is still running — approval is blocked until reviews finish. "}
          {!checking && failed.length > 0 && needsInfo.length > 0 && (
            <>
              {failed.length + needsInfo.length} departments need attention (
              See Review.
            </>
          )}
          {!checking && failed.length > 0 && needsInfo.length === 0 && (
            <>
              {failed.length} department review{failed.length === 1 ? "" : "s"} have objections — see Review. Request
              changes or approve with override.
            </>
          )}
          {!checking && needsInfo.length > 0 && failed.length === 0 && (
            <>
              {needsInfo.length} department review{needsInfo.length === 1 ? "" : "s"} need more information (
              {needsInfo.map((row) => row.department).join(", ")}). Add missing identifiers on Overview or approve with
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
            className={`px-4 py-2 text-sm border-b-2 -mb-px ${
              tab === name ? "border-pp-accent text-pp-accent font-medium" : "border-transparent text-slate-600"
            }`}
          >
            {TAB_LABELS[name]}
          </button>
        ))}
      </div>

      <div hidden={tab !== "overview"}>
        <SummaryTab
          tabsId={tabsId}
          caseData={caseData}
          canDecide={canDecide}
          busy={busy}
          briefing={briefing}
          storedBriefing={storedBriefing}
          hasStoredBriefing={hasStoredBriefing}
          contextLoading={contextLoading}
          context={context}
          showAllPermits={showAllPermits}
          onEdit={openEditCase}
          onBriefing={() =>
            runAction(
              "briefing",
              async () => {
                const result = await api.orchestrate(caseId);
                setBriefing(result.summary);
                writeBriefing(caseId, result.summary);
              },
              hasStoredBriefing ? "Clerk briefing regenerated." : "Clerk briefing generated.",
            )
          }
          onTogglePermits={() => setShowAllPermits((value) => !value)}
        />
      </div>
      <div hidden={tab !== "review"}>
        <ReviewTab
          tabsId={tabsId}
          bundle={bundle}
          departmentRows={departmentRows}
          criticReview={criticReview}
          canDecide={canDecide}
          busy={busy}
          distributionUpdatedAt={distributionUpdatedAt ?? null}
          distributionStale={distributionStale}
          onRefresh={() =>
            runAction(
              "refresh",
              async () => {
                await api.refreshDistribution(caseId);
              },
              "City records refresh queued.",
            )
          }
          onConfirmHitl={() =>
            runAction("hitl", async () => {
              await api.confirmHitl(caseId);
            }, "Draft recorded on the case file.")
          }
          onRejectHitl={() =>
            runAction("hitl-reject", async () => {
              await api.rejectHitl(caseId);
            }, "Draft discarded. The case was not changed.")
          }
          onSelect={setSelected}
        />
      </div>
      <div hidden={tab !== "packet"}>
        <DocumentsTab tabsId={tabsId} bundle={bundle} planUrl={planUrl} />
      </div>
      <div hidden={tab !== "applicant"}>
        <ClaimsTab
          tabsId={tabsId}
          bundle={bundle}
          canDecide={canDecide}
          busy={busy}
          claimText={claimText}
          responseText={responseText}
          respondingClaimId={respondingClaimId}
          onClaimText={setClaimText}
          onResponseText={setResponseText}
          onCreateClaim={() =>
            runAction(
              "claim",
              async () => {
                if (!claimText.trim()) throw new Error("Enter a document request for the applicant");
                await api.createClaim(caseId, claimText.trim());
                setClaimText("");
              },
              "Claim recorded with manual DOB NOW reference.",
            )
          }
          onCopy={copyText}
          onMarkDob={(claim: Claim) =>
            runAction(`dob-${claim.id}`, async () => {
              await api.markClaimDobNowSent(caseId, claim.id);
            }, "Marked as entered in DOB NOW.")
          }
          onRespond={(claim: Claim) =>
            runAction(`respond-${claim.id}`, async () => {
              if (!responseText.trim()) throw new Error("Enter a response");
              await api.respondToClaim(caseId, claim.id, responseText.trim());
              setRespondingClaimId(null);
              setResponseText("");
            }, "Applicant response recorded. Fleet re-queued.")
          }
          onStartRespond={(id) => setRespondingClaimId(id)}
          onCancelRespond={() => {
            setRespondingClaimId(null);
            setResponseText("");
          }}
        />
      </div>
      <div hidden={tab !== "history"}>
        <TechnicalHistoryControls
          bundle={bundle}
          canDecide={canDecide}
          busy={busy}
          onFleet={() =>
            runAction("fleet", async () => {
              await api.runFleet(caseId);
            }, "Specialist re-run queued.")
          }
          onInterrupt={() =>
            runAction("crash", async () => {
              await api.interruptDistribution(caseId);
            }, "Remaining work paused.")
          }
          onResume={() =>
            runAction("resume", async () => {
              await api.resumeDistribution(caseId);
            }, "Resume queued. Finished departments are skipped.")
          }
        />
        <AuditTab
          tabsId={tabsId}
          bundle={bundle}
          expandedAudit={expandedAudit}
          onToggleAudit={(id) => setExpandedAudit((current) => ({ ...current, [id]: !current[id] }))}
        />
      </div>

      <ModalDialog
        open={Boolean(selected)}
        title={selected ? `${departmentLabel(selected.department)} review` : "Department review"}
        onClose={() => setSelected(null)}
        variant="drawer"
      >
        {selected && (
          <div className="space-y-4">
            <StatusBadge status={selected.status} />
            {generatedByHint(selected.generated_by) ? (
              <p className="text-sm text-slate-600">{generatedByHint(selected.generated_by)}</p>
            ) : null}
            <p className="text-sm text-slate-700">{selected.summary}</p>
            {(selected.objections ?? []).length > 0 && (
              <div>
                <h3 className="text-sm font-medium">Objections</h3>
                <ol className="mt-2 text-sm space-y-2">
                  {selected.objections?.map((item) => (
                    <li key={item.obj_no} className="border border-pp-border rounded-xl p-2">
                      <p className="font-medium">
                        Obj {item.obj_no} · {item.code || "uncited"}
                      </p>
                      <p className="text-slate-600">{item.description}</p>
                    </li>
                  ))}
                </ol>
              </div>
            )}
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
                  <li key={`${ev.dataset_id}-${ev.label}`} className="border border-pp-border rounded-xl p-2">
                    <span className="text-slate-500">{ev.label}</span>: <strong>{String(ev.value)}</strong>
                    <p className="text-xs text-slate-500 mt-1">{ev.dataset_id}</p>
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
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm space-y-2">
                  <p className="text-amber-900">This review needs a BIN to query NYC Open Data.</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={busy === "lookup-bin"}
                      onClick={() => lookupBinForCase()}
                      className="pp-btn-primary text-sm"
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
                        className="pp-btn-secondary text-sm"
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
          {(["address", "bbl", "bin", "work_type", "owner", "borough"] as const).map((field) => (
            <label key={field} className="block">
              <span className="font-medium text-slate-700 capitalize">{field.replace("_", " ")}</span>
              <input
                className="pp-input mt-1"
                value={editForm[field]}
                onChange={(e) => setEditForm((form) => ({ ...form, [field]: e.target.value }))}
              />
            </label>
          ))}
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={() => setEditOpen(false)} className="pp-btn-secondary">
              Cancel
            </button>
            <button type="button" onClick={() => saveEditCase()} className="pp-btn-primary" disabled={busy === "edit-case"}>
              {busy === "edit-case" ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </ModalDialog>

      {showDecisionFooter && (
        <>
          <div ref={mobileFooterRef} className="pp-decision-footer-mobile sm:hidden">
            <button type="button" onClick={() => setDecisionSheetOpen(true)} className="w-full pp-btn-primary py-3">
              Record decision
            </button>
          </div>
          <Sheet open={decisionSheetOpen} onOpenChange={setDecisionSheetOpen} title="Record decision">
            <DecisionFields noteId="clerk-note-mobile" {...decisionProps} />
          </Sheet>
          <footer ref={footerRef} className="pp-decision-footer hidden sm:block">
            <div className="pp-decision-footer-inner py-3">
              <DecisionFields noteId="clerk-note" {...decisionProps} />
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
