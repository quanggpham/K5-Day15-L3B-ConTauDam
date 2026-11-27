import { Sparkles } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { EmptyState } from "@/components/states"

/** Panel Copilot mặc định (placeholder). Route báo cáo thay bằng `handle.copilot`. */
export function CopilotPanel() {
  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-violet-950">Copilot</h2>
        <Badge variant="secondary" className="bg-violet-100 text-violet-900">
          Sắp có
        </Badge>
      </div>
      <EmptyState
        icon={Sparkles}
        headingLevel={3}
        title="Chưa có báo cáo đang mở"
        description="Copilot sẽ trả lời dựa trên báo cáo đã lưu khi bạn mở một báo cáo. Hiện chưa có gì để hiển thị."
      />
    </div>
  )
}
