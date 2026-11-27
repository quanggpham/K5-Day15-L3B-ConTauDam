import { useCallback, useEffect, useRef, useState } from "react"
import type { RecommendationItem, ReviewResponse } from "@/features/reports/types"
import { api, apiErrorCode, apiErrorMessage, isAbortError, isApiError } from "@/services/api"
import type { ReviewDecision } from "@/features/reports/labels"

export interface ReviewPayload {
  recommendation_id: string
  version: number
  decision: ReviewDecision
  comment?: string
  content?: string
}

export type SubmitOutcome =
  | { kind: "saved"; decision: ReviewDecision; replayed: boolean }
  | { kind: "conflict"; currentVersion: number | null; currentStatus: string | null }
  | { kind: "invalid_transition"; status: string | null }
  | { kind: "invalid_input" }
  | { kind: "not_found" }
  | { kind: "retryable"; message: string }
  | { kind: "error"; message: string }

function numberOrNull(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function classify(error: unknown): SubmitOutcome {
  if (isApiError(error)) {
    const code = apiErrorCode(error)
    if (error.kind === "conflict" && code === "version_conflict") {
      const current = error.payload?.recommendation as Partial<RecommendationItem> | null | undefined
      return {
        kind: "conflict",
        currentVersion: numberOrNull(error.payload?.current_version) ?? numberOrNull(current?.version),
        currentStatus: typeof current?.review_status === "string" ? current.review_status : null,
      }
    }
    if (error.kind === "validation" && code === "invalid_transition") {
      const status = error.payload?.review_status
      return { kind: "invalid_transition", status: typeof status === "string" ? status : null }
    }
    if (error.kind === "validation") return { kind: "invalid_input" }
    if (error.kind === "not_found") return { kind: "not_found" }
    if (error.kind === "server" || error.kind === "network") {
      return {
        kind: "retryable",
        message:
          error.kind === "network"
            ? "Mất kết nối tới backend, chưa biết quyết định đã được lưu hay chưa. Bấm Thử lại: nếu đã lưu, hệ thống ghi nhận là đã lưu và không ghi trùng."
            : "Kho lưu báo cáo đang không truy cập được. Chưa lưu được quyết định; bấm Thử lại sau ít phút.",
      }
    }
  }
  return { kind: "error", message: apiErrorMessage(error) }
}

/**
 * Gửi một quyết định duyệt cho một đề xuất. Khoá khi đang gửi (ref + state), nhớ payload gần nhất để thử lại
 * đúng nội dung (backend trả 200 replayed nếu lần trước thực ra đã lưu), huỷ khi rời trang.
 * 201 và 200 replayed đều gọi `onApplied` để cập nhật tại chỗ.
 */
export function useSubmitReview(runId: string, onApplied: (result: ReviewResponse) => void) {
  const [pending, setPending] = useState(false)
  const inFlight = useRef(false)
  const controllerRef = useRef<AbortController | null>(null)
  const lastPayload = useRef<ReviewPayload | null>(null)
  const onAppliedRef = useRef(onApplied)
  onAppliedRef.current = onApplied

  useEffect(() => () => controllerRef.current?.abort(), [])

  const submit = useCallback(
    async (payload: ReviewPayload): Promise<SubmitOutcome | null> => {
      if (inFlight.current) return null
      inFlight.current = true
      lastPayload.current = payload
      setPending(true)
      const controller = new AbortController()
      controllerRef.current = controller
      try {
        const result = await api.post<ReviewResponse>(`/api/analysis-runs/${encodeURIComponent(runId)}/reviews`, payload, {
          signal: controller.signal,
        })
        if (controller.signal.aborted) return null
        onAppliedRef.current(result)
        return { kind: "saved", decision: payload.decision, replayed: result.replayed === true }
      } catch (error) {
        if (isAbortError(error) || controller.signal.aborted) return null
        return classify(error)
      } finally {
        inFlight.current = false
        if (!controller.signal.aborted) setPending(false)
      }
    },
    [runId],
  )

  const retry = useCallback(() => (lastPayload.current ? submit(lastPayload.current) : Promise.resolve(null)), [submit])

  return { submit, retry, pending }
}
