interface Props {
  rows?: number;
  label?: string;
}

/** Pulse placeholder matching app loading patterns; respects reduced motion via CSS. */
export default function Skeleton({ rows = 5, label = "Loading" }: Props) {
  return (
    <div className="pp-card p-4 space-y-3" aria-busy="true" aria-live="polite">
      <span className="sr-only">{label}</span>
      {Array.from({ length: rows }, (_, index) => (
        <div key={index} className="h-8 rounded-lg bg-pp-paper-2 skeleton-pulse" />
      ))}
    </div>
  );
}
