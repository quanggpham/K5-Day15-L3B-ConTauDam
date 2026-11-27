import { NOT_RECORDED } from "@/lib/format"

/** Tên trường metadata của run (not_recorded) để báo cho coach bằng tiếng Việt. */
const NOT_RECORDED_FIELDS: Record<string, string> = {
  request_id: "mã yêu cầu tạo báo cáo",
  snapshot_version: "phiên bản snapshot",
  ai_status: "trạng thái AI",
  ai_status_reason: "lý do trạng thái AI",
  metrics_snapshot: "snapshot số liệu",
  review_status: "trạng thái duyệt",
}

export function notRecordedFieldLabel(key: string): string {
  return NOT_RECORDED_FIELDS[key] ?? key
}

export type ReviewStatus = "pending" | "accepted" | "rejected" | "changes_requested" | "edited"
export type ReviewDecision = "accept" | "reject" | "request_changes" | "edited"

const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: "Chưa duyệt",
  accepted: "Đã chấp nhận",
  rejected: "Đã từ chối",
  changes_requested: "Yêu cầu chỉnh sửa",
  edited: "Đã sửa tay, chờ duyệt lại",
}

/** review_status NULL = "pending" (đúng như máy trạng thái ở backend). Giá trị lạ hiện nguyên văn. */
export function reviewStatusLabel(status: string | null | undefined): string {
  if (status === null || status === undefined || status === "") return REVIEW_STATUS_LABELS.pending
  return REVIEW_STATUS_LABELS[status as ReviewStatus] ?? status
}

/** Trạng thái trước/sau trong lịch sử: thiếu (bản ghi cũ) -> "chưa được ghi nhận", không suy diễn. */
export function historyStatusLabel(status: string | null | undefined): string {
  return status ? reviewStatusLabel(status) : NOT_RECORDED
}

const DECISION_LABELS: Record<ReviewDecision, string> = {
  accept: "Chấp nhận",
  reject: "Từ chối",
  request_changes: "Yêu cầu chỉnh sửa",
  edited: "Lưu bản sửa tay",
}

export function decisionLabel(decision: string | null | undefined): string {
  return decision ? (DECISION_LABELS[decision as ReviewDecision] ?? decision) : NOT_RECORDED
}

/** Nhãn cho bản sửa tay (backend đặt needs_rereview=true, jev_score=null). */
export const EDITED_NOTE = "Bản sửa tay: chờ duyệt lại, không có điểm JEV của bản gốc"
