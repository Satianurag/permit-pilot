import { useEffect, useId, useRef } from "react";

interface Props {
  open: boolean;
  title: string;
  description: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
  busy?: boolean;
  /** Destructive / irreversible actions use the stronger button. */
  danger?: boolean;
}

export default function ConfirmDialog({
  open,
  title,
  description,
  confirmLabel,
  onConfirm,
  onCancel,
  busy,
  danger,
}: Props) {
  const titleId = useId();
  const descId = useId();
  const dialogRef = useRef<HTMLDialogElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    const node = dialogRef.current;
    if (!node || !open) return;
    node.showModal();
    confirmRef.current?.focus();
    return () => node.close();
  }, [open]);

  return (
    <dialog
      ref={dialogRef}
      className="pp-dialog"
      aria-labelledby={titleId}
      aria-describedby={descId}
      onClose={onCancel}
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
          className={`px-4 py-2 text-sm rounded-md text-white disabled:opacity-50 ${
            danger ? "bg-red-700" : "bg-emerald-700"
          }`}
        >
          {busy ? "Saving…" : confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
