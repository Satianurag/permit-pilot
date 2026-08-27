import AgentRegistry from "../components/AgentRegistry";
import PageHeader from "../components/PageHeader";
import Panel from "../components/Panel";

export default function AgentsPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Signed allowlist"
        title="Agent registry"
        subtitle="Fingerprint allowlist gateway — trusted agents are admitted; tampered fingerprints are blocked and logged on the open case file."
      />
      <Panel title="Registered agents" subtitle="Test gateway admission against the current case context when a case file is open.">
        <AgentRegistry />
      </Panel>
    </div>
  );
}
