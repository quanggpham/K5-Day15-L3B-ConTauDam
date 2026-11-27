import { X } from "lucide-react"
import { Dialog } from "radix-ui"
import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface DrawerProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  side: "left" | "right"
  title: string
  children: ReactNode
}

/**
 * Drawer cho mobile dựa trên Radix Dialog: khoá focus trong drawer, đóng bằng Esc,
 * trả focus về nút đã mở, aria-modal.
 */
export function Drawer({ open, onOpenChange, side, title, children }: DrawerProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-slate-900/40" />
        <Dialog.Content
          aria-describedby={undefined}
          className={cn(
            "fixed inset-y-0 z-50 flex w-[85vw] max-w-sm flex-col bg-white shadow-xl outline-none",
            side === "left" ? "left-0 border-r border-violet-200" : "right-0 border-l border-violet-200",
          )}
        >
          <div className="flex items-center justify-between border-b border-violet-100 px-4 py-3">
            <Dialog.Title className="text-base font-semibold text-violet-950">{title}</Dialog.Title>
            <Dialog.Close
              aria-label="Đóng"
              className="flex size-10 items-center justify-center rounded-lg text-violet-900 outline-none hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-600"
            >
              <X aria-hidden="true" className="size-5" />
            </Dialog.Close>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
