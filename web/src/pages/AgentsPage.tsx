import AgentRegistry from "../components/AgentRegistry";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Agent Registry"
        title="Fleet"
        subtitle="Department agents deployed on Agent Runtime with Agent Identity. Tools are the governed NYC Open Data MCP server."
      />
      <Panel title="Registered agents" subtitle="Live catalog from Gemini Enterprise Agent Platform.">
        <AgentRegistry />
      </Panel>
    </div>
  );
}
