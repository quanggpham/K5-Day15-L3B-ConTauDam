import { useCallback, useEffect, useRef, useState } from "react"
import { api, isAbortError } from "@/services/api"
import type { RunListResponse, RunSummary } from "./types"

const PAGE_SIZE = 20

export interface RunFilters {
  lessonId?: string
  status?: string
}

interface ListState {
  phase: "loading" | "ready" | "error"
  items: RunSummary[]
  nextCursor: string | null
  error: unknown
}

/**
 * Danh sách báo cáo theo cursor. Đổi bộ lọc => tải lại trang đầu và huỷ mọi request cũ (request cuối thắng).
 * `loadMore` nối trang kế tiếp; lỗi khi tải thêm giữ nguyên danh sách đã có.
 */
export function useRunList({ lessonId, status }: RunFilters) {
  const [state, setState] = useState<ListState>({ phase: "loading", items: [], nextCursor: null, error: null })
  const [more, setMore] = useState<{ loading: boolean; error: unknown }>({ loading: false, error: null })
  const [nonce, setNonce] = useState(0)
  const moreController = useRef<AbortController | null>(null)
  const loadingMore = useRef(false)
  const cursorRef = useRef<string | null>(null)
  cursorRef.current = state.nextCursor

  const fetchPage = useCallback(
    (cursor: string | null, signal: AbortSignal) =>
      api.get<RunListResponse>("/api/analysis-runs", {
        query: { lesson_id: lessonId, status, limit: PAGE_SIZE, cursor },
        signal,
      }),
    [lessonId, status],
  )

  useEffect(() => {
    const controller = new AbortController()
    moreController.current?.abort()
    loadingMore.current = false
    setMore({ loading: false, error: null })
    setState({ phase: "loading", items: [], nextCursor: null, error: null })
    fetchPage(null, controller.signal)
      .then((page) => {
        if (controller.signal.aborted) return
        setState({ phase: "ready", items: page.items, nextCursor: page.next_cursor, error: null })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setState({ phase: "error", items: [], nextCursor: null, error })
      })
    return () => {
      controller.abort()
      moreController.current?.abort()
    }
  }, [fetchPage, nonce])

  const loadMore = useCallback(() => {
    const cursor = cursorRef.current
    if (!cursor || loadingMore.current) return
    loadingMore.current = true
    const controller = new AbortController()
    moreController.current = controller
    setMore({ loading: true, error: null })
    fetchPage(cursor, controller.signal)
      .then((page) => {
        if (controller.signal.aborted) return
        setState((current) => {
          const seen = new Set(current.items.map((item) => item.run_id))
          return {
            ...current,
            items: [...current.items, ...page.items.filter((item) => !seen.has(item.run_id))],
            nextCursor: page.next_cursor,
          }
        })
        setMore({ loading: false, error: null })
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted || isAbortError(error)) return
        setMore({ loading: false, error })
      })
      .finally(() => {
        if (moreController.current === controller) loadingMore.current = false
      })
  }, [fetchPage])

  return { ...state, more, loadMore, reload: () => setNonce((value) => value + 1) }
}
