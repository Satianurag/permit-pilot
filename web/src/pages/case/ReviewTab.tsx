import EmptyState from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import { CaseBundle, DepartmentReview } from "../../lib/api";
import {
  collectObjections,
  departmentLabel,
  generatedByBadge,
  generatedByHint,
  hitlKindLabel,
} from "../../lib/clerkLanguage";
import { formatStatus } from "../../lib/formatStatus";

export function ReviewTab({
  tabsId,
  bundle,
  departmentRows,
  criticReview,
  canDecide,
  busy,
  distributionUpdatedAt,
  distributionStale,
  onRefresh,
  onConfirmHitl,
  onRejectHitl,
  onSelect,
}: {
  tabsId: string;
  bundle: CaseBundle;
  departmentRows: DepartmentReview[];
  criticReview?: DepartmentReview;
  canDecide: boolean;
  busy: string | null;
  distributionUpdatedAt: string | null;
  distributionStale: boolean;
  onRefresh: () => void;
  onConfirmHitl: () => void;
  onRejectHitl: () => void;
  onSelect: (row: DepartmentReview) => void;
}) {
  const plan = bundle.routing_plan;
  const completeness = bundle.completeness;
  const pending = bundle.pending_hitl;
  const objections = collectObjections(departmentRows);
  const fallbackHint = departmentRows.map((row) => generatedByHint(row.generated_by)).find(Boolean);
  const skipped = Object.entries(plan?.skipped || {});
  const checking = departmentRows.some((row) => row.status === "checking") || bundle.workflow.some((step) => step.status === "running" || step.status === "pending");

  return (
    <div role="tabpanel" id={`${tabsId}-panel-review`} aria-labelledby={`${tabsId}-review`} className="space-y-4">
      {completeness && !completeness.complete_enough && (
        <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm space-y-2">
          <p className="font-medium text-amber-950">Packet is not complete enough for technical review</p>
          <p className="text-amber-900 whitespace-pre-wrap">{completeness.checklist || completeness.findings.join(" ")}</p>
          {completeness.missing.length > 0 && (
            <p className="text-amber-800 text-xs">Still needed: {completeness.missing.join(", ")}</p>
          )}
        </div>
      )}

      {fallbackHint && (
        <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-800">
          {fallbackHint}
        </div>
      )}

      {pending && !pending.confirmed && (
        <div className="rounded-xl border border-pp-border bg-white p-4 text-sm space-y-2">
          <p className="font-medium text-pp-navy">{hitlKindLabel(pending.kind)}</p>
          <p className="text-slate-600">Nothing has been sent to the applicant. Confirm to record it on the case file.</p>
          {typeof pending.payload.message === "string" && (
            <p className="text-slate-700 whitespace-pre-wrap">{pending.payload.message}</p>
          )}
          {typeof pending.payload.note === "string" && (
            <p className="text-slate-700 whitespace-pre-wrap">{pending.payload.note}</p>
          )}
          {canDecide && (
            <div className="flex flex-wrap gap-2">
              <button type="button" disabled={busy === "hitl"} onClick={onConfirmHitl} className="pp-btn-primary text-sm py-1.5 disabled:opacity-50">
                {busy === "hitl" ? "Saving…" : "Confirm"}
              </button>
              <button type="button" disabled={busy === "hitl-reject"} onClick={onRejectHitl} className="pp-btn-secondary text-sm py-1.5 disabled:opacity-50">
                Discard draft
              </button>
            </div>
          )}
        </div>
      )}

      {checking && (
        <p className="text-sm text-slate-700 bg-blue-50 border border-blue-100 rounded-xl p-3">Checking city records…</p>
      )}

      <div className="bg-white border border-pp-border rounded-xl p-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-medium text-pp-navy">Objection sheet</h3>
          <button type="button" disabled={!canDecide || busy === "refresh"} onClick={onRefresh} className="pp-btn-secondary text-sm py-1.5 disabled:opacity-50">
            {busy === "refresh" ? "Refreshing…" : "Refresh city records"}
          </button>
        </div>
        {distributionUpdatedAt && (
          <p className="text-xs text-slate-500">
            City records as of {new Date(distributionUpdatedAt).toLocaleString()}
            {distributionStale ? " — older than a day. Refresh before you decide." : ""}
          </p>
        )}
        {objections.length === 0 ? (
          <EmptyState
            title={completeness && !completeness.complete_enough ? "No technical objections yet" : "No open objections"}
            description={
              completeness && !completeness.complete_enough
                ? "Finish the completeness checklist first. Technical objections are written after the packet is complete enough."
                : "Specialists did not draft numbered objections for this work type. Read the department notes if you still need context."
            }
          />
        ) : (
          <div className="pp-table-wrap">
            <table className="pp-table">
              <caption className="sr-only">Numbered objections in DOB first-review form</caption>
              <thead>
                <tr>
                  <th scope="col">Obj #</th>
                  <th scope="col">Section of code</th>
                  <th scope="col">Description</th>
                </tr>
              </thead>
              <tbody>
                {objections.map((item) => (
                  <tr key={`${item.department}-${item.obj_no}`}>
                    <td className="font-mono">{item.obj_no}</td>
                    <td>
                      <p className="font-medium">{item.code || "—"}</p>
                      <p className="text-xs text-slate-500">{departmentLabel(item.department)}</p>
                    </td>
                    <td>
                      <p>{item.description}</p>
                      {item.recommended_fix ? <p className="text-xs text-slate-500 mt-1">{item.recommended_fix}</p> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {skipped.length > 0 && (
        <details className="bg-white border border-pp-border rounded-xl p-4 text-sm">
          <summary className="font-medium text-pp-navy cursor-pointer">Why was this skipped?</summary>
          <ul className="mt-3 list-disc pl-5 space-y-1 text-slate-600">
            {skipped.map(([dept, reason]) => (
              <li key={dept}>
                <span className="font-medium">{departmentLabel(dept)}</span> — {reason}
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="bg-white border border-pp-border rounded-xl p-4 space-y-3">
        <h3 className="font-medium text-pp-navy">Department progress</h3>
        {departmentRows.length === 0 ? (
          <p className="text-sm text-slate-600">No department notes yet. Completeness runs first.</p>
        ) : (
          <ul className="space-y-2">
            {departmentRows.map((row) => (
              <li key={row.department}>
                <button type="button" onClick={() => onSelect(row)} className="w-full text-left border border-pp-border rounded-xl p-3 hover:border-pp-accent">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-pp-navy">{departmentLabel(row.department)}</span>
                    <StatusBadge status={row.status} />
                    {generatedByBadge(row.generated_by) ? (
                      <span className="text-xs text-slate-500">{generatedByBadge(row.generated_by)}</span>
                    ) : null}
                  </div>
                  <p className="text-sm text-slate-600 mt-1">{row.summary}</p>
                </button>
              </li>
            ))}
          </ul>
        )}
        {criticReview && (
          <button type="button" onClick={() => onSelect(criticReview)} className="w-full text-left text-sm text-pp-accent hover:underline">
            Citation check: {formatStatus(criticReview.status)} — {criticReview.summary}
          </button>
        )}
      </div>
    </div>
  );
}

export function TechnicalHistoryControls({
  bundle,
  canDecide,
  busy,
  onFleet,
  onInterrupt,
  onResume,
}: {
  bundle: CaseBundle;
  canDecide: boolean;
  busy: string | null;
  onFleet: () => void;
  onInterrupt: () => void;
  onResume: () => void;
}) {
  return (
    <details className="bg-white border border-pp-border rounded-xl p-4 text-sm">
      <summary className="font-medium text-pp-navy cursor-pointer">Technical record</summary>
      <p className="text-slate-600 mt-2">
        Use this only when you need to re-run specialists or inspect a paused run. Daily review is on the Review tab.
      </p>
      <div className="flex flex-wrap gap-2 mt-3">
        <button type="button" disabled={busy === "fleet"} onClick={onFleet} className="pp-btn-secondary text-sm py-1.5 disabled:opacity-50">
          {busy === "fleet" ? "Queuing…" : "Re-run specialists"}
        </button>
        <button type="button" disabled={!canDecide || busy === "crash"} onClick={onInterrupt} className="pp-btn-ghost text-sm py-1.5 border border-pp-border disabled:opacity-50">
          {busy === "crash" ? "Flagging…" : "Pause remaining work"}
        </button>
        <button type="button" disabled={!canDecide || busy === "resume"} onClick={onResume} className="pp-btn-ghost text-sm py-1.5 border border-pp-border disabled:opacity-50">
          {busy === "resume" ? "Resuming…" : "Resume remaining work"}
        </button>
      </div>
      {bundle.interrupt_requested && (
        <p className="text-amber-800 text-xs mt-2">Pause requested — remaining hops will skip until you resume.</p>
      )}
      {(bundle.critic_iterations ?? 0) > 0 && (
        <p className="text-xs text-slate-500 mt-2">Citation re-checks: {bundle.critic_iterations}</p>
      )}
      {bundle.workflow.length > 0 && (
        <div className="flex flex-wrap gap-2 mt-3">
          {bundle.workflow.map((step) => (
            <span key={step.department ?? step.name} className="px-2 py-0.5 rounded-full text-xs bg-slate-50 border border-pp-border">
              {departmentLabel(step.department ?? step.name)}: {formatStatus(step.status)}
            </span>
          ))}
        </div>
      )}
    </details>
  );
}
