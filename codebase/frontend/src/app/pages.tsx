import { Link, isRouteErrorResponse, useRouteError } from "react-router-dom"
import { EmptyState, ErrorState, stateButtonClass } from "@/components/states"

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
