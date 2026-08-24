import { TraceSpan } from "../lib/api";

interface Props {
  spans: TraceSpan[];
  cloudTraceUrl?: string | null;
  langfuseUrl?: string | null;
  gcpWorkflowsUrl?: string | null;
}

export default function TraceReplay({ spans, cloudTraceUrl, langfuseUrl, gcpWorkflowsUrl }: Props) {
  if (spans.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No trace spans yet. Run distribution workflow to record agent steps.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3 text-sm">
        {cloudTraceUrl && (
          <a href={cloudTraceUrl} target="_blank" rel="noreferrer" className="text-pp-accent hover:underline">
            Open in Cloud Trace →
          </a>
        )}
        {langfuseUrl && (
          <a href={langfuseUrl} target="_blank" rel="noreferrer" className="text-pp-accent hover:underline">
            Open in Langfuse →
          </a>
        )}
        {gcpWorkflowsUrl && (
          <a href={gcpWorkflowsUrl} target="_blank" rel="noreferrer" className="text-pp-accent hover:underline">
            Open in Cloud Workflows →
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
            />
            <p className="text-sm font-medium text-pp-navy">{span.name}</p>
            <p className="text-xs text-slate-500">
              {span.actor} · {span.duration_ms ?? 0}ms ·{" "}
              {new Date(span.started_at).toLocaleTimeString()}
            </p>
            {span.detail && <p className="text-sm text-slate-600 mt-1">{span.detail}</p>}
          </li>
        ))}
      </ol>
    </div>
  );
}
