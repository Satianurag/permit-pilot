import { useEffect, useId, useRef } from "react";

interface Props {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  onConfirm,
  onCancel,
  busy,
}: Props) {
  const titleId = useId();
  const descId = useId();
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    confirmRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onCancel();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center p-4 bg-black/40" role="presentation">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={descId}
        className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl"
      >
        <h2 id={titleId} className="text-lg font-semibold text-pp-navy">
          {title}
        </h2>
        <p id={descId} className="mt-2 text-sm text-slate-600">
          {description}
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="px-4 py-2 text-sm rounded-md border border-pp-border">
            Cancel
          </button>
          <button
            ref={confirmRef}
            type="button"
            disabled={busy}
            onClick={onConfirm}
            className="px-4 py-2 text-sm rounded-md bg-emerald-600 text-white disabled:opacity-50"
          >
            {busy ? "Saving…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
