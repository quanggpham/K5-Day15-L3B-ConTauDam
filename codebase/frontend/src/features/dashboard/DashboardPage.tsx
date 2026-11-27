import { FilePlus2 } from "lucide-react"
import { Link, useSearchParams } from "react-router-dom"
import { EmptyState, ErrorState, LoadingState, stateButtonClass, stateSecondaryButtonClass } from "@/components/states"
import { controlClass, labelClass } from "@/components/ui/controls"
import { formatDateTime } from "@/lib/format"
import { apiErrorMessage, isApiError } from "@/services/api"
import { DistributionSection, KcRateSection, PrioritySection } from "./KcSection"
import { MetricCards } from "./MetricCards"
import type { DashboardOk } from "./types"
import { lessonOptionLabel, useDashboard } from "./useDashboard"

/** /dashboard: số liệu bài đang chọn (`?lesson_id=`) từ GET /api/dashboard. Container: lấy dữ liệu, chọn trạng thái hiển thị. */
export default function DashboardPage() {
  const [params, setParams] = useSearchParams()
  const lessonParam = params.get("lesson_id") || undefined
  const query = useDashboard(lessonParam)
  const data = query.data
  const ok: DashboardOk | null = data?.status === "ok" ? data : null

  function selectLesson(lessonId: string) {
    setParams(lessonId ? { lesson_id: lessonId } : {})
  }

  if (!data) {
    if (query.status === "error") return <DashboardError error={query.error} onRetry={query.reload} />
    return <LoadingState label="Đang tải số liệu..." onRetry={query.reload} />
  }

  if (!ok) {
    return (
      <PageFrame>
        <EmptyState
          title="Chưa có dữ liệu tổng hợp"
          description="Backend chưa có snapshot số liệu pre-class hoặc snapshot chưa có bài học nào. Hãy chạy bước tạo snapshot rồi tải lại."
          action={
            <button type="button" onClick={query.reload} className={stateButtonClass}>
              Tải lại
            </button>
          }
        />
      </PageFrame>
    )
  }

  const selectedId = lessonParam ?? ok.selected_lesson_id
  const inCatalog = ok.catalog.some((item) => item.lesson_id === selectedId)
  const ctaLesson = query.status === "success" ? ok.selected_lesson_id : null

  return (
    <PageFrame>
      <div className="mt-4 flex flex-wrap items-end justify-between gap-4">
        <div className="w-full max-w-xs">
          <label htmlFor="dashboard-lesson" className={labelClass}>
            Bài học
          </label>
          <select
            id="dashboard-lesson"
            className={controlClass}
            value={inCatalog ? selectedId : ""}
            onChange={(event) => selectLesson(event.target.value)}
          >
            {!inCatalog && (
              <option value="" disabled>
                Chọn bài học
              </option>
            )}
            {ok.catalog.map((item) => (
              <option key={item.lesson_id} value={item.lesson_id}>
                {lessonOptionLabel(item)}
              </option>
            ))}
          </select>
        </div>
        {ctaLesson && (
          <Link to={`/analysis/new?${new URLSearchParams({ lesson_id: ctaLesson })}`} className={stateButtonClass}>
            <FilePlus2 aria-hidden="true" className="size-4" />
            Tạo phân tích
          </Link>
        )}
      </div>
      <p className="mt-2 text-xs text-slate-700">
        Nguồn: dữ liệu pre-class AI20K K5, tổng hợp lúc {formatDateTime(ok.generated_at)}.
      </p>

      <div className="mt-6" aria-busy={query.status === "loading"}>
        {query.status === "loading" ? (
          <LoadingState label="Đang tải số liệu của bài..." onRetry={query.reload} />
        ) : query.status === "error" ? (
          <DashboardError error={query.error} onRetry={query.reload} inline />
        ) : (
          <LessonBody data={ok} />
        )}
      </div>
    </PageFrame>
  )
}

function PageFrame({ children }: { children: React.ReactNode }) {
  return (
    <section aria-labelledby="dashboard-title" className="mx-auto w-full max-w-5xl">
      <h1 id="dashboard-title" className="text-2xl font-bold tracking-tight text-violet-950">
        Dashboard
      </h1>
      {children}
    </section>
  )
}

function DashboardError({ error, onRetry, inline }: { error: unknown; onRetry: () => void; inline?: boolean }) {
  const notFound = isApiError(error) && error.kind === "not_found"
  const state = (
    <ErrorState
      title={notFound ? "Không có dữ liệu cho bài này" : "Không tải được số liệu"}
      message={notFound ? "Bài học này không có trong dữ liệu tổng hợp. Hãy chọn bài khác." : apiErrorMessage(error)}
      onRetry={notFound ? undefined : onRetry}
      action={
        notFound ? (
          <Link to="/dashboard" className={stateSecondaryButtonClass}>
            Xem bài mới nhất
          </Link>
        ) : undefined
      }
    />
  )
  return inline ? state : <PageFrame>{state}</PageFrame>
}

function LessonBody({ data }: { data: DashboardOk }) {
  const { lesson, units, min_sample: minSample } = data
  return (
    <div className="space-y-6">
      {lesson.status === "no_graded" && (
        <p role="status" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Bài {lesson.lesson_id} chưa có lượt chấm lần đầu (mẫu số 0): các tỷ lệ không được tính, không hiển thị là 0%.
        </p>
      )}
      {lesson.status === "insufficient_sample" && (
        <p role="status" className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-950">
          Bài {lesson.lesson_id} có ít lượt chấm hơn ngưỡng mẫu: chỉ nên dùng số liệu để tham khảo.
        </p>
      )}
      <MetricCards lesson={lesson} units={units} minSample={minSample} />
      <KcRateSection lesson={lesson} minSample={minSample} />
      <div className="grid gap-6 xl:grid-cols-2">
        <DistributionSection lesson={lesson} units={units} />
        <PrioritySection lesson={lesson} />
      </div>
    </div>
  )
}
