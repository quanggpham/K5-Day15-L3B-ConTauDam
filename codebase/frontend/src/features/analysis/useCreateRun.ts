import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { api, apiErrorMessage, isAbortError, isApiError } from "@/services/api"
import { clearRequestId, getRequestId, replaceRequestId } from "./requestId"
import type { CreatedRun } from "./types"

export interface SubmitError {
  lessonId: string
  message: string
  /** true: bấm lại sẽ gửi cùng request_id (không tạo nháp trùng). */
  canRetry: boolean
}

function toSubmitError(error: unknown, lessonId: string, userId: string): SubmitError {
  if (isApiError(error)) {
    switch (error.kind) {
      case "conflict":
        replaceRequestId(userId, lessonId)
        return {
          lessonId,
          canRetry: false,
          message: "Mã yêu cầu trước đó đã được dùng cho một bài học khác, nên hệ thống đã tạo mã mới. Bấm \"Tạo phân tích\" để gửi lại.",
        }
      case "not_found":
        return { lessonId, canRetry: false, message: "Bài học này không còn dữ liệu tổng hợp. Hãy chọn bài khác hoặc tải lại danh sách bài." }
      case "validation":
        return { lessonId, canRetry: false, message: "Yêu cầu không hợp lệ (bài học hoặc mã yêu cầu bị từ chối). Hãy chọn lại bài rồi thử lại." }
      case "server":
        return { lessonId, canRetry: true, message: "Kho lưu báo cáo đang không truy cập được. Hãy thử lại sau ít phút; thử lại không tạo bản nháp trùng." }
      case "network":
        return { lessonId, canRetry: true, message: "Mất kết nối tới backend. Hãy kiểm tra mạng rồi thử lại; thử lại không tạo bản nháp trùng." }
      default:
        return { lessonId, canRetry: false, message: apiErrorMessage(error) }
    }
  }
  return { lessonId, canRetry: true, message: "Có lỗi không xác định. Hãy thử lại." }
}

/**
 * Tạo bản nháp phân tích: khoá khi đang gửi (ref chống double-click), giữ request_id khi lỗi, huỷ request khi rời trang.
 * Thành công -> /reports/:runId (replace).
 */
export function useCreateRun(userId: string | null) {
  const navigate = useNavigate()
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<SubmitError | null>(null)
  const inFlight = useRef(false)
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const submit = useCallback(
    async (lessonId: string) => {
      if (inFlight.current || !userId || !lessonId) return
      inFlight.current = true
      setPending(true)
      setError(null)
      const controller = new AbortController()
      controllerRef.current = controller
      try {
        const run = await api.post<CreatedRun>(
          "/api/analysis-runs",
          { lesson_id: lessonId, request_id: getRequestId(userId, lessonId) },
          { signal: controller.signal },
        )
        clearRequestId(userId, lessonId)
        navigate(`/reports/${encodeURIComponent(run.run_id)}`, { replace: true })
        return // giữ nút khoá cho tới khi route đổi
      } catch (caught) {
        if (isAbortError(caught) || controller.signal.aborted) return
        setError(toSubmitError(caught, lessonId, userId))
      }
      inFlight.current = false
      setPending(false)
    },
    [navigate, userId],
  )

  return { submit, pending, error }
}
