import { SearchX } from "lucide-react"
import { Link } from "react-router-dom"
import { EmptyState, stateButtonClass } from "@/components/states"

/** 404: không tồn tại hoặc không thuộc coach đều hiện cùng một màn, không nêu lý do. */
export function ReportNotFound() {
  return (
    <EmptyState
      icon={SearchX}
      headingLevel={1}
      title="Không tìm thấy báo cáo"
      description="Báo cáo này không tồn tại hoặc bạn không mở được. Hãy mở lại từ Lịch sử."
      action={
        <Link to="/history" className={stateButtonClass}>
          Về Lịch sử
        </Link>
      }
    />
  )
}
