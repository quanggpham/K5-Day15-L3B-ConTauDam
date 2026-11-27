import { Inbox, type LucideIcon } from "lucide-react"
import type { ReactNode } from "react"
import { StateShell } from "./StateShell"

interface EmptyStateProps {
  title: string
  description?: string
  icon?: LucideIcon
  /** Nút hoặc liên kết gợi ý bước tiếp theo. */
  action?: ReactNode
  fullPage?: boolean
  /** Cấp tiêu đề (mặc định h2). */
  headingLevel?: 1 | 2 | 3
  className?: string
}

/** Trạng thái rỗng: nói rõ vì sao chưa có dữ liệu và làm gì tiếp. */
export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  fullPage,
  headingLevel = 2,
  className,
}: EmptyStateProps) {
  const Heading = `h${headingLevel}` as "h1" | "h2" | "h3"
  return (
    <StateShell fullPage={fullPage} className={className}>
      <span aria-hidden="true" className="flex size-12 items-center justify-center rounded-full bg-violet-100 text-violet-800">
        <Icon className="size-6" />
      </span>
      <Heading className="text-lg font-semibold text-violet-950">{title}</Heading>
      {description && <p className="max-w-md text-sm leading-6 text-slate-700">{description}</p>}
      {action && <div className="mt-2 flex flex-wrap justify-center gap-2">{action}</div>}
    </StateShell>
  )
}
