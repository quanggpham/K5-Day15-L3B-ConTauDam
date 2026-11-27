import { LoaderCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { StateShell, stateButtonClass } from "./StateShell"

interface LoadingStateProps {
  label?: string
  fullPage?: boolean
  /** Sau ngần này ms (mặc định 15 giây) hiện gợi ý chậm và nút thử lại (nếu có onRetry). */
  slowAfterMs?: number
  onRetry?: () => void
  className?: string
}

/** Trạng thái đang tải. Không quay vô hạn: tải lâu thì báo và cho thử lại. */
export function LoadingState({
  label = "Đang tải...",
  fullPage,
  slowAfterMs = 15000,
  onRetry,
  className,
}: LoadingStateProps) {
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), slowAfterMs)
    return () => window.clearTimeout(timer)
  }, [slowAfterMs])
  return (
    <StateShell fullPage={fullPage} className={className}>
      <div role="status" aria-live="polite" className="flex flex-col items-center gap-3">
        <LoaderCircle aria-hidden="true" className="size-8 animate-spin text-violet-700 motion-reduce:animate-none" />
        <p className="text-sm font-medium text-slate-700">{label}</p>
        {slow && <p className="max-w-sm text-sm text-slate-600">Việc này đang lâu hơn bình thường.</p>}
      </div>
      {slow && onRetry && (
        <button type="button" onClick={onRetry} className={stateButtonClass}>
          Thử lại
        </button>
      )}
    </StateShell>
  )
}
