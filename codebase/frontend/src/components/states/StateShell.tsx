import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

/** Khung chung cho các trạng thái: căn giữa, có thể chiếm cả màn hình. */
export function StateShell({
  fullPage = false,
  className,
  children,
}: {
  fullPage?: boolean
  className?: string
  children: ReactNode
}) {
  return (
    <div
      className={cn(
        "flex w-full flex-col items-center justify-center gap-3 px-4 py-10 text-center",
        fullPage && "min-h-dvh bg-gradient-to-b from-violet-50 via-white to-violet-50",
        className,
      )}
    >
      {children}
    </div>
  )
}

export const stateButtonClass =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg bg-violet-700 px-4 text-sm font-semibold text-white outline-none transition-colors hover:bg-violet-800 focus-visible:ring-2 focus-visible:ring-violet-700 focus-visible:ring-offset-2 disabled:opacity-60 motion-reduce:transition-none"

export const stateSecondaryButtonClass =
  "inline-flex h-10 items-center justify-center gap-2 rounded-lg border border-violet-300 bg-white px-4 text-sm font-semibold text-violet-900 outline-none transition-colors hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-700 focus-visible:ring-offset-2 disabled:opacity-60 motion-reduce:transition-none"
