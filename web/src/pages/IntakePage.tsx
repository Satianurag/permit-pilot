import { Link, useNavigate } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import IntakeModal from "../components/IntakeModal";

export default function IntakePage() {
  const navigate = useNavigate();
  return (
    <div className="space-y-4">
      <PageHeader
        title="New intake"
        subtitle="Open a case file from an address, BBL, and packet. Completeness is checked before technical objections."
        action={
          <Link to="/work" className="pp-btn-secondary text-sm">
            Back to My work
          </Link>
        }
      />
      <IntakeModal open onClose={() => navigate("/work")} />
    </div>
  );
}
