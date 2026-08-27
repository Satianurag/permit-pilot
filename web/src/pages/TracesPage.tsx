import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";
import { errorMessage } from "../lib/errors";

export default function TracesPage() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["observability"],
    queryFn: () => api.getObservability(),
  });
  const links = data ?? {};

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Optimize"
        title="Observability"
        subtitle="Cloud Trace, Agent Observability, Agent Registry, Model Armor, and App Topology consoles for this project."
      />
      {error && (
        <p className="rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-950" role="alert">
          {errorMessage(error)}
        </p>
      )}
      <Panel title="Console links">
        {isLoading ? (
          <p className="text-sm text-pp-muted">Loading console links…</p>
        ) : (
          <ul className="space-y-2 text-sm">
            <ConsoleLink href={pickUrl(links, "cloud_trace_url")} label="Cloud Trace" />
            <ConsoleLink href={pickUrl(links, "agent_observability_url")} label="Agent Observability" />
            <ConsoleLink href={pickUrl(links, "agent_registry_url")} label="Agent Registry" />
            <ConsoleLink href={pickUrl(links, "agent_gateway_url")} label="Agent Gateway" />
            <ConsoleLink href={pickUrl(links, "model_armor_url")} label="Model Armor" />
            <ConsoleLink href={pickUrl(links, "topology_url")} label="App Topology" />
          </ul>
        )}
        <p className="text-sm text-pp-muted mt-4">
          Per-case traces live on the case Audit tab after a distribution run. Open a case file to replay department
          spans with durations.
        </p>
      </Panel>
    </div>
  );
}

function pickUrl(data: Record<string, string | null>, key: string): string | null {
  const value = data[key];
  return typeof value === "string" ? value : null;
}

function ConsoleLink({ href, label }: { href: string | null; label: string }) {
  if (!href) return null;
  return (
    <li>
      <a href={href} className="text-pp-accent hover:underline" target="_blank" rel="noreferrer">
        {label}
      </a>
    </li>
  );
}
