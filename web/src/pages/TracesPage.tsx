import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api, ObservabilityLinks, TraceRunSummary } from "../lib/api";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import TraceReplay from "../components/TraceReplay";
import EmptyState from "../components/EmptyState";
import Skeleton from "../components/Skeleton";
import { errorMessage } from "../lib/errors";

function formatWhen(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export default function TracesPage() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["traces"],
    queryFn: () => api.listTraces(20),
  });
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const runs = data?.runs ?? [];
  const links: ObservabilityLinks = data?.observability ?? {
    cloud_trace_url: null,
  };
  const selected = runs.find((run) => run.root_span_id === selectedId) ?? runs[0] ?? null;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Agent Platform"
        title="Observability"
        subtitle="Recent distribution runs with nested department spans. LLM and tool reasoning chains export to Vertex Agent Observability after fleet telemetry is enabled."
      />
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-950" role="alert">
          {errorMessage(error)}
        </p>
      )}

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <Panel title="Recent reasoning runs" subtitle={`${data?.total ?? 0} case run${data?.total === 1 ? "" : "s"} with spans`}>
          {isLoading ? (
            <Skeleton rows={6} label="Loading trace runs" />
          ) : runs.length === 0 ? (
            <EmptyState
              title="No runs recorded yet"
              description="Run Agent Runtime fleet on a case — department spans appear here; the orchestrator LLM/tool DAG is in Agent Observability."
            />
          ) : (
            <ul className="space-y-2">
              {runs.map((run) => (
                <RunRow
                  key={run.root_span_id}
                  run={run}
                  active={selected?.root_span_id === run.root_span_id}
                  onSelect={() => setSelectedId(run.root_span_id)}
                />
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Span tree" subtitle={selected ? selected.address : "Select a run"}>
          {selected ? (
            <TraceReplay
              spans={selected.spans}
              cloudTraceUrl={links.cloud_trace_url}
              agentObservabilityUrl={links.agent_observability_url}
              agentGatewayUrl={links.agent_gateway_url}
              agentRegistryUrl={links.agent_registry_url}
              topologyUrl={links.topology_url}
            />
          ) : (
            <EmptyState
              title="Select a run"
              description="Choose a case run to inspect nested department and orchestrator spans."
            />
          )}
        </Panel>
      </div>

      <Panel title="Platform consoles" subtitle="Deep links for judges and operators — GEAP Agent Observability shows invoke_agent and tool spans.">
        <ul className="space-y-2 text-sm">
          <ConsoleLink href={links.cloud_trace_url} label="Cloud Trace" />
          <ConsoleLink href={links.agent_observability_url} label="Agent Registry · permit_orchestrator (open Traces tab)" />
          <ConsoleLink href={links.agent_registry_url} label="Agent Registry" />
          <ConsoleLink href={links.agent_gateway_url} label="Agent Gateway" />
          <ConsoleLink href={links.model_armor_url} label="Model Armor" />
          <ConsoleLink href={links.topology_url} label="App Topology" />
        </ul>
      </Panel>
    </div>
  );
}

function RunRow({
  run,
  active,
  onSelect,
}: {
  run: TraceRunSummary;
  active: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        className={`w-full rounded-xl border px-3 py-3 text-left transition ${
          active ? "border-pp-accent bg-orange-50/60" : "border-pp-border bg-white hover:border-slate-300"
        }`}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="font-medium text-pp-navy">{run.address}</p>
            <p className="text-xs text-pp-muted mt-1">
              {run.span_count} span{run.span_count === 1 ? "" : "s"} · {formatWhen(run.started_at)}
            </p>
          </div>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              run.status === "error" ? "bg-red-100 text-red-800" : "bg-emerald-100 text-emerald-800"
            }`}
          >
            {run.status}
          </span>
        </div>
        <Link
          to={`/cases/${run.case_id}?tab=history`}
          className="text-xs text-pp-accent hover:underline mt-2 inline-block"
          onClick={(event) => event.stopPropagation()}
        >
          Open case audit
        </Link>
      </button>
    </li>
  );
}

function ConsoleLink({ href, label }: { href?: string | null; label: string }) {
  if (!href) return null;
  return (
    <li>
      <a href={href} className="text-pp-accent hover:underline" target="_blank" rel="noreferrer">
        {label}
      </a>
    </li>
  );
}
