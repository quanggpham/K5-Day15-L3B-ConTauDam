import { useEffect, useRef, useState } from "react"
import { isAbortError } from "@/services/api"

export type QueryStatus = "loading" | "success" | "error"

interface QueryState<T> {
  status: QueryStatus
  /** Kết quả thành công gần nhất (có thể của tham số trước khi đang tải lại). */
  data: T | null
  error: unknown
}

/**
 * Gọi API khi `deps` đổi; huỷ request cũ (đổi tham số/unmount) nên kết quả cũ không ghi đè kết quả mới.
 * `reload()` chạy lại với cùng tham số.
 */
export function useApiQuery<T>(fetcher: (signal: AbortSignal) => Promise<T>, deps: readonly unknown[]) {
  const [state, setState] = useState<QueryState<T>>({ status: "loading", data: null, error: null })
  const [nonce, setNonce] = useState(0)
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    const controller = new AbortController()
    setState((current) => ({ ...current, status: "loading", error: null }))
    fetcherRef
      .current(controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) setState({ status: "success", data, error: null })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setState((current) => ({ ...current, status: "error", error }))
      })
    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, nonce])

  return { ...state, reload: () => setNonce((value) => value + 1) }
}
