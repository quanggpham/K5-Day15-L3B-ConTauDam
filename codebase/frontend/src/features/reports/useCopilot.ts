import { useCallback, useEffect, useRef, useState } from "react"
import { api, apiErrorCode, apiErrorMessage, isAbortError, isApiError } from "@/services/api"
import type { CopilotAction, CopilotResult } from "./copilotTypes"

export interface CopilotRequest {
  action: CopilotAction
  kcCode: string | null
}

export interface CopilotProblem {
  message: string
  /** Lỗi tạm thời (mạng/5xx): cho thử lại đúng yêu cầu vừa rồi. */
  retryable: boolean
  /** Lỗi do chưa chọn KC / KC không hợp lệ: đưa focus về ô chọn KC. */
  kcProblem: boolean
}

function toProblem(error: unknown): CopilotProblem {
  const code = apiErrorCode(error)
  if (code === "kc_required") return { message: "Thao tác này cần chọn một KC. Hãy chọn KC rồi bấm lại.", retryable: false, kcProblem: true }
  if (code === "kc_not_in_snapshot") {
    return { message: "KC này không có trong snapshot đã lưu của báo cáo. Hãy chọn KC khác trong danh sách.", retryable: false, kcProblem: true }
  }
  if (code === "snapshot_unavailable") {
    return {
      message: "Báo cáo này không có snapshot số liệu đúng định dạng hiện hành nên Copilot không có căn cứ để trả lời.",
      retryable: false,
      kcProblem: false,
    }
  }
  if (isApiError(error)) {
    if (error.kind === "not_found") return { message: "Không tìm thấy báo cáo này nên Copilot không trả lời được.", retryable: false, kcProblem: false }
    if (error.kind === "server" || error.kind === "network") {
      const base = error.kind === "network" ? "Mất kết nối tới backend." : "Kho lưu báo cáo đang không truy cập được (503)."
      return { message: `${base} Chưa có kết quả; bấm thử lại.`, retryable: true, kcProblem: false }
    }
    if (error.kind === "validation") return { message: "Yêu cầu Copilot không hợp lệ. Hãy chọn lại thao tác và KC rồi thử lại.", retryable: false, kcProblem: false }
  }
  return { message: apiErrorMessage(error), retryable: false, kcProblem: false }
}

/**
 * Gọi POST /copilot cho một báo cáo. Một yêu cầu tại một thời điểm (ref chống bấm đúp), huỷ khi rời trang.
 * 409 ai_unavailable -> `aiLock` (danh sách lý do từ server) để khoá hai thao tác tạo nội dung.
 */
export function useCopilot(runId: string) {
  const [pending, setPending] = useState<CopilotRequest | null>(null)
  const [result, setResult] = useState<CopilotResult | null>(null)
  const [problem, setProblem] = useState<CopilotProblem | null>(null)
  const [aiLock, setAiLock] = useState<string[] | null>(null)
  const inFlight = useRef(false)
  const controllerRef = useRef<AbortController | null>(null)
  const lastRequest = useRef<CopilotRequest | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const run = useCallback(
    async (request: CopilotRequest) => {
      if (inFlight.current) return
      inFlight.current = true
      lastRequest.current = request
      setPending(request)
      setProblem(null)
      const controller = new AbortController()
      controllerRef.current = controller
      try {
        const body: { action: CopilotAction; kc_code?: string } = { action: request.action }
        if (request.kcCode) body.kc_code = request.kcCode
        const data = await api.post<CopilotResult>(`/api/analysis-runs/${encodeURIComponent(runId)}/copilot`, body, {
          signal: controller.signal,
        })
        if (controller.signal.aborted) return
        setResult({ ...data, evidence: Array.isArray(data.evidence) ? data.evidence : [] })
      } catch (error) {
        if (isAbortError(error) || controller.signal.aborted) return
        if (isApiError(error) && error.kind === "conflict" && apiErrorCode(error) === "ai_unavailable") {
          const reasons = error.payload?.reasons
          setAiLock(Array.isArray(reasons) && reasons.length > 0 ? reasons.map(String) : ["unknown"])
        } else {
          setProblem(toProblem(error))
        }
      } finally {
        inFlight.current = false
        if (!controller.signal.aborted) setPending(null)
      }
    },
    [runId],
  )

  const retry = useCallback(() => {
    if (lastRequest.current) void run(lastRequest.current)
  }, [run])

  return { run, retry, pending, result, problem, aiLock, clearAiLock: () => setAiLock(null), setProblem }
}
