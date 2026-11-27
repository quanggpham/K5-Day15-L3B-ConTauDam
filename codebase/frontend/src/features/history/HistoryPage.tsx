import { FilePlus2 } from "lucide-react"
import { Link, useSearchParams } from "react-router-dom"
import { EmptyState, ErrorState, LoadingState, stateButtonClass, stateSecondaryButtonClass } from "@/components/states"
import { controlClass, labelClass } from "@/components/ui/controls"
import { lessonOptionLabel, useLessonCatalog } from "@/features/dashboard/useDashboard"
import { apiErrorMessage } from "@/services/api"
import { RUN_STATUS_OPTIONS, runStatusLabel } from "./labels"
import { RunList } from "./RunList"
import { useRunList } from "./useRunList"

/** /history: báo cáo của coach (GET /api/analysis-runs), lọc bài/trạng thái qua query, phân trang cursor. */
export default function HistoryPage() {
  const [params, setParams] = useSearchParams()
  const lessonId = params.get("lesson_id") || undefined
  const status = params.get("status") || undefined
  const list = useRunList({ lessonId, status })
  const catalog = useLessonCatalog()
  const filtered = !!lessonId || !!status

  function setFilter(key: "lesson_id" | "status", value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  // Bài đang lọc nhưng không có trong catalog vẫn phải chọn được (không mất bộ lọc).
  const lessonOptions = [...(catalog.catalog ?? [])]
  const lessonKnown = !lessonId || lessonOptions.some((item) => item.lesson_id === lessonId)
  const statusKnown = !status || RUN_STATUS_OPTIONS.some((option) => option.value === status)

  let body: React.ReactNode
  if (list.phase === "loading") {
    body = <LoadingState label="Đang tải lịch sử..." onRetry={list.reload} />
  } else if (list.phase === "error") {
    body = <ErrorState title="Không tải được lịch sử" message={apiErrorMessage(list.error)} onRetry={list.reload} />
  } else if (list.items.length === 0) {
    body = (
      <EmptyState
        title={filtered ? "Không có báo cáo khớp bộ lọc" : "Chưa có báo cáo nào"}
        description={filtered ? "Thử bỏ bớt bộ lọc để xem các báo cáo khác." : "Báo cáo bạn tạo sẽ được lưu và hiện ở đây."}
        action={
          filtered ? (
            <button type="button" onClick={() => setParams({}, { replace: true })} className={stateSecondaryButtonClass}>
              Xoá bộ lọc
            </button>
          ) : (
            <Link to="/analysis/new" className={stateButtonClass}>
              <FilePlus2 aria-hidden="true" className="size-4" />
              Tạo phân tích
            </Link>
          )
        }
      />
    )
  } else {
    body = (
      <>
        <p role="status" className="mb-3 text-sm text-slate-700">
          Đang hiển thị {list.items.length} báo cáo{list.nextCursor ? " (còn nữa)" : ", đã hết"}.
        </p>
        <RunList items={list.items} />
        {list.more.error != null && (
          <p role="alert" className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
            Không tải thêm được. {apiErrorMessage(list.more.error)}
          </p>
        )}
        {list.nextCursor && (
          <div className="mt-4 flex justify-center">
            <button type="button" onClick={list.loadMore} disabled={list.more.loading} className={stateSecondaryButtonClass}>
              {list.more.loading ? "Đang tải..." : list.more.error != null ? "Thử tải thêm lại" : "Tải thêm"}
            </button>
          </div>
        )}
      </>
    )
  }

  return (
    <section aria-labelledby="history-title" className="mx-auto w-full max-w-3xl">
      <h1 id="history-title" className="text-2xl font-bold tracking-tight text-violet-950">
        Lịch sử
      </h1>
      <p className="mt-1 text-sm text-slate-700">Báo cáo của bạn, mở lại từ số liệu đã lưu lúc tạo.</p>

      <form className="mt-6 grid gap-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end" onSubmit={(event) => event.preventDefault()} aria-label="Bộ lọc lịch sử">
        <div>
          <label htmlFor="history-lesson" className={labelClass}>
            Bài học
          </label>
          <select
            id="history-lesson"
            className={controlClass}
            value={lessonId ?? ""}
            disabled={catalog.catalog === null && !lessonId}
            onChange={(event) => setFilter("lesson_id", event.target.value)}
          >
            <option value="">Tất cả bài</option>
            {!lessonKnown && lessonId && <option value={lessonId}>{lessonId}</option>}
            {lessonOptions.map((item) => (
              <option key={item.lesson_id} value={item.lesson_id}>
                {lessonOptionLabel(item)}
              </option>
            ))}
          </select>
          {catalog.status === "error" && catalog.catalog === null && (
            <p className="mt-1 text-xs text-slate-700">
              Chưa tải được danh sách bài.{" "}
              <button type="button" onClick={catalog.reload} className="font-medium text-violet-800 underline">
                Thử lại
              </button>
            </p>
          )}
        </div>
        <div>
          <label htmlFor="history-status" className={labelClass}>
            Trạng thái
          </label>
          <select id="history-status" className={controlClass} value={status ?? ""} onChange={(event) => setFilter("status", event.target.value)}>
            <option value="">Tất cả trạng thái</option>
            {!statusKnown && status && <option value={status}>{runStatusLabel(status)}</option>}
            {RUN_STATUS_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>
        {filtered && (
          <button type="button" onClick={() => setParams({}, { replace: true })} className={stateSecondaryButtonClass}>
            Xoá bộ lọc
          </button>
        )}
      </form>

      <div className="mt-6" aria-busy={list.phase === "loading"}>
        {body}
      </div>
    </section>
  )
}
