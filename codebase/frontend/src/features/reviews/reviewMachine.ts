import type { ReviewDecision, ReviewStatus } from "@/features/reports/labels"

/**
 * Máy trạng thái duyệt. PHẢI khớp REVIEW_TRANSITIONS trong codebase/backend/api/run_repository.py
 * (và hàm SQL review_recommendation). Backend vẫn kiểm lại: UI chỉ ẩn các quyết định chắc chắn bị từ chối.
 * review_status NULL coi như "pending".
 */
export const REVIEW_TRANSITIONS: Record<ReviewStatus, readonly ReviewDecision[]> = {
  pending: ["accept", "reject", "request_changes"],
  accepted: ["reject", "request_changes"],
  rejected: ["accept", "request_changes"],
  changes_requested: ["edited", "reject"],
  edited: ["accept", "reject", "request_changes", "edited"],
}

export function isReviewStatus(value: string): value is ReviewStatus {
  return Object.prototype.hasOwnProperty.call(REVIEW_TRANSITIONS, value)
}

/** Quyết định hợp lệ ở trạng thái hiện tại. Trạng thái lạ -> [] (không đoán). */
export function allowedDecisions(status: string | null | undefined): readonly ReviewDecision[] {
  const current = status === null || status === undefined || status === "" ? "pending" : status
  return isReviewStatus(current) ? REVIEW_TRANSITIONS[current] : []
}

export const MAX_COMMENT = 2000
export const MAX_CONTENT = 4000
