import { ReactNode, useEffect, useId, useRef } from "react";

interface Props {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  /** Side sheet for case detail. Default is a centered modal. */
  variant?: "modal" | "drawer";
}

/** Native modal dialog — focus trap, Escape, and inert backdrop from the browser (WCAG 2.2). */
export default function ModalDialog({ open, title, onClose, children, variant = "modal" }: Props) {
  const titleId = useId();
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node || !open) return;
    node.showModal();
    return () => node.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      className={variant === "drawer" ? "pp-dialog pp-dialog-drawer" : "pp-dialog"}
      onClose={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <h2 id={titleId} className="text-lg font-semibold text-pp-navy">
          {title}
        </h2>
        <button type="button" onClick={onClose} className="text-sm text-slate-600 hover:text-pp-navy">
          Close
        </button>
      </div>
      {children}
    </dialog>
  );
}
