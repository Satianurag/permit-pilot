import { Link } from "react-router-dom";

interface Props {
  onNewIntake: () => void;
}

export default function QuickActions({ onNewIntake }: Props) {
  return (
    <ul className="space-y-1">
      <li>
        <button type="button" onClick={onNewIntake} className="pp-quick-action w-full text-left">
          <span className="pp-quick-action-icon" aria-hidden>
            +
          </span>
          <span>
            <span className="block text-sm font-semibold text-pp-navy">New intake</span>
            <span className="block text-xs text-pp-muted">Create dossier and run distribution</span>
          </span>
        </button>
      </li>
      <li>
        <Link to="/tasks" className="pp-quick-action">
          <span className="pp-quick-action-icon" aria-hidden>
            ☰
          </span>
          <span>
            <span className="block text-sm font-semibold text-pp-navy">Open task queue</span>
            <span className="block text-xs text-pp-muted">All open reviews by review clock</span>
          </span>
        </Link>
      </li>
      <li>
        <Link to="/tasks?assign=mine" className="pp-quick-action">
          <span className="pp-quick-action-icon" aria-hidden>
            ◉
          </span>
          <span>
            <span className="block text-sm font-semibold text-pp-navy">My assigned work</span>
            <span className="block text-xs text-pp-muted">Tasks assigned to you</span>
          </span>
        </Link>
      </li>
      <li>
        <Link to="/permits" className="pp-quick-action">
          <span className="pp-quick-action-icon" aria-hidden>
            ⌕
          </span>
          <span>
            <span className="block text-sm font-semibold text-pp-navy">Search permits</span>
            <span className="block text-xs text-pp-muted">Find any dossier by address or BBL</span>
          </span>
        </Link>
      </li>
    </ul>
  );
}
