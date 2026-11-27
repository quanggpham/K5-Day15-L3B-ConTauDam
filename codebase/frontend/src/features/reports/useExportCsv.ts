import { useCallback, useEffect, useRef, useState } from "react"
import { api, apiErrorMessage, isAbortError, isApiError } from "@/services/api"

export function csvFallbackName(lessonId: string, runId: string): string {
  const lesson = lessonId.replace(/[^A-Za-z0-9_-]/g, "_").slice(0, 40) || "bai"
  const id = runId.replace(/[^A-Za-z0-9]/g, "").slice(0, 8)
  return `bao-cao-${lesson}-${id}.csv`
}

function exportErrorMessage(error: unknown): string {
  if (isApiError(error) && error.kind === "not_found") return "Không tìm thấy báo cáo để tải CSV."
  if (isApiError(error) && error.kind === "network") return "Mất kết nối khi tải CSV. Hãy kiểm tra mạng rồi bấm Tải CSV lại."
  if (isApiError(error) && error.kind === "server") return "Máy chủ chưa xuất được CSV. Hãy thử lại sau ít phút."
  return apiErrorMessage(error)
}

/** Tải CSV của báo cáo đã lưu: khoá nút khi đang tải, huỷ khi rời trang, tên tệp theo Content-Disposition (nếu đọc được). */
export function useExportCsv(runId: string, lessonId: string) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<string | null>(null)
  const inFlight = useRef(false)
  const controllerRef = useRef<AbortController | null>(null)

  useEffect(() => () => controllerRef.current?.abort(), [])

  const start = useCallback(async () => {
    if (inFlight.current) return
    inFlight.current = true
    setPending(true)
    setError(null)
    setDone(null)
    const controller = new AbortController()
    controllerRef.current = controller
    try {
      const { blob, filename } = await api.download(`/api/analysis-runs/${encodeURIComponent(runId)}/export`, {
        signal: controller.signal,
      })
      if (controller.signal.aborted) return
      const name = filename ?? csvFallbackName(lessonId, runId)
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = name
      link.rel = "noopener"
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 10_000)
      setDone(name)
    } catch (caught) {
      if (isAbortError(caught) || controller.signal.aborted) return
      setError(exportErrorMessage(caught))
    } finally {
      inFlight.current = false
      if (!controller.signal.aborted) setPending(false)
    }
  }, [runId, lessonId])

  return { start, pending, error, done }
}
