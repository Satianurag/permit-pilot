interface Props {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ title, description, action }: Props) {
  return (
    <div className="pp-card border-dashed px-6 py-12 text-center">
      <p className="pp-display text-lg font-semibold text-pp-navy">{title}</p>
      {description && <p className="mt-2 text-sm text-pp-muted max-w-md mx-auto">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
