interface Props {
  rows?: number;
  label?: string;
}

/** Pulse placeholder matching USWDS loading patterns; respects reduced motion via CSS. */
export default function Skeleton({ rows = 5, label = "Loading" }: Props) {
  return (
    <div className="rounded-lg border border-pp-border bg-white p-4 space-y-3" aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="h-8 rounded bg-slate-100 skeleton-pulse" />
      ))}
    </div>
  );
}
