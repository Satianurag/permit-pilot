import { TraceSpan } from "../lib/api";
import EmptyState from "./EmptyState";

interface Props {
  spans: TraceSpan[];
  cloudTraceUrl?: string | null;
  langfuseUrl?: string | null;
  gcpWorkflowsUrl?: string | null;
}

function formatWhen(value: string): string {
  return new Date(value).toLocaleString();
}

function buildTree(spans: TraceSpan[]): TraceSpan[] {
  const byId = new Map(spans.map((span) => [span.id, span]));
  const roots: TraceSpan[] = [];
  for (const span of spans) {
    if (!span.parent_id || !byId.has(span.parent_id)) {
      roots.push(span);
    }
  }
  return roots.length ? roots : spans;
}

function childrenOf(spans: TraceSpan[], parentId: string): TraceSpan[] {
  return spans.filter((span) => span.parent_id === parentId);
}

function SpanNode({ span, spans, depth = 0 }: { span: TraceSpan; spans: TraceSpan[]; depth?: number }) {
  const kids = childrenOf(spans, span.id);
  return (
    <li className="ml-4" style={{ marginLeft: depth > 0 ? depth * 12 : undefined }}>
      <p className="text-sm font-medium text-pp-navy">{span.name}</p>
      <p className="text-xs text-slate-500">
        {span.actor} · {span.duration_ms ?? 0}ms · {formatWhen(span.started_at)}
      </p>
      {span.detail && <p className="text-sm text-slate-600 mt-1">{span.detail}</p>}
      {kids.length > 0 && (
        <ul className="mt-2 space-y-3 border-l border-pp-border pl-3">
          {kids.map((child) => (
            <SpanNode key={child.id} span={child} spans={spans} depth={depth + 1} />
          ))}
        </ul>
      )}
    </li>
  );
}

export default function TraceReplay({ spans, cloudTraceUrl, langfuseUrl, gcpWorkflowsUrl }: Props) {
  if (spans.length === 0) {
    return (
      <EmptyState
        title="No activity recorded yet"
        description="Department and briefing spans appear here after distribution runs."
      />
    );
  }

  const roots = buildTree(spans);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap gap-3 text-sm">
        {cloudTraceUrl && (
          <a href={cloudTraceUrl} target="_blank" rel="noreferrer noopener" className="text-pp-accent hover:underline">
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
        {roots.map((span) => (
          <li key={span.id} className="relative">
            <span
              className={`absolute -left-1.5 mt-1.5 h-3 w-3 rounded-full border-2 border-white ${
                span.status === "ok" ? "bg-emerald-500" : "bg-red-500"
              }`}
              aria-hidden="true"
            />
            <SpanNode span={span} spans={spans} />
          </li>
        ))}
      </ol>
    </div>
  );
}
