import { ArrowLeft } from "lucide-react"
import { useMemo } from "react"
import { Link } from "react-router-dom"
import { ErrorState, LoadingState, stateSecondaryButtonClass } from "@/components/states"
import { useAuth } from "@/features/auth/useAuth"
import { AiUnavailable } from "@/features/reports/AiUnavailable"
import { ReportNotFound } from "@/features/reports/ReportNotFound"
import { useReportRun } from "@/features/reports/ReportRunContext"
import type { ReviewItem } from "@/features/reports/types"
import { apiErrorMessage, isApiError } from "@/services/api"
import { RecommendationReviewCard } from "./RecommendationReviewCard"

/** /reports/:runId/review: duyệt từng đề xuất. Container: lấy run từ context, chọn trạng thái hiển thị. */
export default function ReviewPage() {
  const run = useReportRun()
  const { user } = useAuth()
  const reviews = run?.data?.reviews
  const byRecommendation = useMemo(() => {
    const map = new Map<string, ReviewItem[]>()
    for (const review of reviews ?? []) map.set(review.recommendation_id, [...(map.get(review.recommendation_id) ?? []), review])
    return map
  }, [reviews])

  if (!run) return <ErrorState title="Không mở được báo cáo" message="Đường dẫn báo cáo không hợp lệ." />
  if (run.phase === "error") {
    if (isApiError(run.error) && run.error.kind === "not_found") return <ReportNotFound />
    return <ErrorState title="Không tải được báo cáo" message={apiErrorMessage(run.error)} onRetry={() => void run.reload()} />
  }
  if (run.phase === "loading" || !run.data) return <LoadingState label="Đang tải đề xuất..." onRetry={() => void run.reload()} />

  const detail = run.data
  const reportPath = `/reports/${encodeURIComponent(detail.run_id)}`
  return (
    <section aria-labelledby="review-title" className="mx-auto w-full max-w-3xl">
      <Link to={reportPath} className="inline-flex items-center gap-1 text-sm font-medium text-violet-800 underline">
        <ArrowLeft aria-hidden="true" className="size-4" />
        Về báo cáo bài {detail.lesson_id}
      </Link>
      <h1 id="review-title" className="mt-2 text-2xl font-bold tracking-tight text-violet-950">
        Duyệt đề xuất · bài {detail.lesson_id}
      </h1>
      <p className="mt-1 text-sm text-slate-700">
        Chấp nhận, từ chối hoặc yêu cầu chỉnh sửa từng đề xuất. Coach quyết định cuối cùng; điểm JEV chỉ là tín hiệu hỗ trợ. Mọi lượt duyệt được lưu kèm người thao tác và thời điểm.
      </p>

      {run.refreshing && (
        <p role="status" className="mt-3 text-sm text-slate-700">
          Đang tải lại báo cáo...
        </p>
      )}
      {run.refreshError != null && !run.refreshing && (
        <p role="alert" className="mt-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
          Chưa tải lại được báo cáo. {apiErrorMessage(run.refreshError)}
        </p>
      )}

      <div className="mt-6" aria-busy={run.refreshing}>
        {detail.recommendations.length === 0 ? (
          <AiUnavailable
            context="recommendations"
            aiStatus={detail.ai_status}
            aiStatusReason={detail.ai_status_reason}
            action={
              <Link to={reportPath} className={stateSecondaryButtonClass}>
                Về báo cáo
              </Link>
            }
          />
        ) : (
          <ul className="space-y-4">
            {detail.recommendations.map((rec) => (
              <li key={rec.id}>
                <RecommendationReviewCard
                  runId={detail.run_id}
                  rec={rec}
                  reviews={byRecommendation.get(rec.id) ?? []}
                  currentUserId={user?.id ?? null}
                  onApplied={run.applyReview}
                  onReload={run.reload}
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}
