/** Một dòng của GET /api/analysis-runs (`items`). Trường có thể null ở nháp cũ -> "chưa được ghi nhận". */
export interface RunSummary {
  run_id: string
  lesson_id: string
  status: string | null
  ai_status: string | null
  ai_status_reason: string | null
  created_at: string | null
  updated_at: string | null
  not_recorded?: string[]
}

export interface RunListResponse {
  items: RunSummary[]
  next_cursor: string | null
  limit: number
}
