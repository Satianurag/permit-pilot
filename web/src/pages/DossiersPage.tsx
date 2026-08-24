import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import Skeleton from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { api, Case } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { useDebouncedValue } from "../lib/useDebouncedValue";

export default function DossiersPage() {
  const [params, setParams] = useSearchParams();
  const urlQuery = params.get("q") ?? "";
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
      .listCases(urlQuery.trim() || undefined)
      .then(setCases)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [urlQuery]);

  useEffect(() => {
    const onPop = () => {
      setDraft(new URLSearchParams(window.location.search).get("q") ?? "");
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-pp-navy">Permit search</h2>
        <p className="text-sm text-slate-600">Find a dossier by address, BBL, BIN, owner, or status. Search waits 300ms after you stop typing.</p>
      </div>
      <label className="block">
        <span className="sr-only">Search permits</span>
        <input
          className="w-full max-w-xl border border-pp-border rounded-md px-3 py-2 text-sm"
          placeholder="Search address, BBL, BIN, owner, status…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
        />
      </label>
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}
      {loading ? (
        <Skeleton rows={6} label="Loading permits" />
      ) : cases.length === 0 ? (
        <EmptyState title="No permits match your search" description="Try a different address, BBL, or BIN." />
      ) : (
        <div className="table-scroll rounded-lg border border-pp-border bg-white" tabIndex={0}>
          <table className="min-w-full text-sm">
            <caption className="sr-only">Matching permit dossiers</caption>
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th scope="col" className="px-4 py-2 font-medium">
                  Address
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  BIN / BBL
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Work
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Status
                </th>
                <th scope="col" className="px-4 py-2 font-medium">
                  Updated
                </th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id} className="relative border-t border-pp-border hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      className="text-pp-accent font-medium hover:underline after:absolute after:inset-0"
                      to={`/cases/${item.id}?from=search`}
                    >
                      {item.address}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {item.bin || "—"} · {item.bbl}
                  </td>
                  <td className="px-4 py-3 text-slate-600 max-w-xs truncate">{item.work_type}</td>
                  <td className="px-4 py-3">
                    <StatusBadge status={item.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-500">{new Date(item.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
