import AgentRegistry from "../components/AgentRegistry";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Agent Registry"
        title="Fleet"
        subtitle="Department specialists on Agent Runtime. Test a signed invoke or send a tampered fingerprint — the allowlist returns 403, not a missing-admin error."
      />
      <Panel title="Registered agents" subtitle="Live catalog from Gemini Enterprise Agent Platform.">
        <AgentRegistry />
      </Panel>
    </div>
  );
}
