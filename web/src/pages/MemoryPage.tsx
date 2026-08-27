import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../lib/api";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import { errorMessage } from "../lib/errors";

export default function MemoryPage() {
  const [bbl, setBbl] = useState("3014930048");
  const [query, setQuery] = useState("");
  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ["memory", bbl, query],
    queryFn: () => api.getParcelMemory(bbl, query || undefined),
    enabled: bbl.length === 10,
  });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Memory Bank"
        title="Parcel memory"
        subtitle="Long-term memories scoped to a BBL so later cases recall prior determinations."
      />
      <Panel title="Lookup">
        <div className="flex flex-wrap gap-2">
          <input className="pp-input" value={bbl} onChange={(event) => setBbl(event.target.value)} aria-label="BBL" />
          <input
            className="pp-input flex-1 min-w-[12rem]"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Optional similarity query"
            aria-label="Memory search query"
          />
          <button type="button" className="pp-btn-primary" onClick={() => refetch()}>
            {isFetching ? "Loading…" : "Retrieve"}
          </button>
        </div>
        {error && (
          <p className="mt-3 text-sm text-red-800" role="alert">
            {errorMessage(error)}
          </p>
        )}
        <pre className="mt-4 text-xs overflow-auto bg-pp-paper-2 rounded-lg p-3">
          {JSON.stringify(data?.memories ?? [], null, 2)}
        </pre>
      </Panel>
    </div>
  );
}
