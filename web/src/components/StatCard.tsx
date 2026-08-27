import { Link } from "react-router-dom";

interface Props {
  label: string;
  value: string | number;
  meta?: string;
  href?: string;
  tone?: "default" | "warn" | "danger" | "success";
}

const toneStyles = {
  default: "text-pp-navy",
  warn: "text-amber-700",
  danger: "text-red-700",
  success: "text-emerald-700",
};

export default function StatCard({ label, value, meta, href, tone = "default" }: Props) {
  const body = (
    <>
      <p className="pp-stat-label">{label}</p>
      <p className={`pp-stat-value ${toneStyles[tone]}`}>{value}</p>
      {meta && <p className="pp-stat-meta">{meta}</p>}
    </>
  );

  if (href) {
    return (
      <Link to={href} className="pp-stat-card pp-card-hover block no-underline text-inherit">
        {body}
      </Link>
    );
  }

  return <div className="pp-stat-card">{body}</div>;
}
