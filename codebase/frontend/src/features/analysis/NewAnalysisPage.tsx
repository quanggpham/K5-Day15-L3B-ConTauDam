import { useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { EmptyState, ErrorState, LoadingState } from "@/components/states"
import { stateSecondaryButtonClass } from "@/components/states"
import { useLessonCatalog } from "@/features/dashboard/useDashboard"
import { useAuth } from "@/features/auth/useAuth"
import { apiErrorMessage } from "@/services/api"
import { CreateRunForm } from "./CreateRunForm"
import { useCreateRun } from "./useCreateRun"

/** /analysis/new: chọn bài (mặc định theo `?lesson_id=`) và tạo bản nháp idempotent. */
export default function NewAnalysisPage() {
  const { user } = useAuth()
  const [params] = useSearchParams()
  const queryLesson = params.get("lesson_id") || null
  const { status, error, catalog, latest, reload } = useLessonCatalog()
  const { submit, pending, error: submitError } = useCreateRun(user?.id ?? null)
  const [picked, setPicked] = useState<string | null>(null)

  const queryValid = !!queryLesson && !!catalog?.some((item) => item.lesson_id === queryLesson)
  // Chọn của người dùng > query hợp lệ > bài mới nhất (theo backend).
  const lessonId = picked ?? (queryValid ? queryLesson : latest) ?? ""

  let body: React.ReactNode
  if (!catalog) {
    body =
      status === "error" ? (
        <ErrorState title="Không tải được danh sách bài" message={apiErrorMessage(error)} onRetry={reload} />
      ) : (
        <LoadingState label="Đang tải danh sách bài..." onRetry={reload} />
      )
  } else if (catalog.length === 0) {
    body = (
      <EmptyState
        title="Chưa có bài học để phân tích"
        description="Backend chưa có snapshot số liệu pre-class nên chưa tạo được phân tích."
        action={
          <Link to="/dashboard" className={stateSecondaryButtonClass}>
            Về Dashboard
          </Link>
        }
      />
    )
  } else {
    body = (
      <CreateRunForm
        catalog={catalog}
        lessonId={lessonId}
        invalidQueryLesson={queryLesson && !queryValid && picked === null ? queryLesson : null}
        pending={pending}
        error={submitError}
        onLessonChange={setPicked}
        onSubmit={() => void submit(lessonId)}
      />
    )
  }

  return (
    <section aria-labelledby="analysis-title" className="mx-auto w-full max-w-2xl">
      <h1 id="analysis-title" className="text-2xl font-bold tracking-tight text-violet-950">
        Tạo phân tích
      </h1>
      {body}
    </section>
  )
}
