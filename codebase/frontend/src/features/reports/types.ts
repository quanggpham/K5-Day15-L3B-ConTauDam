import type { LessonView } from "@/features/dashboard/types"

/** Kiểu payload GET /api/analysis-runs/{id}. Trường backend có thể thiếu/null (nháp cũ) -> UI hiện "chưa được ghi nhận". */
export const RUN_SNAPSHOT_SCHEMA = "analysis_run_snapshot/1"

export interface StoredSnapshot {
  schema: string
  snapshot_version?: string | null
  source_version?: number | null
  generated_at?: string | null
  min_sample?: number | null
  units?: Record<string, string>
  lesson: LessonView
}

export interface RunSnapshotView {
  /** "analysis_run_snapshot/1" | "legacy" | "not_recorded" */
  format: string
  data: unknown
  notice: string | null
}

export interface RecommendationItem {
  id: string
  analysis_run_id?: string
  kc_code: string | null
  priority: number | null
  content: string | null
  /** jsonb: danh sách chuỗi hoặc object {source_id,title,source,url}. */
  citations: unknown
  version: number | null
  review_status: string | null
  is_edited?: boolean | null
  needs_rereview?: boolean | null
  /** jsonb hoặc null. Bản sửa tay luôn null. */
  jev_score?: unknown
  updated_at?: string | null
  not_recorded?: string[]
}

export interface EvaluationItem {
  id: string
  analysis_run_id?: string
  metrics: unknown
  judge: string | null
  passed: boolean | null
}

export interface ReviewItem {
  id: string
  run_id?: string
  recommendation_id: string
  expected_version?: number | null
  new_version?: number | null
  decision: string
  comment: string | null
  content_before: string | null
  content_after: string | null
  status_before: string | null
  status_after: string | null
  needs_rereview?: boolean | null
  actor_id: string | null
  at: string | null
}

export interface RunDetail {
  run_id: string
  lesson_id: string
  status: string | null
  ai_status: string | null
  ai_status_reason: string | null
  snapshot_version: string | null
  request_id: string | null
  model: string | null
  version?: number | null
  created_at: string | null
  updated_at: string | null
  not_recorded: string[]
  not_recorded_label?: string
  snapshot: RunSnapshotView
  recommendations: RecommendationItem[]
  evaluations: EvaluationItem[]
  reviews: ReviewItem[]
}

/** 201 / 200 của POST /reviews. */
export interface ReviewResponse {
  recommendation: RecommendationItem
  review: ReviewItem
  replayed: boolean
}
