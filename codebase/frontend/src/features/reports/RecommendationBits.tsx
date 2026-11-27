import { NOT_RECORDED } from "@/lib/format"
import { cn } from "@/lib/utils"
import { EDITED_NOTE, reviewStatusLabel } from "./labels"
import type { RecommendationItem } from "./types"
import { entriesOf, valueText } from "./values"

export const chipClass =
  "inline-flex items-center rounded-full border border-violet-200 bg-violet-50 px-2.5 py-0.5 text-xs font-medium text-violet-950"

export function ReviewStatusChip({ status }: { status: string | null }) {
  return <span className={chipClass}>Duyệt: {reviewStatusLabel(status)}</span>
}

/** Bản sửa tay: cờ chữ rõ ràng (không chỉ màu). */
export function EditedFlag({ rec }: { rec: RecommendationItem }) {
  if (!rec.is_edited && !rec.needs_rereview) return null
  return (
    <p className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
      {rec.is_edited ? EDITED_NOTE : "Đề xuất này cần được duyệt lại."}
    </p>
  )
}

/** Điểm JEV chỉ là tín hiệu hỗ trợ; null = không có điểm (không hiện là 0). */
export function JevScore({ rec, className }: { rec: RecommendationItem; className?: string }) {
  const entries = entriesOf(rec.jev_score)
  const hasScalar = rec.jev_score !== null && rec.jev_score !== undefined && !entries
  return (
    <div className={cn("text-sm text-slate-800", className)}>
      <span className="font-medium">Điểm JEV: </span>
      {entries ? (
        <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
          {entries.map(([key, value]) => (
            <li key={key}>
              {key}: <span className="tabular-nums">{value}</span>
            </li>
          ))}
        </ul>
      ) : hasScalar ? (
        <span className="tabular-nums">{valueText(rec.jev_score)}</span>
      ) : (
        <span>{rec.is_edited ? "không có (bản sửa tay không thừa hưởng điểm của bản gốc)" : "chưa có điểm JEV"}</span>
      )}
    </div>
  )
}

export function kcLabel(rec: RecommendationItem): string {
  return rec.kc_code ? `KC ${rec.kc_code}` : `KC ${NOT_RECORDED}`
}
