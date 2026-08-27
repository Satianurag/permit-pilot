import { createContext, ReactNode, useCallback, useContext, useMemo, useState } from "react";

export type ToastTone = "success" | "error" | "info";

export interface ToastMessage {
  id: number;
  text: string;
  tone: ToastTone;
  sticky?: boolean;
}

interface ToastContextValue {
  push: (text: string, tone?: ToastTone, options?: { sticky?: boolean }) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const push = useCallback((text: string, tone: ToastTone = "info", options?: { sticky?: boolean }) => {
    const id = Date.now() + Math.random();
    const sticky = options?.sticky ?? false;
    setToasts((current) => [...current, { id, text, tone, sticky }]);
    if (!sticky) {
      window.setTimeout(() => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
      }, 6000);
    }
  }, []);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const value = useMemo(() => ({ push }), [push]);

  const toneClass: Record<ToastTone, string> = {
    success: "bg-emerald-50 border-emerald-200 text-emerald-950",
    error: "bg-red-50 border-red-200 text-red-950",
    info: "bg-slate-50 border-pp-border text-slate-900",
  };

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        className="fixed top-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full pointer-events-none"
        aria-live="polite"
      >
        {toasts.map((toast) => (
          <p
            key={toast.id}
            role={toast.tone === "error" ? "alert" : "status"}
            className={`rounded-md border px-3 py-2 text-sm shadow-sm pointer-events-auto ${toneClass[toast.tone]}`}
          >
            <span>{toast.text}</span>
            {toast.sticky && (
              <button
                type="button"
                className="ml-2 text-xs underline"
                onClick={() => dismiss(toast.id)}
              >
                Dismiss
              </button>
            )}
          </p>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used within ToastProvider");
  return ctx;
}
