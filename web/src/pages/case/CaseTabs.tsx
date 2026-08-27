import EmptyState from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import TraceReplay from "../../components/TraceReplay";
import {
  Case,
  CaseBundle,
  Claim,
  ClerkBriefing,
  ConditionTemplate,
  DepartmentReview,
  ParcelContext,
  RelatedPermit,
} from "../../lib/api";
import { groupAuditEvents } from "../../lib/auditFormat";
import { formatStatus } from "../../lib/formatStatus";

export function SummaryTab({
  tabsId,
  caseData,
  canDecide,
  busy,
  briefing,
  storedBriefing,
  hasStoredBriefing,
  contextLoading,
  context,
  showAllPermits,
  onEdit,
  onBriefing,
  onTogglePermits,
}: {
  tabsId: string;
  caseData: Case;
  canDecide: boolean;
  busy: string | null;
  briefing: string | null;
  storedBriefing?: ClerkBriefing | null;
  hasStoredBriefing: boolean;
  contextLoading: boolean;
  context: { related_permits: RelatedPermit[]; parcel: ParcelContext | null } | null | undefined;
  showAllPermits: boolean;
  onEdit: () => void;
  onBriefing: () => void;
  onTogglePermits: () => void;
}) {
  return (
    <div role="tabpanel" id={`${tabsId}-panel-summary`} aria-labelledby={`${tabsId}-summary`} className="grid md:grid-cols-2 gap-4">
      <div className="bg-white border border-pp-border rounded-xl p-4">
        <div className="flex items-center justify-between gap-2 mb-3">
          <h3 className="font-medium text-pp-navy">Property</h3>
          {canDecide && (
            <button type="button" onClick={onEdit} className="text-sm text-pp-accent hover:underline">
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
            <a href={context.parcel.map_url} target="_blank" rel="noreferrer" className="text-sm text-pp-accent hover:underline">
              Open parcel map (NYC Open Data)
            </a>
          </div>
        )}
      </div>
      <div className="bg-white border border-pp-border rounded-xl p-4 space-y-4">
        <div>
          <h3 className="font-medium text-pp-navy mb-3">Case timeline</h3>
          <p className="text-sm text-slate-600">Opened {new Date(caseData.created_at).toLocaleString()}</p>
          <p className="text-sm text-slate-600">Updated {new Date(caseData.updated_at).toLocaleString()}</p>
          <button
            type="button"
            disabled={!canDecide || busy === "briefing"}
            onClick={onBriefing}
            className="mt-4 pp-btn-primary text-sm py-1.5 disabled:opacity-50"
          >
            {busy === "briefing" ? "Generating…" : hasStoredBriefing ? "Regenerate briefing" : "Generate clerk briefing"}
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
        {contextLoading && <p className="text-sm text-slate-500">Loading NYC Open Data context…</p>}
        {context && !contextLoading && (
          <div>
            <h3 className="font-medium text-pp-navy mb-2">Related permits (NYC Open Data)</h3>
            {context.related_permits.length === 0 ? (
              <p className="text-sm text-slate-600">No related permit filings found for this BBL or BIN.</p>
            ) : (
              <>
                <ul className="text-sm space-y-2">
                  {(showAllPermits ? context.related_permits : context.related_permits.slice(0, 5)).map((permit, index) => (
                    <li
                      key={`${permit.job_number ?? "job"}-${permit.filing_date ?? index}-${permit.work_type ?? ""}`}
                      className="border border-pp-border rounded-xl p-2"
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
                  <button type="button" className="mt-2 text-sm text-pp-accent hover:underline" onClick={onTogglePermits}>
                    {showAllPermits ? "Show fewer" : `Show all ${context.related_permits.length} permits`}
                  </button>
                )}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function DistributionTab({
  tabsId,
  bundle,
  departmentRows,
  criticReview,
  canDecide,
  busy,
  distributionUpdatedAt,
  distributionStale,
  onRefresh,
  onFleet,
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
  onFleet: () => void;
  onSelect: (row: DepartmentReview) => void;
}) {
  return (
    <div role="tabpanel" id={`${tabsId}-panel-distribution`} aria-labelledby={`${tabsId}-distribution`} className="space-y-3">
      {bundle.workflow.length > 0 && (
        <div className="bg-slate-50 border border-pp-border rounded-xl p-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <p className="font-medium text-pp-navy">Department fleet</p>
            <button type="button" disabled={busy === "fleet"} onClick={onFleet} className="pp-btn-secondary text-sm py-1.5 disabled:opacity-50">
              {busy === "fleet" ? "Queuing…" : "Run Agent Runtime fleet"}
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {bundle.workflow.map((step) => (
              <span key={step.department ?? step.name} className="px-2 py-0.5 rounded-full text-xs capitalize bg-white border border-pp-border">
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
              <p className="text-amber-800 bg-amber-50 border border-amber-200 rounded-xl px-2 py-1 mt-1 text-xs">
                Distribution data is over 24 hours old — refresh from NYC Open Data before deciding.
              </p>
            )}
          </div>
        )}
        <button type="button" disabled={!canDecide || busy === "refresh"} onClick={onRefresh} className="pp-btn-primary text-sm py-1.5 disabled:opacity-50">
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
          <div className="pp-table-wrap">
            <table className="pp-table">
              <caption className="sr-only">Department distribution reviews. Activate a row for findings.</caption>
              <thead>
                <tr>
                  <th scope="col">Department</th>
                  <th scope="col">Status</th>
                  <th scope="col">Summary</th>
                  <th scope="col">Updated</th>
                </tr>
              </thead>
              <tbody>
                {departmentRows.map((row) => (
                  <tr key={row.department}>
                    <td>
                      <button type="button" onClick={() => onSelect(row)} className="flex items-center gap-2 text-left capitalize font-medium text-pp-navy hover:text-pp-accent w-full">
                        <span>{row.department}</span>
                        <span className="text-slate-400 text-xs" aria-hidden="true">
                          ›
                        </span>
                        <span className="sr-only">Open {row.department} review details</span>
                      </button>
                    </td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>
                    <td className="text-slate-600">{row.summary}</td>
                    <td className="text-slate-500 text-xs">{new Date(row.updated_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {criticReview && (
            <div className="bg-white border border-pp-border rounded-xl p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <h3 className="font-medium text-pp-navy">Policy check</h3>
                <StatusBadge status={criticReview.status} />
              </div>
              <p className="text-sm text-slate-600">{criticReview.summary}</p>
              <button type="button" className="mt-3 text-sm text-pp-accent hover:underline" onClick={() => onSelect(criticReview)}>
                View policy check details
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export function DocumentsTab({
  tabsId,
  bundle,
  planUrl,
}: {
  tabsId: string;
  bundle: CaseBundle | null;
  planUrl: string | null;
}) {
  return (
    <div role="tabpanel" id={`${tabsId}-panel-documents`} aria-labelledby={`${tabsId}-documents`} className="space-y-4">
      {!bundle?.document ? (
        <EmptyState
          title="No intake document on file"
          description="Upload a plan PDF or applicant packet during intake. Packet text is stored redacted after PII removal."
        />
      ) : (
        <div className="bg-white border border-pp-border rounded-xl p-4 space-y-4">
          <div>
            <h3 className="font-medium text-pp-navy">Intake packet (redacted)</h3>
            <p className="text-xs text-slate-500 mt-1">
              {bundle.document.filename ? `${bundle.document.filename} · ` : ""}
              {bundle.document.redacted_text.length.toLocaleString()} characters · stored {new Date(bundle.document.stored_at).toLocaleString()}
            </p>
          </div>
          {bundle.document.pii_findings.length > 0 && (
            <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-sm">
              <p className="font-medium text-amber-900">PII redacted</p>
              <p className="text-amber-800 mt-1">{bundle.document.pii_findings.join(", ")}</p>
            </div>
          )}
          {bundle.document.redacted_text ? (
            <pre className="whitespace-pre-wrap text-sm text-slate-700 bg-slate-50 border border-pp-border rounded-xl p-4">
              {bundle.document.redacted_text}
            </pre>
          ) : (
            <p className="text-sm text-slate-600">No packet text — plan PDF only.</p>
          )}
          {bundle.document.has_pdf && (
            <div>
              <h3 className="font-medium text-pp-navy mb-2">Plan PDF</h3>
              {planUrl ? (
                <iframe title="Plan PDF" src={planUrl} className="w-full min-h-[28rem] border border-pp-border rounded-xl" />
              ) : (
                <p className="text-sm text-pp-muted">Loading plan PDF…</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function ClaimsTab({
  tabsId,
  bundle,
  canDecide,
  busy,
  claimText,
  responseText,
  respondingClaimId,
  onClaimText,
  onResponseText,
  onCreateClaim,
  onCopy,
  onMarkDob,
  onRespond,
  onStartRespond,
  onCancelRespond,
}: {
  tabsId: string;
  bundle: CaseBundle;
  canDecide: boolean;
  busy: string | null;
  claimText: string;
  responseText: string;
  respondingClaimId: string | null;
  onClaimText: (value: string) => void;
  onResponseText: (value: string) => void;
  onCreateClaim: () => void;
  onCopy: (value: string) => void;
  onMarkDob: (claim: Claim) => void;
  onRespond: (claim: Claim) => void;
  onStartRespond: (id: string) => void;
  onCancelRespond: () => void;
}) {
  return (
    <div role="tabpanel" id={`${tabsId}-panel-claims`} aria-labelledby={`${tabsId}-claims`} className="space-y-4">
      <p className="text-sm text-slate-600">
        Claims are recorded on the case file with a reference ID for manual DOB NOW entry. The applicant is not notified automatically.
      </p>
      {canDecide && (
        <div className="flex flex-col sm:flex-row gap-2">
          <label htmlFor="claim-message" className="sr-only">
            Request missing document
          </label>
          <input
            id="claim-message"
            className="pp-input flex-1"
            placeholder="Request missing document from applicant…"
            value={claimText}
            onChange={(e) => onClaimText(e.target.value)}
          />
          <button type="button" disabled={busy === "claim"} onClick={onCreateClaim} className="pp-btn-primary text-sm disabled:opacity-50">
            {busy === "claim" ? "Saving…" : "Record claim"}
          </button>
        </div>
      )}
      {bundle.claims.length === 0 ? (
        <EmptyState title="No claims on this case" description="Use a claim when the applicant must supply missing documents." />
      ) : (
        <ul className="space-y-3">
          {bundle.claims.map((claim: Claim) => (
            <li key={claim.id} className="bg-white border border-pp-border rounded-xl p-4 text-sm space-y-3">
              <div className="flex items-center justify-between gap-2">
                <StatusBadge status={claim.status} />
                <span className="text-xs text-slate-500">{new Date(claim.created_at).toLocaleString()}</span>
              </div>
              <p>{claim.message}</p>
              {claim.notification_reference && (
                <div className="text-xs text-slate-600 space-y-2 border border-pp-border rounded-xl p-3 bg-slate-50">
                  <p>
                    Reference for manual DOB NOW entry: <span className="font-mono">{claim.notification_reference}</span>
                  </p>
                  <p className="text-slate-500">The applicant is not notified automatically.</p>
                  <div className="flex flex-wrap items-center gap-3">
                    <button type="button" className="pp-btn-secondary text-xs py-1" onClick={() => onCopy(claim.notification_reference ?? "")}>
                      Copy reference
                    </button>
                    {!claim.manual_dob_now_sent && (
                      <button
                        type="button"
                        className="pp-btn-secondary text-xs py-1"
                        disabled={busy === `dob-${claim.id}`}
                        onClick={() => onMarkDob(claim)}
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
                <div className="rounded-xl bg-slate-50 border border-pp-border p-3">
                  <p className="text-xs font-medium text-slate-500">Applicant response (recorded by clerk)</p>
                  <p className="mt-1">{claim.response_message}</p>
                  {claim.responded_at && <p className="text-xs text-slate-500 mt-2">{new Date(claim.responded_at).toLocaleString()}</p>}
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
                        className="pp-input min-h-20"
                        value={responseText}
                        onChange={(e) => onResponseText(e.target.value)}
                      />
                      <div className="flex gap-2">
                        <button
                          type="button"
                          disabled={busy === `respond-${claim.id}`}
                          onClick={() => onRespond(claim)}
                          className="pp-btn-primary text-sm py-1.5 disabled:opacity-50"
                        >
                          {busy === `respond-${claim.id}` ? "Saving…" : "Save response"}
                        </button>
                        <button type="button" onClick={onCancelRespond} className="pp-btn-secondary text-sm py-1.5">
                          Cancel
                        </button>
                      </div>
                    </>
                  ) : (
                    <button type="button" onClick={() => onStartRespond(claim.id)} className="text-sm text-pp-accent hover:underline">
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
  );
}

export function AuditTab({
  tabsId,
  bundle,
  expandedAudit,
  onToggleAudit,
}: {
  tabsId: string;
  bundle: CaseBundle;
  expandedAudit: Record<string, boolean>;
  onToggleAudit: (id: string) => void;
}) {
  return (
    <div role="tabpanel" id={`${tabsId}-panel-audit`} aria-labelledby={`${tabsId}-audit`} className="space-y-6">
      <div className="bg-white border border-pp-border rounded-xl p-4">
        <h3 className="font-medium text-pp-navy mb-3">Activity log</h3>
        <TraceReplay
          spans={bundle.trace}
          cloudTraceUrl={bundle.observability.cloud_trace_url}
          agentGatewayUrl={bundle.observability.agent_gateway_url}
          agentRegistryUrl={bundle.observability.agent_registry_url}
          topologyUrl={bundle.observability.topology_url}
          agentObservabilityUrl={bundle.observability.agent_observability_url}
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
                  <li key={`workflow-group-${index}`} className="bg-slate-50 border border-pp-border rounded-xl p-3 text-sm">
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
                <li key={event.id} className="bg-white border border-pp-border rounded-xl p-3 text-sm">
                  <p className="font-medium capitalize">{formatStatus(event.action)}</p>
                  <p className="text-slate-600 whitespace-pre-wrap">{truncated && expanded ? event.detail : summary}</p>
                  {truncated && (
                    <button type="button" className="text-xs text-pp-accent hover:underline mt-1" onClick={() => onToggleAudit(event.id)}>
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
  );
}

export function DecisionFields({
  noteId,
  note,
  conditions,
  overrideNeeded,
  busy,
  decisionBlocked,
  decisionDisabledTitle,
  mutating,
  onNote,
  onAppend,
  onApprove,
  onChanges,
}: {
  noteId: string;
  note: string;
  conditions: ConditionTemplate[];
  overrideNeeded: boolean;
  busy: string | null;
  decisionBlocked: boolean;
  decisionDisabledTitle?: string;
  mutating: boolean;
  onNote: (value: string) => void;
  onAppend: (template: ConditionTemplate) => void;
  onApprove: () => void;
  onChanges: () => void;
}) {
  return (
    <div className="space-y-3">
      {conditions.length > 0 && (
        <div>
          <p className="text-xs font-medium text-slate-600 mb-2">Insert standard condition:</p>
          <div className="flex flex-wrap gap-2">
            {conditions.map((template) => (
              <button key={template.id} type="button" onClick={() => onAppend(template)} className="pp-btn-ghost text-xs py-1 border border-pp-border">
                {template.code}
              </button>
            ))}
          </div>
        </div>
      )}
      <div>
        <label htmlFor={noteId} className="text-sm font-medium text-slate-700">
          Clerk note (required)
        </label>
        <textarea
          id={noteId}
          className="pp-input mt-1 min-h-24"
          placeholder="Clerk note — required for the audit trail"
          value={note}
          onChange={(e) => onNote(e.target.value)}
        />
        {overrideNeeded && <p className="text-xs text-slate-500 mt-1">Override decisions require at least 20 characters.</p>}
      </div>
      <div className="flex gap-2">
        <button
          type="button"
          disabled={busy === "decide" || decisionBlocked}
          title={decisionDisabledTitle}
          onClick={onApprove}
          className="flex-1 px-4 py-2 rounded-full bg-emerald-700 text-white text-sm font-medium disabled:opacity-50"
        >
          Approve dossier
        </button>
        <button
          type="button"
          disabled={busy === "decide" || mutating}
          onClick={onChanges}
          className="flex-1 pp-btn-secondary text-sm disabled:opacity-50"
        >
          Request changes
        </button>
      </div>
    </div>
  );
}
