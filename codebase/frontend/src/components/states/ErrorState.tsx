import { RefreshCw, TriangleAlert } from "lucide-react"
import type { ReactNode } from "react"
import { StateShell, stateButtonClass } from "./StateShell"

interface ErrorStateProps {
  title?: string
  /** Thông điệp hướng dẫn được cho người dùng (không đưa stack trace hay mã lỗi trần). */
  message: string
  onRetry?: () => void
  retryLabel?: string
  /** Hành động phụ, vd đăng xuất hoặc về trang chủ. */
  action?: ReactNode
  fullPage?: boolean
  className?: string
}

/** Trạng thái lỗi có nút thử lại. */
export function ErrorState({
  title = "Đã xảy ra lỗi",
  message,
  onRetry,
  retryLabel = "Thử lại",
  action,
  fullPage,
  className,
}: ErrorStateProps) {
  return (
    <StateShell fullPage={fullPage} className={className}>
      <div role="alert" className="flex flex-col items-center gap-3">
        <span aria-hidden="true" className="flex size-12 items-center justify-center rounded-full bg-red-100 text-red-800">
          <TriangleAlert className="size-6" />
        </span>
        <h2 className="text-lg font-semibold text-violet-950">{title}</h2>
        <p className="max-w-md text-sm leading-6 text-slate-700">{message}</p>
      </div>
      {(onRetry || action) && (
        <div className="mt-2 flex flex-wrap justify-center gap-2">
          {onRetry && (
            <button type="button" onClick={onRetry} className={stateButtonClass}>
              <RefreshCw aria-hidden="true" className="size-4" />
              {retryLabel}
            </button>
          )}
          {action}
        </div>
      )}
    </StateShell>
  )
}
