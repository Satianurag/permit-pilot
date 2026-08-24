interface Props {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export default function EmptyState({ title, description, action }: Props) {
  return (
    <div className="rounded-lg border border-dashed border-pp-border bg-slate-50 px-6 py-10 text-center">
      <p className="font-medium text-pp-navy">{title}</p>
      {description && <p className="mt-2 text-sm text-slate-600">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
