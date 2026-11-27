import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react"
import { Outlet, useMatch } from "react-router-dom"
import { api, isAbortError } from "@/services/api"
import type { ReviewResponse, RunDetail } from "./types"

export interface ReportRunValue {
  runId: string
  /** "loading": chưa có dữ liệu lần đầu; "error": lần tải đầu lỗi; "ready": đã có `data` (kể cả khi đang tải lại). */
  phase: "loading" | "ready" | "error"
  data: RunDetail | null
  error: unknown
  /** Đang tải lại nền (data cũ vẫn hiển thị). */
  refreshing: boolean
  /** Lỗi của lần tải lại gần nhất (data cũ vẫn giữ). */
  refreshError: unknown
  /** Tải lại chi tiết báo cáo. true nếu thành công. Không xoá dữ liệu cũ khi lỗi. */
  reload: () => Promise<boolean>
  /** Cập nhật tại chỗ sau khi POST /reviews thành công (201 hoặc 200 replayed). */
  applyReview: (result: ReviewResponse) => void
}

interface State {
  runId: string | null
  phase: "loading" | "ready" | "error"
  data: RunDetail | null
  error: unknown
  refreshing: boolean
  refreshError: unknown
}

const IDLE: State = { runId: null, phase: "loading", data: null, error: null, refreshing: false, refreshError: null }
const ReportRunContext = createContext<ReportRunValue | null>(null)

/** Dữ liệu báo cáo đang mở, dùng chung cho trang và panel Copilot (chỉ một lần gọi API chi tiết). null ngoài /reports/:runId. */
export function useReportRun(): ReportRunValue | null {
  return useContext(ReportRunContext)
}

function useRunDetail(runId: string | null): ReportRunValue | null {
  const [state, setState] = useState<State>(IDLE)
  const controllerRef = useRef<AbortController | null>(null)
  const hasDataRef = useRef(false)
  hasDataRef.current = state.runId === runId && state.data !== null

  const load = useCallback(async (id: string, mode: "initial" | "refresh"): Promise<boolean> => {
    controllerRef.current?.abort()
    const controller = new AbortController()
    controllerRef.current = controller
    if (mode === "initial") setState({ ...IDLE, runId: id })
    else setState((s) => ({ ...s, refreshing: true, refreshError: null }))
    try {
      const data = await api.get<RunDetail>(`/api/analysis-runs/${encodeURIComponent(id)}`, { signal: controller.signal })
      if (controller.signal.aborted) return false
      setState({ runId: id, phase: "ready", data, error: null, refreshing: false, refreshError: null })
      return true
    } catch (error) {
      if (controller.signal.aborted || isAbortError(error)) return false
      setState((s) =>
        mode === "initial" || !s.data
          ? { runId: id, phase: "error", data: null, error, refreshing: false, refreshError: null }
          : { ...s, refreshing: false, refreshError: error },
      )
      return false
    }
  }, [])

  // Đổi báo cáo hoặc rời /reports: huỷ request cũ; kết quả cũ không ghi đè báo cáo mới.
  useEffect(() => {
    if (!runId) {
      controllerRef.current?.abort()
      setState(IDLE)
      return
    }
    void load(runId, "initial")
    return () => controllerRef.current?.abort()
  }, [runId, load])

  const reload = useCallback(
    () => (runId ? load(runId, hasDataRef.current ? "refresh" : "initial") : Promise.resolve(false)),
    [runId, load],
  )

  const applyReview = useCallback((result: ReviewResponse) => {
    controllerRef.current?.abort() // bản tải lại bắt đầu trước khi lưu có thể cũ hơn kết quả vừa nhận
    setState((s) => {
      if (!s.data) return s
      const { recommendation, review } = result
      return {
        ...s,
        refreshing: false,
        data: {
          ...s.data,
          recommendations: s.data.recommendations.map((item) => (item.id === recommendation.id ? recommendation : item)),
          reviews: s.data.reviews.some((item) => item.id === review.id) ? s.data.reviews : [...s.data.reviews, review],
        },
      }
    })
  }, [])

  return useMemo(() => {
    if (!runId) return null
    const current = state.runId === runId
    return {
      runId,
      phase: current ? state.phase : "loading",
      data: current ? state.data : null,
      error: current ? state.error : null,
      refreshing: current && state.refreshing,
      refreshError: current ? state.refreshError : null,
      reload,
      applyReview,
    }
  }, [runId, state, reload, applyReview])
}

/**
 * Route layout đặt TRÊN AppShell: Copilot nằm ngoài <Outlet/> của shell nên context phải bọc cả shell.
 * Chỉ tải khi URL là /reports/:runId[/...]; route khác nhận null và không gọi API.
 * Luôn render cùng một cây (Provider > Outlet) nên đổi route không làm AppShell mount lại.
 */
export function ReportRunScope() {
  const match = useMatch("/reports/:runId/*")
  const value = useRunDetail(match?.params.runId ?? null)
  return (
    <ReportRunContext.Provider value={value}>
      <Outlet />
    </ReportRunContext.Provider>
  )
}
