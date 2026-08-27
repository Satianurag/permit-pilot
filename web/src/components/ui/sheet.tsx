import * as Dialog from "@radix-ui/react-dialog";
import { ReactNode } from "react";

export function Sheet({
  open,
  onOpenChange,
  title,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
}) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <Dialog.Content
          aria-describedby={undefined}
          className="fixed inset-x-0 bottom-0 z-50 m-0 max-h-[85vh] w-full overflow-y-auto rounded-t-xl border border-pp-border bg-white p-4 shadow-xl"
        >
          <div className="mb-3 flex items-center justify-between">
            <Dialog.Title className="font-medium text-pp-navy">{title}</Dialog.Title>
            <Dialog.Close className="text-sm text-slate-600 hover:text-pp-navy">Close</Dialog.Close>
          </div>
          {children}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
