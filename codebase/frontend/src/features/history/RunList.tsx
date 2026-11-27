import { ChevronRight } from "lucide-react"
import { Link } from "react-router-dom"
import { NOT_RECORDED, formatDateTime } from "@/lib/format"
import { aiStatusLabel, runStatusLabel } from "./labels"
import type { RunSummary } from "./types"

const chip = "inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-950"

/** Danh sách báo cáo đã lưu (presentational). Mỗi dòng là một liên kết tới /reports/:runId. */
export function RunList({ items }: { items: RunSummary[] }) {
  return (
    <ul className="space-y-3">
      {items.map((run) => (
        <li key={run.run_id}>
          <Link
            to={`/reports/${encodeURIComponent(run.run_id)}`}
            className="flex items-center justify-between gap-3 rounded-2xl border border-violet-200 bg-white p-4 outline-none transition-colors hover:bg-violet-50 focus-visible:ring-2 focus-visible:ring-violet-600 motion-reduce:transition-none"
          >
            <div className="min-w-0 space-y-2">
              <p className="break-words font-semibold text-violet-950">Bài {run.lesson_id}</p>
              <p className="text-sm text-slate-700">
                Tạo lúc <time dateTime={run.created_at ?? undefined}>{formatDateTime(run.created_at)}</time>
              </p>
              <div className="flex flex-wrap gap-2">
                <span className={chip}>Trạng thái: {runStatusLabel(run.status)}</span>
                <span className={chip}>{run.ai_status ? aiStatusLabel(run.ai_status) : `AI: ${NOT_RECORDED}`}</span>
              </div>
              {run.ai_status_reason && <p className="text-xs leading-5 text-slate-700">{run.ai_status_reason}</p>}
            </div>
            <ChevronRight aria-hidden="true" className="size-5 shrink-0 text-violet-700" />
          </Link>
        </li>
      ))}
    </ul>
  )
}
