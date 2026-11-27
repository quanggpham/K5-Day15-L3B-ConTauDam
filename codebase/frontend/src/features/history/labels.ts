import { NOT_RECORDED } from "@/lib/format"

/** Giá trị `status` của analysis_runs đã biết ở backend/migration; giá trị lạ hiện nguyên văn. */
export const RUN_STATUS_OPTIONS = [
  { value: "draft", label: "Bản nháp" },
  { value: "pending", label: "Chờ xử lý (nháp cũ)" },
]

const AI_LABELS: Record<string, string> = {
  not_enabled: "AI chưa bật",
  blocked: "AI bị chặn",
  ready: "AI sẵn sàng",
  failed: "AI lỗi",
}

export function runStatusLabel(status: string | null): string {
  if (!status) return NOT_RECORDED
  return RUN_STATUS_OPTIONS.find((o) => o.value === status)?.label ?? status
}

export function aiStatusLabel(aiStatus: string | null): string {
  if (!aiStatus) return NOT_RECORDED
  return AI_LABELS[aiStatus] ?? aiStatus
}
