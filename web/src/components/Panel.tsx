interface Props {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

export default function Panel({ title, subtitle, action, children, className = "" }: Props) {
  return (
    <section className={`pp-panel flex flex-col gap-4 ${className}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="pp-display text-lg font-semibold text-pp-navy">{title}</h2>
          {subtitle && <p className="text-sm text-pp-muted mt-0.5">{subtitle}</p>}
        </div>
        {action}
      </div>
      {children}
    </section>
  );
}
