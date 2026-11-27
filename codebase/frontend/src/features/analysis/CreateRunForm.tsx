import { FilePlus2, LoaderCircle } from "lucide-react"
import { cardClass, controlClass, labelClass } from "@/components/ui/controls"
import { stateButtonClass } from "@/components/states"
import { formatCount, formatDateTime } from "@/lib/format"
import type { CatalogItem } from "@/features/dashboard/types"
import { lessonOptionLabel } from "@/features/dashboard/useDashboard"
import type { SubmitError } from "./useCreateRun"

interface CreateRunFormProps {
  catalog: CatalogItem[]
  lessonId: string
  /** Query `lesson_id` không có trong catalog (để báo cho người dùng). */
  invalidQueryLesson?: string | null
  pending: boolean
  error: SubmitError | null
  onLessonChange: (lessonId: string) => void
  onSubmit: () => void
}

const SOURCES = [
  { id: "pre", label: "Pre-class", available: true },
  { id: "in", label: "In-class", available: false },
  { id: "post", label: "Post-class", available: false },
]

/** Form tạo phân tích (presentational): không gọi API. */
export function CreateRunForm({ catalog, lessonId, invalidQueryLesson, pending, error, onLessonChange, onSubmit }: CreateRunFormProps) {
  const lesson = catalog.find((item) => item.lesson_id === lessonId)
  return (
    <form
      className={`${cardClass} mt-6 space-y-6`}
      onSubmit={(event) => {
        event.preventDefault()
        onSubmit()
      }}
      aria-busy={pending}
    >
      <div>
        <p className={labelClass}>Cohort</p>
        <p className="flex h-11 items-center rounded-lg border border-violet-200 bg-violet-50 px-3 text-sm font-medium text-violet-950">
          AI20K K5
        </p>
        <p className="mt-1 text-xs text-slate-700">Cố định một cohort. Số liệu lấy từ nguồn pre-class của cohort này.</p>
      </div>

      <fieldset>
        <legend className={labelClass}>Nguồn dữ liệu</legend>
        <div className="space-y-2">
          {SOURCES.map((source) => (
            <label key={source.id} className={`flex items-center gap-3 text-sm ${source.available ? "text-slate-900" : "text-slate-600"}`}>
              <input
                type="radio"
                name="source"
                value={source.id}
                checked={source.available}
                disabled={!source.available}
                onChange={() => {}}
                className="size-4 accent-violet-700"
              />
              <span>
                {source.label}
                {!source.available && <span className="ml-2 text-xs">(chưa có dữ liệu)</span>}
              </span>
            </label>
          ))}
        </div>
      </fieldset>

      <div>
        <label htmlFor="analysis-lesson" className={labelClass}>
          Bài học
        </label>
        <select
          id="analysis-lesson"
          className={controlClass}
          value={lessonId}
          disabled={pending}
          onChange={(event) => onLessonChange(event.target.value)}
          aria-describedby={invalidQueryLesson ? "analysis-lesson-note" : undefined}
        >
          {catalog.map((item) => (
            <option key={item.lesson_id} value={item.lesson_id}>
              {lessonOptionLabel(item)}
            </option>
          ))}
        </select>
        {invalidQueryLesson && (
          <p id="analysis-lesson-note" className="mt-1 text-xs text-amber-900">
            Bài "{invalidQueryLesson}" trong liên kết không có trong danh sách; đang chọn bài mới nhất. Hãy kiểm tra lại bài trước khi tạo.
          </p>
        )}
        {lesson?.sample && (
          <p className="mt-2 text-xs text-slate-700">
            Mẫu của bài: {formatCount(lesson.sample.responses)} lượt chấm lần đầu, {formatCount(lesson.sample.learners)} người. Sự kiện gần nhất: {formatDateTime(lesson.last_event_at)}.
          </p>
        )}
      </div>

      {error && error.lessonId === lessonId && (
        <p role="alert" className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-900">
          {error.message}
        </p>
      )}

      <div>
        <button type="submit" disabled={pending || !lessonId} className={stateButtonClass}>
          {pending ? (
            <LoaderCircle aria-hidden="true" className="size-4 animate-spin motion-reduce:animate-none" />
          ) : (
            <FilePlus2 aria-hidden="true" className="size-4" />
          )}
          {pending ? "Đang tạo..." : error?.canRetry && error.lessonId === lessonId ? "Thử lại" : "Tạo phân tích"}
        </button>
        <p className="mt-2 text-xs text-slate-700">Hệ thống lưu một bản nháp từ số liệu tại thời điểm tạo, rồi mở báo cáo đã lưu.</p>
      </div>
    </form>
  )
}
