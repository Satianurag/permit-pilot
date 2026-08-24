import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import EmptyState from "../components/EmptyState";
import { StatusBadge } from "../components/StatusBadge";
import { api, Case } from "../lib/api";
import { errorMessage } from "../lib/errors";

export default function DossiersPage() {
  const [cases, setCases] = useState<Case[]>([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .listCases(query.trim() || undefined)
      .then(setCases)
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [query]);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-pp-navy">Permit search</h2>
        <p className="text-sm text-slate-600">Find any dossier by address, BBL, BIN, owner, or status.</p>
      </div>
      <label className="block">
        <span className="sr-only">Search permits</span>
        <input
          className="w-full max-w-xl border border-pp-border rounded-md px-3 py-2 text-sm"
          placeholder="Search address, BBL, BIN, owner, status…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </label>
      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-md p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}
      {loading ? (
        <p className="text-sm text-slate-600">Loading permits…</p>
      ) : cases.length === 0 ? (
        <EmptyState
          title="No permits match your search"
          description="Try a different address, BBL, or BIN."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-pp-border bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">
                  Address
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  BIN / BBL
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Work
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Status
                </th>
                <th scope="col" className="px-4 py-3 font-medium">
                  Updated
                </th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id} className="border-t border-pp-border hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link className="text-pp-accent font-medium hover:underline" to={`/cases/${item.id}`}>
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
