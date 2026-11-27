/** Kiểu payload GET /api/dashboard. Trường nào backend có thể thiếu thì để optional/null: UI hiện "chưa được ghi nhận". */
export type KcStatus = "ok" | "insufficient_sample" | "no_graded" | "small_group"

export interface KcStat {
  kc_code: string
  status?: KcStatus | string
  graded_count?: number | null
  learner_count?: number | null
  incorrect_count?: number | null
  ungraded_count?: number | null
  incorrect_rate: number | null
  delta_vs_previous_pp?: number | null
  rank?: number
}

export interface LessonSample {
  responses?: number | null
  learners?: number | null
  ungraded?: number | null
  incorrect?: number | null
}

export interface CatalogItem {
  lesson_id: string
  status?: string
  kc_count?: number
  sample?: LessonSample
  first_event_at?: string | null
  last_event_at?: string | null
}

export interface LessonView {
  lesson_id: string
  status?: KcStatus | string
  sample: LessonSample
  incorrect_rate: number | null
  first_attempt_accuracy: number | null
  delta_vs_previous_pp: number | null
  previous_lesson_id: string | null
  sufficient_kc_count: number
  kc_count: number
  kcs: KcStat[]
  priority: KcStat[]
  distribution: { correct: number; incorrect: number; ungraded: number }
}

export interface DashboardOk {
  status: "ok"
  generated_at?: string | null
  min_sample?: number | null
  units?: Record<string, string>
  catalog: CatalogItem[]
  selected_lesson_id: string
  lesson: LessonView
}

export interface DashboardNoData {
  status: "no_data"
}

export type DashboardResponse = DashboardOk | DashboardNoData
