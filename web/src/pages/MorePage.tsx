import { Link } from "react-router-dom";
import PageHeader from "../components/PageHeader";

const LINKS = [
  {
    to: "/more/departments",
    title: "Departments",
    detail: "Sister-agency specialists that can be reused across city departments.",
  },
  {
    to: "/more/security",
    title: "Security",
    detail: "Who is allowed to call specialists, and how city records are protected.",
  },
  {
    to: "/more/property-notes",
    title: "Property notes",
    detail: "Saved notes for a lot, including open objections from an earlier filing.",
  },
  {
    to: "/more/history",
    title: "Technical history",
    detail: "Run history for this deployment. Use this when a judge asks how the work was traced.",
  },
  {
    to: "/more/activity",
    title: "Activity log",
    detail: "Clerk and system actions across cases.",
  },
  {
    to: "/more/metrics",
    title: "Queue metrics",
    detail: "Counts and alerts. Daily work still starts on My work.",
  },
];

export default function MorePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="More"
        subtitle="These screens are the technical record. Daily work is on My work and Find a case."
      />
      <ul className="grid gap-3 sm:grid-cols-2">
        {LINKS.map((item) => (
          <li key={item.to}>
            <Link
              to={item.to}
              className="block bg-white border border-pp-border rounded-xl p-4 hover:border-pp-accent"
            >
              <p className="font-medium text-pp-navy">{item.title}</p>
              <p className="text-sm text-pp-muted mt-1">{item.detail}</p>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
