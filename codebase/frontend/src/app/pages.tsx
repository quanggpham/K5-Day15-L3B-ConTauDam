import { Link, isRouteErrorResponse, useParams, useRouteError } from "react-router-dom"
import { ComingSoon } from "@/components/ComingSoon"
import { EmptyState, ErrorState, stateButtonClass } from "@/components/states"

export function DashboardPage() {
  return <ComingSoon title="Dashboard" description="Tổng quan theo bài học sẽ hiển thị số liệu thật từ backend khi hoàn thiện." />
}

export function NewAnalysisPage() {
  return <ComingSoon title="Tạo phân tích" description="Chọn bài học và tạo bản nháp phân tích sẽ có ở bước tiếp theo." />
}

export function HistoryPage() {
  return <ComingSoon title="Lịch sử" description="Danh sách báo cáo đã lưu của bạn sẽ hiển thị ở đây khi hoàn thiện." />
}

export function ReportPage() {
  const { runId } = useParams()
  return (
    <ComingSoon
      title="Báo cáo"
      detail={runId ? `Mã báo cáo: ${runId}` : undefined}
      description="Nội dung báo cáo sẽ được đọc từ snapshot đã lưu khi màn hình này hoàn thiện."
    />
  )
}

export function ReportReviewPage() {
  const { runId } = useParams()
  return (
    <ComingSoon
      title="Duyệt báo cáo"
      detail={runId ? `Mã báo cáo: ${runId}` : undefined}
      description="Duyệt từng đề xuất và xem lịch sử duyệt sẽ có khi màn hình này hoàn thiện."
    />
  )
}

export function NotFoundPage() {
  return (
    <EmptyState
      fullPage
      headingLevel={1}
      title="Không tìm thấy trang"
      description="Đường dẫn này không tồn tại."
      action={
        <Link to="/" className={stateButtonClass}>
          Về trang chủ
        </Link>
      }
    />
  )
}

/** Lỗi không bắt được trong route: không lộ stack trace. */
export function RouteErrorPage() {
  const error = useRouteError()
  if (isRouteErrorResponse(error) && error.status === 404) return <NotFoundPage />
  return (
    <ErrorState
      fullPage
      title="Ứng dụng gặp lỗi"
      message="Có lỗi ngoài dự kiến khi hiển thị trang này. Hãy tải lại trang."
      onRetry={() => window.location.reload()}
      retryLabel="Tải lại trang"
    />
  )
}
