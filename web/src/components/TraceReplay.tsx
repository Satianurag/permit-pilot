import { TraceSpan } from "../lib/api";
import EmptyState from "./EmptyState";

interface Props {
  spans: TraceSpan[];
  cloudTraceUrl?: string | null;
  langfuseUrl?: string | null;
  gcpWorkflowsUrl?: string | null;
}

export default function TraceReplay({ spans, cloudTraceUrl, langfuseUrl, gcpWorkflowsUrl }: Props) {
  if (spans.length === 0) {
    return (
      <EmptyState
        title="No trace spans recorded yet"
        description="Agent and briefing activity will appear here after distribution and review steps run."
      />
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3 text-sm">
        {cloudTraceUrl && (
          <a
            href={cloudTraceUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="text-pp-accent hover:underline"
          >
            Open in Cloud Trace (new tab)
          </a>
        )}
        {langfuseUrl && (
          <a href={langfuseUrl} target="_blank" rel="noreferrer noopener" className="text-pp-accent hover:underline">
            Open in Langfuse (new tab)
          </a>
        )}
        {gcpWorkflowsUrl && (
          <a
            href={gcpWorkflowsUrl}
            target="_blank"
            rel="noreferrer noopener"
            className="text-pp-accent hover:underline"
          >
            Open in Cloud Workflows (new tab)
          </a>
        )}
      </div>
      <ol className="relative border-l border-pp-border ml-3 space-y-4">
        {spans.map((span) => (
          <li key={span.id} className="ml-4">
            <span
              className={`absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white ${
                span.status === "ok" ? "bg-emerald-500" : "bg-red-500"
              }`}
              aria-hidden="true"
            />
            <p className="text-sm font-medium text-pp-navy">{span.name}</p>
            <p className="text-xs text-slate-500">
              {span.actor} · {span.duration_ms ?? 0}ms · {new Date(span.started_at).toLocaleTimeString()}
            </p>
            {span.detail && <p className="text-sm text-slate-600 mt-1">{span.detail}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}
