import { NOT_RECORDED, formatDateTime } from "@/lib/format"
import { decisionLabel, historyStatusLabel } from "@/features/reports/labels"
import type { ReviewItem } from "@/features/reports/types"

function actorText(actorId: string | null, currentUserId: string | null): string {
  if (!actorId) return NOT_RECORDED
  if (currentUserId && actorId === currentUserId) return "Bạn"
  return `Coach khác (mã …${actorId.slice(-6)})`
}

/** Lịch sử duyệt của một đề xuất (cũ -> mới): người thao tác, thời điểm, trước/sau, nhận xét. */
export function ReviewHistory({ reviews, currentUserId }: { reviews: ReviewItem[]; currentUserId: string | null }) {
  return (
    <details className="rounded-lg border border-violet-100 bg-white px-3 py-2">
      <summary className="cursor-pointer text-sm font-medium text-violet-950 outline-none focus-visible:ring-2 focus-visible:ring-violet-700">
        Lịch sử duyệt ({reviews.length})
      </summary>
      {reviews.length === 0 ? (
        <p className="mt-2 text-sm text-slate-700">Chưa có lượt duyệt nào cho đề xuất này.</p>
      ) : (
        <ol className="mt-3 space-y-3">
          {reviews.map((review) => (
            <li key={review.id} className="space-y-1 border-l-2 border-violet-200 pl-3 text-sm">
              <p className="font-medium text-slate-900">
                {decisionLabel(review.decision)} · {actorText(review.actor_id, currentUserId)} ·{" "}
                <time dateTime={review.at ?? undefined}>{formatDateTime(review.at)}</time>
              </p>
              <p className="text-slate-800">
                Trạng thái: {historyStatusLabel(review.status_before)} → {historyStatusLabel(review.status_after)}
                {review.new_version != null && <span className="text-slate-700"> (phiên bản {review.new_version})</span>}
              </p>
              {review.comment ? (
                <p className="whitespace-pre-wrap break-words text-slate-800">Nhận xét: {review.comment}</p>
              ) : (
                <p className="text-slate-700">Không có nhận xét.</p>
              )}
              {review.decision === "edited" && (
                <div className="grid gap-2 sm:grid-cols-2">
                  <div className="rounded-lg bg-slate-50 p-2">
                    <p className="text-xs font-semibold text-slate-700">Nội dung trước</p>
                    <p className="whitespace-pre-wrap break-words text-slate-900">{review.content_before ?? NOT_RECORDED}</p>
                  </div>
                  <div className="rounded-lg bg-violet-50 p-2">
                    <p className="text-xs font-semibold text-slate-700">Nội dung sau (chờ duyệt lại, không có điểm JEV của bản gốc)</p>
                    <p className="whitespace-pre-wrap break-words text-slate-900">{review.content_after ?? NOT_RECORDED}</p>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}
    </details>
  )
}
