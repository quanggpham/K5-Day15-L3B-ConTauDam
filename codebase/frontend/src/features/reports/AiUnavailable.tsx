import { Sparkles } from "lucide-react"
import type { ReactNode } from "react"
import { EmptyState } from "@/components/states"
import { aiStatusLabel } from "@/features/history/labels"

export type AiContext = "recommendations" | "evaluation" | "evidence"

const TITLES: Record<AiContext, string> = {
  recommendations: "Chưa có đề xuất cho báo cáo này",
  evaluation: "Chưa có đánh giá AI cho báo cáo này",
  evidence: "Chưa có căn cứ bài giảng cho đề xuất",
}

function statusSentence(aiStatus: string | null): string {
  switch (aiStatus) {
    case "not_enabled":
      return "Đề xuất AI chưa được bật cho báo cáo này."
    case "blocked":
      return "Đề xuất AI đang bị chặn cho báo cáo này."
    case "failed":
      return "Lần tạo đề xuất AI của báo cáo này đã lỗi."
    case "ready":
      return "AI ở trạng thái sẵn sàng nhưng báo cáo chưa lưu đề xuất nào."
    default:
      return `Trạng thái AI của báo cáo này ${aiStatusLabel(null)}.`
  }
}

interface Props {
  context: AiContext
  aiStatus: string | null
  aiStatusReason: string | null
  action?: ReactNode
}

/**
 * Giải thích vì sao chưa có đề xuất/đánh giá/căn cứ. Lý do lấy từ trạng thái đã lưu của báo cáo (không suy diễn);
 * phần "điều kiện bật" là quy tắc cố định của sản phẩm. Báo cáo chỉ-có-số-liệu vẫn dùng được.
 */
export function AiUnavailable({ context, aiStatus, aiStatusReason, action }: Props) {
  const parts = [statusSentence(aiStatus)]
  if (aiStatusReason) parts.push(`Lý do hệ thống ghi nhận: ${aiStatusReason}`)
  parts.push(
    "Điều kiện để bật AI: có Lesson KB được phép và đã hiệu chuẩn JEV. Báo cáo số liệu vẫn đầy đủ: xem Tổng quan và Lỗ hổng, tải CSV, hoặc dùng Copilot để giải thích ưu tiên và so sánh bài trước.",
  )
  return (
    <EmptyState
      icon={Sparkles}
      headingLevel={2}
      title={TITLES[context]}
      description={parts.join(" ")}
      action={action}
      className="rounded-2xl border border-dashed border-violet-300 bg-white/70"
    />
  )
}
