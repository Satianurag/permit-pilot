import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { api, Case } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { useDebouncedValue } from "../lib/useDebouncedValue";

const STATUS_FILTERS = [
  { id: "", label: "All statuses" },
  { id: "in_review", label: "In review" },
  { id: "awaiting_clerk", label: "Awaiting clerk" },
  { id: "awaiting_applicant", label: "Awaiting applicant" },
  { id: "approved", label: "Approved" },
  { id: "changes_requested", label: "Changes requested" },
] as const;

export default function DossiersPage() {
  const [params, setParams] = useSearchParams();
  const urlQuery = params.get("q") ?? "";
  const urlStatus = params.get("status") ?? "";
  const [draft, setDraft] = useState(urlQuery);
  const debounced = useDebouncedValue(draft, 300);
  const [cases, setCases] = useState<Case[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (debounced === urlQuery) return;
    const next = new URLSearchParams(params);
    if (debounced.trim()) next.set("q", debounced.trim());
    else next.delete("q");
    setParams(next, { replace: true });
  }, [debounced, params, setParams, urlQuery]);

  useEffect(() => {
    setLoading(true);
    api
      .listCases(urlQuery.trim() || undefined, urlStatus || undefined)
      .then(setCases)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [urlQuery, urlStatus]);

  useEffect(() => {
    const onPop = () => {
      const next = new URLSearchParams(window.location.search);
      setDraft(next.get("q") ?? "");
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const setStatus = (status: string) => {
    const next = new URLSearchParams(params);
    if (status) next.set("status", status);
    else next.delete("status");
    setParams(next, { replace: true });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Permit search"
        subtitle="Find a dossier by address, BBL, BIN, owner, or status. Search waits 300ms after you stop typing."
      />

      <div className="pp-panel max-w-4xl">
        <div className="flex flex-col sm:flex-row gap-3">
          <label className="block flex-1">
            <span className="block text-sm font-medium text-pp-navy mb-1.5">Search</span>
            <input
              className="pp-input"
              placeholder="Address, BBL, BIN, owner, status…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
            />
          </label>
          <label className="block sm:w-56">
            <span className="block text-sm font-medium text-pp-navy mb-1.5">Status</span>
            <select className="pp-select" value={urlStatus} onChange={(e) => setStatus(e.target.value)}>
              {STATUS_FILTERS.map((item) => (
                <option key={item.id || "all"} value={item.id}>
                  {item.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}
      {loading ? (
        <Skeleton rows={6} label="Loading permits" />
      ) : cases.length === 0 ? (
        <EmptyState title="No permits match your search" description="Try a different address, BBL, BIN, or status." />
      ) : (
        <div className="pp-table-wrap">
          <table className="pp-table">
            <caption className="sr-only">Matching permit dossiers</caption>
            <thead>
              <tr>
                <th scope="col">Address</th>
                <th scope="col">BIN / BBL</th>
                <th scope="col">Work</th>
                <th scope="col">Status</th>
                <th scope="col">Updated</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id} className="relative">
                  <td>
                    <Link
                      className="text-pp-accent font-medium hover:underline after:absolute after:inset-0"
                      to={`/cases/${item.id}?from=search`}
                    >
                      {item.address}
                    </Link>
                  </td>
                  <td className="text-pp-muted">
                    {item.bin || "—"} · {item.bbl}
                  </td>
                  <td className="text-pp-muted max-w-xs truncate">{item.work_type}</td>
                  <td>
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="text-pp-muted">{new Date(item.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
