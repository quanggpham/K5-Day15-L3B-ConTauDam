/** Kiểu của POST /api/analysis-runs/{id}/copilot. */
export type CopilotAction = "explain_priority" | "compare_previous" | "review_plan_15m" | "recheck_questions"

export interface CopilotEvidence {
  kc_code: string | null
  field: string
  value: unknown
}

export interface CopilotResult {
  run_id?: string
  action: CopilotAction
  kc_code: string | null
  /** "ok" | "insufficient_comparison_data" (giá trị lạ vẫn hiển thị nguyên văn). */
  status: string
  message: string
  evidence: CopilotEvidence[]
  source?: string
  generated_by?: string
  snapshot_version?: string | null
  units?: Record<string, string>
}

export interface CopilotActionDef {
  id: CopilotAction
  label: string
  /** required: bắt buộc chọn KC; optional: tuỳ chọn. */
  kc: "required" | "optional"
  /** Thao tác tạo nội dung: cần Lesson KB + hiệu chuẩn JEV. */
  generative: boolean
  description: string
}

export const COPILOT_ACTIONS: CopilotActionDef[] = [
  { id: "explain_priority", label: "Giải thích ưu tiên", kc: "required", generative: false, description: "Vì sao KC này được (hoặc không được) xếp ưu tiên. Cần chọn KC." },
  { id: "compare_previous", label: "So sánh bài trước", kc: "optional", generative: false, description: "Chênh lệch tỷ lệ sai so với bài trước. Chọn KC để so riêng KC, bỏ trống để so cả bài." },
  { id: "review_plan_15m", label: "Kế hoạch ôn 15 phút", kc: "optional", generative: true, description: "Tạo nội dung: cần Lesson KB và hiệu chuẩn JEV." },
  { id: "recheck_questions", label: "3 câu hỏi kiểm tra lại", kc: "required", generative: true, description: "Tạo nội dung: cần chọn KC, Lesson KB và hiệu chuẩn JEV." },
]

export function actionLabel(action: string): string {
  return COPILOT_ACTIONS.find((item) => item.id === action)?.label ?? action
}

const AI_REASONS: Record<string, string> = {
  kb_missing: "Chưa có Lesson KB (tài liệu bài giảng được phép) để làm căn cứ.",
  jev_uncalibrated: "Chưa hiệu chuẩn JEV (bộ chấm tự động chưa có ngưỡng được xác nhận).",
  run_ai_not_ready: "Báo cáo này chưa ở trạng thái AI sẵn sàng.",
  generation_not_enabled: "Chức năng tạo nội dung chưa được bật.",
  unknown: "Máy chủ báo chưa đủ điều kiện mở AI (không nêu lý do cụ thể).",
}

export function aiReasonText(reason: string): string {
  return AI_REASONS[reason] ?? `Điều kiện AI chưa đáp ứng (${reason}).`
}

/** Tên tiếng Việt cho các trường evidence đã biết; trường lạ hiện nguyên mã. */
const FIELD_LABELS: Record<string, string> = {
  "kcs.status": "Trạng thái số liệu của KC",
  "kcs.graded_count": "Số lượt chấm lần đầu (lượt)",
  "kcs.ungraded_count": "Số lượt chưa chấm (lượt)",
  "kcs.learner_count": "Số người có lượt chấm (người)",
  "kcs.incorrect_rate": "Tỷ lệ sai (0-1)",
  "kcs.delta_vs_previous_pp": "Chênh lệch tỷ lệ sai so với bài trước (điểm %)",
  "priority.rank": "Hạng ưu tiên",
  "priority.incorrect_rate": "Tỷ lệ sai trong nhóm ưu tiên (0-1)",
  min_sample: "Ngưỡng mẫu tối thiểu (lượt)",
  previous_lesson_id: "Bài trước",
  incorrect_rate: "Tỷ lệ sai của bài (0-1)",
  delta_vs_previous_pp: "Chênh lệch tỷ lệ sai của bài so với bài trước (điểm %)",
  "sample.responses": "Số lượt chấm lần đầu của bài (lượt)",
}

export function evidenceFieldLabel(field: string): string {
  return FIELD_LABELS[field] ?? field
}
