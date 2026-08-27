import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import ActivityFeed from "../components/ActivityFeed";
import EmptyState from "../components/EmptyState";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import { api, ActivityFeedResponse } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";

const PAGE_SIZE = 50;

export default function ActivityPage() {
  const [params, setParams] = useSearchParams();
  const actionFilter = params.get("action") ?? "";
  const [feed, setFeed] = useState<ActivityFeedResponse | null>(null);
  const [items, setItems] = useState<ActivityFeedResponse["items"]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);

  const load = (offset = 0, append = false) => {
    if (append) setLoadingMore(true);
    else setLoading(true);

    api
      .listActivity(PAGE_SIZE, offset, actionFilter || undefined)
      .then((response) => {
        setFeed(response);
        setItems((current) => (append ? [...current, ...response.items] : response.items));
        setError(null);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => {
        setLoading(false);
        setLoadingMore(false);
      });
  };

  useEffect(() => {
    load(0, false);
  }, [actionFilter]);

  const setActionFilter = (action: string) => {
    const next = new URLSearchParams(params);
    if (action) next.set("action", action);
    else next.delete("action");
    setParams(next, { replace: true });
  };

  const hasMore = feed ? items.length < feed.total : false;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recent activity"
        subtitle="Cross-case audit trail from Firestore — every clerk action, workflow step, and distribution event. Per-case trace replay stays on each dossier's Audit tab."
        action={
          <button type="button" className="pp-btn-secondary" onClick={() => load(0, false)} disabled={loading}>
            Refresh
          </button>
        }
      />

      <div className="pp-panel max-w-5xl">
        <div className="flex flex-col sm:flex-row sm:items-end gap-3">
          <label className="block flex-1">
            <span className="block text-sm font-medium text-pp-navy mb-1.5">Filter by action</span>
            <select
              className="pp-select"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              disabled={loading && !feed}
            >
              <option value="">All actions</option>
              {(feed?.actions ?? []).map((action) => (
                <option key={action} value={action}>
                  {formatStatus(action)}
                </option>
              ))}
            </select>
          </label>
          {feed && (
            <p className="text-sm text-pp-muted sm:pb-2">
              Showing {items.length} of {feed.total} event{feed.total === 1 ? "" : "s"}
            </p>
          )}
        </div>
      </div>

      {error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3" role="alert">
          {errorMessage(error)}
        </p>
      )}

      {loading && !feed ? (
        <Skeleton rows={8} label="Loading activity feed" />
      ) : items.length === 0 ? (
        <EmptyState
          title="No activity in this view"
          description={
            actionFilter
              ? "Try clearing the action filter to see the full audit feed."
              : "Audit events appear when cases are created, reviewed, or updated."
          }
          action={
            actionFilter ? (
              <button type="button" className="pp-btn-secondary" onClick={() => setActionFilter("")}>
                Clear filter
              </button>
            ) : (
              <Link to="/tasks" className="pp-btn-primary">
                Open task queue
              </Link>
            )
          }
        />
      ) : (
        <div className="pp-panel max-w-5xl">
          <ActivityFeed items={items} />
          {hasMore && (
            <div className="mt-6 flex justify-center">
              <button
                type="button"
                className="pp-btn-secondary"
                disabled={loadingMore}
                onClick={() => load(items.length, true)}
              >
                {loadingMore ? "Loading…" : `Load more (${feed!.total - items.length} remaining)`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
