import { useApiQuery } from "@/hooks/useApiQuery"
import { api } from "@/services/api"
import type { CatalogItem, DashboardResponse } from "./types"

/** Bỏ `lessonId` => backend chọn bài mới nhất trong catalog. */
export function useDashboard(lessonId?: string) {
  return useApiQuery(
    (signal) => api.get<DashboardResponse>("/api/dashboard", { query: { lesson_id: lessonId }, signal }),
    [lessonId],
  )
}

/** Catalog bài học (lấy từ /api/dashboard, nguồn catalog duy nhất). `catalog` null khi chưa tải/đang lỗi. */
export function useLessonCatalog() {
  const query = useDashboard(undefined)
  let catalog: CatalogItem[] | null = null
  let latest: string | null = null
  if (query.data?.status === "ok") {
    catalog = query.data.catalog
    latest = query.data.selected_lesson_id
  } else if (query.data?.status === "no_data") {
    catalog = []
  }
  return { status: query.status, error: query.error, catalog, latest, reload: query.reload }
}

export function lessonOptionLabel(item: CatalogItem): string {
  return item.status === "no_graded" ? `${item.lesson_id} (chưa có lượt chấm)` : item.lesson_id
}
