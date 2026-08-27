interface Props {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export default function PageHeader({ eyebrow, title, subtitle, action }: Props) {
  const today = new Date().toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <header className="pp-page-header">
      <div>
        <p className="pp-page-date">{eyebrow ?? today}</p>
        <h1 className="pp-page-title">{title}</h1>
        {subtitle && <p className="pp-page-subtitle">{subtitle}</p>}
      </div>
      {action}
    </header>
  );
}
