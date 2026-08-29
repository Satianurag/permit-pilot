import { useInfiniteQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import ActivityFeed from "../components/ActivityFeed";
import EmptyState from "../components/EmptyState";
import PageHeader from "../components/PageHeader";
import Skeleton from "../components/Skeleton";
import { api } from "../lib/api";
import { errorMessage } from "../lib/errors";
import { formatStatus } from "../lib/formatStatus";

const PAGE_SIZE = 50;

export default function ActivityPage() {
  const [params, setParams] = useSearchParams();
  const actionFilter = params.get("action") ?? "";
  const query = useInfiniteQuery({
    queryKey: ["activity", actionFilter],
    queryFn: ({ pageParam }) => api.listActivity(PAGE_SIZE, pageParam, actionFilter || undefined),
    initialPageParam: 0,
    getNextPageParam: (lastPage, pages) => {
      const loaded = pages.reduce((sum, page) => sum + page.items.length, 0);
      return loaded < lastPage.total ? loaded : undefined;
    },
  });

  const items = query.data?.pages.flatMap((page) => page.items) ?? [];
  const feed = query.data?.pages.at(-1);
  const setActionFilter = (action: string) => {
    const next = new URLSearchParams(params);
    if (action) next.set("action", action);
    else next.delete("action");
    setParams(next, { replace: true });
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recent activity"
        subtitle="Cross-case audit trail from Firestore — clerk actions, fleet enqueue, and distribution events. Agent run spans and Vertex reasoning chains live under Traces."
        action={
          <button type="button" className="pp-btn-secondary" onClick={() => void query.refetch()} disabled={query.isFetching}>
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
              disabled={query.isLoading && !feed}
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

      {query.error && (
        <p className="text-sm text-red-700 bg-red-50 border border-red-200 rounded-xl p-3" role="alert">
          {errorMessage(query.error)}
        </p>
      )}

      {query.isLoading && !feed ? (
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
              <Link to="/work" className="pp-btn-primary">
                Open task queue
              </Link>
            )
          }
        />
      ) : (
        <div className="pp-panel max-w-5xl">
          <ActivityFeed items={items} />
          {query.hasNextPage && (
            <div className="mt-6 flex justify-center">
              <button
                type="button"
                className="pp-btn-secondary"
                disabled={query.isFetchingNextPage}
                onClick={() => void query.fetchNextPage()}
              >
                {query.isFetchingNextPage ? "Loading…" : `Load more (${(feed?.total ?? 0) - items.length} remaining)`}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
